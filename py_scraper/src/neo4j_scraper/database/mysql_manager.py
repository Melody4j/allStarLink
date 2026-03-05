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
                    'update_time': datetime.now(),
                    'current_link_count': node.connections
                })

                logger.debug(f"节点 {node.node_id} 数据已更新到MySQL")
        except Exception as e:
            logger.error(f"更新节点 {node.node_id} 到MySQL失败: {e}")
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

                logger.info(f"批量更新 {len(valid_nodes)} 个节点到MySQL")
        except Exception as e:
            logger.error(f"批量更新节点到MySQL失败: {e}")
            raise
