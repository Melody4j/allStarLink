"""
OtherSource 探测任务 repository。
"""

import json
from dataclasses import asdict

from .domain import OtherSourceProbeResult


class OtherSourceProbeRepository:
    """保存第二数据源最近一次探测结果。"""

    def __init__(self, redis_client) -> None:
        self.redis_client = redis_client
        self.redis_key = "other_source:probe:last_result"

    async def save(self, result: OtherSourceProbeResult) -> None:
        payload = asdict(result)
        payload["checked_at"] = result.checked_at.isoformat()
        await self.redis_client.set(self.redis_key, json.dumps(payload, ensure_ascii=True))
