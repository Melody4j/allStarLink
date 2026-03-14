"""`node_topology` 任务的解析服务。"""

import logging
from typing import Dict, Optional

from ....sources import SourceMapper
from ..models.domain import CanonicalNodeBundle

logger = logging.getLogger(__name__)


class NodeTopologyParseService:
    """负责把节点详情 payload 转成任务领域对象。"""

    def __init__(self, source_mapper: SourceMapper) -> None:
        self.source_mapper = source_mapper

    def parse_node_detail(
        self,
        payload: Dict,
        batch_no: Optional[str],
    ) -> Optional[CanonicalNodeBundle]:
        logger.debug("node_topology: 开始解析节点详情，batch_no=%s", batch_no)
        bundle = self.source_mapper.map_node_detail(payload, batch_no)
        if bundle is None:
            logger.warning("node_topology: 节点详情解析失败")
            return None
        return bundle
