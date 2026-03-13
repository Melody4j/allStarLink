"""
第二数据源 client 骨架。
"""

import logging
from typing import Any, Dict, Optional

from ...config.settings import APIConfig

logger = logging.getLogger(__name__)


class OtherSourceClient:
    """第二数据源 client。

    这里先提供最小可装配实现，目的是让主流程具备真正的 source 切换能力。
    等后续拿到第二数据源的真实接口契约后，再把这里替换成真实请求逻辑。
    """

    def __init__(self, api_config: APIConfig) -> None:
        self.api_config = api_config

    async def fetch_node_list(self) -> Optional[Dict[str, Any]]:
        logger.warning("OtherSourceClient 仍是骨架实现，尚未接入真实节点列表接口")
        return None

    async def fetch_node_detail(self, node_id: int) -> Optional[Dict[str, Any]]:
        logger.warning("OtherSourceClient 仍是骨架实现，尚未接入真实节点详情接口: %s", node_id)
        return None

    async def close(self) -> None:
        """预留统一关闭接口，便于与其他 source 保持一致。"""
        return None

