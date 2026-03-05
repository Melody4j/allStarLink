"""
连接关系模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from ..config.constants import (
    CONNECTION_STATUS_INACTIVE,
    CONNECTION_DIRECTION_UNKNOWN
)


@dataclass
class Connection:
    """连接关系模型"""
    source_id: int
    target_id: int
    status: Literal['Active', 'Inactive']
    direction: Literal['Transceive', 'RX Only', 'Local', 'Permanent', 'Unknown']
    last_updated: datetime
    active: bool

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'status': self.status,
            'direction': self.direction,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'active': self.active
        }

    def validate(self) -> bool:
        """验证数据有效性"""
        # 验证节点ID
        if not isinstance(self.source_id, int) or self.source_id <= 0:
            return False
        if not isinstance(self.target_id, int) or self.target_id <= 0:
            return False

        # 验证状态和方向
        if self.status not in ['Active', 'Inactive']:
            return False
        if self.direction not in ['Transceive', 'RX Only', 'Local', 'Permanent', 'Unknown']:
            return False

        # 验证时间
        if not self.last_updated:
            return False

        return True

    @classmethod
    def create_default(cls, source_id: int, target_id: int) -> 'Connection':
        """创建默认连接"""
        now = datetime.now()
        return cls(
            source_id=source_id,
            target_id=target_id,
            status=CONNECTION_STATUS_INACTIVE,
            direction=CONNECTION_DIRECTION_UNKNOWN,
            last_updated=now,
            active=False
        )
