"""
Neo4j拓扑爬虫主程序

负责初始化和启动整个爬虫系统：
1. 加载配置
2. 初始化数据库连接
3. 创建Redis队列
4. 启动快照扫描器和API工作者
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional
import redis.asyncio as redis
import argparse

if __name__ == '__main__':
    # 在Docker环境中，/app是工作目录，包含link_scraper包
    # 在本地开发环境中，需要添加src目录到路径
    if os.path.exists('/app/link_scraper'):
        # Docker环境
        pass
    else:
        # 本地开发环境
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

    from link_scraper.config.settings import Settings
    from link_scraper.config.constants import QUEUE_KEY, TASK_SET_KEY
    from link_scraper.database.neo4j_manager import Neo4jManager
    from link_scraper.database.mysql_manager import MySQLManager
    from link_scraper.task_queue.priority_queue import RedisPriorityQueue
    from link_scraper.scrapers.snapshot_scanner import SnapshotScanner
    from link_scraper.scrapers.api_worker import APIWorker
    from link_scraper.utils.logger import Logger
    from link_scraper.utils.rate_limiter import RateLimiter
    from link_scraper.utils.batch_manager import BatchManager
else:
    # 当作为模块导入时，使用绝对导入
    import sys
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from link_scraper.config.settings import Settings
    from link_scraper.config.constants import QUEUE_KEY, TASK_SET_KEY
    from link_scraper.database.neo4j_manager import Neo4jManager
    from link_scraper.database.mysql_manager import MySQLManager
    from link_scraper.task_queue.priority_queue import RedisPriorityQueue
    from link_scraper.scrapers.snapshot_scanner import SnapshotScanner
    from link_scraper.scrapers.api_worker import APIWorker
    from link_scraper.utils.logger import Logger
    from link_scraper.utils.rate_limiter import RateLimiter
    from link_scraper.utils.batch_manager import BatchManager

logger = logging.getLogger(__name__)


class Neo4jScraperApp:
    """Neo4j爬虫应用主类

    职责：
    - 初始化所有组件
    - 管理应用生命周期
    - 处理优雅关闭
    """

    def __init__(self, config: Settings) -> None:
        """初始化应用

        Args:
            config: 应用配置
        """
        self.config: Settings = config
        self.redis_client: Optional[redis.Redis] = None
        self.neo4j_manager: Optional[Neo4jManager] = None
        self.mysql_manager: Optional[MySQLManager] = None
        self.priority_queue: Optional[RedisPriorityQueue] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.snapshot_scanner: Optional[SnapshotScanner] = None
        self.api_worker: Optional[APIWorker] = None
        self.running: bool = False

    async def initialize(self) -> None:
        """初始化所有组件"""
        logger.info("正在初始化Neo4j爬虫应用...")

        # 初始化Redis客户端
        self.redis_client = redis.Redis(
            host=self.config.redis.host,
            port=self.config.redis.port,
            password=self.config.redis.password,
            db=self.config.redis.db,
            decode_responses=True
        )

        # 初始化优先级队列
        self.priority_queue = RedisPriorityQueue(self.redis_client)

        # 检查队列是否为空
        queue_size = await self.priority_queue.get_size()
        if queue_size > 0:
            logger.info(f"Redis队列中有 {queue_size} 个未处理任务，将继续处理这些任务")
        else:
            logger.info("Redis队列为空，将清空旧数据并重新爬取")
            await self.priority_queue.clear()

        # 初始化Neo4j管理器
        self.neo4j_manager = Neo4jManager(
            uri=self.config.neo4j.uri,
            user=self.config.neo4j.user,
            password=self.config.neo4j.password
        )
        await self.neo4j_manager.connect()
        await self.neo4j_manager.initialize()

        # 初始化MySQL管理器
        self.mysql_manager = MySQLManager(
            host=self.config.mysql.host,
            user=self.config.mysql.user,
            password=self.config.mysql.password,
            database=self.config.mysql.database,
            charset=self.config.mysql.charset
        )
        await self.mysql_manager.connect()
        await self.mysql_manager.initialize()

        # 初始化速率限制器
        self.rate_limiter = RateLimiter(
            max_requests=self.config.api.rate_limit,
            time_window=self.config.api.rate_limit_window
        )

        # 初始化批次管理器
        self.batch_manager = BatchManager(self.redis_client)
        # 初始化批次号
        current_batch_no = await self.batch_manager.initialize_batch_no(self.mysql_manager)
        logger.info(f"初始化批次号: {current_batch_no}")

        # 初始化快照扫描器
        self.snapshot_scanner = SnapshotScanner(
            redis_queue=self.priority_queue,
            neo4j_manager=self.neo4j_manager,
            mysql_manager=self.mysql_manager,
            api_config=self.config.api,
            batch_manager=self.batch_manager
        )

        # 初始化API工作者
        self.api_worker = APIWorker(
            redis_queue=self.priority_queue,
            neo4j_manager=self.neo4j_manager,
            mysql_manager=self.mysql_manager,
            api_config=self.config.api,
            rate_limiter=self.rate_limiter
        )
        # 设置初始批次号到APIWorker
        if current_batch_no:
            self.api_worker.set_batch_no(current_batch_no)
            logger.info(f"已设置初始批次号 {current_batch_no} 到APIWorker")

        logger.info("Neo4j爬虫应用初始化完成")

    async def start(self) -> None:
        """启动应用"""
        logger.info("正在启动Neo4j爬虫应用...")
        self.running = True

        # 注册信号处理
        self._setup_signal_handlers()

        # 启动API工作者
        api_worker_task = asyncio.create_task(self.api_worker.start())

        try:
            # 主循环：监控队列状态，触发快照扫描
            while self.running:
                # 检查队列是否为空
                queue_size = await self.priority_queue.get_size()

                if queue_size == 0:
                    logger.info("队列已处理完成，清空任务集合...")
                    # 清空任务集合
                    await self.priority_queue.clear()

                    logger.info("触发新一轮节点列表扫描...")
                    # 触发一次快照扫描
                    await self.snapshot_scanner.scan_and_update()
                    # 获取当前批次号并设置到APIWorker
                    current_batch_no = self.snapshot_scanner.get_current_batch_no()
                    if current_batch_no:
                        self.api_worker.set_batch_no(current_batch_no)
                        logger.info(f"已设置批次号 {current_batch_no} 到APIWorker")
                    else:
                        logger.warning("未能获取批次号，APIWorker将使用None作为批次号")

                    # 等待半小时再检查
                    await asyncio.sleep(1800)
                else:
                    logger.debug(f"队列中还有 {queue_size} 个任务待处理...")
                    # 等待一段时间再检查
                    await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info("收到取消信号，正在关闭应用...")
            api_worker_task.cancel()
        except Exception as e:
            logger.error(f"应用运行异常: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """关闭应用"""
        logger.info("正在关闭Neo4j爬虫应用...")
        self.running = False

        # 关闭Redis连接
        if self.redis_client:
            await self.redis_client.close()

        # 关闭Neo4j连接
        if self.neo4j_manager:
            await self.neo4j_manager.close()

        # 关闭MySQL连接
        if self.mysql_manager:
            await self.mysql_manager.close()

        logger.info("Neo4j爬虫应用已关闭")

    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备关闭应用...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main(rate_limit: int = None, delay_max: float = None, 
              delay_min: float = None, cooldown: int = None) -> None:
    """主函数
    
    Args:
        rate_limit: 爬取速率（每分钟请求数）
        delay_max: 爬取最大间隔（秒）
        delay_min: 爬取最小间隔（秒）
        cooldown: 限速时冷却时间（秒）
    """
    # 从环境变量读取日志级别，默认为INFO
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # 设置根logger，确保所有模块的日志都能显示
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 为根logger添加处理器（如果还没有的话）
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    # 设置应用日志（不添加额外的handler，避免重复）
    app_logger = logging.getLogger('link_scraper')
    app_logger.setLevel(log_level)
    # 不添加handler，让它继承根logger的handler

    # 加载配置
    config = Settings.load()

    # 使用参数覆盖配置
    if rate_limit is not None:
        config.api.rate_limit = rate_limit
        app_logger.info(f'使用参数覆盖爬取速率: {rate_limit}')
    if delay_max is not None:
        config.api.request_delay_max = delay_max
        app_logger.info(f'使用参数覆盖最大间隔: {delay_max}')
    if delay_min is not None:
        config.api.request_delay_min = delay_min
        app_logger.info(f'使用参数覆盖最小间隔: {delay_min}')
    if cooldown is not None:
        config.api.cooldown_429 = cooldown
        app_logger.info(f'使用参数覆盖冷却时间: {cooldown}')

    # 创建并启动应用
    app = Neo4jScraperApp(config)
    await app.initialize()
    await app.start()


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Neo4j拓扑爬虫')
    parser.add_argument('rate_limit', type=int, nargs='?', default=None,
                       help='爬取速率（每分钟请求数）')
    parser.add_argument('delay_max', type=float, nargs='?', default=None,
                       help='爬取最大间隔（秒）')
    parser.add_argument('delay_min', type=float, nargs='?', default=None,
                       help='爬取最小间隔（秒）')
    parser.add_argument('cooldown', type=int, nargs='?', default=None,
                       help='限速时冷却时间（秒）')
    args = parser.parse_args()
    
    try:
        asyncio.run(main(
            rate_limit=args.rate_limit,
            delay_max=args.delay_max,
            delay_min=args.delay_min,
            cooldown=args.cooldown
        ))
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        sys.exit(0)
