"""
ODS 写入服务。
"""

import logging

from ..domain.models import CanonicalNodeBundle
from ..repositories.mappers import OdsMapper
from ..repositories import OdsRepository

logger = logging.getLogger(__name__)


class OdsWriteService:
    """负责 ODS 明细构建与写入。

    单独拆出来的意义在于：
    1. ODS 的字段语义和图/维表不同
    2. ODS 当前仍然依赖部分原始 payload 语义
    3. 后续如果要做按 source 分流、批量写入、异步落盘，这里会是稳定入口
    """

    def __init__(self, ods_repository: OdsRepository) -> None:
        self.ods_repository = ods_repository

    async def write_bundle(self, bundle: CanonicalNodeBundle) -> None:
        """写入单个节点聚合对应的 ODS 快照。"""
        ods_detail = OdsMapper.map_bundle(bundle)
        await self.ods_repository.insert_detail(ods_detail)
        logger.info("ODS服务: 成功写入节点 %s 的ODS详情", bundle.primary_node.node_id)
