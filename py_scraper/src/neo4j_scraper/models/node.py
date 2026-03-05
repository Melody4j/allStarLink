"""
节点数据模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from ..config.constants import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_UPTIME,
    DEFAULT_TOTAL_KEYUPS,
    DEFAULT_TOTAL_TX_TIME,
    DEFAULT_CONNECTIONS,
    NODE_TYPE_UNKNOWN,
    NODE_RANK_NORMAL,
    HARDWARE_TYPE_UNKNOWN,
    SOURCE_ALLSTARLINK
)


@dataclass
class Node:
    """节点数据模型"""
    node_id: int
    callsign: str
    node_type: str
    lat: float
    lon: float
    uptime: int
    total_keyups: int
    total_tx_time: int
    last_seen: datetime
    active: bool
    updated_at: datetime
    source: str
    node_rank: str
    features: List[str]
    tone: Optional[float]
    location_desc: Optional[str]
    hardware_type: str
    connections: int

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'node_id': self.node_id,
            'callsign': self.callsign,
            'node_type': self.node_type,
            'lat': self.lat,
            'lon': self.lon,
            'uptime': self.uptime,
            'total_keyups': self.total_keyups,
            'total_tx_time': self.total_tx_time,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'active': self.active,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'source': self.source,
            'node_rank': self.node_rank,
            'features': self.features,
            'tone': self.tone,
            'location_desc': self.location_desc,
            'hardware_type': self.hardware_type,
            'connections': self.connections
        }

    def validate(self) -> bool:
        """验证数据有效性"""
        # 验证节点ID
        if not isinstance(self.node_id, int) or self.node_id <= 0:
            return False

        # 验证坐标
        if not (-90 <= self.lat <= 90) or not (-180 <= self.lon <= 180):
            return False

        # 验证时间
        if self.last_seen and self.updated_at and self.last_seen > self.updated_at:
            return False

        # 验证统计值
        if self.uptime < 0 or self.total_keyups < 0 or self.total_tx_time < 0:
            return False

        return True

    @classmethod
    def create_default(cls, node_id: int) -> 'Node':
        """创建默认节点"""
        now = datetime.now()
        return cls(
            node_id=node_id,
            callsign='',
            node_type=NODE_TYPE_UNKNOWN,
            lat=DEFAULT_LATITUDE,
            lon=DEFAULT_LONGITUDE,
            uptime=DEFAULT_UPTIME,
            total_keyups=DEFAULT_TOTAL_KEYUPS,
            total_tx_time=DEFAULT_TOTAL_TX_TIME,
            last_seen=now,
            active=False,
            updated_at=now,
            source=SOURCE_OTHER,
            node_rank=NODE_RANK_NORMAL,
            features=[],
            tone=None,
            location_desc=None,
            hardware_type=HARDWARE_TYPE_UNKNOWN,
            connections=DEFAULT_CONNECTIONS
        )
