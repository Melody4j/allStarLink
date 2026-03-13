"""
AllStarLink source mapping helpers.
"""

import logging
import re
from typing import Any, Dict, List

from ...domain.models import CanonicalConnection, CanonicalNode, CanonicalNodeBundle
from .parser import AllStarLinkParser

logger = logging.getLogger(__name__)


class AllStarLinkMapper:
    """Maps AllStarLink-specific payloads into queue-ready items."""

    def __init__(self, parser: AllStarLinkParser | None = None) -> None:
        # 复用 source parser，避免在 mapper 中重复解析规则。
        self.parser = parser or AllStarLinkParser()

    def map_node_list(self, payload: Dict[str, Any]) -> List[Dict[str, int]]:
        nodes: List[Dict[str, int]] = []

        try:
            for row in payload.get("data", []):
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

        logger.info("从 DataTables JSON 数据中解析出 %s 个节点", len(nodes))
        return nodes

    def map_node_detail(self, payload: Dict[str, Any], batch_no: str | None = None) -> CanonicalNodeBundle | None:
        """将详情 payload 映射为统一领域聚合。"""
        primary_node = self.parser.parse_node(payload)
        if not primary_node:
            return None

        primary_node.batch_no = batch_no
        stats = payload.get("stats", {})
        data = stats.get("data", {})
        linked_nodes_raw = data.get("linkedNodes", [])

        canonical_linked_nodes: List[CanonicalNode] = []
        for linked_node_raw in linked_nodes_raw:
            linked_node = self.parser.parse_linked_node(linked_node_raw)
            if not linked_node:
                continue
            linked_node.batch_no = batch_no
            canonical_linked_nodes.append(
                CanonicalNode.from_legacy_node(
                    linked_node,
                    source_name="allstarlink",
                    record_kind="stub",
                    data_completeness="partial",
                )
            )

        connections = self.parser.parse_connections(
            int(primary_node.node_id),
            data.get("nodes", ""),
            linked_nodes_raw,
            batch_no,
        )

        return CanonicalNodeBundle(
            primary_node=CanonicalNode.from_legacy_node(
                primary_node,
                source_name="allstarlink",
                record_kind="full",
                data_completeness="complete",
            ),
            linked_nodes=canonical_linked_nodes,
            connections=[
                CanonicalConnection.from_legacy_connection(conn, source_name="allstarlink")
                for conn in connections
            ],
            raw_payload=payload,
        )
