"""
解析服务。
"""

import logging
from typing import Dict, Optional

from ..domain.models import CanonicalNodeBundle
from ..sources.base import SourceMapper

logger = logging.getLogger(__name__)


class NodeParseService:
    """负责把原始 payload 转换为统一领域模型。

    这一层的职责是把“数据源差异”收口到 source mapper，
    同时把 APIWorker 从具体解析细节中解耦出来。
    后续如果引入第二个数据源，worker 不需要知道字段结构差异，
    只需要拿到 CanonicalNodeBundle 继续走同步流程即可。
    """

    def __init__(self, source_mapper: SourceMapper) -> None:
        self.source_mapper = source_mapper

    def parse_node_detail(
        self,
        payload: Dict,
        batch_no: Optional[str],
    ) -> Optional[CanonicalNodeBundle]:
        """解析节点详情 payload。

        这里保留中文日志，方便后续联调时直接判断失败是在抓取阶段还是解析阶段。
        """
        logger.debug("解析服务: 开始解析节点详情，批次号=%s", batch_no)
        bundle = self.source_mapper.map_node_detail(payload, batch_no)
        if bundle is None:
            logger.warning("解析服务: 节点详情解析失败")
            return None

        logger.debug(
            "解析服务: 解析完成，主节点=%s，连接节点数=%s，关系数=%s",
            bundle.primary_node.node_id,
            len(bundle.linked_nodes),
            len(bundle.connections),
        )
        return bundle

