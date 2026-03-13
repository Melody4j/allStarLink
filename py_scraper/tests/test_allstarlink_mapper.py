"""
AllStarLink mapper 相关测试。
"""

import unittest

from src.link_scraper.sources.allstarlink.mapper import AllStarLinkMapper


def build_node_detail_payload() -> dict:
    """构造一个足够覆盖当前解析链路的详情样例。"""
    return {
        "stats": {
            "user_node": {
                "name": 2105,
                "callsign": "KJ7OMO",
                "node_frequency": "PRIDE Multi-mode HUB",
                "node_tone": "kimberlychase.com",
                "User_ID": "KJ7OMO",
                "ipaddr": "209.222.4.140",
                "is_nnx": "No",
                "access_webtransceiver": "1",
                "access_telephoneportal": "1",
                "access_functionlist": "0",
                "access_reverseautopatch": "1",
                "server": {
                    "Affiliation": "Pride Radio Network",
                    "Server_Name": "2105-PRIDE-HUB",
                    "SiteName": "Pride Radio Network Hub",
                    "Latitude": "40.5545",
                    "Logitude": "-74.4601",
                    "Location": "Cloud 69",
                    "udpport": 4569,
                },
            },
            "data": {
                "apprptuptime": "240706",
                "totalkeyups": "21",
                "totaltxtime": "92",
                "apprptvers": "3.7.1",
                "timeouts": "0",
                "seqno": "9645",
                "totalexecdcommands": "0",
                "nodes": "T520580,R1001",
                "linkedNodes": [
                    {
                        "Node_ID": 65481,
                        "name": 520580,
                        "callsign": "KJ7OMO",
                        "Status": "Active",
                        "node_frequency": "444.900 (+)",
                        "node_tone": "110.9",
                        "server": {
                            "SiteName": "Raspberry Pi",
                            "Latitude": "32.6686",
                            "Logitude": "-114.5991",
                        },
                    },
                    {
                        "name": "1001",
                        "callsign": "REMOTE",
                        "Status": "Inactive",
                        "node_frequency": "",
                        "node_tone": "",
                    },
                ],
            },
        }
    }


class TestAllStarLinkMapper(unittest.TestCase):
    """验证 AllStarLink source mapper 的关键行为。"""

    def test_map_node_list_extracts_node_id_and_link_count(self) -> None:
        mapper = AllStarLinkMapper()
        payload = {
            "data": [
                ['<a href="/stats/2105">2105</a>', "ignored", 5],
                ["1001 something", "ignored", "2"],
                ["bad-row", "ignored", "x"],
            ]
        }

        result = mapper.map_node_list(payload)

        self.assertEqual(
            result,
            [
                {"node_id": 2105, "link_count": 5},
                {"node_id": 1001, "link_count": 2},
            ],
        )

    def test_map_node_detail_builds_canonical_bundle(self) -> None:
        mapper = AllStarLinkMapper()

        bundle = mapper.map_node_detail(build_node_detail_payload(), batch_no="202603130001")

        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle.primary_node.node_id, "2105")
        self.assertEqual(bundle.primary_node.source_name, "allstarlink")
        self.assertEqual(bundle.primary_node.record_kind, "full")
        self.assertEqual(bundle.primary_node.data_completeness, "complete")
        self.assertEqual(len(bundle.linked_nodes), 2)
        self.assertEqual(bundle.linked_nodes[0].record_kind, "stub")
        self.assertEqual(bundle.linked_nodes[0].data_completeness, "partial")
        self.assertEqual(len(bundle.connections), 2)
        self.assertEqual(bundle.connections[0].direction, "Transceive")
        self.assertEqual(bundle.connections[1].direction, "RX Only")

