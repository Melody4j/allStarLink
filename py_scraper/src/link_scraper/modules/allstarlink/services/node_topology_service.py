"""`node_topology` 任务的运行时装配。"""

from dataclasses import dataclass
import logging

from ....app.context import AppContext
from ....sources import SourceComponents, build_source_components
from ..repositories.node_topology_repository import (
    NodeTopologyDimNodeRepository,
    NodeTopologyGraphRepository,
    NodeTopologyOdsRepository,
    NodeTopologyRepositories,
)
from .node_topology_fetch_service import NodeTopologyFetchService
from .node_topology_parse_service import NodeTopologyParseService
from .node_topology_scanner import NodeTopologySnapshotScanner
from .node_topology_worker import NodeTopologyWorker

logger = logging.getLogger(__name__)


class NodeTopologySyncService:
    """负责把节点详情同步到图和维表。"""

    def __init__(self, repositories: NodeTopologyRepositories) -> None:
        self.repositories = repositories

    async def sync_bundle(self, bundle) -> None:
        await self.repositories.upsert_primary_graph_node(bundle)
        await self.repositories.upsert_linked_graph_nodes(bundle)
        await self.repositories.upsert_topology(bundle)
        await self.repositories.refresh_linked_graph_nodes(bundle)
        await self.repositories.upsert_dim_nodes(bundle)


class NodeTopologyOdsService:
    """负责把节点详情追加写入 ODS 明细。"""

    def __init__(self, repositories: NodeTopologyRepositories) -> None:
        self.repositories = repositories

    async def write_bundle(self, bundle) -> None:
        await self.repositories.write_ods_snapshot(bundle)
        logger.info("Node topology task wrote ODS snapshot for node %s", bundle.primary_node.node_id)


@dataclass
class NodeTopologyRuntime:
    """`node_topology` 任务运行所需依赖集合。"""

    source_components: SourceComponents
    repositories: NodeTopologyRepositories
    scanner: NodeTopologySnapshotScanner
    worker: NodeTopologyWorker

    async def close(self) -> None:
        await self.source_components.client.close()


def build_node_topology_runtime(context: AppContext) -> NodeTopologyRuntime:
    """装配 `node_topology` 任务运行时依赖。"""

    source_components = build_source_components(context.settings.source_name, context.settings)
    repositories = NodeTopologyRepositories(
        graph=NodeTopologyGraphRepository(context.graph_storage_manager),
        dim_node=NodeTopologyDimNodeRepository(context.relational_storage_manager),
        ods=NodeTopologyOdsRepository(context.relational_storage_manager),
    )

    fetch_service = NodeTopologyFetchService(source_components.client)
    parse_service = NodeTopologyParseService(source_components.mapper)
    sync_service = NodeTopologySyncService(repositories)
    ods_service = NodeTopologyOdsService(repositories)

    scanner = NodeTopologySnapshotScanner(
        redis_queue=context.priority_queue,
        mysql_manager=context.relational_storage_manager,
        network_config=context.settings.network,
        batch_manager=context.batch_manager,
        source_client=source_components.client,
        source_mapper=source_components.mapper,
    )
    worker = NodeTopologyWorker(
        redis_queue=context.priority_queue,
        network_config=context.settings.network,
        rate_limiter=context.rate_limiter,
        fetch_service=fetch_service,
        parse_service=parse_service,
        sync_service=sync_service,
        ods_service=ods_service,
        repositories=repositories,
    )

    return NodeTopologyRuntime(
        source_components=source_components,
        repositories=repositories,
        scanner=scanner,
        worker=worker,
    )
