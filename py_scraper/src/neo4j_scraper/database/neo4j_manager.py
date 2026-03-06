"""
Neo4j数据库管理器

负责与Neo4j图数据库的交互，包括：
1. 连接管理
2. 节点数据的插入和更新
3. 连接关系的管理
4. 失效关系的清理
"""

import logging
from typing import List, Optional
from datetime import datetime
from neo4j import AsyncGraphDatabase
from .base import BaseDatabaseManager
from ..models.node import Node
from ..models.connection import Connection
from ..config.constants import STALE_RELATIONSHIP_THRESHOLD

logger = logging.getLogger(__name__)


class Neo4jManager(BaseDatabaseManager):
    """Neo4j数据库管理器

    职责：
    - 管理数据库连接
    - 执行节点的UPSERT操作
    - 管理连接关系
    - 清理失效的关系
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        """初始化Neo4j连接配置

        Args:
            uri: Neo4j数据库URI
            user: 数据库用户名
            password: 数据库密码
        """
        self.uri: str = uri
        self.user: str = user
        self.password: str = password
        self.driver: Optional[AsyncGraphDatabase.driver] = None

    async def connect(self) -> None:
        """建立Neo4j连接"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            logger.info(f"已连接到Neo4j数据库: {self.uri}")
        except Exception as e:
            logger.error(f"连接Neo4j失败: {e}")
            raise

    async def close(self) -> None:
        """关闭Neo4j连接"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j连接已关闭")

    async def initialize(self) -> None:
        """初始化Neo4j数据库（创建约束）"""
        try:
            async with self.driver.session() as session:
                # 创建节点ID的唯一性约束
                await session.run(
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.node_id IS UNIQUE"
                )
                logger.info("Neo4j约束初始化完成")
        except Exception as e:
            logger.error(f"初始化Neo4j约束失败: {e}")
            raise

    async def update_node(self, node: Node) -> None:
        """更新节点数据到Neo4j

        Args:
            node: 要更新的节点对象
        """
        if not node.validate():
            logger.warning(f"节点数据验证失败，跳过更新: {node.node_id}")
            return

        try:
            async with self.driver.session() as session:
                properties = {
                    'node_id': node.node_id,
                    'callsign': node.callsign,
                    'node_type': node.node_type,
                    'lat': node.lat,
                    'lon': node.lon,
                    'uptime': node.uptime,
                    'total_keyups': node.total_keyups,
                    'total_tx_time': node.total_tx_time,
                    'last_seen': node.last_seen.isoformat() if node.last_seen else None,
                    'active': node.active,
                    'updated_at': node.updated_at.isoformat() if node.updated_at else None,
                    'source': node.source,
                    'node_rank': node.node_rank,
                    'features': node.features,
                    'tone': node.tone,
                    'location_desc': node.location_desc,
                    'hardware_type': node.hardware_type,
                    'connections': node.connections
                }

                # 使用MERGE确保节点存在，然后更新属性
                query = """
                MERGE (n:Node {node_id: $node_id})
                SET n += $properties
                """
                await session.run(query, node_id=node.node_id, properties=properties)
                logger.debug(f"节点 {node.node_id} 数据已更新到Neo4j")
        except Exception as e:
            logger.error(f"更新节点 {node.node_id} 到Neo4j失败: {e}")
            raise

    async def update_topology(self, node_id: int, connections: List[Connection]) -> None:
        """更新节点拓扑关系到Neo4j

        Args:
            node_id: 源节点ID
            connections: 连接关系列表
        """
        try:
            async with self.driver.session() as session:
                current_time = datetime.now().isoformat()

                # 处理每个连接
                for conn in connections:
                    if not conn.validate():
                        logger.warning(f"连接数据验证失败，跳过: {node_id} -> {conn.target_id}")
                        continue

                    # 使用MERGE创建或更新关系
                    query = """
                    MERGE (src:Node {node_id: $src_id})
                    MERGE (dst:Node {node_id: $dst_id})
                    MERGE (src)-[r:CONNECTED_TO]->(dst)
                    SET r.status = $status,
                        r.direction = $direction,
                        r.last_updated = $last_updated,
                        r.active = $active
                    """
                    await session.run(
                        query,
                        src_id=node_id,
                        dst_id=conn.target_id,
                        status=conn.status,
                        direction=conn.direction,
                        last_updated=current_time,
                        active=conn.active
                    )

                # 清理失效的关系
                await self._cleanup_stale_relationships(session, node_id, connections, current_time)

                logger.debug(f"节点 {node_id} 拓扑关系已更新")
        except Exception as e:
            logger.error(f"更新节点 {node_id} 拓扑关系失败: {e}")
            raise

    async def set_node_inactive(self, node_id: int) -> None:
        """设置节点为不活跃状态

        Args:
            node_id: 节点ID
        """
        try:
            async with self.driver.session() as session:
                await session.run("""
                MATCH (n:Node {node_id: $node_id})
                SET n.active = false, n.last_seen = $last_seen
                """, node_id=node_id, last_seen=datetime.now().isoformat())
                logger.debug(f"节点 {node_id} 已设置为不活跃状态")
        except Exception as e:
            logger.error(f"设置节点 {node_id} 不活跃状态失败: {e}")
            raise

    async def _cleanup_stale_relationships(self, session, node_id: int,
                                       current_connections: List[Connection],
                                       current_time: str) -> None:
        """清理失效的关系

        Args:
            session: Neo4j会话
            node_id: 源节点ID
            current_connections: 当前活跃的连接列表
            current_time: 当前时间
        """
        try:
            # 获取所有现有的关系
            query = """
            MATCH (src:Node {node_id: $src_id})-[r:CONNECTED_TO]->(dst:Node)
            RETURN dst.node_id AS target_id, r.last_updated AS last_updated
            """
            result = await session.run(query, src_id=node_id)

            # 构建当前连接的节点ID集合
            current_target_ids = {conn.target_id for conn in current_connections}
            stale_count = 0

            # 检查每个关系是否仍然有效
            async for record in result:
                target_id = record['target_id']
                last_updated = record['last_updated']

                # 如果连接不再存在或超过阈值未更新，则禁用关系
                if (target_id not in current_target_ids or 
                    self._is_stale(last_updated, current_time)):
                    await session.run("""
                    MATCH (src:Node {node_id: $src_id})-[r:CONNECTED_TO]->(dst:Node {node_id: $dst_id})
                    SET r.active = false
                    """, src_id=node_id, dst_id=target_id)
                    stale_count += 1
                    logger.debug(f"Neo4j关系清理: 禁用节点 {node_id} 到 {target_id} 的失效关系")

            if stale_count > 0:
                logger.info(f"Neo4j关系清理: 节点 {node_id} 已清理 {stale_count} 个失效关系")
        except Exception as e:
            logger.error(f"Neo4j关系清理失败: 清理节点 {node_id} 失效关系异常 - {e}")

    def _is_stale(self, last_updated: str, current_time: str,
                  threshold_minutes: int = STALE_RELATIONSHIP_THRESHOLD) -> bool:
        """检查关系是否过期

        Args:
            last_updated: 最后更新时间
            current_time: 当前时间
            threshold_minutes: 过期阈值（分钟）

        Returns:
            bool: 关系是否过期
        """
        try:
            last_time = datetime.fromisoformat(last_updated)
            curr_time = datetime.fromisoformat(current_time)
            time_diff = (curr_time - last_time).total_seconds() / 60
            return time_diff > threshold_minutes
        except Exception as e:
            logger.error(f"检查关系过期状态失败: {e}")
            return True
