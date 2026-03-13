"""
manager 层 record 兼容测试。
"""

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.link_scraper.database.mysql_manager import MySQLManager
from src.link_scraper.database.neo4j_manager import Neo4jManager
from src.link_scraper.repositories.records import DimNodeRecord, GraphNodeRecord, OdsNodeDetailRecord


class FakeTransaction:
    """模拟 SQLAlchemy 事务对象。"""

    def __init__(self) -> None:
        self.commit = MagicMock()
        self.rollback = MagicMock()


class FakeConnection:
    """模拟 SQLAlchemy 连接。"""

    def __init__(self) -> None:
        self.executed = []
        self.transaction = FakeTransaction()

    def begin(self):
        return self.transaction

    def execute(self, stmt, params=None):
        self.executed.append((stmt, params))
        return MagicMock()


class FakeConnectionContext:
    """模拟 with engine.connect() 上下文。"""

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    """模拟 SQLAlchemy engine。"""

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def connect(self):
        return FakeConnectionContext(self.connection)


class TestManagerRecordCompatibility(unittest.IsolatedAsyncioTestCase):
    """验证 manager 能接收新的 record 输入。"""

    async def test_mysql_manager_accepts_dim_record(self) -> None:
        manager = MySQLManager("host", "user", "pwd", "db", "utf8mb4")
        connection = FakeConnection()
        manager.engine = FakeEngine(connection)
        record = DimNodeRecord(
            node_id="2105",
            node_type="allstarlink",
            callsign="KJ7OMO",
            tone=None,
            owner=None,
            affiliation=None,
            site_name="2105-PRIDE-HUB",
            features=[],
            affiliation_type=None,
            country=None,
            continent=None,
            active=True,
            last_seen=datetime(2026, 3, 13, 10, 0, 0),
            node_rank="Hub",
            mobility_type=None,
            first_seen_at=None,
            lat=40.5545,
            lon=-74.4601,
            location_desc=None,
            is_mobile=None,
            app_version=None,
            is_bridge=None,
            access_webtransceiver=True,
            ip_address="209.222.4.140",
            timezone_offset=None,
            is_nnx=False,
            hardware_type="Infrastructure",
            total_keyups=21,
            history_total_keyups=0,
            total_tx_time=92,
            history_tx_time=0,
            access_telephoneportal=True,
            access_functionlist=False,
            access_reverseautopatch=True,
            seqno=9645,
            timeout=0,
            apprptuptime=240706,
            totalexecdcommands=0,
            current_link_count=2,
        )

        await manager.updateSingleNode(record)

        self.assertEqual(len(connection.executed), 1)
        self.assertEqual(connection.executed[0][1]["node_id"], "2105")
        self.assertEqual(connection.executed[0][1]["current_link_count"], 2)
        connection.transaction.commit.assert_called_once()

    async def test_mysql_manager_accepts_ods_record(self) -> None:
        manager = MySQLManager("host", "user", "pwd", "db", "utf8mb4")
        connection = FakeConnection()
        manager.engine = FakeEngine(connection)
        record = OdsNodeDetailRecord(
            node_id=2105,
            node_type="ALLSTARLINK",
            callsign="KJ7OMO",
            frequency="PRIDE Multi-mode HUB",
            tone="kimberlychase.com",
            affiliation="Pride Radio Network",
            site_name="Pride Radio Network Hub",
            is_active=True,
            last_seen=datetime(2026, 3, 13, 10, 0, 0),
            latitude=40.5545,
            longitude=-74.4601,
            app_version="3.7.1",
            ip="209.222.4.140",
            timezone_offset=None,
            is_nnx=False,
            total_keyups=21,
            total_tx_time=92,
            access_webtransceiver=True,
            access_telephoneportal=True,
            access_functionlist=False,
            access_reverseautopatch=True,
            seqno=9645,
            timeout=0,
            apprptuptime=240706,
            total_execd_commands=0,
            max_uptime=None,
            current_link_count=2,
            linked_nodes=[{"name": 520580}],
            links="T520580",
            port="4569",
            batch_no="202603130001",
        )

        await manager.insert_ods_node_detail(record)

        self.assertEqual(len(connection.executed), 1)
        params = connection.executed[0][1]
        self.assertEqual(params["node_id"], 2105)
        self.assertEqual(params["batch_no"], 202603130001)
        self.assertIsInstance(params["linked_nodes"], str)
        self.assertIsInstance(params["links"], str)
        connection.transaction.commit.assert_called_once()

    async def test_neo4j_manager_accepts_graph_record(self) -> None:
        manager = Neo4jManager("bolt://x", "neo4j", "pwd")
        session = MagicMock()
        session.run = AsyncMock()
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session)
        session_cm.__aexit__ = AsyncMock(return_value=False)
        manager.driver = MagicMock()
        manager.driver.session.return_value = session_cm

        record = GraphNodeRecord(
            unique_id="2105_202603130001",
            node_id="2105",
            callsign="KJ7OMO",
            node_type="allstarlink",
            lat=40.5545,
            lon=-74.4601,
            apprptuptime=240706,
            total_keyups=21,
            total_tx_time=92,
            last_seen="2026-03-13T10:00:00",
            active=True,
            updated_at="2026-03-13T10:00:00",
            node_rank="Hub",
            features=["PRIDE Multi-mode HUB"],
            tone=None,
            location_desc="kimberlychase.com",
            hardware_type="Infrastructure",
            site_name="2105-PRIDE-HUB",
            connections=2,
            batch_no="202603130001",
        )

        await manager.update_node(record, preserve_uptime=True)

        session.run.assert_awaited_once()
        _, kwargs = session.run.await_args
        self.assertEqual(kwargs["unique_id"], "2105_202603130001")
        self.assertEqual(kwargs["create_properties"]["node_id"], "2105")
        self.assertNotIn("apprptuptime", kwargs["match_properties"])

