"""
快照扫描器

负责定期扫描 AllStarLink 在线节点列表，并执行以下操作：
1. 获取在线节点列表及其连接数
2. 根据连接数计算优先级
3. 将节点加入优先级队列
"""

import logging
import asyncio
import aiohttp
import re
from typing import List, Dict, Optional

from ..task_queue.priority_queue import RedisPriorityQueue
from ..database.mysql_manager import MySQLManager
from ..config.settings import APIConfig
from ..utils.batch_manager import BatchManager

logger = logging.getLogger(__name__)


class SnapshotScanner:
    """快照扫描器"""

    def __init__(
        self,
        redis_queue: RedisPriorityQueue,
        mysql_manager: MySQLManager,
        api_config: APIConfig,
        batch_manager: BatchManager
    ) -> None:
        self.redis_queue: RedisPriorityQueue = redis_queue
        self.mysql_manager: MySQLManager = mysql_manager
        self.api_config: APIConfig = api_config
        self.batch_manager: BatchManager = batch_manager
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_batch_no: Optional[str] = None

    async def start(self) -> None:
        """启动快照扫描器"""
        logger.info("快照扫描器启动")
        while True:
            try:
                await self.scan_and_update()
                await aiohttp.ClientSession().close()
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"快照扫描器运行异常: {e}")
                await asyncio.sleep(60)

    async def scan_and_update(self) -> None:
        """扫描节点列表并更新优先级队列"""
        self.current_batch_no = await self.batch_manager.get_or_create_batch_no(self.mysql_manager)
        logger.info(f"开始扫描节点列表，当前批次号: {self.current_batch_no}")

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.post(self.api_config.node_list_url) as response:
                if response.status != 200:
                    logger.error(f"获取节点列表失败，状态码: {response.status}")
                    return

                json_data = await response.json()
                nodes = self._parse_node_list_json(json_data)
                logger.info(f"扫描到 {len(nodes)} 个在线节点")

                await self._batch_update_mysql(nodes)
                await self._batch_enqueue_to_redis(nodes)

        except Exception as e:
            logger.error(f"扫描节点列表异常: {e}")
        finally:
            if self.session:
                await self.session.close()
                self.session = None

    def _parse_node_list_json(self, json_data: Dict) -> List[Dict]:
        """解析节点列表 JSON 数据"""
        nodes = []
        try:
            data = json_data.get('data', [])
            for row in data:
                if not isinstance(row, list) or len(row) == 0:
                    continue

                node_id_str = row[0] if isinstance(row[0], str) else ''
                match = re.search(r'/stats/(\d+)', node_id_str)
                if match:
                    node_id_str = match.group(1)
                else:
                    node_id_str = node_id_str.split()[0]

                if node_id_str.isdigit():
                    link_count = 0
                    if len(row) > 0:
                        try:
                            last_col = row[-1]
                            link_count = int(last_col) if last_col and str(last_col).isdigit() else 0
                        except (ValueError, TypeError):
                            link_count = 0

                    nodes.append({
                        'node_id': int(node_id_str),
                        'link_count': link_count
                    })
        except Exception as e:
            logger.error(f"解析节点列表 JSON 失败: {e}")

        logger.info(f"从 DataTables JSON 数据中解析出 {len(nodes)} 个节点")
        return nodes

    async def _update_priority_queue(self, nodes: List[Dict]) -> None:
        """更新优先级队列"""
        for node in nodes:
            node_id = node['node_id']
            link_count = node['link_count']

            if link_count <= 0:
                continue

            priority = link_count

            if not await self.redis_queue.contains(node_id):
                await self.redis_queue.enqueue(node_id, priority)
                logger.debug(
                    f"快照扫描: 节点 {node_id} 已加入队列，优先级分数: {priority} (连接数: {link_count})"
                )

    async def _batch_update_mysql(self, nodes: List[Dict]) -> None:
        """批量更新 MySQL 的 dim_nodes 表"""
        if not nodes:
            logger.info("没有需要更新的节点")
            return

        batch_size = 500
        total_nodes = len(nodes)
        total_batches = (total_nodes + batch_size - 1) // batch_size

        logger.info(f"开始批量更新 MySQL，共 {total_nodes} 个节点，分 {total_batches} 批处理")

        for i in range(0, total_nodes, batch_size):
            batch = nodes[i:i + batch_size]
            batch_num = i // batch_size + 1

            try:
                node_ids = [str(node['node_id']) for node in batch]
                query = f"""
                UPDATE dim_nodes
                SET current_link_count = CASE node_id
                    {''.join([f"WHEN {node_id} THEN {node['link_count']}" for node in batch])}
                    ELSE current_link_count
                END,
                last_seen = NOW(),
                is_active = 1
                WHERE node_id IN ({','.join(node_ids)})
                """

                await self.mysql_manager.execute_query(query)
                logger.info(f"已更新 MySQL 第 {batch_num}/{total_batches} 批，包含 {len(batch)} 个节点")

            except Exception as e:
                logger.error(f"批量更新 MySQL 第 {batch_num} 批失败: {e}")

        logger.info(f"MySQL 批量更新完成，共处理 {total_nodes} 个节点")

    async def _batch_enqueue_to_redis(self, nodes: List[Dict]) -> None:
        """批量插入 Redis 优先级队列"""
        valid_nodes = [node for node in nodes if node['link_count'] > 1]

        if not valid_nodes:
            logger.info("没有需要加入队列的节点（连接数都 <= 1）")
            return

        batch_size = 500
        total_nodes = len(valid_nodes)
        total_batches = (total_nodes + batch_size - 1) // batch_size

        logger.info(f"开始批量插入 Redis 队列，共 {total_nodes} 个节点，分 {total_batches} 批处理")

        lock_acquired = await self.redis_queue.acquire_batch_lock()
        if not lock_acquired:
            logger.error("无法获取批量锁，批量插入操作被拒绝")
            return

        try:
            total_added = 0
            for i in range(0, total_nodes, batch_size):
                batch = valid_nodes[i:i + batch_size]
                batch_num = i // batch_size + 1

                try:
                    batch_data = [(node['node_id'], node['link_count']) for node in batch]
                    added_count = await self.redis_queue.batch_enqueue(batch_data)
                    total_added += added_count

                    logger.info(
                        f"已插入 Redis 队列第 {batch_num}/{total_batches} 批，本批新增 {added_count} 个节点"
                    )

                except Exception as e:
                    logger.error(f"批量插入 Redis 队列第 {batch_num} 批失败: {e}")

            logger.info(
                f"Redis 队列批量插入完成，共处理 {total_nodes} 个节点，实际新增 {total_added} 个节点"
            )
        finally:
            await self.redis_queue.release_batch_lock()

    def get_current_batch_no(self) -> Optional[str]:
        """获取当前批次号"""
        return self.current_batch_no
