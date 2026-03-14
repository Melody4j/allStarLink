"""node_topology repository 测试。"""

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.link_scraper.modules.allstarlink.models.record import (
    DimNodeRecord,
    GraphConnectionRecord,
    GraphNodeRecord,
    OdsNodeDetailRecord,
)
from src.link_scraper.modules.allstarlink.repositories.node_topology_repository import (
    NodeTopologyDimNodeRepository,
    NodeTopologyGraphRepository,
    NodeTopologyOdsRepository,
)


class TestRepositories(unittest.IsolatedAsyncioTestCase):
    async def test_graph_repository_builds_queries(self) -> None:
        neo4j_manager = AsyncMock()
        delete_summary = MagicMock()
        delete_summary.counters.nodes_deleted = 1
        neo4j_manager.execute_write.side_effect = [None, None, delete_summary]
        neo4j_manager.execute_read.side_effect = [[], []]
        repository = NodeTopologyGraphRepository(neo4j_manager)

        node = GraphNodeRecord(
            unique_id="2105_202603130001",
            node_id="2105",
            callsign="KJ7OMO",
            node_type="allstarlink",
            lat=40.5545,
            lon=-74.4601,
            apprptuptime=1,
            total_keyups=2,
            total_tx_time=3,
            last_seen="2026-03-13T10:00:00",
            active=True,
            updated_at="2026-03-13T10:00:00",
            node_rank="Hub",
            features=[],
            tone=None,
            location_desc=None,
            hardware_type="Infrastructure",
            site_name="2105-PRIDE-HUB",
            connections=1,
            batch_no="202603130001",
        )
        connection = GraphConnectionRecord(
            src_unique_id="2105_202603130001",
            dst_unique_id="520580_202603130001",
            source_id="2105",
            target_id="520580",
            status="Active",
            direction="Transceive",
            last_updated=datetime(2026, 3, 13, 10, 0, 0),
            active=True,
            batch_no="202603130001",
        )

        await repository.upsert_node(node, preserve_counters=True, preserve_uptime=True)
        await repository.upsert_topology("2105", [connection])
        deleted = await repository.delete_node_by_unique_id("2105_202603130001")

        self.assertTrue(deleted)
        self.assertEqual(neo4j_manager.execute_write.await_count, 3)
        self.assertEqual(neo4j_manager.execute_read.await_count, 2)

    async def test_dim_and_ods_repository_execute_sql(self) -> None:
        mysql_manager = AsyncMock()
        dim_repository = NodeTopologyDimNodeRepository(mysql_manager)
        ods_repository = NodeTopologyOdsRepository(mysql_manager)

        dim_record = DimNodeRecord(
            node_id="2105",
            node_type="allstarlink",
            callsign="KJ7OMO",
            tone=None,
            owner=None,
            affiliation=None,
            site_name=None,
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
            access_webtransceiver=None,
            ip_address=None,
            timezone_offset=None,
            is_nnx=None,
            hardware_type="Infrastructure",
            total_keyups=None,
            history_total_keyups=None,
            total_tx_time=None,
            history_tx_time=None,
            access_telephoneportal=None,
            access_functionlist=None,
            access_reverseautopatch=None,
            seqno=None,
            timeout=None,
            apprptuptime=None,
            totalexecdcommands=None,
            current_link_count=1,
        )
        ods_record = OdsNodeDetailRecord(
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
            current_link_count=1,
            linked_nodes=[{"name": 520580}],
            links="T520580",
            port="4569",
            batch_no="202603130001",
        )

        await dim_repository.update_node(dim_record, update_current_link_count=False)
        await ods_repository.insert_detail(ods_record)

        self.assertEqual(mysql_manager.execute_statement.await_count, 2)
