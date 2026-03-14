"""
Registry for source modules and scheduled jobs.
"""

from typing import List

from .context import AppContext
from .contracts import ScheduledJob, SourceModule


class TaskRegistry:
    def __init__(self) -> None:
        self._modules: List[SourceModule] = []
        self._jobs: List[ScheduledJob] = []

    def register_module(self, module: SourceModule, context: AppContext) -> None:
        # registry 只做“收集”，不介入调度细节；
        # module 返回多少个 job，由 module 自己决定。
        self._modules.append(module)
        self._jobs.extend(module.build_jobs(context))

    @property
    def modules(self) -> List[SourceModule]:
        return list(self._modules)

    @property
    def jobs(self) -> List[ScheduledJob]:
        return list(self._jobs)
