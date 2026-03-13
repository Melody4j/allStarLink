"""
第二数据源 mapper 骨架。
"""

import logging
from typing import Any, Dict, List, Optional

from ...domain.models import CanonicalNodeBundle
from .parser import OtherSourceParser

logger = logging.getLogger(__name__)


class OtherSourceMapper:
    """第二数据源 mapper 骨架。"""

    def __init__(self, parser: Optional[OtherSourceParser] = None) -> None:
        self.parser = parser or OtherSourceParser()

    def map_node_list(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.warning("OtherSourceMapper 尚未实现 map_node_list")
        return []

    def map_node_detail(
        self,
        payload: Dict[str, Any],
        batch_no: Optional[str] = None,
    ) -> Optional[CanonicalNodeBundle]:
        logger.warning("OtherSourceMapper 尚未实现 map_node_detail")
        return None
