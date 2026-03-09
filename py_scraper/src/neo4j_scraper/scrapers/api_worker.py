"""
API工作者

负责从优先级队列中获取节点ID，并执行以下操作：
1. 调用AllStarLink API获取节点详情
2. 解析节点数据
3. 更新Neo4j数据库
4. 更新MySQL数据库
"""

import logging
import aiohttp
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from ..queue.priority_queue import RedisPriorityQueue
from ..database.neo4j_manager import Neo4jManager
from ..database.mysql_manager import MySQLManager
from ..utils.rate_limiter import RateLimiter
from ..scrapers.node_parser import NodeParser
from ..config.settings import APIConfig

logger = logging.getLogger(__name__)


class APIWorker:
    """API工作者

    职责：
    - 从Redis队列获取任务
    - 遵守速率限制
    - 获取节点详细数据
    - 更新Neo4j和MySQL数据库
    - 错误处理和重试
    """

    def __init__(self, redis_queue: RedisPriorityQueue,
                 neo4j_manager: Neo4jManager,
                 mysql_manager: MySQLManager,
                 api_config: APIConfig,
                 rate_limiter: RateLimiter) -> None:
        """初始化API工作者

        Args:
            redis_queue: Redis优先级队列实例
            neo4j_manager: Neo4j数据库管理器
            mysql_manager: MySQL数据库管理器
            api_config: API配置
            rate_limiter: 速率限制器
        """
        self.redis_queue: RedisPriorityQueue = redis_queue
        self.neo4j_manager: Neo4jManager = neo4j_manager
        self.mysql_manager: MySQLManager = mysql_manager
        self.api_config: APIConfig = api_config
        self.rate_limiter: RateLimiter = rate_limiter
        self.session: Optional[aiohttp.ClientSession] = None
        self.parser: NodeParser = NodeParser()

    async def start(self) -> None:
        """启动API工作者

        持续从队列中获取任务并处理
        """
        logger.info("API工作者启动")
        while True:
            try:
                await self.process_queue()
                # 短暂休眠后继续处理队列
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"API工作者运行异常: {e}")
                await asyncio.sleep(10)  # 出错后等待10秒再重试

    async def process_queue(self) -> None:
        """处理优先级队列中的任务

        执行流程：
        1. 检查速率限制
        2. 从队列获取节点ID
        3. 获取节点数据
        4. 更新数据库
        """
        # 检查速率限制
        if not await self.rate_limiter.can_make_request():
            logger.debug("API工作者: 达到速率限制，等待...")
            await asyncio.sleep(1)
            return

        # 从队列中获取任务
        node_id = await self.redis_queue.dequeue()
        if not node_id:
            return

        logger.info(f"API工作者: 开始处理节点 {node_id}")
        try:
            # 获取节点详细数据
            logger.info(f"API工作者: 正在获取节点 {node_id} 的详细数据...")
            node_data = await self._fetch_node_data(node_id)
            if node_data:
                logger.info(f"API工作者: 成功获取节点 {node_id} 的数据，开始解析和更新数据库...")
                # 更新数据库
                await self._update_databases(node_data)
                logger.info(f"API工作者: 成功处理节点 {node_id}")
            else:
                logger.warning(f"API工作者: 未能获取节点 {node_id} 的数据，跳过处理")
        except Exception as e:
            logger.error(f"API工作者: 处理节点 {node_id} 失败 - {e}", exc_info=True)

    async def _fetch_node_data(self, node_id: int) -> Optional[Dict]:
        """获取节点详细数据

        Args:
            node_id: 节点ID

        Returns:
            Optional[Dict]: 节点数据，失败返回None
        """
        url = f"{self.api_config.base_url}/{node_id}"
        logger.debug(f"请求URL: {url}")

        # 创建HTTP会话
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.debug("创建新的HTTP会话")

        # 带重试机制的请求
        for attempt in range(self.api_config.max_retries):
            try:
                logger.debug(f"尝试获取节点 {node_id} 数据 (第 {attempt + 1}/{self.api_config.max_retries} 次)")
                async with self.session.get(url) as response:
                    # 检查是否触发速率限制
                    if response.status == 429:
                        logger.warning(f"触发速率限制，冷却 {self.api_config.cooldown_429} 秒")
                        await asyncio.sleep(self.api_config.cooldown_429)
                        continue

                    if response.status != 200:
                        logger.warning(f"获取节点 {node_id} 数据失败，状态码: {response.status}")
                        return None

                    data = await response.json()
                    logger.debug(f"成功获取节点 {node_id} 的原始数据")
                    return data

            except Exception as e:
                logger.error(f"获取节点 {node_id} 数据异常 (尝试 {attempt + 1}/{self.api_config.max_retries}): {e}", exc_info=True)
                if attempt < self.api_config.max_retries - 1:
                    # 指数退避
                    backoff_time = self.api_config.retry_backoff ** (attempt + 1)
                    logger.debug(f"等待 {backoff_time} 秒后重试...")
                    await asyncio.sleep(backoff_time)

        logger.error(f"获取节点 {node_id} 数据失败，已达到最大重试次数")
        return None

    async def _update_databases(self, data: Dict) -> None:
        """更新Neo4j和MySQL数据库

        Args:
            data: API返回的节点数据
        """
        try:
            logger.debug("API工作者: 开始解析和更新数据库...")
            # 解析主节点数据
            node = self.parser.parse_node(data)
            if not node:
                logger.warning("API工作者: 节点数据解析失败，跳过更新")
                return

            logger.debug(f"API工作者: 成功解析主节点数据 - ID:{node.node_id}, 类型:{node.node_type}, 呼号:{node.callsign}")
            # 更新Neo4j
            await self.neo4j_manager.update_node(node)
            logger.debug(f"API工作者: 已更新节点 {node.node_id} 的Neo4j数据")

            # 解析连接节点
            stats = data.get('stats', {})
            node_data = stats.get('data', {})
            linked_nodes = node_data.get('linkedNodes', [])
            connection_modes = node_data.get('nodes', '')

            logger.info(f"API工作者: 发现 {len(linked_nodes)} 个连接节点")
            # 解析连接关系
            connections = self.parser.parse_connections(
                node.node_id,
                connection_modes,
                linked_nodes
            )

            # 更新拓扑关系
            if connections:
                await self.neo4j_manager.update_topology(
                    node.node_id,
                    connections
                )
                logger.debug(f"API工作者: 已更新节点 {node.node_id} 的 {len(connections)} 个连接关系")

            # 更新linkedNodes中的节点数据到Neo4j
            for linked_node in linked_nodes:
                linked_node_obj = self.parser.parse_linked_node(linked_node)
                if linked_node_obj:
                    await self.neo4j_manager.update_node(linked_node_obj)
                    logger.debug(f"API工作者: 已更新连接节点 {linked_node_obj.node_id} 的Neo4j数据")

            # 更新MySQL（只更新AllStarLink节点）
            if node.source == 'allstarlink':
                logger.debug(f"API工作者: 开始更新节点 {node.node_id} 的MySQL数据...")
                await self.mysql_manager.upsert_node(node)
                logger.debug(f"API工作者: 已更新节点 {node.node_id} 的MySQL数据")

                # 更新linkedNodes中的节点数据到MySQL
                mysql_update_count = 0
                for linked_node in linked_nodes:
                    linked_node_id = linked_node.get('name')
                    if linked_node_id and isinstance(linked_node_id, (int, str)):
                        # 只处理整数类型的节点ID
                        if isinstance(linked_node_id, int):
                            linked_node_int = linked_node_id
                        elif isinstance(linked_node_id, str) and linked_node_id.isdigit():
                            linked_node_int = int(linked_node_id)
                        else:
                            continue

                        linked_node_obj = self.parser.parse_linked_node(linked_node)
                        if linked_node_obj and linked_node_obj.source == 'allstarlink':
                            await self.mysql_manager.upsert_node(linked_node_obj)
                            mysql_update_count += 1

                if mysql_update_count > 0:
                    logger.info(f"API工作者: 已更新 {mysql_update_count} 个连接节点到MySQL")

            logger.debug("API工作者: 数据库更新完成")
        except Exception as e:
            logger.error(f"API工作者: 更新数据库失败 - {e}", exc_info=True)
            raise
