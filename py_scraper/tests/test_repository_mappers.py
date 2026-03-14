"""
领域模型到持久化对象映射测试。
"""

import unittest
from datetime import datetime

from src.link_scraper.modules.allstarlink.models.domain import (
    CanonicalConnection,
    CanonicalNode,
    CanonicalNodeBundle,
)
from src.link_scraper.modules.allstarlink.mappers import DimNodeMapper, GraphMapper, OdsMapper


class TestRepositoryMappers(unittest.TestCase):
    """验证 record mapper 是否保留关键字段语义。"""

    def setUp(self) -> None:
        now = datetime(2026, 3, 13, 10, 0, 0)
        self.node = CanonicalNode(
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
            connections=2,
            site_name="2105-PRIDE-HUB",
            batch_no="202603130001",
        )

    def test_graph_mapper_builds_unique_id(self) -> None:
        record = GraphMapper.map_node(self.node)

        self.assertEqual(record.unique_id, "2105_202603130001")
        self.assertEqual(record.to_properties()["siteName"], "2105-PRIDE-HUB")

    def test_dim_mapper_maps_current_link_count(self) -> None:
        record = DimNodeMapper.map_node(self.node)

        self.assertEqual(record.node_id, "2105")
        self.assertEqual(record.current_link_count, 2)

    def test_ods_mapper_uses_raw_payload_semantics(self) -> None:
        bundle = CanonicalNodeBundle(
            primary_node=self.node,
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
                        "nodes": "T520580,R1001",
                        "linkedNodes": [{"name": 520580}, {"name": 1001}],
                    },
                }
            },
        )

        record = OdsMapper.map_bundle(bundle)

        self.assertEqual(record.node_id, 2105)
        self.assertEqual(record.current_link_count, 2)
        self.assertEqual(record.links, "T520580,R1001")
        self.assertEqual(record.port, "4569")

