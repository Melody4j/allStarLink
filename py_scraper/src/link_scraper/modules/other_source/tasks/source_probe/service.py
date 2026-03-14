"""OtherSource 探测任务服务。"""

import logging
from datetime import datetime

from .....app.context import AppContext
from .....sources import build_source_components
from .domain import OtherSourceProbeResult
from .repository import OtherSourceProbeRepository

logger = logging.getLogger(__name__)


class OtherSourceProbeService:
    """最小探测服务，只验证 source 模块装配链路是否可用。"""

    def __init__(self, context: AppContext) -> None:
        self.context = context
        # 这里显式指定 other_source，避免受当前全局 source_name 影响。
        self.source_components = build_source_components("other_source", context.settings)
        self.repository = OtherSourceProbeRepository(context.redis_client)

    async def run_probe(self) -> OtherSourceProbeResult:
        payload = await self.source_components.client.fetch_node_list()
        # 当前 second source 还是骨架实现，因此允许拿不到真实 payload。
        success = payload is not None
        message = "other_source payload fetched" if success else "other_source payload unavailable"

        result = OtherSourceProbeResult(
            source_name="other_source",
            checked_at=datetime.now(),
            success=success,
            message=message,
        )
        await self.repository.save(result)
        logger.info("OtherSource probe finished: success=%s message=%s", result.success, result.message)
        return result

    async def close(self) -> None:
        await self.source_components.client.close()
