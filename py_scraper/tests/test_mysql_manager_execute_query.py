"""RelationalStorageManager.execute_query 测试。"""

import unittest

from src.link_scraper.database.mysql_manager import RelationalStorageManager


class FakeResultWithRows:
    returns_rows = True

    def keys(self):
        return ["id", "name"]

    def fetchall(self):
        return [(1, "alice")]


class FakeResultWithoutRows:
    returns_rows = False


class FakeConnection:
    def __init__(self, result):
        self.result = result

    def execute(self, stmt, params=None):
        return self.result


class FakeConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    def __init__(self, result):
        self.result = result

    def connect(self):
        return FakeConnectionContext(FakeConnection(self.result))


class TestRelationalStorageManagerExecuteQuery(unittest.IsolatedAsyncioTestCase):
    async def test_execute_query_returns_rows_for_select(self) -> None:
        manager = RelationalStorageManager("host", "user", "pwd", "db", "utf8mb4")
        manager.engine = FakeEngine(FakeResultWithRows())

        result = await manager.execute_query("SELECT 1")

        self.assertEqual(result, [{"id": 1, "name": "alice"}])

    async def test_execute_query_returns_empty_list_for_dml(self) -> None:
        manager = RelationalStorageManager("host", "user", "pwd", "db", "utf8mb4")
        manager.engine = FakeEngine(FakeResultWithoutRows())

        result = await manager.execute_query("UPDATE dim_nodes SET is_active = 1")

        self.assertEqual(result, [])
