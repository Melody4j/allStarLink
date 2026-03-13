"""
Snapshot scanner.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from ..config.settings import APIConfig
from ..database.mysql_manager import MySQLManager
from ..sources.allstarlink.client import AllStarLinkClient
from ..sources.allstarlink.mapper import AllStarLinkMapper
from ..sources.base import SourceClient, SourceMapper
from ..task_queue.priority_queue import RedisPriorityQueue
from ..utils.batch_manager import BatchManager

logger = logging.getLogger(__name__)


class SnapshotScanner:
    """Fetches the online node list and refreshes queue state."""

    def __init__(
        self,
        redis_queue: RedisPriorityQueue,
        mysql_manager: MySQLManager,
        api_config: APIConfig,
        batch_manager: BatchManager,
        source_client: Optional[SourceClient] = None,
        source_mapper: Optional[SourceMapper] = None,
    ) -> None:
        self.redis_queue = redis_queue
        self.mysql_manager = mysql_manager
        self.api_config = api_config
        self.batch_manager = batch_manager
        self.source_client: SourceClient = source_client or AllStarLinkClient(api_config)
        self.source_mapper: SourceMapper = source_mapper or AllStarLinkMapper()
        self.current_batch_no: Optional[str] = None

    async def start(self) -> None:
        logger.info("快照扫描器启动")
        while True:
            try:
                await self.scan_and_update()
                await asyncio.sleep(3600)
            except Exception as exc:
                logger.error("快照扫描器运行异常: %s", exc, exc_info=True)
                await asyncio.sleep(60)

    async def scan_and_update(self) -> None:
        self.current_batch_no = await self.batch_manager.get_or_create_batch_no(self.mysql_manager)
        logger.info("开始扫描节点列表，当前批次号: %s", self.current_batch_no)

        try:
            payload = await self.source_client.fetch_node_list()
            if not payload:
                return

            nodes = self.source_mapper.map_node_list(payload)
            logger.info("扫描到 %s 个在线节点", len(nodes))

            await self._batch_update_mysql(nodes)
            await self._batch_enqueue_to_redis(nodes)
        except Exception as exc:
            logger.error("扫描节点列表异常: %s", exc, exc_info=True)

    async def _update_priority_queue(self, nodes: List[Dict]) -> None:
        for node in nodes:
            node_id = node["node_id"]
            link_count = node["link_count"]

            if link_count <= 0:
                continue

            if not await self.redis_queue.contains(node_id):
                await self.redis_queue.enqueue(node_id, link_count)
                logger.debug(
                    "快照扫描: 节点 %s 已加入队列，优先级分数 %s (连接数 %s)",
                    node_id,
                    link_count,
                    link_count,
                )

    async def _batch_update_mysql(self, nodes: List[Dict]) -> None:
        if not nodes:
            logger.info("没有需要更新的节点")
            return

        batch_size = 500
        total_nodes = len(nodes)
        total_batches = (total_nodes + batch_size - 1) // batch_size
        logger.info("开始批量更新MySQL，共 %s 个节点，分 %s 批处理", total_nodes, total_batches)

        for i in range(0, total_nodes, batch_size):
            batch = nodes[i:i + batch_size]
            batch_num = i // batch_size + 1

            try:
                node_ids = [str(node["node_id"]) for node in batch]
                # 这里按批次拼 CASE WHEN，必须显式引用每条记录自己的 node_id；
                # 否则会退化成引用外层不存在的变量，联调时会直接触发 NameError。
                case_when_sql = "".join(
                    [f"WHEN {node['node_id']} THEN {node['link_count']} " for node in batch]
                )
                query = f"""
                UPDATE dim_nodes
                SET current_link_count = CASE node_id
                    {case_when_sql}
                    ELSE current_link_count
                END,
                last_seen = NOW(),
                is_active = 1
                WHERE node_id IN ({','.join(node_ids)})
                """
                await self.mysql_manager.execute_query(query)
                logger.info("已更新MySQL 第 %s/%s 批，包含 %s 个节点", batch_num, total_batches, len(batch))
            except Exception as exc:
                logger.error("批量更新 MySQL 第 %s 批失败: %s", batch_num, exc, exc_info=True)

        logger.info("MySQL 批量更新完成，共处理 %s 个节点", total_nodes)

    async def _batch_enqueue_to_redis(self, nodes: List[Dict]) -> None:
        valid_nodes = [node for node in nodes if node["link_count"] > 1]

        if not valid_nodes:
            logger.info("没有需要加入队列的节点（连接数都 <= 1）")
            return

        batch_size = 500
        total_nodes = len(valid_nodes)
        total_batches = (total_nodes + batch_size - 1) // batch_size

        logger.info("开始批量插入Redis队列，共 %s 个节点，分 %s 批处理", total_nodes, total_batches)

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
                    batch_data = [(node["node_id"], node["link_count"]) for node in batch]
                    added_count = await self.redis_queue.batch_enqueue(batch_data)
                    total_added += added_count
                    logger.info(
                        "已插入Redis队列第 %s/%s 批，本批新增 %s 个节点",
                        batch_num,
                        total_batches,
                        added_count,
                    )
                except Exception as exc:
                    logger.error("批量插入 Redis 队列第 %s 批失败: %s", batch_num, exc, exc_info=True)

            logger.info(
                "Redis 队列批量插入完成，共处理 %s 个节点，实际新增 %s 个节点",
                total_nodes,
                total_added,
            )
        finally:
            await self.redis_queue.release_batch_lock()

    def get_current_batch_no(self) -> Optional[str]:
        return self.current_batch_no
