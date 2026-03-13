"""
抓取服务。
"""

import logging
from typing import Dict, Optional

from ..sources.base import SourceClient

logger = logging.getLogger(__name__)


class NodeFetchService:
    """负责节点详情抓取。

    这里单独拆成 service 的目的不是“多一层包装”，而是把：
    1. worker 的任务消费职责
    2. source client 的底层 HTTP 职责
    3. 抓取结果的业务日志语义
    明确分开。

    这样后续如果要补缓存、熔断、抓取指标、失败重排等逻辑，
    都可以放在这个 service 中，而不是继续把 APIWorker 变回大类。
    """

    def __init__(self, source_client: SourceClient) -> None:
        self.source_client = source_client

    async def fetch_node_detail(self, node_id: int) -> Optional[Dict]:
        """抓取单个节点详情。

        保持当前行为最重要，所以这里仍然直接复用 source client 的返回值，
        不在这一层改变数据结构；真正的结构转换留给 parse service。
        """
        logger.debug("抓取服务: 开始抓取节点 %s 的详情数据", node_id)
        payload = await self.source_client.fetch_node_detail(node_id)
        if payload is None:
            logger.warning("抓取服务: 节点 %s 详情抓取失败或返回为空", node_id)
            return None

        logger.debug("抓取服务: 节点 %s 详情抓取完成", node_id)
        return payload

