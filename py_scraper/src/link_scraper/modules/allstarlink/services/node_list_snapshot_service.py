"""节点列表快照任务服务。"""

import logging
from datetime import datetime

from ....app.context import AppContext
from ....sources import build_source_components
from ..models.domain import NodeListSnapshot
from ..repositories.node_list_snapshot_repository import NodeListSnapshotRepository

logger = logging.getLogger(__name__)


class NodeListSnapshotService:
    """抓取节点列表，并写入 Redis 最新摘要。"""

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self.source_components = build_source_components(
            context.settings.source_name,
            context.settings,
        )
        self.repository = NodeListSnapshotRepository(context.redis_client)

    async def capture_snapshot(self) -> NodeListSnapshot | None:
        payload = await self.source_components.client.fetch_node_list()
        if not payload:
            logger.warning("Node list snapshot task received empty payload")
            return None

        nodes = self.source_components.mapper.map_node_list(payload)
        snapshot = NodeListSnapshot(
            source_name=self.context.settings.source_name,
            captured_at=datetime.now(),
            node_count=len(nodes),
            connected_node_count=len([node for node in nodes if node.get("link_count", 0) > 0]),
        )
        await self.repository.save(snapshot)
        logger.info(
            "Captured node list snapshot: source=%s node_count=%s connected_nodes=%s",
            snapshot.source_name,
            snapshot.node_count,
            snapshot.connected_node_count,
        )
        return snapshot

    async def close(self) -> None:
        await self.source_components.client.close()
