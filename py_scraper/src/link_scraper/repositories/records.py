"""
持久化 record 模型。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class GraphNodeRecord:
    """Neo4j 节点写入对象。"""

    unique_id: str
    node_id: str
    callsign: str
    node_type: str
    lat: float
    lon: float
    apprptuptime: Optional[int]
    total_keyups: Optional[int]
    total_tx_time: Optional[int]
    last_seen: Optional[str]
    active: bool
    updated_at: Optional[str]
    node_rank: str
    features: List[str]
    tone: Optional[float]
    location_desc: Optional[str]
    hardware_type: str
    site_name: Optional[str]
    connections: Optional[int]
    batch_no: Optional[str]

    def validate(self) -> bool:
        return bool(self.unique_id and self.node_id and -90 <= self.lat <= 90 and -180 <= self.lon <= 180)

    def to_properties(self) -> Dict[str, Any]:
        return {
            "unique_id": self.unique_id,
            "node_id": self.node_id,
            "callsign": self.callsign,
            "node_type": self.node_type,
            "lat": self.lat,
            "lon": self.lon,
            "apprptuptime": self.apprptuptime,
            "total_keyups": self.total_keyups,
            "total_tx_time": self.total_tx_time,
            "last_seen": self.last_seen,
            "active": self.active,
            "updated_at": self.updated_at,
            "node_rank": self.node_rank,
            "features": self.features,
            "tone": self.tone,
            "location_desc": self.location_desc,
            "hardware_type": self.hardware_type,
            "siteName": self.site_name,
            "connections": self.connections,
            "batch_no": self.batch_no,
        }


@dataclass
class GraphConnectionRecord:
    """Neo4j 关系写入对象。"""

    src_unique_id: str
    dst_unique_id: str
    source_id: str
    target_id: str
    status: str
    direction: str
    last_updated: datetime
    active: bool
    batch_no: Optional[str]

    def validate(self) -> bool:
        return bool(self.src_unique_id and self.dst_unique_id and self.source_id and self.target_id and self.last_updated)


@dataclass
class DimNodeRecord:
    """MySQL dim_nodes 写入对象。"""

    node_id: str
    node_type: str
    callsign: str
    tone: Optional[float]
    owner: Optional[str]
    affiliation: Optional[str]
    site_name: Optional[str]
    features: List[str]
    affiliation_type: Optional[str]
    country: Optional[str]
    continent: Optional[str]
    active: bool
    last_seen: datetime
    node_rank: Optional[str]
    mobility_type: Optional[str]
    first_seen_at: Optional[datetime]
    lat: float
    lon: float
    location_desc: Optional[str]
    is_mobile: Optional[bool]
    app_version: Optional[str]
    is_bridge: Optional[bool]
    access_webtransceiver: Optional[bool]
    ip_address: Optional[str]
    timezone_offset: Optional[float]
    is_nnx: Optional[bool]
    hardware_type: str
    total_keyups: Optional[int]
    history_total_keyups: Optional[int]
    total_tx_time: Optional[int]
    history_tx_time: Optional[int]
    access_telephoneportal: Optional[bool]
    access_functionlist: Optional[bool]
    access_reverseautopatch: Optional[bool]
    seqno: Optional[int]
    timeout: Optional[int]
    apprptuptime: Optional[int]
    totalexecdcommands: Optional[int]
    current_link_count: Optional[int]

    def validate(self) -> bool:
        return bool(self.node_id and -90 <= self.lat <= 90 and -180 <= self.lon <= 180)


@dataclass
class OdsNodeDetailRecord:
    """MySQL ods_nodes_details 写入对象。"""

    node_id: int
    node_type: str
    callsign: Optional[str]
    frequency: Optional[str]
    tone: Optional[str]
    affiliation: Optional[str]
    site_name: Optional[str]
    is_active: Optional[bool]
    last_seen: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    app_version: Optional[str]
    ip: Optional[str]
    timezone_offset: Optional[float]
    is_nnx: Optional[bool]
    total_keyups: Optional[int]
    total_tx_time: Optional[int]
    access_webtransceiver: Optional[bool]
    access_telephoneportal: Optional[bool]
    access_functionlist: Optional[bool]
    access_reverseautopatch: Optional[bool]
    seqno: Optional[int]
    timeout: Optional[int]
    apprptuptime: Optional[int]
    total_execd_commands: Optional[int]
    max_uptime: Optional[int]
    current_link_count: Optional[int]
    linked_nodes: Optional[List[Dict[str, Any]]]
    links: Optional[Any]
    port: Optional[str]
    batch_no: Optional[str]

    def validate(self) -> bool:
        return isinstance(self.node_id, int) and self.node_id > 0
