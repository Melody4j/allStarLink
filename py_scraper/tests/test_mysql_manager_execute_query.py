"""
MySQLManager.execute_query 测试。
"""

import unittest

from src.link_scraper.database.mysql_manager import MySQLManager


class FakeResultWithRows:
    """模拟有结果集的 SQLAlchemy result。"""

    returns_rows = True

    def keys(self):
        return ["id", "name"]

    def fetchall(self):
        return [(1, "alice")]


class FakeResultWithoutRows:
    """模拟无结果集的 DML 执行结果。"""

    returns_rows = False


class FakeConnection:
    """模拟数据库连接。"""

    def __init__(self, result):
        self.result = result

    def execute(self, stmt):
        return self.result


class FakeConnectionContext:
    """模拟 engine.connect() 上下文。"""

    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    """模拟 SQLAlchemy engine。"""

    def __init__(self, result):
        self.result = result

    def connect(self):
        return FakeConnectionContext(FakeConnection(self.result))


class TestMySQLManagerExecuteQuery(unittest.IsolatedAsyncioTestCase):
    """验证 execute_query 对 SELECT 和 DML 的处理分支。"""

    async def test_execute_query_returns_rows_for_select(self) -> None:
        manager = MySQLManager("host", "user", "pwd", "db", "utf8mb4")
        manager.engine = FakeEngine(FakeResultWithRows())

        result = await manager.execute_query("SELECT 1")

        self.assertEqual(result, [{"id": 1, "name": "alice"}])

    async def test_execute_query_returns_empty_list_for_dml(self) -> None:
        manager = MySQLManager("host", "user", "pwd", "db", "utf8mb4")
        manager.engine = FakeEngine(FakeResultWithoutRows())

        result = await manager.execute_query("UPDATE dim_nodes SET is_active = 1")

        self.assertEqual(result, [])
