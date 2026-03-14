"""`node_topology` 任务的队列消费 worker。"""

import asyncio
import logging
import random
from typing import Any, Dict, Optional

from ....config.settings import NetworkRuntimeConfig
from ....task_queue.priority_queue import RedisPriorityQueue
from ....utils.rate_limiter import RateLimiter
from ..models.payload import AslNodeDetailsPayload
from ..repositories.node_topology_repository import NodeTopologyRepositories
from .node_topology_fetch_service import NodeTopologyFetchService
from .node_topology_parse_service import NodeTopologyParseService

logger = logging.getLogger(__name__)


class NodeTopologyWorker:
    """负责消费节点详情队列并更新存储。"""

    def __init__(
        self,
        redis_queue: RedisPriorityQueue,
        network_config: NetworkRuntimeConfig,
        rate_limiter: RateLimiter,
        fetch_service: NodeTopologyFetchService,
        parse_service: NodeTopologyParseService,
        sync_service,
        ods_service,
        repositories: NodeTopologyRepositories,
    ) -> None:
        self.redis_queue = redis_queue
        self.network_config = network_config
        self.rate_limiter = rate_limiter
        self.fetch_service = fetch_service
        self.parse_service = parse_service
        self.sync_service = sync_service
        self.ods_service = ods_service
        self.repositories = repositories
        self.current_batch_no: Optional[str] = None

    def set_batch_no(self, batch_no: str) -> None:
        self.current_batch_no = batch_no
        logger.info("node_topology: worker 当前批次号设为 %s", batch_no)

    async def start(self) -> None:
        logger.info("node_topology: worker 启动")
        while True:
            try:
                await self.process_queue()
                await asyncio.sleep(1)
            except Exception as exc:
                logger.error("node_topology: worker 运行异常: %s", exc, exc_info=True)
                await asyncio.sleep(10)

    async def process_queue(self) -> None:
        if not await self.rate_limiter.can_make_request():
            await asyncio.sleep(1)
            return

        node_id = await self.redis_queue.dequeue()
        if not node_id:
            return

        delay = random.uniform(
            self.network_config.request_delay_min,
            self.network_config.request_delay_max,
        )
        await asyncio.sleep(delay)

        try:
            node_data = await self.fetch_service.fetch_node_detail(node_id)
            if not node_data:
                return
            await self._update_databases(node_data)
        except Exception as exc:
            logger.error("node_topology: 处理节点 %s 失败 - %s", node_id, exc, exc_info=True)

    async def _update_databases(self, data: Dict[str, Any] | AslNodeDetailsPayload) -> None:
        stats = self._get_stats(data)
        if not stats:
            await self._delete_offline_node(data)
            return

        bundle = self.parse_service.parse_node_detail(data, self.current_batch_no)
        if not bundle:
            return

        await self.sync_service.sync_bundle(bundle)
        await self.ods_service.write_bundle(bundle)

    async def _delete_offline_node(self, data: Dict[str, Any] | AslNodeDetailsPayload) -> None:
        node_id = self._get_node_id(data)
        if not node_id:
            return

        deleted = await self.repositories.delete_offline_node(node_id, self.current_batch_no)
        if deleted:
            logger.info("node_topology: 已删除离线节点 %s", node_id)

    @staticmethod
    def _get_stats(data: Dict[str, Any] | AslNodeDetailsPayload) -> Dict[str, Any]:
        if isinstance(data, AslNodeDetailsPayload):
            return data.stats
        return data.get("stats", {})

    @staticmethod
    def _get_node_id(data: Dict[str, Any] | AslNodeDetailsPayload) -> str:
        if isinstance(data, AslNodeDetailsPayload):
            node_id_value = data.user_node.get("name", "")
        else:
            node_id_value = data.get("node_id", "")
            if not node_id_value:
                stats = data.get("stats", {})
                user_node = stats.get("user_node", {}) if isinstance(stats, dict) else {}
                node_id_value = user_node.get("name", "")

        return str(node_id_value) if node_id_value else ""
