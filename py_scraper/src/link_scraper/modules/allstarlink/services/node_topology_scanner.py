"""`node_topology` 任务的快照扫描器。"""

import logging
from typing import Dict, List, Optional

from ....config.settings import NetworkRuntimeConfig
from ....database.mysql_manager import RelationalStorageManager
from ....sources import SourceClient, SourceMapper
from ....task_queue.priority_queue import RedisPriorityQueue
from ....utils.batch_manager import BatchManager

logger = logging.getLogger(__name__)


class NodeTopologySnapshotScanner:
    """抓取节点列表，并刷新 MySQL 与 Redis 队列状态。"""

    def __init__(
        self,
        redis_queue: RedisPriorityQueue,
        mysql_manager: RelationalStorageManager,
        network_config: NetworkRuntimeConfig,
        batch_manager: BatchManager,
        source_client: SourceClient,
        source_mapper: SourceMapper,
    ) -> None:
        self.redis_queue = redis_queue
        self.mysql_manager = mysql_manager
        self.network_config = network_config
        self.batch_manager = batch_manager
        self.source_client = source_client
        self.source_mapper = source_mapper
        self.current_batch_no: Optional[str] = None

    async def scan_and_update(self) -> None:
        self.current_batch_no = await self.batch_manager.get_or_create_batch_no(self.mysql_manager)
        logger.info("node_topology: 开始扫描节点列表，当前批次号 %s", self.current_batch_no)

        try:
            payload = await self.source_client.fetch_node_list()
            if not payload:
                return

            nodes = self.source_mapper.map_node_list(payload)
            logger.info("node_topology: 扫描到 %s 个在线节点", len(nodes))

            await self._batch_update_mysql(nodes)
            await self._batch_enqueue_to_redis(nodes)
        except Exception as exc:
            logger.error("node_topology: 扫描节点列表异常: %s", exc, exc_info=True)

    async def _batch_update_mysql(self, nodes: List[Dict]) -> None:
        if not nodes:
            logger.info("node_topology: 没有需要更新的节点")
            return

        batch_size = 500
        total_nodes = len(nodes)
        total_batches = (total_nodes + batch_size - 1) // batch_size

        for i in range(0, total_nodes, batch_size):
            batch = nodes[i : i + batch_size]
            batch_num = i // batch_size + 1

            try:
                node_ids = [str(node["node_id"]) for node in batch]
                case_when_sql = "".join([f"WHEN {node['node_id']} THEN {node['link_count']} " for node in batch])
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
                logger.info(
                    "node_topology: 已更新 MySQL 第 %s/%s 批，包含 %s 个节点",
                    batch_num,
                    total_batches,
                    len(batch),
                )
            except Exception as exc:
                logger.error("node_topology: 批量更新 MySQL 第 %s 批失败: %s", batch_num, exc, exc_info=True)

    async def _batch_enqueue_to_redis(self, nodes: List[Dict]) -> None:
        valid_nodes = [node for node in nodes if node["link_count"] > 1]
        if not valid_nodes:
            logger.info("node_topology: 没有需要加入队列的节点")
            return

        batch_size = 500
        total_nodes = len(valid_nodes)
        total_batches = (total_nodes + batch_size - 1) // batch_size

        lock_acquired = await self.redis_queue.acquire_batch_lock()
        if not lock_acquired:
            logger.error("node_topology: 无法获取批量锁，放弃写入 Redis 队列")
            return

        try:
            for i in range(0, total_nodes, batch_size):
                batch = valid_nodes[i : i + batch_size]
                batch_num = i // batch_size + 1
                batch_data = [(node["node_id"], node["link_count"]) for node in batch]
                added_count = await self.redis_queue.batch_enqueue(batch_data)
                logger.info(
                    "node_topology: 已插入 Redis 队列第 %s/%s 批，本批新增 %s 个节点",
                    batch_num,
                    total_batches,
                    added_count,
                )
        finally:
            await self.redis_queue.release_batch_lock()

    def get_current_batch_no(self) -> Optional[str]:
        return self.current_batch_no
