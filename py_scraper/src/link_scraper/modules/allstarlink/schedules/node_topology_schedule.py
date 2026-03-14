"""`node_topology` 任务的调度配置构建。"""

from ....app.contracts import ScheduleSpec


def build_node_topology_schedule(settings) -> ScheduleSpec:
    """根据配置构建 `node_topology` 的调度规则。"""

    task_config = settings.allstarlink.tasks.node_topology
    return ScheduleSpec(
        mode=task_config.mode,
        interval_seconds=task_config.interval_seconds,
        timeout_seconds=task_config.timeout_seconds,
        cooldown_seconds=task_config.cooldown_seconds,
        max_consecutive_failures=task_config.max_consecutive_failures,
    )
