"""`node_list_snapshot` 任务的调度配置构建。"""

from ....app.contracts import ScheduleSpec


def build_node_list_snapshot_schedule(settings) -> ScheduleSpec:
    """根据配置构建节点列表快照任务的调度规则。"""

    task_config = settings.allstarlink.tasks.node_list_snapshot
    return ScheduleSpec(
        mode=task_config.mode,
        interval_seconds=task_config.interval_seconds,
        timeout_seconds=task_config.timeout_seconds,
        cooldown_seconds=task_config.cooldown_seconds,
        max_consecutive_failures=task_config.max_consecutive_failures,
    )
