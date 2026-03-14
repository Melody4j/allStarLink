"""AllStarLink source 映射辅助。"""

import logging
import re
from typing import Any, Dict, List

from ..models.domain import CanonicalNode, CanonicalNodeBundle
from ..models.payload import AslNodeDetailsPayload, AslNodeOnlineListPayload
from .parser import AllStarLinkParser

logger = logging.getLogger(__name__)


class AllStarLinkMapper:
    """把 AllStarLink 响应转换为队列和领域对象。"""

    def __init__(self, parser: AllStarLinkParser | None = None) -> None:
        self.parser = parser or AllStarLinkParser()

    def map_node_list(self, payload: Dict[str, Any] | AslNodeOnlineListPayload) -> List[Dict[str, int]]:
        nodes: List[Dict[str, int]] = []
        try:
            rows = payload.rows if isinstance(payload, AslNodeOnlineListPayload) else payload.get("data", [])
            for row in rows:
                if not isinstance(row, list) or not row:
                    continue
                node_id_str = row[0] if isinstance(row[0], str) else ""
                match = re.search(r"/stats/(\d+)", node_id_str)
                if match:
                    node_id_str = match.group(1)
                else:
                    node_id_str = node_id_str.split()[0]
                if not node_id_str.isdigit():
                    continue
                try:
                    last_col = row[-1]
                    link_count = int(last_col) if last_col and str(last_col).isdigit() else 0
                except (ValueError, TypeError):
                    link_count = 0
                nodes.append({"node_id": int(node_id_str), "link_count": link_count})
        except Exception as exc:
            logger.error("解析节点列表 JSON 失败: %s", exc, exc_info=True)
        logger.info("从 DataTables JSON 中解析出 %s 个节点", len(nodes))
        return nodes

    def map_node_detail(
        self,
        payload: Dict[str, Any] | AslNodeDetailsPayload,
        batch_no: str | None = None,
    ) -> CanonicalNodeBundle | None:
        primary_node = self.parser.parse_node(payload)
        if not primary_node:
            return None

        primary_node.batch_no = batch_no
        if isinstance(payload, AslNodeDetailsPayload):
            linked_nodes_raw = payload.linked_nodes
            connection_modes = payload.data.get("nodes", "")
            raw_payload = payload.raw_payload
        else:
            stats = payload.get("stats", {})
            data = stats.get("data", {})
            linked_nodes_raw = data.get("linkedNodes", [])
            connection_modes = data.get("nodes", "")
            raw_payload = payload

        canonical_linked_nodes: List[CanonicalNode] = []
        for linked_node_raw in linked_nodes_raw:
            linked_node = self.parser.parse_linked_node(linked_node_raw)
            if not linked_node:
                continue
            linked_node.batch_no = batch_no
            canonical_linked_nodes.append(linked_node)

        connections = self.parser.parse_connections(
            int(primary_node.node_id),
            connection_modes,
            linked_nodes_raw,
            batch_no,
        )

        return CanonicalNodeBundle(
            primary_node=primary_node,
            linked_nodes=canonical_linked_nodes,
            connections=connections,
            raw_payload=raw_payload,
        )
