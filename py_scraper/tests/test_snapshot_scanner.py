"""node_topology 快照扫描器测试。"""

import unittest

from src.link_scraper.modules.allstarlink.services.node_topology_scanner import (
    NodeTopologySnapshotScanner,
)


class FakeBatchManager:
    async def get_or_create_batch_no(self, mysql_manager):
        return "202603130001"


class FakeRedisQueue:
    async def acquire_batch_lock(self):
        return True

    async def release_batch_lock(self):
        return None

    async def batch_enqueue(self, batch_data):
        return len(batch_data)


class FakeMySQLManager:
    def __init__(self) -> None:
        self.queries = []

    async def execute_query(self, query):
        self.queries.append(query)
        return []


class TestSnapshotScanner(unittest.IsolatedAsyncioTestCase):
    async def test_batch_update_mysql_uses_each_row_node_id(self) -> None:
        mysql_manager = FakeMySQLManager()
        scanner = NodeTopologySnapshotScanner(
            redis_queue=FakeRedisQueue(),
            mysql_manager=mysql_manager,
            network_config=None,
            batch_manager=FakeBatchManager(),
            source_client=None,
            source_mapper=None,
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
