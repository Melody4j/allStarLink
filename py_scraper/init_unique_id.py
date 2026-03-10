"""
初始化Neo4j节点的unique_id

将所有节点的unique_id初始化为 unique_id = f"{node.node_id}_{node.batch_no}"
其中batch_no为2026031008000003
"""

import asyncio
from neo4j import AsyncGraphDatabase
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_unique_id():
    """初始化所有节点的unique_id"""

    # Neo4j连接配置
    URI = "bolt://121.41.230.15:7687"
    AUTH = ("neo4j", "0595")

    driver = AsyncGraphDatabase.driver(URI, auth=AUTH)

    try:
        async with driver.session() as session:
            # 处理unique_id冲突：保留最新的节点，删除旧节点
            # 1. 找出所有会导致冲突的unique_id
            find_conflicts_query = """
            MATCH (n:Node)
            WITH n.node_id AS node_id, coalesce(n.batch_no, '2026031008000003') AS batch_no
            WITH node_id + '_' + batch_no AS unique_id, count(*) AS cnt
            WHERE cnt > 1
            RETURN unique_id
            """
            
            result = await session.run(find_conflicts_query)
            conflicts = await result.data()
            
            if conflicts:
                logger.info(f"发现 {len(conflicts)} 个unique_id冲突，开始处理...")
                
                # 2. 对每个冲突的unique_id，保留最新的节点，删除其他节点
                for conflict in conflicts:
                    unique_id = conflict['unique_id']
                    
                    # 找出所有具有此unique_id的节点，按更新时间排序
                    find_nodes_query = """
                    MATCH (n:Node)
                    WHERE n.node_id + '_' + coalesce(n.batch_no, '2026031008000003') = $unique_id
                    RETURN id(n) AS internal_id, n.node_id AS node_id, n.updated_at AS updated_at
                    ORDER BY n.updated_at DESC
                    """
                    
                    result = await session.run(find_nodes_query, unique_id=unique_id)
                    nodes = await result.data()
                    
                    if len(nodes) > 1:
                        # 保留第一个（最新的），删除其余的
                        keep_node = nodes[0]
                        delete_nodes = nodes[1:]
                        
                        logger.info(f"处理冲突 unique_id={unique_id}: 保留节点 {keep_node['node_id']}, 删除 {len(delete_nodes)} 个旧节点")
                        
                        # 删除旧节点
                        for node_data in delete_nodes:
                            internal_id = node_data['internal_id']
                            node_id = node_data['node_id']
                            await session.run("MATCH (n) WHERE id(n) = $node_id DETACH DELETE n", node_id=internal_id)
                            logger.info(f"  已删除节点 {node_id}")
                
                logger.info("冲突处理完成")
            
            # 批量更新所有节点的unique_id
            # 只更新还没有unique_id的节点
            query = """
            MATCH (n:Node)
            WHERE n.unique_id IS NULL
            WITH n, n.node_id AS node_id, coalesce(n.batch_no, '2026031008000003') AS batch_no
            WITH n, node_id + '_' + batch_no AS unique_id
            SET n.unique_id = unique_id
            RETURN count(n) AS updated_count
            """
            
            result = await session.run(query)
            record = await result.single()
            updated_count = record['updated_count'] if record else 0
            
            logger.info(f"已更新 {updated_count} 个节点的unique_id")

            logger.info("所有节点的unique_id初始化完成")

    except Exception as e:
        logger.error(f"初始化unique_id失败: {e}")
        raise
    finally:
        await driver.close()


if __name__ == '__main__':
    asyncio.run(init_unique_id())
