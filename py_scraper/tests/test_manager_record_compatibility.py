"""database 基础执行层测试。"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.link_scraper.database.mysql_manager import RelationalStorageManager
from src.link_scraper.database.neo4j_manager import GraphStorageManager


class FakeTransaction:
    def __init__(self) -> None:
        self.commit = MagicMock()
        self.rollback = MagicMock()


class FakeConnection:
    def __init__(self, result=None) -> None:
        self.result = result or MagicMock()
        self.executed = []
        self.transaction = FakeTransaction()

    def begin(self):
        return self.transaction

    def execute(self, stmt, params=None):
        self.executed.append((stmt, params))
        return self.result


class FakeConnectionContext:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def connect(self):
        return FakeConnectionContext(self.connection)


class TestDatabaseBaseExecution(unittest.IsolatedAsyncioTestCase):
    async def test_mysql_execute_statement_wraps_transaction(self) -> None:
        manager = RelationalStorageManager("host", "user", "pwd", "db", "utf8mb4")
        connection = FakeConnection()
        manager.engine = FakeEngine(connection)

        await manager.execute_statement("UPDATE dim_nodes SET is_active = :flag", {"flag": 1})

        self.assertEqual(len(connection.executed), 1)
        self.assertEqual(connection.executed[0][1]["flag"], 1)
        connection.transaction.commit.assert_called_once()

    async def test_neo4j_execute_write_delegates_to_driver(self) -> None:
        manager = GraphStorageManager("bolt://x", "neo4j", "pwd")
        result = MagicMock()
        result.consume = AsyncMock(return_value=MagicMock())
        session = MagicMock()
        session.run = AsyncMock(return_value=result)
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session)
        session_cm.__aexit__ = AsyncMock(return_value=False)
        manager.driver = MagicMock()
        manager.driver.session.return_value = session_cm

        await manager.execute_write("CREATE (n:Node {id: $id})", id="2105")

        session.run.assert_awaited_once_with("CREATE (n:Node {id: $id})", id="2105")
        result.consume.assert_awaited_once()
