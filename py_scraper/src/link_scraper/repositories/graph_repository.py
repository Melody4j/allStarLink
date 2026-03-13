"""
图存储仓储。
"""

import logging
from typing import TYPE_CHECKING, List

from .records import GraphConnectionRecord, GraphNodeRecord

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..database.neo4j_manager import Neo4jManager


class GraphRepository:
    """封装图数据库写入语义。

    这里保留 repository 的意义是把“图存储操作”与“业务同步顺序”分开：
    - service 决定先写谁、后写谁
    - repository 只负责把 record 写进图数据库

    后续如果底层从 Neo4jManager 再继续拆分，这一层可以保持稳定接口。
    """

    def __init__(self, neo4j_manager: "Neo4jManager") -> None:
        self.neo4j_manager = neo4j_manager

    async def upsert_node(
        self,
        node: GraphNodeRecord,
        preserve_counters: bool = False,
        preserve_uptime: bool = False,
    ) -> None:
        await self.neo4j_manager.update_node(
            node,
            preserve_counters=preserve_counters,
            preserve_uptime=preserve_uptime,
        )

    async def upsert_topology(
        self,
        node_id: str,
        connections: List[GraphConnectionRecord],
    ) -> None:
        await self.neo4j_manager.update_topology(node_id, connections)

    async def delete_node_by_unique_id(self, unique_id: str) -> bool:
        return await self.neo4j_manager.delete_node_by_unique_id(unique_id)
