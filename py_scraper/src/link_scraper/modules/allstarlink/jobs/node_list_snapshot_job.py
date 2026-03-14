"""AllStarLink `node_list_snapshot` 任务入口。"""

from ....app.context import AppContext
from ..schedules.node_list_snapshot_schedule import build_node_list_snapshot_schedule
from ..services.node_list_snapshot_service import NodeListSnapshotService


class NodeListSnapshotJob:
    """提供给调度器执行的节点列表快照任务入口。"""

    name = "allstarlink.node_list_snapshot"

    def __init__(self, context: AppContext) -> None:
        self.schedule_spec = build_node_list_snapshot_schedule(context.settings)
        self.service = NodeListSnapshotService(context)

    async def start(self) -> None:
        await self.run_once()

    async def run_once(self) -> None:
        await self.service.capture_snapshot()

    async def shutdown(self) -> None:
        await self.service.close()
