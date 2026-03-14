"""第二数据源 parser 骨架。"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OtherSourceParser:
    """第二数据源 parser 骨架。"""

    def parse_node(self, data: Dict) -> Optional[Any]:
        logger.warning("OtherSourceParser 尚未实现 parse_node")
        return None

    def parse_linked_node(self, linked_node: Dict) -> Optional[Any]:
        logger.warning("OtherSourceParser 尚未实现 parse_linked_node")
        return None

    def parse_connections(
        self,
        node_id: int,
        connection_modes: str,
        linked_nodes: List[Dict],
        batch_no: Optional[str] = None,
    ) -> List[Any]:
        logger.warning("OtherSourceParser 尚未实现 parse_connections")
        return []
