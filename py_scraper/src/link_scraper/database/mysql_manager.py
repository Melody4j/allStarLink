"""MySQL 基础连接与执行层。"""

import logging
from typing import Any, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from .base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class RelationalStorageManager(BaseDatabaseManager):
    """只负责 MySQL 连接和基础 SQL 执行。

    这里不再承载 `allstarlink` 业务写入语义。
    具体表的更新、插入规则应下沉到各自模块 repository。
    """

    def __init__(self, host: str, user: str, password: str, database: str, charset: str) -> None:
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.engine: Optional[create_engine] = None

    async def connect(self) -> None:
        try:
            db_url = (
                f"mysql+pymysql://{self.user}:{self.password}@"
                f"{self.host}/{self.database}?charset={self.charset}"
            )
            self.engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=5,
                max_overflow=10,
                poolclass=QueuePool,
            )
            logger.info("已连接到 MySQL: %s/%s", self.host, self.database)
        except Exception as exc:
            logger.error("连接 MySQL 失败: %s", exc)
            raise

    async def close(self) -> None:
        if self.engine:
            self.engine.dispose()
            logger.info("MySQL 连接已关闭")

    async def initialize(self) -> None:
        logger.info("MySQL 初始化完成，默认假设表结构已存在")

    async def execute_query(self, query: str, params: Optional[dict[str, Any]] = None) -> Optional[List[dict]]:
        """执行查询语句并返回字典列表。"""

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                if not result.returns_rows:
                    return []

                columns = result.keys()
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as exc:
            logger.error("执行查询失败: %s", exc)
            return None

    async def execute_statement(self, query: str, params: Optional[dict[str, Any]] = None) -> None:
        """执行写语句并自动包事务。"""

        try:
            with self.engine.connect() as conn:
                trans = conn.begin()
                try:
                    conn.execute(text(query), params or {})
                    trans.commit()
                except Exception:
                    trans.rollback()
                    raise
        except Exception as exc:
            logger.error("执行写语句失败: %s", exc)
            raise
