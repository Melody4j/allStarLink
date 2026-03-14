"""`node_topology` 任务领域对象。"""

from dataclasses import dataclass


@dataclass
class NodeTopologyRuntimeState:
    """记录主链任务当前批次号。"""

    current_batch_no: str | None = None
