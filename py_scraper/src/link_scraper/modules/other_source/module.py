"""
OtherSource 模块注册入口。
"""

from ...app.context import AppContext
from ...app.contracts import ScheduledJob
from .tasks.source_probe.job import OtherSourceProbeJob


class OtherSourceModule:
    """第二数据源模块骨架。

    当前 purpose 不是提供真实业务，而是验证：
    1. 新 source 可以按相同协议接入
    2. 新 source 不需要改主入口
    3. 新 source 不需要改 scheduler 核心逻辑
    """

    name = "other_source"

    def build_jobs(self, context: AppContext) -> list[ScheduledJob]:
        # 当前只挂一个最小探测任务，先把 source module 横向扩展路径打通。
        return [OtherSourceProbeJob(context)]
