"""
source factory 与配置切换测试。
"""

import os
import unittest

from src.link_scraper.config.settings import Settings
from src.link_scraper.sources.allstarlink import AllStarLinkClient, AllStarLinkMapper, AllStarLinkParser
from src.link_scraper.sources.factory import build_source_components
from src.link_scraper.sources.other_source import OtherSourceClient, OtherSourceMapper, OtherSourceParser


class TestSourceFactory(unittest.TestCase):
    """验证 source 配置切换是否真正生效。"""

    def test_build_allstarlink_components(self) -> None:
        settings = Settings.load()

        components = build_source_components("allstarlink", settings.api)

        self.assertIsInstance(components.client, AllStarLinkClient)
        self.assertIsInstance(components.parser, AllStarLinkParser)
        self.assertIsInstance(components.mapper, AllStarLinkMapper)

    def test_build_other_source_components(self) -> None:
        settings = Settings.load()

        components = build_source_components("other_source", settings.api)

        self.assertIsInstance(components.client, OtherSourceClient)
        self.assertIsInstance(components.parser, OtherSourceParser)
        self.assertIsInstance(components.mapper, OtherSourceMapper)

    def test_build_unknown_source_raises(self) -> None:
        settings = Settings.load()

        with self.assertRaises(ValueError):
            build_source_components("unknown_source", settings.api)

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
