"""
AllStarLink API client.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from ...config.settings import APIConfig

logger = logging.getLogger(__name__)


class AllStarLinkClient:
    """Encapsulates AllStarLink HTTP requests and retry behavior."""

    def __init__(self, api_config: APIConfig) -> None:
        self.api_config = api_config
        self.session: Optional[aiohttp.ClientSession] = None

    async def fetch_node_list(self) -> Optional[Dict[str, Any]]:
        session = await self._get_session()

        async with session.post(self.api_config.node_list_url) as response:
            if response.status != 200:
                logger.error("获取节点列表失败，状态码: %s", response.status)
                return None

            return await response.json()

    async def fetch_node_detail(self, node_id: int) -> Optional[Dict[str, Any]]:
        url = f"{self.api_config.base_url}/{node_id}"
        session = await self._get_session()
        logger.debug("请求URL: %s", url)

        for attempt in range(self.api_config.max_retries):
            try:
                logger.debug(
                    "尝试获取节点 %s 数据 (%s/%s)",
                    node_id,
                    attempt + 1,
                    self.api_config.max_retries,
                )
                async with session.get(url) as response:
                    if response.status == 429:
                        logger.warning("触发速率限制，冷却 %s 秒", self.api_config.cooldown_429)
                        await asyncio.sleep(self.api_config.cooldown_429)
                        continue

                    if response.status != 200:
                        logger.warning("获取节点 %s 数据失败，状态码: %s", node_id, response.status)
                        return None

                    return await response.json()
            except Exception as exc:
                logger.error(
                    "获取节点 %s 数据异常 (尝试 %s/%s): %s",
                    node_id,
                    attempt + 1,
                    self.api_config.max_retries,
                    exc,
                    exc_info=True,
                )
                if attempt < self.api_config.max_retries - 1:
                    await asyncio.sleep(self.api_config.retry_backoff ** (attempt + 1))

        logger.error("获取节点 %s 数据失败，已达到最大重试次数", node_id)
        return None

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

