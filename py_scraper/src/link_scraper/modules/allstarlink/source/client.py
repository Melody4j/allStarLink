"""AllStarLink 数据源 HTTP 客户端。"""

import asyncio
import logging
from typing import Optional

import aiohttp

from ....config.settings import AllStarLinkSourceConfig, NetworkRuntimeConfig
from ..models.payload import AslNodeDetailsPayload, AslNodeOnlineListPayload

logger = logging.getLogger(__name__)


class AllStarLinkClient:
    """封装 AllStarLink 接口请求和基础重试逻辑。"""

    def __init__(
        self,
        source_config: AllStarLinkSourceConfig,
        network_config: NetworkRuntimeConfig,
    ) -> None:
        self.source_config = source_config
        self.network_config = network_config
        self.session: Optional[aiohttp.ClientSession] = None

    async def fetch_node_list(self) -> Optional[AslNodeOnlineListPayload]:
        """抓取在线节点列表，并转换成 payload 模型。"""
        session = await self._get_session()
        async with session.post(self.source_config.node_online_list_url) as response:
            if response.status != 200:
                logger.error("获取节点列表失败，状态码: %s", response.status)
                return None
            return AslNodeOnlineListPayload.from_dict(await response.json())

    async def fetch_node_detail(self, node_id: int) -> Optional[AslNodeDetailsPayload]:
        """抓取单个节点详情，遇到限流时按共享网络配置退避重试。"""
        url = f"{self.source_config.node_details_url}/{node_id}"
        session = await self._get_session()

        for attempt in range(self.network_config.max_retries):
            try:
                async with session.get(url) as response:
                    if response.status == 429:
                        logger.warning(
                            "触发速率限制，等待 %s 秒后重试",
                            self.network_config.cooldown_429,
                        )
                        await asyncio.sleep(self.network_config.cooldown_429)
                        continue

                    if response.status != 200:
                        logger.warning("获取节点 %s 详情失败，状态码: %s", node_id, response.status)
                        return None

                    return AslNodeDetailsPayload.from_dict(await response.json())
            except Exception as exc:
                logger.error(
                    "获取节点 %s 详情异常（第 %s/%s 次）: %s",
                    node_id,
                    attempt + 1,
                    self.network_config.max_retries,
                    exc,
                    exc_info=True,
                )
                if attempt < self.network_config.max_retries - 1:
                    await asyncio.sleep(self.network_config.retry_backoff ** (attempt + 1))

        logger.error("获取节点 %s 详情失败，已达到最大重试次数", node_id)
        return None

    async def close(self) -> None:
        """关闭共享会话，避免连接泄漏。"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """懒初始化 aiohttp 会话，供同一轮任务复用。"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
