"""
Neo4j数据库管理器

负责与Neo4j图数据库的交互，包括：
1. 连接管理
2. 节点数据的插入和更新
3. 连接关系的管理
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
                # 先删除所有Node标签的约束
                try:
                    result = await session.run("SHOW CONSTRAINTS")
                    constraints = await result.data()
                    for constraint in constraints:
                        if constraint.get("labelsOrTypes") == ["Node"]:
                            constraint_name = constraint.get("name")
                            if constraint_name:
                                logger.info(f"删除旧约束: {constraint_name}")
                                await session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
                except Exception as e:
                    logger.warning(f"删除旧约束时出现警告: {e}")
                
                # 创建unique_id的唯一性约束
                logger.info("创建unique_id唯一约束...")
                await session.run(
                    "CREATE CONSTRAINT node_unique_id IF NOT EXISTS FOR (n:Node) REQUIRE n.unique_id IS UNIQUE"
                )
                logger.info("Neo4j约束初始化完成")
        except Exception as e:
            logger.error(f"初始化Neo4j约束失败: {e}")
            raise

    async def update_node(self, node: Node, preserve_counters: bool = False) -> None:
        """更新节点数据到Neo4j

        Args:
            node: 要更新的节点对象
        """
        if not node.validate():
            logger.warning(f"节点数据验证失败，跳过更新: {node.node_id}")
            return

        try:
            async with self.driver.session() as session:
                # 生成unique_id：node_id_batch_no
                unique_id = f"{node.node_id}_{node.batch_no}"
                
                properties = {
                    'unique_id': unique_id,
                    'node_id': node.node_id,
                    'callsign': node.callsign,
                    'node_type': node.node_type,
                    'lat': node.lat,
                    'lon': node.lon,
                    'total_keyups': node.total_keyups,
                    'total_tx_time': node.total_tx_time,
                    'last_seen': node.last_seen.isoformat() if node.last_seen else None,
                    'active': node.active,
                    'updated_at': node.updated_at.isoformat() if node.updated_at else None,
                    'node_rank': node.node_rank,
                    'features': node.features,
                    'tone': node.tone,
                    'location_desc': node.location_desc,
                    'hardware_type': node.hardware_type,
                    'connections': node.connections,
                    'batch_no': node.batch_no
                }

                # 使用MERGE确保节点存在（基于unique_id），然后更新属性
                # 同一节点在不同批次会有多个实例，通过unique_id区分
                if preserve_counters:
                    create_properties = properties.copy()
                    match_properties = properties.copy()
                    match_properties.pop('total_keyups', None)
                    match_properties.pop('total_tx_time', None)
                    query = """
                    MERGE (n:Node {unique_id: $unique_id})
                    ON CREATE SET n = $create_properties
                    ON MATCH SET n += $match_properties
                    """
                    await session.run(
                        query,
                        unique_id=unique_id,
                        create_properties=create_properties,
                        match_properties=match_properties
                    )
                else:
                    query = """
                    MERGE (n:Node {unique_id: $unique_id})
                    ON CREATE SET n = $properties
                    ON MATCH SET n = $properties
                    """
                    await session.run(query, unique_id=unique_id, properties=properties)
                logger.debug(f"节点 {node.node_id} (批次{node.batch_no}) 数据已更新到Neo4j")
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

                    # 使用CREATE直接创建关系，不使用MERGE
                    # 通过unique_id匹配节点
                    query = """
                    MATCH (src:Node {unique_id: $src_unique_id})
                    MATCH (dst:Node {unique_id: $dst_unique_id})
                    CREATE (src)-[r:CONNECTED_TO]->(dst)
                    SET r.status = $status,
                        r.direction = $direction,
                        r.last_updated = $last_updated,
                        r.active = $active,
                        r.batch_no = $batch_no
                    """
                    src_unique_id = f"{node_id}_{conn.batch_no}"
                    dst_unique_id = f"{conn.target_id}_{conn.batch_no}"
                    await session.run(
                        query,
                        src_unique_id=src_unique_id,
                        dst_unique_id=dst_unique_id,
                        status=conn.status,
                        direction=conn.direction,
                        last_updated=current_time,
                        active=conn.active,
                        batch_no=conn.batch_no
                    )

                logger.debug(f"节点 {node_id} 拓扑关系已更新")
        except Exception as e:
            logger.error(f"更新节点 {node_id} 拓扑关系失败: {e}")
            raise

    async def set_node_inactive(self, node_id: int, batch_no: str) -> None:
        """设置节点为不活跃状态

        Args:
            node_id: 节点ID
            batch_no: 批次号
        """
        try:
            async with self.driver.session() as session:
                unique_id = f"{node_id}_{batch_no}"
                await session.run("""
                MATCH (n:Node {unique_id: $unique_id})
                SET n.active = false, n.last_seen = $last_seen
                """, unique_id=unique_id, last_seen=datetime.now().isoformat())
                logger.debug(f"节点 {node_id} (批次{batch_no}) 已设置为不活跃状态")
        except Exception as e:
            logger.error(f"设置节点 {node_id} (批次{batch_no}) 不活跃状态失败: {e}")

    async def get_topology_by_batch(self, batch_no: str) -> List[dict]:
        """查询指定批次的拓扑关系

        Args:
            batch_no: 批次号

        Returns:
            List[dict]: 拓扑关系列表，每个元素包含源节点、目标节点和关系信息
        """
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (src:Node {batch_no: $batch_no})-[r:CONNECTED_TO]->(dst:Node {batch_no: $batch_no})
                RETURN src.node_id AS source_id,
                       src.callsign AS source_callsign,
                       src.unique_id AS source_unique_id,
                       dst.node_id AS target_id,
                       dst.callsign AS target_callsign,
                       dst.unique_id AS target_unique_id,
                       r.status AS status,
                       r.direction AS direction,
                       r.last_updated AS last_updated,
                       r.active AS active,
                       r.batch_no AS batch_no
                """
                result = await session.run(query, batch_no=batch_no)
                records = await result.data()
                logger.debug(f"查询批次 {batch_no} 的拓扑关系，返回 {len(records)} 条记录")
                return records
        except Exception as e:
            logger.error(f"查询批次 {batch_no} 的拓扑关系失败: {e}")
            raise

    async def get_latest_batch_no(self) -> Optional[str]:
        """获取最新的批次号

        Returns:
            Optional[str]: 最新的批次号，如果没有数据则返回None
        """
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (n:Node)
                WHERE n.batch_no IS NOT NULL
                RETURN n.batch_no AS batch_no
                ORDER BY n.batch_no DESC
                LIMIT 1
                """
                result = await session.run(query)
                record = await result.single()
                if record:
                    batch_no = record["batch_no"]
                    logger.debug(f"获取到最新批次号: {batch_no}")
                    return batch_no
                return None
        except Exception as e:
            logger.error(f"获取最新批次号失败: {e}")
            raise


