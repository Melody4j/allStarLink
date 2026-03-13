"""
数据源工厂。
"""

from dataclasses import dataclass

from ..config.settings import APIConfig
from .allstarlink import AllStarLinkClient, AllStarLinkMapper, AllStarLinkParser
from .base import SourceClient, SourceMapper, SourceParser
from .other_source import OtherSourceClient, OtherSourceMapper, OtherSourceParser


@dataclass
class SourceComponents:
    """统一承载数据源实例，避免 main 中散落多处判断。"""

    client: SourceClient
    parser: SourceParser
    mapper: SourceMapper


def build_source_components(source_name: str, api_config: APIConfig) -> SourceComponents:
    """按配置创建对应的数据源组件。

    当前支持：
    - allstarlink: 生产主线数据源
    - other_source: 第二数据源骨架，占位后续真实接入
    """
    normalized_name = (source_name or "allstarlink").strip().lower()

    if normalized_name == "allstarlink":
        parser = AllStarLinkParser()
        return SourceComponents(
            client=AllStarLinkClient(api_config),
            parser=parser,
            mapper=AllStarLinkMapper(parser),
        )

    if normalized_name == "other_source":
        parser = OtherSourceParser()
        return SourceComponents(
            client=OtherSourceClient(api_config),
            parser=parser,
            mapper=OtherSourceMapper(parser),
        )

    raise ValueError(f"不支持的数据源: {source_name}")
