"""AllStarLink payload 解析器。"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

from .constants import (
    CONNECTION_DIRECTION_UNKNOWN,
    CONNECTION_PREFIXES,
    CONNECTION_STATUS_ACTIVE,
    CONNECTION_STATUS_INACTIVE,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_TOTAL_KEYUPS,
    DEFAULT_TOTAL_TX_TIME,
    HARDWARE_KEYWORDS,
    HARDWARE_TYPE_EMBEDDED,
    HARDWARE_TYPE_INFRASTRUCTURE,
    HARDWARE_TYPE_PERSONAL,
    HARDWARE_TYPE_UNKNOWN,
    NODE_RANK_HUB,
    NODE_RANK_REPEATER,
    NODE_RANK_UNKNOWN,
    NODE_TYPE_ALLSTARLINK,
    NODE_TYPE_KEYWORDS,
    NODE_TYPE_OTHERS,
)
from ..models.domain import CanonicalConnection, CanonicalNode
from ..models.payload import AslNodeDetailsPayload

logger = logging.getLogger(__name__)


class AllStarLinkParser:
    """把 AllStarLink 详情响应解析成 canonical 模型。"""

    def parse_node(self, data: Dict | AslNodeDetailsPayload) -> Optional[CanonicalNode]:
        try:
            payload = data.raw_payload if isinstance(data, AslNodeDetailsPayload) else data
            stats = payload.get("stats", {})
            user_node = stats.get("user_node", {})
            if not user_node:
                logger.warning("stats.user_node 为空，无法解析节点数据")
                return None

            server_info = user_node.get("server", {})
            node_data = stats.get("data", {})
            node_id_value = user_node.get("name", "")

            node_type, node_rank, features = self._parse_node_info(user_node.get("node_frequency", ""))
            node_type = NODE_TYPE_ALLSTARLINK if node_id_value else NODE_TYPE_OTHERS
            tone, location_desc = self._parse_business_info(user_node.get("node_tone", ""))
            hardware_type = self._parse_hardware_type(server_info.get("SiteName", ""))

            return CanonicalNode(
                node_id=str(node_id_value) if node_id_value else "",
                callsign=user_node.get("callsign", ""),
                source_name="allstarlink",
                node_type=node_type,
                lat=float(server_info.get("Latitude", DEFAULT_LATITUDE) or DEFAULT_LATITUDE),
                lon=float(server_info.get("Logitude", DEFAULT_LONGITUDE) or DEFAULT_LONGITUDE),
                apprptuptime=int(node_data.get("apprptuptime", 0) or 0),
                total_keyups=int(node_data.get("totalkeyups", DEFAULT_TOTAL_KEYUPS) or DEFAULT_TOTAL_KEYUPS),
                total_tx_time=int(node_data.get("totaltxtime", DEFAULT_TOTAL_TX_TIME) or DEFAULT_TOTAL_TX_TIME),
                last_seen=datetime.now(),
                active=True,
                updated_at=datetime.now(),
                node_rank=node_rank,
                features=features,
                tone=tone,
                location_desc=location_desc,
                hardware_type=hardware_type,
                connections=len(node_data.get("linkedNodes", [])),
                owner=user_node.get("User_ID", ""),
                affiliation=server_info.get("Affiliation", ""),
                site_name=server_info.get("Server_Name", ""),
                access_webtransceiver=user_node.get("access_webtransceiver", "0") == "1",
                ip_address=user_node.get("ipaddr", ""),
                timezone_offset=None,
                is_nnx=user_node.get("is_nnx", "No") == "Yes",
                history_total_keyups=0,
                history_tx_time=0,
                access_telephoneportal=user_node.get("access_telephoneportal", "0") == "1",
                access_functionlist=user_node.get("access_functionlist", "0") == "1",
                access_reverseautopatch=user_node.get("access_reverseautopatch", "0") == "1",
                seqno=int(node_data.get("seqno", 0) or 0),
                timeout=int(node_data.get("timeouts", 0) or 0),
                totalexecdcommands=int(node_data.get("totalexecdcommands", 0) or 0),
            )
        except Exception as exc:
            logger.error("解析节点数据失败: %s", exc, exc_info=True)
            return None

    def parse_linked_node(self, linked_node: Dict) -> Optional[CanonicalNode]:
        try:
            linked_node_id = linked_node.get("name")
            if not linked_node_id:
                logger.warning("连接节点缺少 name 字段")
                return None

            is_allstarlink = "Node_ID" in linked_node
            node_type, node_rank, features = self._parse_node_info(linked_node.get("node_frequency", ""))
            node_type = NODE_TYPE_ALLSTARLINK if linked_node_id else NODE_TYPE_OTHERS
            tone, location_desc = self._parse_business_info(linked_node.get("node_tone", ""))

            if is_allstarlink:
                server_info = linked_node.get("server", {})
                hardware_type = self._parse_hardware_type(server_info.get("SiteName", ""))
                lat = float(server_info.get("Latitude", DEFAULT_LATITUDE) or DEFAULT_LATITUDE)
                lon = float(server_info.get("Logitude", DEFAULT_LONGITUDE) or DEFAULT_LONGITUDE)
            else:
                hardware_type = HARDWARE_TYPE_UNKNOWN
                lat = DEFAULT_LATITUDE
                lon = DEFAULT_LONGITUDE

            return CanonicalNode(
                node_id=str(linked_node_id),
                callsign=linked_node.get("callsign", ""),
                source_name="allstarlink" if is_allstarlink else "other",
                node_type=node_type,
                lat=lat,
                lon=lon,
                apprptuptime=None,
                total_keyups=None,
                total_tx_time=None,
                last_seen=datetime.now(),
                active=True,
                updated_at=datetime.now(),
                node_rank=node_rank,
                features=features,
                tone=tone,
                location_desc=location_desc,
                hardware_type=hardware_type,
                connections=None,
                record_kind="stub",
                data_completeness="partial",
            )
        except Exception as exc:
            logger.error("解析连接节点数据失败: %s", exc, exc_info=True)
            return None

    def parse_connections(
        self,
        node_id: int,
        connection_modes: str,
        linked_nodes: List[Dict],
        batch_no: Optional[str] = None,
    ) -> List[CanonicalConnection]:
        connections: List[CanonicalConnection] = []
        try:
            connection_dict = self._parse_connection_modes(connection_modes)
            for linked_node in linked_nodes:
                target_id = linked_node.get("name")
                if not target_id:
                    continue
                status = linked_node.get("Status", CONNECTION_STATUS_INACTIVE)
                direction = connection_dict.get(str(target_id), CONNECTION_DIRECTION_UNKNOWN)
                connections.append(
                    CanonicalConnection(
                        source_id=str(node_id),
                        target_id=str(target_id),
                        status=status,
                        direction=direction,
                        last_updated=datetime.now(),
                        active=(status == CONNECTION_STATUS_ACTIVE),
                        batch_no=batch_no,
                        source_name="allstarlink",
                    )
                )
            return connections
        except Exception as exc:
            logger.error("解析连接关系失败: %s", exc, exc_info=True)
            return []

    def _parse_node_info(self, frequency: str) -> tuple:
        node_type = NODE_TYPE_OTHERS
        node_rank = NODE_RANK_UNKNOWN
        features = []
        if not frequency:
            return node_type, node_rank, features
        if re.search(r"\d+\.\d+", frequency):
            node_rank = NODE_RANK_REPEATER
        elif any(keyword in frequency.upper() for keyword in NODE_TYPE_KEYWORDS[NODE_RANK_HUB]):
            node_rank = NODE_RANK_HUB
            features.append(frequency)
        return node_type, node_rank, features

    def _parse_business_info(self, tone_str: str) -> tuple:
        tone = None
        location_desc = None
        if not tone_str:
            return tone, location_desc
        try:
            if tone_str.replace(".", "", 1).isdigit():
                tone = float(tone_str)
            elif "." in tone_str and not tone_str.replace(".", "", 1).isdigit():
                location_desc = tone_str
        except (ValueError, TypeError):
            pass
        return tone, location_desc

    def _parse_hardware_type(self, site_name: str) -> str:
        if not site_name:
            return HARDWARE_TYPE_UNKNOWN
        site_name_upper = site_name.upper()
        if any(keyword in site_name_upper for keyword in HARDWARE_KEYWORDS[HARDWARE_TYPE_PERSONAL]):
            return HARDWARE_TYPE_PERSONAL
        if any(keyword in site_name_upper for keyword in HARDWARE_KEYWORDS[HARDWARE_TYPE_INFRASTRUCTURE]):
            return HARDWARE_TYPE_INFRASTRUCTURE
        if any(keyword in site_name_upper for keyword in HARDWARE_KEYWORDS[HARDWARE_TYPE_EMBEDDED]):
            return HARDWARE_TYPE_EMBEDDED
        return HARDWARE_TYPE_UNKNOWN

    def _parse_connection_modes(self, connection_modes: str) -> Dict[str, str]:
        connection_dict: Dict[str, str] = {}
        if not connection_modes:
            return connection_dict
        for item in connection_modes.split(","):
            if not item:
                continue
            prefix = item[0] if item else ""
            node_id = item[1:] if len(item) > 1 else ""
            if node_id:
                connection_dict[node_id] = CONNECTION_PREFIXES.get(prefix, CONNECTION_DIRECTION_UNKNOWN)
        return connection_dict
