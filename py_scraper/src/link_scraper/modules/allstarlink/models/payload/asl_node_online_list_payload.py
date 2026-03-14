"""`asl_node_online_list_url` 的原始响应模型。"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AslNodeOnlineListPayload:
    """承载 AllStarLink 在线节点列表的原始响应。

    这里保留 `raw_payload`，是为了兼容现有解析逻辑和调试需求。
    `rows` 则把当前任务真正关心的表格数据单独提取出来。
    """

    raw_payload: dict[str, Any]
    rows: list[list[Any]]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AslNodeOnlineListPayload":
        rows = payload.get("data", [])
        return cls(
            raw_payload=payload,
            rows=rows if isinstance(rows, list) else [],
        )
