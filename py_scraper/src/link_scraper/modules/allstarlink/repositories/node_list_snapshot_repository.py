"""`node_list_snapshot` 任务的数据访问实现。"""

import json
from dataclasses import asdict

from ..models.domain import NodeListSnapshot


class NodeListSnapshotRepository:
    """只维护 Redis 中的最新节点列表摘要。"""

    def __init__(self, redis_client) -> None:
        self.redis_client = redis_client
        self.snapshot_key = "allstarlink:node_list_snapshot:last_summary"

    async def save(self, snapshot: NodeListSnapshot) -> None:
        payload = asdict(snapshot)
        payload["captured_at"] = snapshot.captured_at.isoformat()
        await self.redis_client.set(self.snapshot_key, json.dumps(payload, ensure_ascii=True))
