"""source factory 与配置切换测试。"""

import os
import unittest

from src.link_scraper.config.settings import Settings
from src.link_scraper.modules.allstarlink.source import (
    AllStarLinkClient,
    AllStarLinkMapper,
    AllStarLinkParser,
)
from src.link_scraper.modules.other_source.source import (
    OtherSourceClient,
    OtherSourceMapper,
    OtherSourceParser,
)
from src.link_scraper.sources import build_source_components


class TestSourceFactory(unittest.TestCase):
    """验证 source 装配与配置切换是否生效。"""

    def test_build_allstarlink_components(self) -> None:
        settings = Settings.load()

        components = build_source_components("allstarlink", settings)

        self.assertIsInstance(components.client, AllStarLinkClient)
        self.assertIsInstance(components.parser, AllStarLinkParser)
        self.assertIsInstance(components.mapper, AllStarLinkMapper)

    def test_build_other_source_components(self) -> None:
        settings = Settings.load()

        components = build_source_components("other_source", settings)

        self.assertIsInstance(components.client, OtherSourceClient)
        self.assertIsInstance(components.parser, OtherSourceParser)
        self.assertIsInstance(components.mapper, OtherSourceMapper)

    def test_build_unknown_source_raises(self) -> None:
        settings = Settings.load()

        with self.assertRaises(ValueError):
            build_source_components("unknown_source", settings)

    def test_settings_reads_source_name_from_env(self) -> None:
        original = os.environ.get("SOURCE_NAME")
        os.environ["SOURCE_NAME"] = "other_source"
        try:
            settings = Settings.load()
            self.assertEqual(settings.source_name, "other_source")
        finally:
            if original is None:
                os.environ.pop("SOURCE_NAME", None)
            else:
                os.environ["SOURCE_NAME"] = original

    def test_settings_reads_allstarlink_task_overrides_from_env(self) -> None:
        """验证 V3 task 级配置可由环境变量覆盖。"""
        originals = {
            "ALLSTARLINK_ENABLED": os.environ.get("ALLSTARLINK_ENABLED"),
            "ALLSTARLINK_NODE_LIST_SNAPSHOT_ENABLED": os.environ.get("ALLSTARLINK_NODE_LIST_SNAPSHOT_ENABLED"),
            "ALLSTARLINK_NODE_LIST_SNAPSHOT_INTERVAL_SECONDS": os.environ.get("ALLSTARLINK_NODE_LIST_SNAPSHOT_INTERVAL_SECONDS"),
            "ALLSTARLINK_NODE_LIST_SNAPSHOT_TIMEOUT_SECONDS": os.environ.get("ALLSTARLINK_NODE_LIST_SNAPSHOT_TIMEOUT_SECONDS"),
            "ALLSTARLINK_NODE_LIST_SNAPSHOT_COOLDOWN_SECONDS": os.environ.get("ALLSTARLINK_NODE_LIST_SNAPSHOT_COOLDOWN_SECONDS"),
        }
        os.environ["ALLSTARLINK_ENABLED"] = "true"
        os.environ["ALLSTARLINK_NODE_LIST_SNAPSHOT_ENABLED"] = "false"
        os.environ["ALLSTARLINK_NODE_LIST_SNAPSHOT_INTERVAL_SECONDS"] = "120"
        os.environ["ALLSTARLINK_NODE_LIST_SNAPSHOT_TIMEOUT_SECONDS"] = "15"
        os.environ["ALLSTARLINK_NODE_LIST_SNAPSHOT_COOLDOWN_SECONDS"] = "9"
        try:
            settings = Settings.load()
            self.assertTrue(settings.allstarlink.enabled)
            self.assertFalse(settings.allstarlink.tasks.node_list_snapshot.enabled)
            self.assertEqual(settings.allstarlink.tasks.node_list_snapshot.interval_seconds, 120)
            self.assertEqual(settings.allstarlink.tasks.node_list_snapshot.timeout_seconds, 15.0)
            self.assertEqual(settings.allstarlink.tasks.node_list_snapshot.cooldown_seconds, 9.0)
        finally:
            for key, value in originals.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
