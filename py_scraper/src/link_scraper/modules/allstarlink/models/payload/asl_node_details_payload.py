"""`asl_node_details_url` 的原始响应模型。"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AslNodeDetailsPayload:
    """承载 AllStarLink 节点详情接口的原始响应。"""

    raw_payload: dict[str, Any]
    stats: dict[str, Any]
    user_node: dict[str, Any]
    data: dict[str, Any]
    linked_nodes: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AslNodeDetailsPayload":
        stats = payload.get("stats", {})
        user_node = stats.get("user_node", {}) if isinstance(stats, dict) else {}
        data = stats.get("data", {}) if isinstance(stats, dict) else {}
        linked_nodes = data.get("linkedNodes", []) if isinstance(data, dict) else []
        return cls(
            raw_payload=payload,
            stats=stats if isinstance(stats, dict) else {},
            user_node=user_node if isinstance(user_node, dict) else {},
            data=data if isinstance(data, dict) else {},
            linked_nodes=linked_nodes if isinstance(linked_nodes, list) else [],
        )
