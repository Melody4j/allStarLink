"""
统一领域模型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.connection import Connection
from ..models.node import Node


@dataclass
class CanonicalNode:
    """统一节点模型，屏蔽具体数据源和存储实现差异。"""

    node_id: str
    callsign: str
    source_name: str
    node_type: str
    lat: float
    lon: float
    apprptuptime: Optional[int]
    total_keyups: Optional[int]
    total_tx_time: Optional[int]
    last_seen: datetime
    active: bool
    updated_at: datetime
    node_rank: str
    features: List[str]
    tone: Optional[float]
    location_desc: Optional[str]
    hardware_type: str
    connections: Optional[int]
    owner: Optional[str] = None
    affiliation: Optional[str] = None
    site_name: Optional[str] = None
    affiliation_type: Optional[str] = None
    country: Optional[str] = None
    continent: Optional[str] = None
    mobility_type: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    is_mobile: Optional[bool] = None
    app_version: Optional[str] = None
    is_bridge: Optional[bool] = None
    access_webtransceiver: Optional[bool] = None
    ip_address: Optional[str] = None
    timezone_offset: Optional[float] = None
    is_nnx: Optional[bool] = None
    history_total_keyups: Optional[int] = None
    history_tx_time: Optional[int] = None
    access_telephoneportal: Optional[bool] = None
    access_functionlist: Optional[bool] = None
    access_reverseautopatch: Optional[bool] = None
    seqno: Optional[int] = None
    timeout: Optional[int] = None
    totalexecdcommands: Optional[int] = None
    batch_no: Optional[str] = None
    record_kind: str = "full"
    data_completeness: str = "complete"

    @classmethod
    def from_legacy_node(
        cls,
        node: Node,
        source_name: str,
        record_kind: str = "full",
        data_completeness: str = "complete",
    ) -> "CanonicalNode":
        """从旧版 Node 过渡到统一领域模型。"""
        return cls(
            node_id=node.node_id,
            callsign=node.callsign,
            source_name=source_name,
            node_type=node.node_type,
            lat=node.lat,
            lon=node.lon,
            apprptuptime=node.apprptuptime,
            total_keyups=node.total_keyups,
            total_tx_time=node.total_tx_time,
            last_seen=node.last_seen,
            active=node.active,
            updated_at=node.updated_at,
            node_rank=node.node_rank,
            features=list(node.features),
            tone=node.tone,
            location_desc=node.location_desc,
            hardware_type=node.hardware_type,
            connections=node.connections,
            owner=node.owner,
            affiliation=node.affiliation,
            site_name=node.site_name,
            affiliation_type=node.affiliation_type,
            country=node.country,
            continent=node.continent,
            mobility_type=node.mobility_type,
            first_seen_at=node.first_seen_at,
            is_mobile=node.is_mobile,
            app_version=node.app_version,
            is_bridge=node.is_bridge,
            access_webtransceiver=node.access_webtransceiver,
            ip_address=node.ip_address,
            timezone_offset=node.timezone_offset,
            is_nnx=node.is_nnx,
            history_total_keyups=node.history_total_keyups,
            history_tx_time=node.history_tx_time,
            access_telephoneportal=node.access_telephoneportal,
            access_functionlist=node.access_functionlist,
            access_reverseautopatch=node.access_reverseautopatch,
            seqno=node.seqno,
            timeout=node.timeout,
            totalexecdcommands=node.totalexecdcommands,
            batch_no=node.batch_no,
            record_kind=record_kind,
            data_completeness=data_completeness,
        )


@dataclass
class CanonicalConnection:
    """统一连接关系模型。"""

    source_id: str
    target_id: str
    status: str
    direction: str
    last_updated: datetime
    active: bool
    batch_no: Optional[str] = None
    source_name: str = "allstarlink"

    @classmethod
    def from_legacy_connection(
        cls,
        connection: Connection,
        source_name: str,
    ) -> "CanonicalConnection":
        """从旧版 Connection 过渡到统一领域模型。"""
        return cls(
            source_id=connection.source_id,
            target_id=connection.target_id,
            status=connection.status,
            direction=connection.direction,
            last_updated=connection.last_updated,
            active=connection.active,
            batch_no=connection.batch_no,
            source_name=source_name,
        )


@dataclass
class CanonicalNodeBundle:
    """统一节点抓取结果聚合。"""

    primary_node: CanonicalNode
    linked_nodes: List[CanonicalNode] = field(default_factory=list)
    connections: List[CanonicalConnection] = field(default_factory=list)
    raw_payload: Optional[Dict[str, Any]] = None
