"""第二数据源的 source client 骨架。"""

import logging
from typing import Any, Dict, Optional

from ....config.settings import NetworkRuntimeConfig

logger = logging.getLogger(__name__)


class OtherSourceClient:
    """保留统一调用接口，后续接真实数据源时直接扩展这里。"""

    def __init__(self, network_config: NetworkRuntimeConfig) -> None:
        self.network_config = network_config

    async def fetch_node_list(self) -> Optional[Dict[str, Any]]:
        logger.warning("OtherSourceClient 仍是骨架实现，尚未接入真实节点列表接口")
        return None

    async def fetch_node_detail(self, node_id: int) -> Optional[Dict[str, Any]]:
        logger.warning("OtherSourceClient 仍是骨架实现，尚未接入真实节点详情接口: %s", node_id)
        return None

    async def close(self) -> None:
        return None
