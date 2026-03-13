"""
更新Neo4j中边的batch_no为空的数据

将所有CONNECTED_TO关系中batch_no为空的记录设置为指定批次号
"""

import asyncio
from neo4j import AsyncGraphDatabase

# Neo4j连接配置
NEO4J_URI = "bolt://121.41.230.15:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "0595"
TARGET_BATCH_NO = "2026031008000003"


async def update_edge_batch_no():
    """更新Neo4j中边的batch_no为空的数据"""

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        async with driver.session() as session:
            # 先查询batch_no为空的关系数量
            count_query = """
            MATCH (src:Node)-[r:CONNECTED_TO]->(dst:Node)
            WHERE r.batch_no IS NULL
            RETURN count(r) as count
            """
            result = await session.run(count_query)
            record = await result.single()
            count = record["count"] if record else 0
            print(f"找到 {count} 条batch_no为空的关系记录")

            if count == 0:
                print("没有需要更新的记录")
                return

            # 更新batch_no为空的关系
            update_query = """
            MATCH (src:Node)-[r:CONNECTED_TO]->(dst:Node)
            WHERE r.batch_no IS NULL
            SET r.batch_no = $batch_no
            RETURN count(r) as updated_count
            """
            result = await session.run(update_query, batch_no=TARGET_BATCH_NO)
            record = await result.single()
            updated_count = record["updated_count"] if record else 0

            print(f"成功更新 {updated_count} 条记录，batch_no设置为: {TARGET_BATCH_NO}")

    except Exception as e:
        print(f"更新过程中出错: {e}")
        raise
    finally:
        await driver.close()


if __name__ == "__main__":
    print("开始更新Neo4j边的batch_no...")
    asyncio.run(update_edge_batch_no())
    print("更新完成")
