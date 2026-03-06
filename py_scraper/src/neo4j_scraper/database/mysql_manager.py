"""
MySQL数据库管理器

负责与MySQL数据库的交互，包括：
1. 连接管理
2. 节点数据的插入和更新
3. 批量操作
"""

import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from .base import BaseDatabaseManager
from ..models.node import Node

logger = logging.getLogger(__name__)


class MySQLManager(BaseDatabaseManager):
    """MySQL数据库管理器

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

    async def upsert_node(self, node: Node) -> None:
        """插入或更新单个节点到MySQL

        使用INSERT ... ON DUPLICATE KEY UPDATE语法实现UPSERT：
        - 如果节点不存在则插入
        - 如果节点已存在则更新

        Args:
            node: 要插入或更新的节点对象
        """
        if not node.validate():
            logger.warning(f"节点数据验证失败，跳过更新: {node.node_id}")
            return

        try:
            # 计算平均通话时长
            avg_talk_length = (node.total_tx_time / 
                            max(1, node.total_keyups))

            with self.engine.connect() as conn:
                stmt = text("""
                INSERT INTO dim_nodes
                (node_id, node_type, callsign, frequency, tone, owner, affiliation, site_name,
                 features, affiliation_type, country, continent, is_active, last_seen, node_rank,
                 mobility_type, first_seen_at, update_time, latitude, longitude, location_desc,
                 is_mobile, app_version, is_bridge, access_webtransceiver, ip_address,
                 timezone_offset, is_nnx, hardware_type, total_keyups, history_total_keyups,
                 total_tx_time, history_tx_time, avg_talk_length, access_telephoneportal,
                 access_functionlist, access_reverseautopatch, seqno, timeout, apprptuptime,
                 totalexecdcommands, max_uptime, current_link_count)
                VALUES
                (:node_id, :node_type, :callsign, :frequency, :tone, :owner, :affiliation, :site_name,
                 :features, :affiliation_type, :country, :continent, :is_active, :last_seen, :node_rank,
                 :mobility_type, :first_seen_at, :update_time, :latitude, :longitude, :location_desc,
                 :is_mobile, :app_version, :is_bridge, :access_webtransceiver, :ip_address,
                 :timezone_offset, :is_nnx, :hardware_type, :total_keyups, :history_total_keyups,
                 :total_tx_time, :history_tx_time, :avg_talk_length, :access_telephoneportal,
                 :access_functionlist, :access_reverseautopatch, :seqno, :timeout, :apprptuptime,
                 :totalexecdcommands, :max_uptime, :current_link_count)
                ON DUPLICATE KEY UPDATE
                node_type = VALUES(node_type),
                callsign = VALUES(callsign),
                frequency = VALUES(frequency),
                tone = VALUES(tone),
                owner = VALUES(owner),
                affiliation = VALUES(affiliation),
                site_name = VALUES(site_name),
                features = VALUES(features),
                affiliation_type = VALUES(affiliation_type),
                country = VALUES(country),
                continent = VALUES(continent),
                is_active = VALUES(is_active),
                last_seen = VALUES(last_seen),
                node_rank = VALUES(node_rank),
                mobility_type = VALUES(mobility_type),
                first_seen_at = VALUES(first_seen_at),
                update_time = VALUES(update_time),
                latitude = VALUES(latitude),
                longitude = VALUES(longitude),
                location_desc = VALUES(location_desc),
                is_mobile = VALUES(is_mobile),
                app_version = VALUES(app_version),
                is_bridge = VALUES(is_bridge),
                access_webtransceiver = VALUES(access_webtransceiver),
                ip_address = VALUES(ip_address),
                timezone_offset = VALUES(timezone_offset),
                is_nnx = VALUES(is_nnx),
                hardware_type = VALUES(hardware_type),
                total_keyups = VALUES(total_keyups),
                history_total_keyups = VALUES(history_total_keyups),
                total_tx_time = VALUES(total_tx_time),
                history_tx_time = VALUES(history_tx_time),
                avg_talk_length = VALUES(avg_talk_length),
                access_telephoneportal = VALUES(access_telephoneportal),
                access_functionlist = VALUES(access_functionlist),
                access_reverseautopatch = VALUES(access_reverseautopatch),
                seqno = VALUES(seqno),
                timeout = VALUES(timeout),
                apprptuptime = VALUES(apprptuptime),
                totalexecdcommands = VALUES(totalexecdcommands),
                max_uptime = VALUES(max_uptime),
                current_link_count = VALUES(current_link_count)
                """)

                conn.execute(stmt, {
                    'node_id': node.node_id,
                    'node_type': node.node_type,
                    'callsign': node.callsign,
                    'frequency': '',  # 从API获取
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
                    'avg_talk_length': avg_talk_length,
                    'access_telephoneportal': 1 if node.access_telephoneportal else 0,
                    'access_functionlist': 1 if node.access_functionlist else 0,
                    'access_reverseautopatch': 1 if node.access_reverseautopatch else 0,
                    'seqno': node.seqno if node.seqno is not None else 0,
                    'timeout': node.timeout if node.timeout is not None else 0,
                    'apprptuptime': node.uptime,
                    'totalexecdcommands': node.totalexecdcommands if node.totalexecdcommands is not None else 0,
                    'max_uptime': node.max_uptime if node.max_uptime is not None else 0,
                    'current_link_count': node.connections
                })

                logger.info(f"MySQL数据更新: 节点 {node.node_id} 数据已成功更新 - 类型:{node.node_type}, 呼号:{node.callsign}, 连接数:{node.connections}")
        except Exception as e:
            logger.error(f"MySQL数据更新失败: 更新节点 {node.node_id} 异常 - {e}")
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
                    avg_talk_length = (node.total_tx_time / 
                                    max(1, node.total_keyups))

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
