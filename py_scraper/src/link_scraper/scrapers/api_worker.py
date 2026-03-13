"""
API worker.
"""

import asyncio
import logging
import random
from typing import Dict, Optional

from ..config.settings import APIConfig
from ..repositories import GraphRepository
from ..services.fetch_service import NodeFetchService
from ..services.ods_service import OdsWriteService
from ..services.parse_service import NodeParseService
from ..services.sync_service import NodeSyncService
from ..task_queue.priority_queue import RedisPriorityQueue
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class NodeIngestionWorker:
    """节点摄取编排器。

    新名称强调它当前真正的职责是“编排节点摄取流程”，
    而不是早期那种既抓取、又解析、又落库的大而全 worker。
    旧名字 APIWorker 仍然保留为兼容别名，避免一次性影响其他调用方。
    """

    def __init__(
        self,
        redis_queue: RedisPriorityQueue,
        api_config: APIConfig,
        rate_limiter: RateLimiter,
        fetch_service: NodeFetchService,
        parse_service: NodeParseService,
        sync_service: NodeSyncService,
        ods_service: OdsWriteService,
        graph_repository: GraphRepository,
    ) -> None:
        self.redis_queue = redis_queue
        self.api_config = api_config
        self.rate_limiter = rate_limiter
        self.fetch_service = fetch_service
        self.parse_service = parse_service
        self.sync_service = sync_service
        self.ods_service = ods_service
        self.graph_repository = graph_repository
        self.current_batch_no: Optional[str] = None

    def set_batch_no(self, batch_no: str) -> None:
        self.current_batch_no = batch_no
        logger.info("API工作者: 设置当前批次号为 %s", batch_no)

    async def start(self) -> None:
        logger.info("API工作者启动")
        while True:
            try:
                await self.process_queue()
                await asyncio.sleep(1)
            except Exception as exc:
                logger.error("API工作者运行异常: %s", exc, exc_info=True)
                await asyncio.sleep(10)

    async def process_queue(self) -> None:
        if not await self.rate_limiter.can_make_request():
            logger.debug("API工作者: 达到速率限制，等待中")
            await asyncio.sleep(1)
            return

        node_id = await self.redis_queue.dequeue()
        if not node_id:
            return

        delay = random.uniform(
            self.api_config.request_delay_min,
            self.api_config.request_delay_max,
        )
        logger.debug("API工作者: 等待 %.2f 秒后处理节点 %s", delay, node_id)
        await asyncio.sleep(delay)

        logger.info("API工作者: 开始处理节点 %s", node_id)
        try:
            node_data = await self.fetch_service.fetch_node_detail(node_id)
            if not node_data:
                logger.warning("API工作者: 未能获取节点 %s 的数据，跳过处理", node_id)
                return

            await self._update_databases(node_data)
            logger.info("API工作者: 成功处理节点 %s", node_id)
        except Exception as exc:
            logger.error("API工作者: 处理节点 %s 失败 - %s", node_id, exc, exc_info=True)

    async def _update_databases(self, data: Dict) -> None:
        try:
            stats = data.get("stats", {})
            if not stats:
                await self._delete_offline_node(data)
                return

            bundle = self.parse_service.parse_node_detail(data, self.current_batch_no)
            if not bundle:
                logger.warning("API工作者: 节点数据解析失败，跳过更新")
                return

            await self.sync_service.sync_bundle(bundle)
            await self.ods_service.write_bundle(bundle)
        except Exception as exc:
            logger.error("API工作者: 更新数据库失败 - %s", exc, exc_info=True)
            raise

    async def _delete_offline_node(self, data: Dict) -> None:
        logger.warning("API工作者: 节点stats为空，表示节点已下线，将从Neo4j删除")
        node_id_value = data.get("node_id", "")
        node_id = str(node_id_value) if node_id_value else ""
        if not node_id:
            return

        unique_id = f"{node_id}_{self.current_batch_no}"
        deleted = await self.graph_repository.delete_node_by_unique_id(unique_id)
        if deleted:
            logger.info(
                "API工作者: 已删除下线节点 %s (unique_id: %s) 及其所有连接关系",
                node_id,
                unique_id,
            )
        else:
            logger.warning("API工作者: 删除下线节点 %s (unique_id: %s) 失败", node_id, unique_id)


# 兼容旧命名，逐步将外部引用迁移到 NodeIngestionWorker。
APIWorker = NodeIngestionWorker
