"""`node_topology` 任务的数据访问实现。"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from typing import TYPE_CHECKING, List

from ..mappers import DimNodeMapper, GraphMapper, OdsMapper
from ..models.domain import CanonicalNodeBundle
from ..models.record import GraphConnectionRecord, GraphNodeRecord, OdsNodeDetailRecord

if TYPE_CHECKING:
    from ....database.mysql_manager import RelationalStorageManager
    from ....database.neo4j_manager import GraphStorageManager
    from ..models.record import DimNodeRecord

logger = logging.getLogger(__name__)


def _counter_value(summary, field: str) -> int:
    if not summary or not getattr(summary, "counters", None):
        return 0
    return int(getattr(summary.counters, field, 0) or 0)


class NodeTopologyGraphRepository:
    """封装 `node_topology` 任务的图写入语义。"""

    def __init__(self, neo4j_manager: "GraphStorageManager") -> None:
        self.neo4j_manager = neo4j_manager

    async def upsert_node(
        self,
        node: GraphNodeRecord,
        preserve_counters: bool = False,
        preserve_uptime: bool = False,
    ) -> None:
        if not node.validate():
            logger.warning("图节点 record 校验失败，跳过更新: %s", node.node_id)
            return

        unique_id = node.unique_id
        properties = node.to_properties()

        if preserve_counters:
            create_properties = properties.copy()
            match_properties = properties.copy()
            match_properties.pop("total_keyups", None)
            match_properties.pop("total_tx_time", None)
            if preserve_uptime:
                match_properties.pop("apprptuptime", None)
            summary = await self.neo4j_manager.execute_write(
                """
                MERGE (n:Node {unique_id: $unique_id})
                ON CREATE SET n = $create_properties
                ON MATCH SET n += $match_properties
                """,
                unique_id=unique_id,
                create_properties=create_properties,
                match_properties=match_properties,
            )
            logger.info(
                "node_topology: Neo4j 节点同步完成 node_id=%s unique_id=%s mode=preserve_counters nodes_created=%s properties_set=%s",
                node.node_id,
                unique_id,
                _counter_value(summary, "nodes_created"),
                _counter_value(summary, "properties_set"),
            )
            return

        if preserve_uptime:
            create_properties = properties.copy()
            match_properties = properties.copy()
            match_properties.pop("apprptuptime", None)
            summary = await self.neo4j_manager.execute_write(
                """
                MERGE (n:Node {unique_id: $unique_id})
                ON CREATE SET n = $create_properties
                ON MATCH SET n += $match_properties
                """,
                unique_id=unique_id,
                create_properties=create_properties,
                match_properties=match_properties,
            )
            logger.info(
                "node_topology: Neo4j 节点同步完成 node_id=%s unique_id=%s mode=preserve_uptime nodes_created=%s properties_set=%s",
                node.node_id,
                unique_id,
                _counter_value(summary, "nodes_created"),
                _counter_value(summary, "properties_set"),
            )
            return

        summary = await self.neo4j_manager.execute_write(
            """
            MERGE (n:Node {unique_id: $unique_id})
            ON CREATE SET n = $properties
            ON MATCH SET n = $properties
            """,
            unique_id=unique_id,
            properties=properties,
        )
        logger.info(
            "node_topology: Neo4j 节点同步完成 node_id=%s unique_id=%s mode=replace nodes_created=%s properties_set=%s",
            node.node_id,
            unique_id,
            _counter_value(summary, "nodes_created"),
            _counter_value(summary, "properties_set"),
        )

    async def upsert_topology(self, node_id: str, connections: List[GraphConnectionRecord]) -> None:
        valid_connections = [conn for conn in connections if conn.validate()]
        if not valid_connections:
            logger.warning("节点 %s 没有有效的连接关系", node_id)
            return

        current_time = datetime.now().isoformat()
        connection_pairs = [(conn.src_unique_id, conn.dst_unique_id, conn) for conn in valid_connections]
        existing_connections = await self.neo4j_manager.execute_read(
            """
            UNWIND $pairs AS pair
            MATCH (a:Node {unique_id: pair.src_unique_id})-[r:CONNECTED_TO]-(b:Node {unique_id: pair.dst_unique_id})
            RETURN pair.src_unique_id AS src_unique_id,
                   pair.dst_unique_id AS dst_unique_id,
                   pair.conn AS conn,
                   r
            """,
            pairs=[
                {
                    "src_unique_id": src,
                    "dst_unique_id": dst,
                    "conn": {
                        "status": conn.status,
                        "active": conn.active,
                        "batch_no": conn.batch_no,
                        "direction": conn.direction,
                    },
                }
                for src, dst, conn in connection_pairs
            ],
        )

        existing_pairs = {(record["src_unique_id"], record["dst_unique_id"]) for record in existing_connections}
        to_update = existing_connections
        to_create = [
            (src, dst, conn)
            for src, dst, conn in connection_pairs
            if (src, dst) not in existing_pairs and (dst, src) not in existing_pairs
        ]

        updated_count = 0
        created_count = 0

        if to_update:
            summary = await self.neo4j_manager.execute_write(
                """
                UNWIND $updates AS update
                MATCH (a:Node {unique_id: update.src_unique_id})-[r:CONNECTED_TO]-(b:Node {unique_id: update.dst_unique_id})
                SET r.status = update.status,
                    r.last_updated = $last_updated,
                    r.active = update.active,
                    r.batch_no = update.batch_no
                """,
                updates=[
                    {
                        "src_unique_id": record["src_unique_id"],
                        "dst_unique_id": record["dst_unique_id"],
                        "status": record["conn"]["status"],
                        "active": record["conn"]["active"],
                        "batch_no": record["conn"]["batch_no"],
                    }
                    for record in to_update
                ],
                last_updated=current_time,
            )
            updated_count = _counter_value(summary, "properties_set")

        if to_create:
            all_node_ids = list({src for src, dst, _ in to_create} | {dst for src, dst, _ in to_create})
            existing_nodes = await self.neo4j_manager.execute_read(
                """
                UNWIND $node_ids AS node_id
                MATCH (n:Node {unique_id: node_id})
                RETURN node_id
                """,
                node_ids=all_node_ids,
            )
            valid_node_ids = {record["node_id"] for record in existing_nodes}
            valid_to_create = [
                (src, dst, conn)
                for src, dst, conn in to_create
                if src in valid_node_ids and dst in valid_node_ids
            ]
            if valid_to_create:
                summary = await self.neo4j_manager.execute_write(
                    """
                    UNWIND $creates AS create
                    MATCH (src:Node {unique_id: create.src_unique_id})
                    MATCH (dst:Node {unique_id: create.dst_unique_id})
                    CREATE (src)-[r:CONNECTED_TO]->(dst)
                    SET r.status = create.status,
                        r.direction = create.direction,
                        r.last_updated = $last_updated,
                        r.active = create.active,
                        r.batch_no = create.batch_no
                    """,
                    creates=[
                        {
                            "src_unique_id": src,
                            "dst_unique_id": dst,
                            "status": conn.status,
                            "direction": conn.direction,
                            "active": conn.active,
                            "batch_no": conn.batch_no,
                        }
                        for src, dst, conn in valid_to_create
                    ],
                    last_updated=current_time,
                )
                created_count = _counter_value(summary, "relationships_created")

        logger.info(
            "node_topology: Neo4j 拓扑同步完成 node_id=%s valid_connections=%s matched_existing=%s relationships_created=%s",
            node_id,
            len(valid_connections),
            len(to_update),
            created_count,
        )
        if updated_count:
            logger.info(
                "node_topology: Neo4j 关系属性更新完成 node_id=%s properties_set=%s",
                node_id,
                updated_count,
            )

    async def delete_node_by_unique_id(self, unique_id: str) -> bool:
        relation_summary = await self.neo4j_manager.execute_write(
            """
            MATCH (n:Node {unique_id: $unique_id})-[r]-()
            DELETE r
            """,
            unique_id=unique_id,
        )
        summary = await self.neo4j_manager.execute_write(
            """
            MATCH (n:Node {unique_id: $unique_id})
            DELETE n
            """,
            unique_id=unique_id,
        )
        deleted = bool(summary and summary.counters.nodes_deleted > 0)
        logger.info(
            "node_topology: Neo4j 节点删除完成 unique_id=%s relationships_deleted=%s nodes_deleted=%s",
            unique_id,
            _counter_value(relation_summary, "relationships_deleted"),
            _counter_value(summary, "nodes_deleted"),
        )
        return deleted


class NodeTopologyDimNodeRepository:
    """封装 `node_topology` 任务的维表写入语义。"""

    def __init__(self, mysql_manager: "RelationalStorageManager") -> None:
        self.mysql_manager = mysql_manager

    async def update_node(
        self,
        node: "DimNodeRecord",
        update_current_link_count: bool = True,
    ) -> None:
        if not node.validate():
            logger.warning("维表 record 校验失败，跳过更新: %s", node.node_id)
            return

        params = {
            "node_id": node.node_id,
            "node_type": node.node_type,
            "site_name": node.site_name if node.site_name else "",
            "access_webtransceiver": 1 if node.access_webtransceiver else 0,
            "ip_address": node.ip_address if node.ip_address else "",
            "timezone_offset": node.timezone_offset,
            "is_nnx": 1 if node.is_nnx else 0,
            "history_total_keyups": node.history_total_keyups if node.history_total_keyups is not None else 0,
            "history_tx_time": node.history_tx_time if node.history_tx_time is not None else 0,
            "access_telephoneportal": 1 if node.access_telephoneportal else 0,
            "access_functionlist": 1 if node.access_functionlist else 0,
            "access_reverseautopatch": 1 if node.access_reverseautopatch else 0,
            "seqno": node.seqno if node.seqno is not None else 0,
            "timeout": node.timeout if node.timeout is not None else 0,
            "totalexecdcommands": node.totalexecdcommands if node.totalexecdcommands is not None else 0,
            "apprptuptime": node.apprptuptime,
            "current_link_count": node.current_link_count,
        }
        set_clauses = [
            "access_webtransceiver = :access_webtransceiver",
            "ip_address = :ip_address",
            "timezone_offset = :timezone_offset",
            "is_nnx = :is_nnx",
            "history_total_keyups = :history_total_keyups",
            "history_tx_time = :history_tx_time",
            "access_telephoneportal = :access_telephoneportal",
            "access_functionlist = :access_functionlist",
            "access_reverseautopatch = :access_reverseautopatch",
            "seqno = :seqno",
            "timeout = :timeout",
            "totalexecdcommands = :totalexecdcommands",
            "site_name = :site_name",
            "node_type = :node_type",
        ]
        if node.apprptuptime is not None:
            set_clauses.append("apprptuptime = :apprptuptime")
        if update_current_link_count:
            set_clauses.append("current_link_count = :current_link_count")

        await self.mysql_manager.execute_statement(
            f"""
            UPDATE dim_nodes SET
            {", ".join(set_clauses)}
            WHERE node_id = :node_id
            """,
            params,
        )
        logger.info(
            "node_topology: MySQL 维表更新完成 node_id=%s update_current_link_count=%s",
            node.node_id,
            update_current_link_count,
        )


class NodeTopologyOdsRepository:
    """封装 `node_topology` 任务的 ODS 写入语义。"""

    def __init__(self, mysql_manager: "RelationalStorageManager") -> None:
        self.mysql_manager = mysql_manager

    async def insert_detail(self, detail: OdsNodeDetailRecord) -> None:
        if not detail.validate():
            logger.warning("ODS record 校验失败，跳过写入: %s", detail.node_id)
            return

        params = {
            "node_id": detail.node_id,
            "node_type": detail.node_type,
            "callsign": detail.callsign,
            "frequency": detail.frequency,
            "tone": detail.tone,
            "affiliation": detail.affiliation,
            "site_name": detail.site_name,
            "is_active": 1 if detail.is_active else 0 if detail.is_active is not None else None,
            "last_seen": detail.last_seen,
            "latitude": detail.latitude,
            "longitude": detail.longitude,
            "app_version": detail.app_version,
            "ip": detail.ip,
            "timezone_offset": detail.timezone_offset,
            "is_nnx": 1 if detail.is_nnx else 0 if detail.is_nnx is not None else None,
            "total_keyups": detail.total_keyups,
            "total_tx_time": detail.total_tx_time,
            "access_webtransceiver": 1 if detail.access_webtransceiver else 0 if detail.access_webtransceiver is not None else None,
            "access_telephoneportal": 1 if detail.access_telephoneportal else 0 if detail.access_telephoneportal is not None else None,
            "access_functionlist": 1 if detail.access_functionlist else 0 if detail.access_functionlist is not None else None,
            "access_reverseautopatch": 1 if detail.access_reverseautopatch else 0 if detail.access_reverseautopatch is not None else None,
            "seqno": detail.seqno,
            "timeout": detail.timeout,
            "apprptuptime": detail.apprptuptime,
            "total_execd_commands": detail.total_execd_commands,
            "max_uptime": detail.max_uptime,
            "current_link_count": detail.current_link_count,
            "linked_nodes": json.dumps(detail.linked_nodes) if detail.linked_nodes else None,
            "links": json.dumps(detail.links) if detail.links is not None else None,
            "port": detail.port,
            "batch_no": int(detail.batch_no) if detail.batch_no is not None else None,
        }
        await self.mysql_manager.execute_statement(
            """
            INSERT INTO ods_nodes_details
            (node_id, node_type, callsign, frequency, tone, affiliation, site_name,
             is_active, last_seen, latitude, longitude, app_version, ip, timezone_offset,
             is_nnx, total_keyups, total_tx_time, access_webtransceiver,
             access_telephoneportal, access_functionlist, access_reverseautopatch,
             seqno, timeout, apprptuptime, total_execd_commands, max_uptime,
             current_link_count, linked_nodes, links, port, batch_no)
            VALUES
            (:node_id, :node_type, :callsign, :frequency, :tone, :affiliation, :site_name,
             :is_active, :last_seen, :latitude, :longitude, :app_version, :ip, :timezone_offset,
             :is_nnx, :total_keyups, :total_tx_time, :access_webtransceiver,
             :access_telephoneportal, :access_functionlist, :access_reverseautopatch,
             :seqno, :timeout, :apprptuptime, :total_execd_commands, :max_uptime,
             :current_link_count, :linked_nodes, :links, :port, :batch_no)
            """,
            params,
        )
        logger.info(
            "node_topology: MySQL ODS 插入完成 node_id=%s batch_no=%s linked_nodes=%s",
            detail.node_id,
            detail.batch_no,
            len(detail.linked_nodes or []),
        )


@dataclass
class NodeTopologyRepositories:
    """聚合 `node_topology` 任务所需的全部 repository。"""

    graph: NodeTopologyGraphRepository
    dim_node: NodeTopologyDimNodeRepository
    ods: NodeTopologyOdsRepository

    async def upsert_primary_graph_node(self, bundle: CanonicalNodeBundle) -> None:
        await self.graph.upsert_node(GraphMapper.map_node(bundle.primary_node))

    async def upsert_linked_graph_nodes(self, bundle: CanonicalNodeBundle) -> None:
        for linked_node in bundle.linked_nodes:
            await self.graph.upsert_node(GraphMapper.map_node(linked_node), preserve_uptime=True)

    async def upsert_topology(self, bundle: CanonicalNodeBundle) -> None:
        connection_records = GraphMapper.map_connections(bundle.connections)
        if connection_records:
            await self.graph.upsert_topology(bundle.primary_node.node_id, connection_records)

    async def refresh_linked_graph_nodes(self, bundle: CanonicalNodeBundle) -> None:
        for linked_node in bundle.linked_nodes:
            await self.graph.upsert_node(
                GraphMapper.map_node(linked_node),
                preserve_counters=True,
                preserve_uptime=True,
            )

    async def upsert_dim_nodes(self, bundle: CanonicalNodeBundle) -> None:
        await self.dim_node.update_node(DimNodeMapper.map_node(bundle.primary_node))
        for linked_node in bundle.linked_nodes:
            await self.dim_node.update_node(
                DimNodeMapper.map_node(linked_node),
                update_current_link_count=False,
            )

    async def write_ods_snapshot(self, bundle: CanonicalNodeBundle) -> None:
        await self.ods.insert_detail(OdsMapper.map_bundle(bundle))

    async def delete_offline_node(self, node_id: str, batch_no: str | None) -> bool:
        return await self.graph.delete_node_by_unique_id(f"{node_id}_{batch_no}")
