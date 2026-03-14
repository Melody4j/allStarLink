"""节点列表快照领域对象。"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NodeListSnapshot:
    source_name: str
    captured_at: datetime
    node_count: int
    connected_node_count: int
