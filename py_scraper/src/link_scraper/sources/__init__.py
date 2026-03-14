"""数据源协议与装配入口。"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from ..config.settings import Settings
from ..modules.allstarlink.source import AllStarLinkClient, AllStarLinkMapper, AllStarLinkParser
from ..modules.other_source.source import OtherSourceClient, OtherSourceMapper, OtherSourceParser


class SourceClient(Protocol):
    """约束数据源客户端的最小能力。"""

    async def fetch_node_list(self) -> Optional[Any]:
        """获取节点列表原始响应。"""

    async def fetch_node_detail(self, node_id: int) -> Optional[Any]:
        """获取节点详情原始响应。"""

    async def close(self) -> None:
        """释放客户端持有的资源。"""


class SourceParser(Protocol):
    """约束 source parser 的解析接口。"""

    def parse_node(self, data: Dict[str, Any]) -> Optional[Any]:
        """解析主节点对象。"""

    def parse_linked_node(self, linked_node: Dict[str, Any]) -> Optional[Any]:
        """解析关联节点对象。"""

    def parse_connections(
        self,
        node_id: int,
        connection_modes: str,
        linked_nodes: List[Dict[str, Any]],
        batch_no: Optional[str] = None,
    ) -> List[Any]:
        """解析连接关系对象。"""


class SourceMapper(Protocol):
    """约束 source mapper 的转换接口。"""

    def map_node_list(self, payload: Any) -> List[Dict[str, Any]]:
        """把节点列表响应转换成队列可消费数据。"""

    def map_node_detail(
        self,
        payload: Any,
        batch_no: Optional[str] = None,
    ) -> Optional[Any]:
        """把节点详情响应转换成业务聚合对象。"""


@dataclass
class SourceComponents:
    """统一承载 source 运行时依赖，避免业务层散落多处判断。"""

    client: SourceClient
    parser: SourceParser
    mapper: SourceMapper


def build_source_components(source_name: str, settings: Settings) -> SourceComponents:
    """按 source_name 装配对应的数据源组件。"""

    normalized_name = (source_name or "allstarlink").strip().lower()

    if normalized_name == "allstarlink":
        parser = AllStarLinkParser()
        return SourceComponents(
            client=AllStarLinkClient(settings.allstarlink.source, settings.network),
            parser=parser,
            mapper=AllStarLinkMapper(parser),
        )

    if normalized_name == "other_source":
        parser = OtherSourceParser()
        return SourceComponents(
            client=OtherSourceClient(settings.network),
            parser=parser,
            mapper=OtherSourceMapper(parser),
        )

    raise ValueError(f"不支持的数据源: {source_name}")


__all__ = [
    "SourceClient",
    "SourceParser",
    "SourceMapper",
    "SourceComponents",
    "build_source_components",
]
