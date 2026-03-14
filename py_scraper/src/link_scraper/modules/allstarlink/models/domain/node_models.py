"""AllStarLink 节点领域模型。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CanonicalNode:
    """当前项目实际服务于 AllStarLink 的节点领域模型。"""

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


@dataclass
class CanonicalConnection:
    """AllStarLink 连接关系领域模型。"""

    source_id: str
    target_id: str
    status: str
    direction: str
    last_updated: datetime
    active: bool
    batch_no: Optional[str] = None
    source_name: str = "allstarlink"


@dataclass
class CanonicalNodeBundle:
    """AllStarLink 节点详情聚合。"""

    primary_node: CanonicalNode
    linked_nodes: List[CanonicalNode] = field(default_factory=list)
    connections: List[CanonicalConnection] = field(default_factory=list)
    raw_payload: Optional[Dict[str, Any]] = None
