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
import signal
import sys
from typing import Optional
import redis.asyncio as redis
from .config.settings import Settings
from .config.constants import QUEUE_KEY, TASK_SET_KEY
from .database.neo4j_manager import Neo4jManager
from .database.mysql_manager import MySQLManager
from .queue.priority_queue import RedisPriorityQueue
from .scrapers.snapshot_scanner import SnapshotScanner
from .scrapers.api_worker import APIWorker
from .utils.logger import Logger
from .utils.rate_limiter import RateLimiter

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

        # 清空旧队列
        await self.redis_client.delete(QUEUE_KEY)
        await self.redis_client.delete(TASK_SET_KEY)

        # 初始化优先级队列
        self.priority_queue = RedisPriorityQueue(self.redis_client)

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

        # 初始化快照扫描器
        self.snapshot_scanner = SnapshotScanner(
            redis_queue=self.priority_queue,
            neo4j_manager=self.neo4j_manager,
            api_config=self.config.api
        )

        # 初始化API工作者
        self.api_worker = APIWorker(
            redis_queue=self.priority_queue,
            neo4j_manager=self.neo4j_manager,
            mysql_manager=self.mysql_manager,
            api_config=self.config.api,
            rate_limiter=self.rate_limiter
        )

        logger.info("Neo4j爬虫应用初始化完成")

    async def start(self) -> None:
        """启动应用"""
        logger.info("正在启动Neo4j爬虫应用...")
        self.running = True

        # 注册信号处理
        self._setup_signal_handlers()

        # 启动快照扫描器和API工作者
        tasks = [
            asyncio.create_task(self.snapshot_scanner.start()),
            asyncio.create_task(self.api_worker.start())
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("收到取消信号，正在关闭应用...")
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


async def main() -> None:
    """主函数"""
    # 设置日志
    Logger.setup('neo4j_scraper', level=logging.INFO)

    # 加载配置
    config = Settings.load()

    # 创建并启动应用
    app = Neo4jScraperApp(config)
    await app.initialize()
    await app.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        sys.exit(0)
