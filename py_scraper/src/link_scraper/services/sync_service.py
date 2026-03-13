"""
同步服务。
"""

import logging

from ..domain.models import CanonicalNodeBundle
from ..repositories.mappers import DimNodeMapper, GraphMapper
from ..repositories import DimNodeRepository, GraphRepository

logger = logging.getLogger(__name__)


class NodeSyncService:
    """负责把统一领域模型同步到图和维表。

    这一层承接的是“业务同步顺序”而不是底层数据库细节：
    1. 先写主节点图数据
    2. 再写连接节点图数据，确保关系创建前节点存在
    3. 再写图关系
    4. 再按保留计数器/在线时长策略回写连接节点
    5. 最后写 MySQL dim_nodes

    这段顺序就是当前系统的真实业务策略，所以需要集中放在一个 service 中，
    不能散落回 worker 或 repository。
    """

    def __init__(
        self,
        graph_repository: GraphRepository,
        dim_node_repository: DimNodeRepository,
    ) -> None:
        self.graph_repository = graph_repository
        self.dim_node_repository = dim_node_repository

    async def sync_bundle(self, bundle: CanonicalNodeBundle) -> None:
        """按当前既定顺序同步一个节点聚合。"""
        primary_graph_record = GraphMapper.map_node(bundle.primary_node)
        await self.graph_repository.upsert_node(primary_graph_record)

        logger.info("同步服务: 节点 %s 有 %s 个连接节点", bundle.primary_node.node_id, len(bundle.linked_nodes))

        linked_graph_records = [GraphMapper.map_node(node) for node in bundle.linked_nodes]

        # 这里先做第一轮连接节点写入，目的是确保图中的目标节点已经存在，
        # 否则后续创建 CONNECTED_TO 关系时会因为目标节点缺失而被跳过。
        for linked_record in linked_graph_records:
            await self.graph_repository.upsert_node(linked_record, preserve_uptime=True)

        connection_records = GraphMapper.map_connections(bundle.connections)
        if connection_records:
            await self.graph_repository.upsert_topology(
                bundle.primary_node.node_id,
                connection_records,
            )

        # 第二轮连接节点回写沿用旧逻辑：
        # 如果这些节点之前已经被完整抓取过，就不能让占位数据把真实统计值覆盖掉，
        # 所以这里继续启用 preserve_counters / preserve_uptime。
        for linked_record in linked_graph_records:
            await self.graph_repository.upsert_node(
                linked_record,
                preserve_counters=True,
                preserve_uptime=True,
            )

        primary_dim_record = DimNodeMapper.map_node(bundle.primary_node)
        await self.dim_node_repository.update_node(primary_dim_record)

        mysql_update_count = 0
        for linked_node in bundle.linked_nodes:
            linked_dim_record = DimNodeMapper.map_node(linked_node)
            await self.dim_node_repository.update_node(
                linked_dim_record,
                update_current_link_count=False,
            )
            mysql_update_count += 1

        if mysql_update_count > 0:
            logger.info("同步服务: 已更新 %s 个连接节点到MySQL", mysql_update_count)
