"""Neo4j 基础连接与执行层。"""

import logging
from typing import Any, Optional

from neo4j import AsyncGraphDatabase

from .base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class GraphStorageManager(BaseDatabaseManager):
    """只负责 Neo4j 连接与基础 Cypher 执行。"""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[AsyncGraphDatabase.driver] = None

    async def connect(self) -> None:
        try:
            self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            logger.info("已连接到 Neo4j: %s", self.uri)
        except Exception as exc:
            logger.error("连接 Neo4j 失败: %s", exc)
            raise

    async def close(self) -> None:
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j 连接已关闭")

    async def initialize(self) -> None:
        """初始化通用约束。"""

        try:
            async with self.driver.session() as session:
                try:
                    result = await session.run("SHOW CONSTRAINTS")
                    constraints = await result.data()
                    for constraint in constraints:
                        if constraint.get("labelsOrTypes") == ["Node"]:
                            constraint_name = constraint.get("name")
                            if constraint_name:
                                await session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
                except Exception as exc:
                    logger.warning("清理旧约束时出现警告: %s", exc)

                await session.run(
                    "CREATE CONSTRAINT node_unique_id IF NOT EXISTS FOR (n:Node) REQUIRE n.unique_id IS UNIQUE"
                )
                logger.info("Neo4j 约束初始化完成")
        except Exception as exc:
            logger.error("初始化 Neo4j 约束失败: %s", exc)
            raise

    async def execute_write(self, query: str, **params: Any):
        """执行写 Cypher，返回 consume 后的 summary。"""

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            return await result.consume()

    async def execute_read(self, query: str, **params: Any) -> list[dict]:
        """执行读 Cypher，返回结果列表。"""

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            return await result.data()

    async def execute_read_one(self, query: str, **params: Any):
        """执行读 Cypher，返回单条记录。"""

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            return await result.single()
