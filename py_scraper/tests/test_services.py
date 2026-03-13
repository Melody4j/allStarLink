"""
服务层测试。
"""

import unittest
from datetime import datetime

from src.link_scraper.domain.models import CanonicalNode, CanonicalNodeBundle
from src.link_scraper.services.ods_service import OdsWriteService
from src.link_scraper.services.parse_service import NodeParseService
from src.link_scraper.services.sync_service import NodeSyncService


class FakeSourceMapper:
    """用于验证 parse service 是否正确委派 mapper。"""

    def __init__(self, bundle):
        self.bundle = bundle
        self.calls = []

    def map_node_detail(self, payload, batch_no=None):
        self.calls.append((payload, batch_no))
        return self.bundle


class FakeGraphRepository:
    """记录图仓储调用顺序，便于验证同步流程。"""

    def __init__(self) -> None:
        self.calls = []

    async def upsert_node(self, node, preserve_counters=False, preserve_uptime=False):
        self.calls.append(("node", node.node_id, preserve_counters, preserve_uptime))

    async def upsert_topology(self, node_id, connections):
        self.calls.append(("topology", node_id, len(connections)))


class FakeDimNodeRepository:
    """记录维表更新次数和参数。"""

    def __init__(self) -> None:
        self.calls = []

    async def update_node(self, node, update_current_link_count=True):
        self.calls.append((node.node_id, update_current_link_count))


class FakeOdsRepository:
    """记录 ODS 写入对象。"""

    def __init__(self) -> None:
        self.calls = []

    async def insert_detail(self, detail):
        self.calls.append(detail)


class TestServices(unittest.IsolatedAsyncioTestCase):
    """验证服务层委派与流程顺序。"""

    def build_bundle(self) -> CanonicalNodeBundle:
        now = datetime(2026, 3, 13, 10, 0, 0)
        primary = CanonicalNode(
            node_id="2105",
            callsign="KJ7OMO",
            source_name="allstarlink",
            node_type="allstarlink",
            lat=40.5545,
            lon=-74.4601,
            apprptuptime=240706,
            total_keyups=21,
            total_tx_time=92,
            last_seen=now,
            active=True,
            updated_at=now,
            node_rank="Hub",
            features=["PRIDE Multi-mode HUB"],
            tone=None,
            location_desc="kimberlychase.com",
            hardware_type="Infrastructure",
            connections=1,
            batch_no="202603130001",
        )
        linked = CanonicalNode(
            node_id="520580",
            callsign="REMOTE",
            source_name="allstarlink",
            node_type="allstarlink",
            lat=32.6686,
            lon=-114.5991,
            apprptuptime=None,
            total_keyups=None,
            total_tx_time=None,
            last_seen=now,
            active=True,
            updated_at=now,
            node_rank="Repeater",
            features=[],
            tone=110.9,
            location_desc=None,
            hardware_type="Embedded Node",
            connections=None,
            batch_no="202603130001",
            record_kind="stub",
            data_completeness="partial",
        )
        return CanonicalNodeBundle(
            primary_node=primary,
            linked_nodes=[linked],
            connections=[],
            raw_payload={
                "stats": {
                    "user_node": {
                        "name": 2105,
                        "callsign": "KJ7OMO",
                        "node_frequency": "PRIDE Multi-mode HUB",
                        "node_tone": "kimberlychase.com",
                        "ipaddr": "209.222.4.140",
                        "is_nnx": "No",
                        "access_webtransceiver": "1",
                        "access_telephoneportal": "1",
                        "access_functionlist": "0",
                        "access_reverseautopatch": "1",
                        "server": {
                            "Affiliation": "Pride Radio Network",
                            "SiteName": "Pride Radio Network Hub",
                            "Latitude": "40.5545",
                            "Logitude": "-74.4601",
                            "udpport": 4569,
                        },
                    },
                    "data": {
                        "apprptvers": "3.7.1",
                        "totalkeyups": "21",
                        "totaltxtime": "92",
                        "seqno": "9645",
                        "timeouts": "0",
                        "apprptuptime": "240706",
                        "totalexecdcommands": "0",
                        "nodes": "",
                        "linkedNodes": [{"name": 520580}],
                    },
                }
            },
        )

    def test_parse_service_delegates_to_mapper(self) -> None:
        bundle = self.build_bundle()
        mapper = FakeSourceMapper(bundle)
        service = NodeParseService(mapper)

        result = service.parse_node_detail({"x": 1}, "202603130001")

        self.assertIs(result, bundle)
        self.assertEqual(mapper.calls, [({"x": 1}, "202603130001")])

    async def test_sync_service_preserves_expected_write_order(self) -> None:
        graph_repository = FakeGraphRepository()
        dim_repository = FakeDimNodeRepository()
        service = NodeSyncService(graph_repository, dim_repository)

        await service.sync_bundle(self.build_bundle())

        self.assertEqual(graph_repository.calls[0][0], "node")
        self.assertEqual(graph_repository.calls[0][1], "2105")
        self.assertEqual(graph_repository.calls[1][0], "node")
        self.assertEqual(graph_repository.calls[1][1], "520580")
        self.assertEqual(graph_repository.calls[2], ("node", "520580", True, True))
        self.assertEqual(dim_repository.calls[0], ("2105", True))
        self.assertEqual(dim_repository.calls[1], ("520580", False))

    async def test_ods_service_writes_repository_record(self) -> None:
        ods_repository = FakeOdsRepository()
        service = OdsWriteService(ods_repository)

        await service.write_bundle(self.build_bundle())

        self.assertEqual(len(ods_repository.calls), 1)
        self.assertEqual(ods_repository.calls[0].node_id, 2105)

