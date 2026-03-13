"""
领域模型到持久化 record 的映射器。
"""

from datetime import datetime
from typing import List

from ..domain.models import CanonicalConnection, CanonicalNode, CanonicalNodeBundle
from .records import DimNodeRecord, GraphConnectionRecord, GraphNodeRecord, OdsNodeDetailRecord


class GraphMapper:
    """统一领域模型到图存储对象的映射。"""

    @staticmethod
    def map_node(node: CanonicalNode) -> GraphNodeRecord:
        return GraphNodeRecord(
            unique_id=f"{node.node_id}_{node.batch_no}",
            node_id=node.node_id,
            callsign=node.callsign,
            node_type=node.node_type,
            lat=node.lat,
            lon=node.lon,
            apprptuptime=node.apprptuptime,
            total_keyups=node.total_keyups,
            total_tx_time=node.total_tx_time,
            last_seen=node.last_seen.isoformat() if node.last_seen else None,
            active=node.active,
            updated_at=node.updated_at.isoformat() if node.updated_at else None,
            node_rank=node.node_rank,
            features=list(node.features),
            tone=node.tone,
            location_desc=node.location_desc,
            hardware_type=node.hardware_type,
            site_name=node.site_name,
            connections=node.connections,
            batch_no=node.batch_no,
        )

    @staticmethod
    def map_connections(connections: List[CanonicalConnection]) -> List[GraphConnectionRecord]:
        return [
            GraphConnectionRecord(
                src_unique_id=f"{conn.source_id}_{conn.batch_no}",
                dst_unique_id=f"{conn.target_id}_{conn.batch_no}",
                source_id=conn.source_id,
                target_id=conn.target_id,
                status=conn.status,
                direction=conn.direction,
                last_updated=conn.last_updated,
                active=conn.active,
                batch_no=conn.batch_no,
            )
            for conn in connections
        ]


class DimNodeMapper:
    """统一领域模型到维表存储对象的映射。"""

    @staticmethod
    def map_node(node: CanonicalNode) -> DimNodeRecord:
        return DimNodeRecord(
            node_id=node.node_id,
            node_type=node.node_type,
            callsign=node.callsign,
            tone=node.tone,
            owner=node.owner,
            affiliation=node.affiliation,
            site_name=node.site_name,
            features=list(node.features),
            affiliation_type=node.affiliation_type,
            country=node.country,
            continent=node.continent,
            active=node.active,
            last_seen=node.last_seen,
            node_rank=node.node_rank,
            mobility_type=node.mobility_type,
            first_seen_at=node.first_seen_at,
            lat=node.lat,
            lon=node.lon,
            location_desc=node.location_desc,
            is_mobile=node.is_mobile,
            app_version=node.app_version,
            is_bridge=node.is_bridge,
            access_webtransceiver=node.access_webtransceiver,
            ip_address=node.ip_address,
            timezone_offset=node.timezone_offset,
            is_nnx=node.is_nnx,
            hardware_type=node.hardware_type,
            total_keyups=node.total_keyups,
            history_total_keyups=node.history_total_keyups,
            total_tx_time=node.total_tx_time,
            history_tx_time=node.history_tx_time,
            access_telephoneportal=node.access_telephoneportal,
            access_functionlist=node.access_functionlist,
            access_reverseautopatch=node.access_reverseautopatch,
            seqno=node.seqno,
            timeout=node.timeout,
            apprptuptime=node.apprptuptime,
            totalexecdcommands=node.totalexecdcommands,
            current_link_count=node.connections,
        )


class OdsMapper:
    """统一领域模型到 ODS 存储对象的映射。"""

    @staticmethod
    def map_bundle(bundle: CanonicalNodeBundle) -> OdsNodeDetailRecord:
        """当前仍按现有 ODS 语义，优先复用原始 payload。"""
        raw_payload = bundle.raw_payload or {}
        stats = raw_payload.get("stats", {})
        user_node = stats.get("user_node", {})
        server_info = user_node.get("server", {})
        data = stats.get("data", {})
        linked_nodes = data.get("linkedNodes", [])

        is_nnx = None
        is_nnx_str = user_node.get("is_nnx", "")
        if is_nnx_str:
            is_nnx = is_nnx_str.upper() == "YES"

        port = None
        if "udpport" in server_info:
            port = str(server_info.get("udpport"))
        elif "port" in user_node:
            port = str(user_node.get("port"))

        return OdsNodeDetailRecord(
            node_id=int(user_node.get("name", 0)),
            node_type="ALLSTARLINK",
            callsign=user_node.get("callsign"),
            frequency=user_node.get("node_frequency"),
            tone=user_node.get("node_tone"),
            affiliation=server_info.get("Affiliation"),
            site_name=server_info.get("SiteName"),
            is_active=True,
            last_seen=datetime.now(),
            latitude=float(server_info.get("Latitude", 0.0) or 0.0) or None,
            longitude=float(server_info.get("Logitude", 0.0) or 0.0) or None,
            app_version=data.get("apprptvers"),
            ip=user_node.get("ipaddr"),
            timezone_offset=None,
            is_nnx=is_nnx,
            total_keyups=int(data.get("totalkeyups", 0) or 0),
            total_tx_time=int(data.get("totaltxtime", 0) or 0),
            access_webtransceiver=user_node.get("access_webtransceiver", "0") == "1",
            access_telephoneportal=user_node.get("access_telephoneportal", "0") == "1",
            access_functionlist=user_node.get("access_functionlist", "0") == "1",
            access_reverseautopatch=user_node.get("access_reverseautopatch", "0") == "1",
            seqno=int(data.get("seqno", 0) or 0),
            timeout=int(data.get("timeouts", 0) or 0),
            apprptuptime=int(data.get("apprptuptime", 0) or 0),
            total_execd_commands=int(data.get("totalexecdcommands", 0) or 0),
            max_uptime=None,
            current_link_count=len(linked_nodes),
            linked_nodes=linked_nodes,
            links=data.get("nodes"),
            port=port,
            batch_no=bundle.primary_node.batch_no,
        )
