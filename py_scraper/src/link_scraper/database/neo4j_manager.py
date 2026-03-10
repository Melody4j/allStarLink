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

    async def update_topology(self, node_id: str, connections: List[Connection]) -> None:
        """更新节点拓扑关系到Neo4j（批量操作）

        Args:
            node_id: 源节点ID
            connections: 连接关系列表
        """
        try:
            async with self.driver.session() as session:
                current_time = datetime.now().isoformat()

                # 过滤无效连接
                valid_connections = [conn for conn in connections if conn.validate()]
                if not valid_connections:
                    logger.warning(f"节点 {node_id} 没有有效的连接关系")
                    return

                # 批量检查已存在的连接
                connection_pairs = [
                    (f"{node_id}_{conn.batch_no}", f"{conn.target_id}_{conn.batch_no}", conn)
                    for conn in valid_connections
                ]

                # 批量查询所有连接对
                check_query = """
                UNWIND $pairs AS pair
                MATCH (a:Node {unique_id: pair.src_unique_id})-[r:CONNECTED_TO]-(b:Node {unique_id: pair.dst_unique_id})
                RETURN pair.src_unique_id AS src_unique_id,
                       pair.dst_unique_id AS dst_unique_id,
                       pair.conn AS conn,
                       r
                """
                result = await session.run(
                    check_query,
                    pairs=[
                        {"src_unique_id": src, "dst_unique_id": dst, "conn": {"status": conn.status, "active": conn.active, "batch_no": conn.batch_no}}
                        for src, dst, conn in connection_pairs
                    ]
                )
                existing_connections = await result.data()

                logger.debug(f"节点 {node_id}: 找到 {len(existing_connections)} 个已存在的连接")

                # 提取已存在的连接对
                existing_pairs = {(record["src_unique_id"], record["dst_unique_id"]) for record in existing_connections}

                # 分离需要更新和需要创建的连接
                to_update = [record for record in existing_connections]
                to_create = [
                    (src, dst, conn)
                    for src, dst, conn in connection_pairs
                    if (src, dst) not in existing_pairs and (dst, src) not in existing_pairs
                ]

                logger.debug(f"节点 {node_id}: 总共 {len(connection_pairs)} 个连接，需要更新 {len(to_update)} 个，需要创建 {len(to_create)} 个")

                # 批量更新已存在的连接
                if to_update:
                    update_query = """
                    UNWIND $updates AS update
                    MATCH (a:Node {unique_id: update.src_unique_id})-[r:CONNECTED_TO]-(b:Node {unique_id: update.dst_unique_id})
                    SET r.status = update.status,
                        r.last_updated = $last_updated,
                        r.active = update.active,
                        r.batch_no = update.batch_no
                    """
                    result = await session.run(
                        update_query,
                        updates=[
                            {
                                "src_unique_id": record["src_unique_id"],
                                "dst_unique_id": record["dst_unique_id"],
                                "status": record["conn"]["status"],
                                "active": record["conn"]["active"],
                                "batch_no": record["conn"]["batch_no"]
                            }
                            for record in to_update
                        ],
                        last_updated=current_time
                    )
                    # 等待更新操作完成
                    await result.consume()
                    logger.debug(f"批量更新 {len(to_update)} 个已存在的连接")

                # 批量创建新连接
                if to_create:
                    # 先检查所有要创建连接的节点是否存在
                    check_nodes_query = """
                    UNWIND $node_ids AS node_id
                    MATCH (n:Node {unique_id: node_id})
                    RETURN node_id
                    """
                    all_node_ids = set([src for src, dst, conn in to_create] + [dst for src, dst, conn in to_create])
                    node_check_result = await session.run(check_nodes_query, node_ids=list(all_node_ids))
                    existing_nodes = set([record["node_id"] for record in await node_check_result.data()])
                    
                    # 找出不存在的节点
                    missing_nodes = all_node_ids - existing_nodes
                    if missing_nodes:
                        logger.warning(f"节点 {node_id}: 以下节点不存在，无法创建连接: {missing_nodes}")
                    
                    # 过滤掉涉及不存在节点的连接
                    valid_to_create = [
                        (src, dst, conn)
                        for src, dst, conn in to_create
                        if src in existing_nodes and dst in existing_nodes
                    ]
                    
                    if not valid_to_create:
                        logger.warning(f"节点 {node_id}: 没有有效的连接可以创建（所有涉及的节点都不存在）")
                    else:
                        create_query = """
                        UNWIND $creates AS create
                        MATCH (src:Node {unique_id: create.src_unique_id})
                        MATCH (dst:Node {unique_id: create.dst_unique_id})
                        CREATE (src)-[r:CONNECTED_TO]->(dst)
                        SET r.status = create.status,
                            r.direction = create.direction,
                            r.last_updated = $last_updated,
                            r.active = create.active,
                            r.batch_no = create.batch_no
                        """
                        result = await session.run(
                            create_query,
                            creates=[
                                {
                                    "src_unique_id": src,
                                    "dst_unique_id": dst,
                                    "status": conn.status,
                                    "direction": conn.direction,
                                    "active": conn.active,
                                    "batch_no": conn.batch_no
                                }
                                for src, dst, conn in valid_to_create
                            ],
                            last_updated=current_time
                        )
                        # 等待创建操作完成
                        await result.consume()
                        logger.info(f"批量创建 {len(valid_to_create)} 个新连接")
                        if len(valid_to_create) < len(to_create):
                            logger.warning(f"节点 {node_id}: 跳过了 {len(to_create) - len(valid_to_create)} 个连接，因为相关节点不存在")

                logger.debug(f"节点 {node_id} 拓扑关系已更新: 更新 {len(to_update)} 个, 创建 {len(to_create)} 个")
        except Exception as e:
            logger.error(f"更新节点 {node_id} 拓扑关系失败: {e}")
            raise

    async def set_node_inactive(self, node_id: str, batch_no: str) -> None:
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

    async def delete_node_by_unique_id(self, unique_id: str) -> bool:
        """通过unique_id删除节点及其所有连接关系

        Args:
            unique_id: 节点的唯一标识符

        Returns:
            bool: 是否成功删除
        """
        try:
            async with self.driver.session() as session:
                # 先删除该节点的所有关系（包括入向和出向）
                await session.run("""
                MATCH (n:Node {unique_id: $unique_id})-[r]-()
                DELETE r
                """, unique_id=unique_id)
                
                # 再删除节点本身
                result = await session.run("""
                MATCH (n:Node {unique_id: $unique_id})
                DELETE n
                """, unique_id=unique_id)
                
                summary = await result.consume()
                deleted_count = summary.counters.nodes_deleted
                logger.info(f"已删除节点 {unique_id} 及其所有连接关系，共删除 {deleted_count} 个节点")
                return deleted_count > 0
        except Exception as e:
            logger.error(f"删除节点 {unique_id} 失败: {e}")
            return False


