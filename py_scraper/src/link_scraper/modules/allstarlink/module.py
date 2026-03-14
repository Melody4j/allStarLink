"""AllStarLink source 模块注册入口。"""

from ...app.context import AppContext
from ...app.contracts import ScheduledJob
from .jobs.node_list_snapshot_job import NodeListSnapshotJob
from .jobs.node_topology_job import NodeTopologyJob


class AllStarLinkModule:
    name = "allstarlink"

    def build_jobs(self, context: AppContext) -> list[ScheduledJob]:
        # 模块层只负责把当前 source 下已启用的任务构造成 job 列表。
        # 任务何时运行、如何运行，由各自的 schedule_spec 和 scheduler 决定。
        jobs: list[ScheduledJob] = []
        task_settings = context.settings.allstarlink.tasks

        if task_settings.node_topology.enabled:
            jobs.append(NodeTopologyJob(context))

        if task_settings.node_list_snapshot.enabled:
            jobs.append(NodeListSnapshotJob(context))

        return jobs
