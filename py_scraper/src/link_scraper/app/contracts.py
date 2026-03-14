"""
Contracts for app-level module and job composition.
"""

from dataclasses import dataclass
from typing import List, Literal, Protocol

from .context import AppContext


@dataclass(frozen=True)
class ScheduleSpec:
    """任务调度描述。

    mode:
    - continuous: 任务自身常驻运行，scheduler 负责拉起和异常重启
    - interval: scheduler 按固定间隔调用 run_once
    - manual: 仅注册，不自动运行

    timeout_seconds:
    - 单次执行的超时阈值

    cooldown_seconds:
    - 连续失败后，下一次重试前的冷却时间

    max_consecutive_failures:
    - 允许连续失败的次数阈值，超过后继续冷却但不自动停掉任务
    """

    mode: Literal["continuous", "interval", "manual"]
    interval_seconds: int | None = None
    timeout_seconds: float | None = None
    cooldown_seconds: float = 5.0
    max_consecutive_failures: int = 3


class ScheduledJob(Protocol):
    name: str
    schedule_spec: ScheduleSpec

    async def start(self) -> None:
        """Run the job according to its schedule until cancelled."""

    async def run_once(self) -> None:
        """Run a single iteration of the job."""

    async def shutdown(self) -> None:
        """Release job-local resources."""


class SourceModule(Protocol):
    name: str

    def build_jobs(self, context: AppContext) -> List[ScheduledJob]:
        """Build the jobs owned by the source module."""
