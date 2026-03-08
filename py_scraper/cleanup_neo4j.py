"""
Neo4j数据清理脚本

功能：
1. 清理所有节点和关系
2. 清理失效的关系（超过指定时间未更新）
3. 清理离线节点
4. 清理重复数据
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from neo4j import AsyncGraphDatabase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jCleanup:
    """Neo4j数据清理工具"""

    def __init__(self, uri: str, user: str, password: str):
        """
        初始化Neo4j清理工具

        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
        """
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        """关闭Neo4j连接"""
        await self.driver.close()
        logger.info("Neo4j连接已关闭")

    async def clear_all(self):
        """清空所有节点和关系"""
        logger.warning("开始清空所有节点和关系...")
        async with self.driver.session() as session:
            # 删除所有节点和关系
            result = await session.run("MATCH (n) DETACH DELETE n")
            summary = await result.consume()
            logger.info(f"已删除 {summary.counters.nodes_deleted} 个节点和 {summary.counters.relationships_deleted} 个关系")

    async def clear_stale_relationships(self, threshold_minutes: int = 15):
        """
        清理失效的关系（超过指定时间未更新）

        Args:
            threshold_minutes: 时间阈值（分钟），默认15分钟
        """
        logger.info(f"开始清理失效的关系（阈值: {threshold_minutes}分钟）...")
        async with self.driver.session() as session:
            threshold_time = datetime.now() - timedelta(minutes=threshold_minutes)
            threshold_iso = threshold_time.isoformat()

            # 查找并删除失效的关系
            query = """
            MATCH ()-[r:CONNECTED_TO]->()
            WHERE r.last_updated < $threshold_time OR r.last_updated IS NULL
            DELETE r
            """
            result = await session.run(query, threshold_time=threshold_iso)
            summary = await result.consume()
            logger.info(f"已删除 {summary.counters.relationships_deleted} 个失效关系")

    async def clear_inactive_nodes(self, threshold_hours: int = 24):
        """
        清理离线节点（超过指定时间未活跃）

        Args:
            threshold_hours: 时间阈值（小时），默认24小时
        """
        logger.info(f"开始清理离线节点（阈值: {threshold_hours}小时）...")
        async with self.driver.session() as session:
            threshold_time = datetime.now() - timedelta(hours=threshold_hours)
            threshold_iso = threshold_time.isoformat()

            # 查找并删除离线节点
            query = """
            MATCH (n:Node)
            WHERE n.last_seen < $threshold_time OR n.last_seen IS NULL
            DETACH DELETE n
            """
            result = await session.run(query, threshold_time=threshold_iso)
            summary = await result.consume()
            logger.info(f"已删除 {summary.counters.nodes_deleted} 个离线节点")

    async def clear_orphan_nodes(self):
        """清理孤立节点（没有任何关系的节点）"""
        logger.info("开始清理孤立节点...")
        async with self.driver.session() as session:
            # 查找并删除孤立节点
            query = """
            MATCH (n:Node)
            WHERE NOT (n)-[]-()
            DELETE n
            """
            result = await session.run(query)
            summary = await result.consume()
            logger.info(f"已删除 {summary.counters.nodes_deleted} 个孤立节点")

    async def get_statistics(self):
        """获取数据库统计信息"""
        logger.info("获取数据库统计信息...")
        async with self.driver.session() as session:
            # 获取节点数量
            node_result = await session.run("MATCH (n:Node) RETURN count(n) AS count")
            node_count = (await node_result.single())["count"]

            # 获取关系数量
            rel_result = await session.run("MATCH ()-[r:CONNECTED_TO]->() RETURN count(r) AS count")
            rel_count = (await rel_result.single())["count"]

            # 获取活跃节点数量
            active_result = await session.run("MATCH (n:Node {active: true}) RETURN count(n) AS count")
            active_count = (await active_result.single())["count"]

            # 获取活跃关系数量
            active_rel_result = await session.run("MATCH ()-[r:CONNECTED_TO {active: true}]->() RETURN count(r) AS count")
            active_rel_count = (await active_rel_result.single())["count"]

            logger.info(f"节点总数: {node_count}")
            logger.info(f"关系总数: {rel_count}")
            logger.info(f"活跃节点数: {active_count}")
            logger.info(f"活跃关系数: {active_rel_count}")

            return {
                'total_nodes': node_count,
                'total_relationships': rel_count,
                'active_nodes': active_count,
                'active_relationships': active_rel_count
            }

    async def set_all_nodes_inactive(self):
        """将所有节点设置为不活跃状态"""
        logger.info("将所有节点设置为不活跃状态...")
        async with self.driver.session() as session:
            query = """
            MATCH (n:Node)
            SET n.active = false
            """
            result = await session.run(query)
            summary = await result.consume()
            logger.info(f"已将 {summary.counters.properties_set} 个节点设置为不活跃")

    async def set_all_relationships_inactive(self):
        """将所有关系设置为不活跃状态"""
        logger.info("将所有关系设置为不活跃状态...")
        async with self.driver.session() as session:
            query = """
            MATCH ()-[r:CONNECTED_TO]->()
            SET r.active = false
            """
            result = await session.run(query)
            summary = await result.consume()
            logger.info(f"已将 {summary.counters.properties_set} 个关系设置为不活跃")


async def main():
    """主函数"""
    # Neo4j配置
    NEO4J_CONFIG = {
        'uri': 'bolt://121.41.230.15:7687',
        'user': 'neo4j',
        'password': '0595'  # 请修改为实际密码
    }

    cleanup = Neo4jCleanup(**NEO4J_CONFIG)

    try:
        # 显示当前统计信息
        await cleanup.get_statistics()

        print("请选择清理操作:")
        print("1. 清空所有节点和关系")
        print("2. 清理失效的关系（15分钟未更新）")
        print("3. 清理离线节点（24小时未活跃）")
        print("4. 清理孤立节点")
        print("5. 将所有节点设置为不活跃")
        print("6. 将所有关系设置为不活跃")
        print("7. 执行完整清理（2+3+4）")
        print("8. 仅显示统计信息")
        print("0. 退出")

        choice = input("请输入选项 (0-8): ").strip()

        if choice == '1':
            confirm = input("警告：此操作将删除所有数据！确认吗？(yes/no): ").strip().lower()
            if confirm == 'yes':
                await cleanup.clear_all()
            else:
                print("操作已取消")

        elif choice == '2':
            await cleanup.clear_stale_relationships()

        elif choice == '3':
            await cleanup.clear_inactive_nodes()

        elif choice == '4':
            await cleanup.clear_orphan_nodes()

        elif choice == '5':
            await cleanup.set_all_nodes_inactive()

        elif choice == '6':
            await cleanup.set_all_relationships_inactive()

        elif choice == '7':
            await cleanup.clear_stale_relationships()
            await cleanup.clear_inactive_nodes()
            await cleanup.clear_orphan_nodes()

        elif choice == '8':
            pass

        elif choice == '0':
            print("退出程序")
            return

        else:
            print("无效的选项")

        # 显示清理后的统计信息
        print("清理后的统计信息:")
        await cleanup.get_statistics()

    finally:
        await cleanup.close()


if __name__ == '__main__':
    asyncio.run(main())