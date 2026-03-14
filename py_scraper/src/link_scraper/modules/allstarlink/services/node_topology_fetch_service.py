"""`node_topology` 任务的抓取服务。"""

import logging
from typing import Dict, Optional

from ....sources import SourceClient

logger = logging.getLogger(__name__)


class NodeTopologyFetchService:
    """负责抓取单个节点详情。"""

    def __init__(self, source_client: SourceClient) -> None:
        self.source_client = source_client

    async def fetch_node_detail(self, node_id: int) -> Optional[Dict]:
        logger.debug("node_topology: 开始抓取节点 %s 详情", node_id)
        payload = await self.source_client.fetch_node_detail(node_id)
        if payload is None:
            logger.warning("node_topology: 节点 %s 详情抓取失败或返回为空", node_id)
            return None
        return payload
