"""批次号管理器。"""

import logging
from datetime import datetime
from typing import Optional

import redis.asyncio as redis

from ..config.constants import BATCH_NO_SUFFIX

logger = logging.getLogger(__name__)


class BatchManager:
    """管理某个 source 的批次号状态。"""

    def __init__(self, redis_client: redis.Redis, source_name: str):
        self.redis_client = redis_client
        self.source_name = (source_name or "default").strip().lower()
        self.batch_key = f"{self.source_name}:{BATCH_NO_SUFFIX}"

    async def get_current_batch_no(self) -> Optional[str]:
        try:
            return await self.redis_client.get(self.batch_key)
        except Exception as exc:
            logger.error("从 Redis 获取批次号失败: %s", exc)
            return None

    async def generate_new_batch_no(self) -> Optional[str]:
        try:
            current_batch_no = await self.get_current_batch_no()
            if not current_batch_no:
                return None

            date_part = current_batch_no[:10]
            sequence_part = current_batch_no[10:]
            now = datetime.now()
            new_date_part = now.strftime("%Y%m%d%H")
            new_sequence_part = f"{int(sequence_part) + 1:06d}"
            new_batch_no = new_date_part + new_sequence_part

            await self.redis_client.set(self.batch_key, new_batch_no)
            return new_batch_no
        except Exception as exc:
            logger.error("生成新批次号失败: %s", exc)
            raise

    async def set_batch_no(self, batch_no: str) -> None:
        try:
            await self.redis_client.set(self.batch_key, batch_no)
        except Exception as exc:
            logger.error("设置批次号失败: %s", exc)
            raise

    async def get_latest_batch_no_from_mysql(self, mysql_manager) -> Optional[str]:
        try:
            result = await mysql_manager.execute_query(
                """
                SELECT batch_no
                FROM ods_nodes_details
                WHERE batch_no IS NOT NULL
                ORDER BY create_time DESC
                LIMIT 5
                """
            )
            if result:
                latest_batch_no = result[0]["batch_no"]
                await self.set_batch_no(latest_batch_no)
                return latest_batch_no
            return None
        except Exception as exc:
            logger.error("从 MySQL 获取批次号失败: %s", exc)
            return None

    async def initialize_batch_no(self, mysql_manager) -> str:
        batch_no = await self.get_current_batch_no()
        if batch_no:
            return batch_no

        batch_no = await self.get_latest_batch_no_from_mysql(mysql_manager)
        if batch_no:
            return batch_no

        initial_batch_no = datetime.now().strftime("%Y%m%d%H") + "000001"
        await self.set_batch_no(initial_batch_no)
        return initial_batch_no

    async def get_or_create_batch_no(self, mysql_manager) -> str:
        new_batch_no = await self.generate_new_batch_no()
        if new_batch_no:
            return new_batch_no
        return await self.initialize_batch_no(mysql_manager)

    @staticmethod
    def parse_batch_no(batch_no: str) -> tuple[str, str]:
        if len(batch_no) != 16:
            raise ValueError(f"批次号格式错误: {batch_no}")
        return batch_no[:10], batch_no[10:]
