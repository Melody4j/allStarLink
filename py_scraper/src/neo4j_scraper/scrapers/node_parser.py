"""
节点数据解析器

负责解析AllStarLink API返回的节点数据，包括：
1. 主节点数据解析
2. 连接节点数据解析
3. 连接关系解析
4. 节点类型和硬件类型识别
"""

import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
from ..models.node import Node
from ..models.connection import Connection
from ..config.constants import (
    CONNECTION_PREFIXES,
    NODE_TYPE_KEYWORDS,
    HARDWARE_KEYWORDS,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_UPTIME,
    DEFAULT_TOTAL_KEYUPS,
    DEFAULT_TOTAL_TX_TIME,
    DEFAULT_CONNECTIONS,
    NODE_TYPE_UNKNOWN,
    NODE_TYPE_HUB,
    NODE_TYPE_REPEATER,
    NODE_RANK_CORE,
    NODE_RANK_NORMAL,
    HARDWARE_TYPE_UNKNOWN,
    HARDWARE_TYPE_PERSONAL,
    HARDWARE_TYPE_INFRASTRUCTURE,
    HARDWARE_TYPE_EMBEDDED,
    SOURCE_ALLSTARLINK,
    SOURCE_OTHER,
    CONNECTION_STATUS_ACTIVE,
    CONNECTION_STATUS_INACTIVE,
    CONNECTION_DIRECTION_UNKNOWN
)

logger = logging.getLogger(__name__)


class NodeParser:
    """节点数据解析器

    职责：
    - 解析主节点数据
    - 解析连接节点数据
    - 解析连接关系
    - 识别节点类型和硬件类型
    """

    def parse_node(self, data: Dict) -> Optional[Node]:
        """解析主节点数据

        Args:
            data: API返回的节点数据

        Returns:
            Optional[Node]: 解析后的节点对象，失败返回None
        """
        try:
            stats = data.get('stats', {})

            # 主节点数据从stats.user_node中获取
            user_node = stats.get('user_node', {})
            if not user_node:
                logger.warning("stats.user_node为空，无法解析节点数据")
                return None

            # 节点server数据从stats.user_node.server获取
            server_info = user_node.get('server', {})

            # 连接的节点数据从stats.data.linkedNodes中获取
            node_data = stats.get('data', {})

            # 提取节点基本信息
            node_id_value = user_node.get('name', 0)

            # 解析节点类型和等级
            node_type, node_rank, features = self._parse_node_info(
                user_node.get('node_frequency', '')
            )

            # 解析业务信息（tone和location_desc）
            tone, location_desc = self._parse_business_info(
                user_node.get('node_tone', '')
            )

            # 解析硬件类型
            hardware_type = self._parse_hardware_type(
                server_info.get('SiteName', '')
            )

            # 构建节点对象
            node = Node(
                node_id=int(node_id_value) if isinstance(node_id_value, (int, str)) else 0,
                callsign=user_node.get('callsign', ''),
                node_type=node_type,
                lat=float(server_info.get('Latitude', DEFAULT_LATITUDE) or DEFAULT_LATITUDE),
                lon=float(server_info.get('Logitude', DEFAULT_LONGITUDE) or DEFAULT_LONGITUDE),
                uptime=int(node_data.get('apprptuptime', DEFAULT_UPTIME) or DEFAULT_UPTIME),
                total_keyups=int(node_data.get('totalkeyups', DEFAULT_TOTAL_KEYUPS) or DEFAULT_TOTAL_KEYUPS),
                total_tx_time=int(node_data.get('totaltxtime', DEFAULT_TOTAL_TX_TIME) or DEFAULT_TOTAL_TX_TIME),
                last_seen=datetime.now(),
                active=True,
                updated_at=datetime.now(),
                source=SOURCE_ALLSTARLINK,
                node_rank=node_rank,
                features=features,
                tone=tone,
                location_desc=location_desc,
                hardware_type=hardware_type,
                connections=len(node_data.get('linkedNodes', []))
            )

            return node

        except Exception as e:
            logger.error(f"解析节点数据失败: {e}")
            return None

    def parse_linked_node(self, linked_node: Dict) -> Optional[Node]:
        """解析连接的节点数据

        Args:
            linked_node: API返回的连接节点数据

        Returns:
            Optional[Node]: 解析后的节点对象，失败返回None
        """
        try:
            # 获取节点ID
            linked_node_id = linked_node.get('name')
            if not linked_node_id:
                logger.warning("连接节点缺少name字段")
                return None

            # 判断节点来源
            is_allstarlink = 'Node_ID' in linked_node

            # 解析节点类型和等级
            node_type, node_rank, features = self._parse_node_info(
                linked_node.get('node_frequency', '')
            )

            # 解析业务信息
            tone, location_desc = self._parse_business_info(
                linked_node.get('node_tone', '')
            )

            # 解析硬件类型（仅AllStarLink节点）
            if is_allstarlink:
                server_info = linked_node.get('server', {})
                hardware_type = self._parse_hardware_type(
                    server_info.get('SiteName', '')
                )
                lat = float(server_info.get('Latitude', DEFAULT_LATITUDE) or DEFAULT_LATITUDE)
                lon = float(server_info.get('Logitude', DEFAULT_LONGITUDE) or DEFAULT_LONGITUDE)
            else:
                hardware_type = HARDWARE_TYPE_UNKNOWN
                lat = DEFAULT_LATITUDE
                lon = DEFAULT_LONGITUDE

            # 构建节点对象
            node = Node(
                node_id=int(linked_node_id) if isinstance(linked_node_id, (int, str)) else 0,
                callsign=linked_node.get('callsign', ''),
                node_type=node_type,
                lat=lat,
                lon=lon,
                uptime=DEFAULT_UPTIME,
                total_keyups=DEFAULT_TOTAL_KEYUPS,
                total_tx_time=DEFAULT_TOTAL_TX_TIME,
                last_seen=datetime.now(),
                active=True,
                updated_at=datetime.now(),
                source=SOURCE_ALLSTARLINK if is_allstarlink else SOURCE_OTHER,
                node_rank=node_rank,
                features=features,
                tone=tone,
                location_desc=location_desc,
                hardware_type=hardware_type,
                connections=DEFAULT_CONNECTIONS
            )

            return node

        except Exception as e:
            logger.error(f"解析连接节点数据失败: {e}")
            return None

    def parse_connections(self, node_id: int, connection_modes: str, 
                        linked_nodes: List[Dict]) -> List[Connection]:
        """解析连接关系

        Args:
            node_id: 源节点ID
            connection_modes: 连接模式字符串，如"T62340,T68245"
            linked_nodes: 连接的节点列表

        Returns:
            List[Connection]: 解析后的连接关系列表
        """
        connections = []

        try:
            # 解析连接模式
            connection_dict = self._parse_connection_modes(connection_modes)

            # 处理每个连接的节点
            for linked_node in linked_nodes:
                target_id = linked_node.get('name')
                if not target_id:
                    continue

                # 获取连接状态和方向
                status = linked_node.get('Status', CONNECTION_STATUS_INACTIVE)
                direction = connection_dict.get(str(target_id), CONNECTION_DIRECTION_UNKNOWN)

                # 创建连接对象
                conn = Connection(
                    source_id=node_id,
                    target_id=int(target_id) if isinstance(target_id, (int, str)) else 0,
                    status=status,
                    direction=direction,
                    last_updated=datetime.now(),
                    active=(status == CONNECTION_STATUS_ACTIVE)
                )

                connections.append(conn)

            return connections

        except Exception as e:
            logger.error(f"解析连接关系失败: {e}")
            return []

    def _parse_node_info(self, frequency: str) -> tuple:
        """解析节点类型和特性

        Args:
            frequency: 节点频率字符串

        Returns:
            tuple: (node_type, node_rank, features)
        """
        node_type = NODE_TYPE_UNKNOWN
        node_rank = NODE_RANK_NORMAL
        features = []

        if not frequency:
            return node_type, node_rank, features

        # 中继模式：若包含数字+频率特征（如 444.900）
        if re.search(r'\d+\.\d+', frequency):
            node_type = NODE_TYPE_REPEATER
        # 枢纽模式：若包含文本描述（如 HUB, System, Network）
        elif any(keyword in frequency.upper() for keyword in NODE_TYPE_KEYWORDS[NODE_TYPE_HUB]):
            node_rank = NODE_RANK_CORE
            node_type = NODE_TYPE_HUB
            features.append(frequency)

        return node_type, node_rank, features

    def _parse_business_info(self, tone_str: str) -> tuple:
        """解析业务信息（tone和location_desc）

        Args:
            tone_str: 音调字符串

        Returns:
            tuple: (tone, location_desc)
        """
        tone = None
        location_desc = None

        if not tone_str:
            return tone, location_desc

        try:
            # 技术参数：若是纯数字（如 110.9）
            if tone_str.replace('.', '', 1).isdigit():
                tone = float(tone_str)
            # 业务信息：若是域名或URL
            elif '.' in tone_str and not tone_str.replace('.', '', 1).isdigit():
                location_desc = tone_str
        except (ValueError, TypeError):
            pass

        return tone, location_desc

    def _parse_hardware_type(self, site_name: str) -> str:
        """解析硬件类型

        Args:
            site_name: 站点名称

        Returns:
            str: 硬件类型
        """
        if not site_name:
            return HARDWARE_TYPE_UNKNOWN

        site_name_upper = site_name.upper()

        # Personal Station：如果包含 Shack, Home, Residence
        if any(keyword in site_name_upper for keyword in HARDWARE_KEYWORDS[HARDWARE_TYPE_PERSONAL]):
            return HARDWARE_TYPE_PERSONAL
        # Infrastructure：如果包含 Hub, Network, Data Center, Rack
        elif any(keyword in site_name_upper for keyword in HARDWARE_KEYWORDS[HARDWARE_TYPE_INFRASTRUCTURE]):
            return HARDWARE_TYPE_INFRASTRUCTURE
        # Embedded Node：如果包含 Pi, OrangePi, ClearNode, ARM, RASPBERRY PI
        elif any(keyword in site_name_upper for keyword in HARDWARE_KEYWORDS[HARDWARE_TYPE_EMBEDDED]):
            return HARDWARE_TYPE_EMBEDDED

        return HARDWARE_TYPE_UNKNOWN

    def _parse_connection_modes(self, connection_modes: str) -> Dict[str, str]:
        """解析连接模式字符串

        Args:
            connection_modes: 连接模式字符串，如"T62340,T68245"

        Returns:
            Dict[str, str]: 节点ID到连接模式的映射
        """
        connection_dict = {}

        if not connection_modes:
            return connection_dict

        for item in connection_modes.split(','):
            if not item:
                continue

            # 提取前缀和节点ID
            prefix = item[0] if item else ''
            node_id = item[1:] if len(item) > 1 else ''

            if node_id.isdigit():
                connection_dict[node_id] = CONNECTION_PREFIXES.get(prefix, CONNECTION_DIRECTION_UNKNOWN)

        return connection_dict
