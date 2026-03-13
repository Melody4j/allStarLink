"""
MySQL数据库管理器

负责与MySQL数据库的交互，包括：
1. 连接管理
2. 节点数据的插入和更新
3. 批量操作
"""

import json
import logging
from typing import List, Optional, Union
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from .base import BaseDatabaseManager
from ..models.node import Node
from ..models.ods_node_detail import OdsNodeDetail
from ..repositories.records import DimNodeRecord, OdsNodeDetailRecord

logger = logging.getLogger(__name__)


class RelationalStorageManager(BaseDatabaseManager):
    """关系型数据库管理器

    职责：
    - 管理数据库连接池
    - 执行节点的UPSERT操作
    - 批量更新节点数据
    """

    def __init__(self, host: str, user: str, password: str, 
                 database: str, charset: str) -> None:
        """初始化MySQL连接配置

        Args:
            host: 数据库主机地址
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
            charset: 字符集
        """
        self.host: str = host
        self.user: str = user
        self.password: str = password
        self.database: str = database
        self.charset: str = charset
        self.engine: Optional[create_engine] = None

    async def connect(self) -> None:
        """建立MySQL连接

        使用连接池管理数据库连接，配置参数：
        - pool_pre_ping: 自动检测连接有效性
        - pool_recycle: 连接回收时间（1小时）
        - pool_size: 连接池大小
        - max_overflow: 最大溢出连接数
        """
        try:
            db_url = (f"mysql+pymysql://{self.user}:{self.password}@"
                     f"{self.host}/{self.database}?charset={self.charset}")

            self.engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=5,
                max_overflow=10,
                poolclass=QueuePool
            )

            logger.info(f"已连接到MySQL数据库: {self.host}/{self.database}")
        except Exception as e:
            logger.error(f"连接MySQL失败: {e}")
            raise

    async def close(self) -> None:
        """关闭MySQL连接

        释放所有连接池中的连接
        """
        if self.engine:
            self.engine.dispose()
            logger.info("MySQL连接已关闭")

    async def initialize(self) -> None:
        """初始化MySQL表结构

        假设表结构已存在，此处仅作占位
        实际应用中可以添加表结构检查和创建逻辑
        """
        logger.info("MySQL初始化完成（表结构已存在）")

    async def execute_query(self, query: str) -> Optional[List[dict]]:
        """执行查询语句

        Args:
            query: SQL查询语句

        Returns:
            查询结果列表；对于无结果集的 DML 语句返回空列表；
            真正执行失败时返回 None。
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                # UPDATE/INSERT/DELETE 这类语句没有结果集，不能再 fetchall。
                # 这里统一返回空列表，避免把“执行成功但无返回行”误记成错误。
                if not result.returns_rows:
                    return []

                # SELECT 语句才会走到这里，并被转换为字典列表。
                columns = result.keys()
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            return None

    async def updateSingleNode(
        self,
        node: Union[Node, DimNodeRecord],
        update_current_link_count: bool = True,
    ) -> None:
        """更新单个节点到MySQL

        使用UPDATE语法更新指定字段：
        - 只更新指定的字段列表
        - 节点必须已存在

        Args:
            node: 要更新的节点对象
        """
        if isinstance(node, DimNodeRecord):
            if not node.validate():
                logger.warning(f"维表record验证失败，跳过更新: {node.node_id}")
                return
            params = {
                'node_id': node.node_id,
                'node_type': node.node_type,
                'callsign': node.callsign,
                'frequency': '',
                'tone': str(node.tone) if node.tone else None,
                'owner': node.owner if node.owner else '',
                'affiliation': node.affiliation if node.affiliation else '',
                'site_name': node.site_name if node.site_name else '',
                'features': ','.join(node.features) if node.features else None,
                'affiliation_type': node.affiliation_type if node.affiliation_type else 'Personal',
                'country': node.country if node.country else 'Unknown',
                'continent': node.continent if node.continent else 'Unknown',
                'is_active': 1 if node.active else 0,
                'last_seen': node.last_seen,
                'node_rank': node.node_rank if node.node_rank else 'Normal',
                'mobility_type': node.mobility_type if node.mobility_type else 'Fixed',
                'first_seen_at': node.first_seen_at if node.first_seen_at else node.last_seen,
                'update_time': datetime.now(),
                'latitude': node.lat,
                'longitude': node.lon,
                'location_desc': node.location_desc,
                'is_mobile': 1 if node.is_mobile else 0,
                'app_version': node.app_version if node.app_version else '',
                'is_bridge': 1 if node.is_bridge else 0,
                'access_webtransceiver': 1 if node.access_webtransceiver else 0,
                'ip_address': node.ip_address if node.ip_address else '',
                'timezone_offset': node.timezone_offset,
                'is_nnx': 1 if node.is_nnx else 0,
                'hardware_type': node.hardware_type,
                'total_keyups': node.total_keyups,
                'history_total_keyups': node.history_total_keyups if node.history_total_keyups is not None else 0,
                'total_tx_time': node.total_tx_time,
                'history_tx_time': node.history_tx_time if node.history_tx_time is not None else 0,
                'access_telephoneportal': 1 if node.access_telephoneportal else 0,
                'access_functionlist': 1 if node.access_functionlist else 0,
                'access_reverseautopatch': 1 if node.access_reverseautopatch else 0,
                'seqno': node.seqno if node.seqno is not None else 0,
                'timeout': node.timeout if node.timeout is not None else 0,
                'apprptuptime': node.apprptuptime,
                'totalexecdcommands': node.totalexecdcommands if node.totalexecdcommands is not None else 0,
                'current_link_count': node.current_link_count
            }
            node_id = node.node_id
            node_type = node.node_type
            callsign = node.callsign
            connections = node.current_link_count
            apprptuptime = node.apprptuptime
        else:
            if not node.validate():
                logger.warning(f"节点数据验证失败，跳过更新: {node.node_id}")
                return
            params = {
                'node_id': node.node_id,
                'node_type': node.node_type,
                'callsign': node.callsign,
                'frequency': '',
                'tone': str(node.tone) if node.tone else None,
                'owner': node.owner if node.owner else '',
                'affiliation': node.affiliation if node.affiliation else '',
                'site_name': node.site_name if node.site_name else '',
                'features': ','.join(node.features) if node.features else None,
                'affiliation_type': node.affiliation_type if node.affiliation_type else 'Personal',
                'country': node.country if node.country else 'Unknown',
                'continent': node.continent if node.continent else 'Unknown',
                'is_active': 1 if node.active else 0,
                'last_seen': node.last_seen,
                'node_rank': node.node_rank if node.node_rank else 'Normal',
                'mobility_type': node.mobility_type if node.mobility_type else 'Fixed',
                'first_seen_at': node.first_seen_at if node.first_seen_at else node.last_seen,
                'update_time': datetime.now(),
                'latitude': node.lat,
                'longitude': node.lon,
                'location_desc': node.location_desc,
                'is_mobile': 1 if node.is_mobile else 0,
                'app_version': node.app_version if node.app_version else '',
                'is_bridge': 1 if node.is_bridge else 0,
                'access_webtransceiver': 1 if node.access_webtransceiver else 0,
                'ip_address': node.ip_address if node.ip_address else '',
                'timezone_offset': node.timezone_offset,
                'is_nnx': 1 if node.is_nnx else 0,
                'hardware_type': node.hardware_type,
                'total_keyups': node.total_keyups,
                'history_total_keyups': node.history_total_keyups if node.history_total_keyups is not None else 0,
                'total_tx_time': node.total_tx_time,
                'history_tx_time': node.history_tx_time if node.history_tx_time is not None else 0,
                'access_telephoneportal': 1 if node.access_telephoneportal else 0,
                'access_functionlist': 1 if node.access_functionlist else 0,
                'access_reverseautopatch': 1 if node.access_reverseautopatch else 0,
                'seqno': node.seqno if node.seqno is not None else 0,
                'timeout': node.timeout if node.timeout is not None else 0,
                'apprptuptime': node.apprptuptime,
                'totalexecdcommands': node.totalexecdcommands if node.totalexecdcommands is not None else 0,
                'current_link_count': node.connections
            }
            node_id = node.node_id
            node_type = node.node_type
            callsign = node.callsign
            connections = node.connections
            apprptuptime = node.apprptuptime

        try:
            with self.engine.connect() as conn:
                trans = conn.begin()
                try:
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
                        "node_type = :node_type"
                    ]
                    if apprptuptime is not None:
                        set_clauses.append("apprptuptime = :apprptuptime")
                    if update_current_link_count:
                        set_clauses.append("current_link_count = :current_link_count")

                    stmt = text(f"""
                    UPDATE dim_nodes SET
                    {", ".join(set_clauses)}
                    WHERE node_id = :node_id
                    """)

                    conn.execute(stmt, params)
                    trans.commit()
                    logger.info(f"MySQL数据更新: 节点 {node_id} 数据已成功更新 - 类型:{node_type}, 呼号:{callsign}, 连接数:{connections}")
                except Exception as e:
                    trans.rollback()
                    raise
        except Exception as e:
            logger.error(f"MySQL数据更新失败: 更新节点 {node_id} 异常 - {e}")
            raise

    async def batch_upsert_nodes(self, nodes: List[Node]) -> None:
        """批量插入或更新节点到MySQL

        Args:
            nodes: 要批量插入或更新的节点列表
        """
        if not nodes:
            return

        # 过滤有效节点
        valid_nodes = [node for node in nodes if node.validate()]

        if not valid_nodes:
            logger.warning("没有有效的节点数据，跳过批量更新")
            return

        try:
            now = datetime.now()

            with self.engine.connect() as conn:
                # 批量执行UPSERT
                for node in valid_nodes:
                     
                                    

                    stmt = text("""
                    INSERT INTO dim_nodes
                    (node_id, callsign, total_keyups, total_tx_time, avg_talk_length,
                     latitude, longitude, last_seen, update_time, current_link_count)
                    VALUES
                    (:node_id, :callsign, :total_keyups, :total_tx_time, :avg_talk_length,
                     :latitude, :longitude, :last_seen, :update_time, :current_link_count)
                    ON DUPLICATE KEY UPDATE
                    callsign = VALUES(callsign),
                    total_keyups = VALUES(total_keyups),
                    total_tx_time = VALUES(total_tx_time),
                    avg_talk_length = VALUES(avg_talk_length),
                    latitude = VALUES(latitude),
                    longitude = VALUES(longitude),
                    last_seen = VALUES(last_seen),
                    update_time = VALUES(update_time),
                    current_link_count = VALUES(current_link_count)
                    """)

                    conn.execute(stmt, {
                        'node_id': node.node_id,
                        'callsign': node.callsign,
                        'total_keyups': node.total_keyups,
                        'total_tx_time': node.total_tx_time,
                        'avg_talk_length': avg_talk_length,
                        'latitude': node.lat,
                        'longitude': node.lon,
                        'last_seen': node.last_seen,
                        'update_time': now,
                        'current_link_count': node.connections
                    })

                logger.info(f"MySQL数据更新: 批量更新 {len(valid_nodes)} 个节点到MySQL成功")
        except Exception as e:
            logger.error(f"MySQL数据更新失败: 批量更新节点异常 - {e}")
            raise

    async def insert_ods_node_detail(self, ods_detail: Union[OdsNodeDetail, OdsNodeDetailRecord]) -> None:
        """插入ODS节点详情到MySQL（纯插入策略，保留历史快照）

        Args:
            ods_detail: ODS节点详情对象
        """
        if isinstance(ods_detail, OdsNodeDetailRecord):
            if not ods_detail.validate():
                logger.warning(f"ODS record验证失败，跳过插入: {ods_detail.node_id}")
                return
            detail_dict = {
                'node_id': ods_detail.node_id,
                'node_type': ods_detail.node_type,
                'callsign': ods_detail.callsign,
                'frequency': ods_detail.frequency,
                'tone': ods_detail.tone,
                'affiliation': ods_detail.affiliation,
                'site_name': ods_detail.site_name,
                'is_active': 1 if ods_detail.is_active else 0 if ods_detail.is_active is not None else None,
                'last_seen': ods_detail.last_seen,
                'latitude': ods_detail.latitude,
                'longitude': ods_detail.longitude,
                'app_version': ods_detail.app_version,
                'ip': ods_detail.ip,
                'timezone_offset': ods_detail.timezone_offset,
                'is_nnx': 1 if ods_detail.is_nnx else 0 if ods_detail.is_nnx is not None else None,
                'total_keyups': ods_detail.total_keyups,
                'total_tx_time': ods_detail.total_tx_time,
                'access_webtransceiver': 1 if ods_detail.access_webtransceiver else 0 if ods_detail.access_webtransceiver is not None else None,
                'access_telephoneportal': 1 if ods_detail.access_telephoneportal else 0 if ods_detail.access_telephoneportal is not None else None,
                'access_functionlist': 1 if ods_detail.access_functionlist else 0 if ods_detail.access_functionlist is not None else None,
                'access_reverseautopatch': 1 if ods_detail.access_reverseautopatch else 0 if ods_detail.access_reverseautopatch is not None else None,
                'seqno': ods_detail.seqno,
                'timeout': ods_detail.timeout,
                'apprptuptime': ods_detail.apprptuptime,
                'total_execd_commands': ods_detail.total_execd_commands,
                'max_uptime': ods_detail.max_uptime,
                'current_link_count': ods_detail.current_link_count,
                'linked_nodes': json.dumps(ods_detail.linked_nodes) if ods_detail.linked_nodes else None,
                'links': json.dumps(ods_detail.links) if ods_detail.links is not None else None,
                'port': ods_detail.port,
                'batch_no': int(ods_detail.batch_no) if ods_detail.batch_no is not None else None
            }
            ods_node_id = ods_detail.node_id
        else:
            if not ods_detail.validate():
                logger.warning(f"ODS节点详情数据验证失败，跳过插入: {ods_detail.node_id}")
                return
            detail_dict = ods_detail.to_dict()
            ods_node_id = ods_detail.node_id

        try:
            with self.engine.connect() as conn:
                trans = conn.begin()
                try:
                    logger.debug(f"准备插入ODS节点详情，batch_no: {detail_dict.get('batch_no')}")
                    stmt = text("""
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
                    """)

                    conn.execute(stmt, detail_dict)
                    trans.commit()
                    logger.info(f"MySQL数据插入: 节点 {ods_node_id} ODS详情已成功插入（保留历史快照）")
                except Exception as e:
                    trans.rollback()
                    raise
        except Exception as e:
            logger.error(f"MySQL数据插入失败: 插入节点 {ods_node_id} ODS详情异常 - {e}")
            raise


# 兼容旧命名，后续主流程逐步改用 RelationalStorageManager。
MySQLManager = RelationalStorageManager
