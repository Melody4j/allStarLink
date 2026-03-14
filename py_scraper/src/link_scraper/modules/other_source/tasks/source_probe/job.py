"""
OtherSource 探测任务 job。
"""

from .....app.context import AppContext
from .schedule import build_other_source_probe_schedule
from .service import OtherSourceProbeService


class OtherSourceProbeJob:
    """第二数据源最小 job。"""

    name = "other_source.source_probe"

    def __init__(self, context: AppContext) -> None:
        self.schedule_spec = build_other_source_probe_schedule()
        self.service = OtherSourceProbeService(context)

    async def start(self) -> None:
        await self.run_once()

    async def run_once(self) -> None:
        await self.service.run_probe()

    async def shutdown(self) -> None:
        await self.service.close()
