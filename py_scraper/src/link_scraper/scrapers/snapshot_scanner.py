"""
快照扫描器

负责定期扫描AllStarLink在线节点列表，并执行以下操作：
1. 获取在线节点列表及其连接数
2. 根据连接数计算优先级
3. 将节点加入优先级队列
4. 清理已下线的节点
"""

import logging
import asyncio
import aiohttp
import re
from typing import List, Dict, Optional
from ..task_queue.priority_queue import RedisPriorityQueue
from ..database.neo4j_manager import Neo4jManager
from ..database.mysql_manager import MySQLManager
from ..config.settings import APIConfig
from ..config.constants import (
    NODE_RANK_HUB,
    NODE_RANK_REPEATER,
    NODE_RANK_UNKNOWN
)
from ..utils.batch_manager import BatchManager

logger = logging.getLogger(__name__)


class SnapshotScanner:
    """快照扫描器

    职责：
    - 定期扫描节点列表API
    - 解析节点数据
    - 计算节点优先级
    - 更新Redis队列
    - 清理离线节点
    """

    def __init__(self, redis_queue: RedisPriorityQueue,
                 neo4j_manager: Neo4jManager,
                 mysql_manager: MySQLManager,
                 api_config: APIConfig,
                 batch_manager: BatchManager) -> None:
        """初始化快照扫描器

        Args:
            redis_queue: Redis优先级队列实例
            neo4j_manager: Neo4j数据库管理器
            mysql_manager: MySQL数据库管理器
            api_config: API配置
            batch_manager: 批次管理器
        """
        self.redis_queue: RedisPriorityQueue = redis_queue
        self.neo4j_manager: Neo4jManager = neo4j_manager
        self.mysql_manager: MySQLManager = mysql_manager
        self.api_config: APIConfig = api_config
        self.batch_manager: BatchManager = batch_manager
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_batch_no: Optional[str] = None

    async def start(self) -> None:
        """启动快照扫描器

        每1小时执行一次扫描
        """
        logger.info("快照扫描器启动")
        while True:
            try:
                await self.scan_and_update()
                # 每1小时运行一次
                await aiohttp.ClientSession().close()
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"快照扫描器运行异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试

    async def scan_and_update(self) -> None:
        """扫描节点列表并更新优先级队列

        执行流程：
        1. 生成新的批次号
        2. 创建HTTP会话
        3. 获取节点列表
        4. 解析节点数据
        5. 更新优先级队列
        6. 清理离线节点
        """
        # 生成新的批次号
        self.current_batch_no = await self.batch_manager.get_or_create_batch_no(self.mysql_manager)
        logger.info(f"开始扫描节点列表... 当前批次号: {self.current_batch_no}")

        try:
            # 创建HTTP会话
            if not self.session:
                self.session = aiohttp.ClientSession()

            # 获取节点列表
            async with self.session.post(self.api_config.node_list_url) as response:
                if response.status != 200:
                    logger.error(f"获取节点列表失败，状态码: {response.status}")
                    return

                json_data = await response.json()

                # 解析节点列表
                nodes = self._parse_node_list_json(json_data)
                logger.info(f"扫描到 {len(nodes)} 个在线节点")

                # 更新优先级队列
                await self._update_priority_queue(nodes)

                # 清理离线节点
                await self._cleanup_offline_nodes(nodes)

        except Exception as e:
            logger.error(f"扫描节点列表异常: {e}")
        finally:
            if self.session:
                await self.session.close()
                self.session = None

    def _parse_node_list_json(self, json_data: Dict) -> List[Dict]:
        """解析节点列表JSON数据

        Args:
            json_data: API返回的JSON数据

        Returns:
            List[Dict]: 节点列表，每个节点包含node_id和link_count
        """
        nodes = []
        try:
            data = json_data.get('data', [])
            for row in data:
                if not isinstance(row, list) or len(row) == 0:
                    continue

                # 第一列包含节点ID的HTML链接
                node_id_str = row[0] if isinstance(row[0], str) else ''
                # 提取节点ID（从HTML链接中提取）
                match = re.search(r'/stats/(\d+)', node_id_str)
                if match:
                    node_id_str = match.group(1)
                else:
                    # 如果没有找到链接，尝试直接提取数字
                    node_id_str = node_id_str.split()[0]  # 取第一部分作为节点ID

                if node_id_str.isdigit():
                    # 提取连接数（最后一列）
                    link_count = 0
                    if len(row) > 0:
                        try:
                            last_col = row[-1]  # 最后一列
                            link_count = int(last_col) if last_col and str(last_col).isdigit() else 0
                        except (ValueError, TypeError):
                            link_count = 0

                    nodes.append({
                        'node_id': int(node_id_str),
                        'link_count': link_count
                    })
        except Exception as e:
            logger.error(f"解析节点列表JSON失败: {e}")

        logger.info(f"从DataTables JSON数据中解析出 {len(nodes)} 个节点")
        return nodes

    async def _update_priority_queue(self, nodes: List[Dict]) -> None:
        """更新优先级队列

        根据节点的连接数分配优先级：
        Args:
            nodes: 节点列表
        """
        for node in nodes:
            node_id = node['node_id']
            link_count = node['link_count']

            # 只处理连接数大于0的节点
            if link_count <= 0:
                continue

            # 直接使用连接数作为优先级分数
            priority = link_count

            # 检查节点是否已在队列中
            if not await self.redis_queue.contains(node_id):
                # 将节点加入优先级队列
                await self.redis_queue.enqueue(node_id, priority)
                logger.debug(f"快照扫描: 节点 {node_id} 已加入队列，优先级分数: {priority} (连接数: {link_count})")

    def get_current_batch_no(self) -> Optional[str]:
        """获取当前批次号

        Returns:
            当前批次号
        """
        return self.current_batch_no

    async def _cleanup_offline_nodes(self, online_nodes: List[Dict]) -> None:
        """清理离线节点

        Args:
            online_nodes: 当前在线的节点列表
        """
        # 获取在线节点ID集合
        online_node_ids = {node['node_id'] for node in online_nodes}

        # 从Neo4j获取所有活跃节点
        async with self.neo4j_manager.driver.session() as session:
            result = await session.run("""
            MATCH (n:Node {active: true})
            RETURN n.node_id AS node_id
            """)

            offline_count = 0
            # 检查每个活跃节点是否仍然在线
            async for record in result:
                node_id = record['node_id']
                if node_id not in online_node_ids:
                    # 节点已离线，设置为不活跃
                    await self.neo4j_manager.set_node_inactive(node_id)
                    # 从优先级队列中移除
                    await self.redis_queue.remove(node_id)
                    offline_count += 1

            if offline_count > 0:
                logger.info(f"快照扫描: 已清理 {offline_count} 个离线节点")
