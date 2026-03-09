"""
批次管理器模块

负责管理爬取批次号(batch_no)的生成和获取
"""

import logging
from datetime import datetime
from typing import Optional
import redis.asyncio as redis

from ..config.constants import BATCH_NO_KEY

logger = logging.getLogger(__name__)


class BatchManager:
    """批次管理器

    职责：
    - 从Redis获取当前批次号
    - 生成新的批次号
    - 从MySQL获取最新批次号（Redis无数据时）
    """

    def __init__(self, redis_client: redis.Redis):
        """初始化批次管理器

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client

    async def get_current_batch_no(self) -> Optional[str]:
        """获取当前批次号

        Returns:
            当前批次号，如果不存在则返回None
        """
        try:
            batch_no = await self.redis_client.get(BATCH_NO_KEY)
            return batch_no
        except Exception as e:
            logger.error(f"从Redis获取批次号失败: {e}")
            return None

    async def generate_new_batch_no(self) -> str:
        """生成新的批次号

        逻辑：
        1. 从Redis获取当前批次号
        2. 如果存在，更新日期部分，批次序号+1
        3. 如果不存在，返回None（需要从MySQL获取）

        Returns:
            新的批次号，如果Redis无数据则返回None
        """
        try:
            current_batch_no = await self.get_current_batch_no()

            if not current_batch_no:
                return None

            # 解析当前批次号
            # 格式: yyyymmddHH + 6位序号
            date_part = current_batch_no[:10]  # yyyymmddHH
            sequence_part = current_batch_no[10:]  # 6位序号

            # 生成新的日期部分（当前时间）
            now = datetime.now()
            new_date_part = now.strftime('%Y%m%d%H')

            # 批次序号+1
            new_sequence = int(sequence_part) + 1
            new_sequence_part = f'{new_sequence:06d}'

            # 组合成新的批次号
            new_batch_no = new_date_part + new_sequence_part

            # 更新Redis中的批次号
            await self.redis_client.set(BATCH_NO_KEY, new_batch_no)

            logger.info(f"生成新批次号: {current_batch_no} -> {new_batch_no}")
            return new_batch_no

        except Exception as e:
            logger.error(f"生成新批次号失败: {e}")
            raise

    async def set_batch_no(self, batch_no: str) -> None:
        """设置批次号

        Args:
            batch_no: 批次号
        """
        try:
            await self.redis_client.set(BATCH_NO_KEY, batch_no)
            logger.info(f"设置批次号: {batch_no}")
        except Exception as e:
            logger.error(f"设置批次号失败: {e}")
            raise

    async def get_latest_batch_no_from_mysql(self, mysql_manager) -> Optional[str]:
        """从MySQL获取最新批次号

        Args:
            mysql_manager: MySQL管理器

        Returns:
            最新批次号，如果不存在则返回None
        """
        try:
            # 查询最新创建的5条数据的batch_no
            query = """
                SELECT batch_no 
                FROM ods_nodes_details 
                WHERE batch_no IS NOT NULL 
                ORDER BY create_time DESC 
                LIMIT 5
            """
            result = await mysql_manager.execute_query(query)
            
            if result and len(result) > 0:
                # 返回最新的batch_no
                latest_batch_no = result[0]['batch_no']
                logger.info(f"从MySQL获取到最新批次号: {latest_batch_no}")
                
                # 将批次号保存到Redis
                await self.set_batch_no(latest_batch_no)
                
                return latest_batch_no
            
            logger.info("MySQL中没有找到批次号记录")
            return None
            
        except Exception as e:
            logger.error(f"从MySQL获取批次号失败: {e}")
            return None

    async def initialize_batch_no(self, mysql_manager) -> str:
        """初始化批次号

        逻辑：
        1. 先从Redis获取当前批次号
        2. 如果Redis没有，从MySQL获取最新批次号
        3. 如果MySQL也没有，生成初始批次号

        Args:
            mysql_manager: MySQL管理器

        Returns:
            当前批次号
        """
        # 先从Redis获取
        batch_no = await self.get_current_batch_no()
        if batch_no:
            logger.info(f"从Redis获取到批次号: {batch_no}")
            return batch_no
        
        # Redis没有，从MySQL获取
        batch_no = await self.get_latest_batch_no_from_mysql(mysql_manager)
        if batch_no:
            logger.info(f"从MySQL获取到批次号: {batch_no}")
            return batch_no
        
        # 都没有，生成初始批次号
        now = datetime.now()
        initial_batch_no = now.strftime('%Y%m%d%H') + '000001'
        await self.set_batch_no(initial_batch_no)
        logger.info(f"生成初始批次号: {initial_batch_no}")
        return initial_batch_no

    async def get_or_create_batch_no(self, mysql_manager) -> str:
        """获取或生成新的批次号

        逻辑：
        1. 从Redis获取当前批次号
        2. 如果存在，生成新的批次号
        3. 如果不存在，初始化批次号

        Args:
            mysql_manager: MySQL管理器

        Returns:
            批次号
        """
        # 尝试生成新批次号
        new_batch_no = await self.generate_new_batch_no()
        if new_batch_no:
            return new_batch_no
        
        # Redis没有数据，初始化批次号
        return await self.initialize_batch_no(mysql_manager)

    @staticmethod
    def parse_batch_no(batch_no: str) -> tuple:
        """解析批次号

        Args:
            batch_no: 批次号

        Returns:
            (日期部分, 批次序号)
        """
        if len(batch_no) != 16:
            raise ValueError(f"批次号格式错误: {batch_no}")

        date_part = batch_no[:10]
        sequence_part = batch_no[10:]

        return date_part, sequence_part
