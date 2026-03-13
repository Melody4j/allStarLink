"""
SnapshotScanner 测试。
"""

import unittest

from src.link_scraper.scrapers.snapshot_scanner import SnapshotScanner


class FakeBatchManager:
    """提供最小批次管理能力，满足构造函数依赖。"""

    async def get_or_create_batch_no(self, mysql_manager):
        return "202603130001"


class FakeRedisQueue:
    """仅保留本测试用到的最小接口。"""

    async def acquire_batch_lock(self):
        return True

    async def release_batch_lock(self):
        return None

    async def batch_enqueue(self, batch_data):
        return len(batch_data)

    async def contains(self, node_id):
        return False

    async def enqueue(self, node_id, priority):
        return None


class FakeMySQLManager:
    """记录 SQL，便于断言 CASE WHEN 是否正确引用 node_id。"""

    def __init__(self) -> None:
        self.queries = []

    async def execute_query(self, query):
        self.queries.append(query)
        return []


class TestSnapshotScanner(unittest.IsolatedAsyncioTestCase):
    """验证快照扫描器的批量 SQL 生成行为。"""

    async def test_batch_update_mysql_uses_each_row_node_id(self) -> None:
        mysql_manager = FakeMySQLManager()
        scanner = SnapshotScanner(
            redis_queue=FakeRedisQueue(),
            mysql_manager=mysql_manager,
            api_config=None,
            batch_manager=FakeBatchManager(),
        )

        await scanner._batch_update_mysql(
            [
                {"node_id": 2105, "link_count": 5},
                {"node_id": 1001, "link_count": 2},
            ]
        )

        self.assertEqual(len(mysql_manager.queries), 1)
        query = mysql_manager.queries[0]
        self.assertIn("WHEN 2105 THEN 5", query)
        self.assertIn("WHEN 1001 THEN 2", query)

