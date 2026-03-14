"""AllStarLink `node_topology` 任务入口。"""

import asyncio
import logging

from ....app.context import AppContext
from ..models.domain import NodeTopologyRuntimeState
from ..schedules.node_topology_schedule import build_node_topology_schedule
from ..services.node_topology_service import NodeTopologyRuntime, build_node_topology_runtime

logger = logging.getLogger(__name__)


class NodeTopologyJob:
    """提供给调度器执行的 `node_topology` 任务入口。"""

    name = "allstarlink.node_topology"

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self.schedule_spec = build_node_topology_schedule(context.settings)
        self.runtime: NodeTopologyRuntime = build_node_topology_runtime(context)
        self.state = NodeTopologyRuntimeState()
        self._running = False

    async def start(self) -> None:
        """连续运行主链任务。"""

        self._running = True
        queue_size = await self.context.priority_queue.get_size()
        if queue_size == 0:
            await self.context.priority_queue.clear()

        self.state.current_batch_no = await self.context.batch_manager.initialize_batch_no(
            self.context.relational_storage_manager
        )
        if self.state.current_batch_no:
            self.runtime.worker.set_batch_no(self.state.current_batch_no)

        worker_task = asyncio.create_task(self.runtime.worker.start(), name=f"{self.name}.worker")
        try:
            while self._running:
                await self.run_once()
        except asyncio.CancelledError:
            logger.info("Node topology job cancelled")
            raise
        finally:
            worker_task.cancel()
            await asyncio.gather(worker_task, return_exceptions=True)

    async def run_once(self) -> None:
        """执行一轮主链状态判断。"""

        queue_size = await self.context.priority_queue.get_size()
        if queue_size == 0:
            await self.context.priority_queue.clear()
            await self.runtime.scanner.scan_and_update()
            self.state.current_batch_no = self.runtime.scanner.get_current_batch_no()
            if self.state.current_batch_no:
                self.runtime.worker.set_batch_no(self.state.current_batch_no)
            await asyncio.sleep(1800)
            return

        await asyncio.sleep(10)

    async def shutdown(self) -> None:
        self._running = False
        await self.runtime.close()
