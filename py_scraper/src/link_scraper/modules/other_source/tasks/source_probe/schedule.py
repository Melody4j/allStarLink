"""
OtherSource 探测任务的调度配置。
"""

from .....app.contracts import ScheduleSpec


def build_other_source_probe_schedule() -> ScheduleSpec:
    """当前先使用固定 interval 调度。"""

    return ScheduleSpec(
        mode="interval",
        interval_seconds=3600,
        timeout_seconds=30,
        cooldown_seconds=10,
        max_consecutive_failures=3,
    )
