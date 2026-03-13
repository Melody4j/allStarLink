"""
ODS节点详情数据模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Any
import json


@dataclass
class OdsNodeDetail:
    """ODS节点详情数据模型

    对应数据库表: ods_nodes_details
    """
    node_id: int
    node_type: str = 'ALLSTARLINK'
    callsign: Optional[str] = None
    frequency: Optional[str] = None
    tone: Optional[str] = None
    affiliation: Optional[str] = None
    site_name: Optional[str] = None
    is_active: Optional[bool] = None
    last_seen: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    app_version: Optional[str] = None
    ip: Optional[str] = None
    timezone_offset: Optional[float] = None
    is_nnx: Optional[bool] = None
    total_keyups: Optional[int] = None
    total_tx_time: Optional[int] = None
    access_webtransceiver: Optional[bool] = None
    access_telephoneportal: Optional[bool] = None
    access_functionlist: Optional[bool] = None
    access_reverseautopatch: Optional[bool] = None
    seqno: Optional[int] = None
    timeout: Optional[int] = None
    apprptuptime: Optional[int] = None
    total_execd_commands: Optional[int] = None
    max_uptime: Optional[int] = None
    current_link_count: Optional[int] = None
    linked_nodes: Optional[List[Dict]] = None
    links: Optional[Any] = None
    port: Optional[str] = None
    batch_no: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'node_id': self.node_id,
            'node_type': self.node_type,
            'callsign': self.callsign,
            'frequency': self.frequency,
            'tone': self.tone,
            'affiliation': self.affiliation,
            'site_name': self.site_name,
            'is_active': 1 if self.is_active else 0 if self.is_active is not None else None,
            'last_seen': self.last_seen,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'app_version': self.app_version,
            'ip': self.ip,
            'timezone_offset': self.timezone_offset,
            'is_nnx': 1 if self.is_nnx else 0 if self.is_nnx is not None else None,
            'total_keyups': self.total_keyups,
            'total_tx_time': self.total_tx_time,
            'access_webtransceiver': 1 if self.access_webtransceiver else 0 if self.access_webtransceiver is not None else None,
            'access_telephoneportal': 1 if self.access_telephoneportal else 0 if self.access_telephoneportal is not None else None,
            'access_functionlist': 1 if self.access_functionlist else 0 if self.access_functionlist is not None else None,
            'access_reverseautopatch': 1 if self.access_reverseautopatch else 0 if self.access_reverseautopatch is not None else None,
            'seqno': self.seqno,
            'timeout': self.timeout,
            'apprptuptime': self.apprptuptime,
            'total_execd_commands': self.total_execd_commands,
            'max_uptime': self.max_uptime,
            'current_link_count': self.current_link_count,
            'linked_nodes': json.dumps(self.linked_nodes) if self.linked_nodes else None,
            'links': json.dumps(self.links) if self.links is not None else None,
            'port': self.port,
            'batch_no': int(self.batch_no) if self.batch_no is not None else None
        }

    def validate(self) -> bool:
        """验证数据有效性"""
        # 验证节点ID
        if not isinstance(self.node_id, int) or self.node_id <= 0:
            return False

        # 验证坐标
        if self.latitude is not None and not (-90 <= self.latitude <= 90):
            return False
        if self.longitude is not None and not (-180 <= self.longitude <= 180):
            return False

        # 验证统计值
        if self.total_keyups is not None and self.total_keyups < 0:
            return False
        if self.total_tx_time is not None and self.total_tx_time < 0:
            return False

        return True

    @classmethod
    def from_node_data(cls, node_data: Dict) -> 'OdsNodeDetail':
        """从节点数据创建ODS节点详情对象

        Args:
            node_data: 从API获取的节点数据

        Returns:
            OdsNodeDetail: ODS节点详情对象
        """
        stats = node_data.get('stats', {})
        user_node = stats.get('user_node', {})
        server_info = user_node.get('server', {})
        data = stats.get('data', {})
        linked_nodes = data.get('linkedNodes', [])

        # 解析is_nnx
        is_nnx = None
        is_nnx_str = user_node.get('is_nnx', '')
        if is_nnx_str:
            is_nnx = is_nnx_str.upper() == 'YES'

        # 解析访问权限
        access_webtransceiver = user_node.get('access_webtransceiver', '0') == '1'
        access_telephoneportal = user_node.get('access_telephoneportal', '0') == '1'
        access_functionlist = user_node.get('access_functionlist', '0') == '1'
        access_reverseautopatch = user_node.get('access_reverseautopatch', '0') == '1'

        # linked_nodes保留结构化列表，links保留原始 nodes 字符串
        links_value = data.get('nodes')

        # 解析端口
        port = None
        if 'udpport' in server_info:
            port = str(server_info.get('udpport'))
        elif 'port' in user_node:
            port = str(user_node.get('port'))

        return cls(
            node_id=int(user_node.get('name', 0)),
            node_type='ALLSTARLINK',
            callsign=user_node.get('callsign'),
            frequency=user_node.get('node_frequency'),
            tone=user_node.get('node_tone'),
            affiliation=server_info.get('Affiliation'),
            site_name=server_info.get('SiteName'),
            is_active=True,  # 从API获取的数据都是在线节点
            last_seen=datetime.now(),
            latitude=float(server_info.get('Latitude', 0.0) or 0.0) or None,
            longitude=float(server_info.get('Logitude', 0.0) or 0.0) or None,
            app_version=data.get('apprptvers'),
            ip=user_node.get('ipaddr'),
            timezone_offset=None,  # API中没有提供
            is_nnx=is_nnx,
            total_keyups=int(data.get('totalkeyups', 0) or 0),
            total_tx_time=int(data.get('totaltxtime', 0) or 0),
            access_webtransceiver=access_webtransceiver,
            access_telephoneportal=access_telephoneportal,
            access_functionlist=access_functionlist,
            access_reverseautopatch=access_reverseautopatch,
            seqno=int(data.get('seqno', 0) or 0),
            timeout=int(data.get('timeouts', 0) or 0),
            apprptuptime=int(data.get('apprptuptime', 0) or 0),
            total_execd_commands=int(data.get('totalexecdcommands', 0) or 0),
            max_uptime=None,  # 需要从历史数据计算
            current_link_count=len(linked_nodes),
            linked_nodes=linked_nodes,
            links=links_value,
            port=port
        )
