"""
Redis优先级队列

负责管理基于Redis的优先级队列，实现：
1. 节点任务的入队和出队
2. 任务去重管理
3. 队列状态查询
"""

import logging
import redis.asyncio as redis
from typing import Optional
from ..config.constants import QUEUE_KEY, TASK_SET_KEY

logger = logging.getLogger(__name__)


class RedisPriorityQueue:
    """Redis优先级队列管理器

    使用Redis的有序集合（ZSET）实现优先级队列：
    - 分数越高，优先级越高
    - 使用集合（SET）实现任务去重

    职责：
    - 管理任务队列的入队和出队
    - 维护任务集合用于去重
    - 提供队列状态查询接口
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        """初始化优先级队列

        Args:
            redis_client: Redis异步客户端实例
        """
        self.redis: redis.Redis = redis_client
        self.queue_key: str = QUEUE_KEY
        self.task_set_key: str = TASK_SET_KEY

    async def enqueue(self, node_id: int, priority: int) -> bool:
        """将节点ID加入优先级队列

        Args:
            node_id: 节点ID
            priority: 优先级分数（分数越高优先级越高）

        Returns:
            bool: 是否成功入队
        """
        try:
            # 检查任务是否已存在
            exists = await self.redis.sismember(self.task_set_key, str(node_id))
            if exists:
                logger.debug(f"节点 {node_id} 已在队列中，跳过")
                return False

            # 添加到有序集合和集合
            await self.redis.zadd(self.queue_key, {str(node_id): priority})
            await self.redis.sadd(self.task_set_key, str(node_id))
            logger.debug(f"节点 {node_id} 已加入队列，优先级: {priority}")
            return True
        except Exception as e:
            logger.error(f"入队失败: {e}")
            return False

    async def dequeue(self) -> Optional[int]:
        """从优先级队列中取出优先级最高的节点ID

        Returns:
            Optional[int]: 节点ID，如果队列为空则返回None
        """
        try:
            # 从有序集合中取出分数最高的元素
            result = await self.redis.zpopmax(self.queue_key)
            if not result:
                return None

            node_id = int(result[0][0])
            # 从集合中移除
            await self.redis.srem(self.task_set_key, str(node_id))
            logger.debug(f"节点 {node_id} 已从队列中取出")
            return node_id
        except Exception as e:
            logger.error(f"出队失败: {e}")
            return None

    async def get_size(self) -> int:
        """获取队列大小

        Returns:
            int: 队列中的任务数量
        """
        try:
            return await self.redis.zcard(self.queue_key)
        except Exception as e:
            logger.error(f"获取队列大小失败: {e}")
            return 0

    async def clear(self) -> None:
        """清空队列和任务集合"""
        try:
            await self.redis.delete(self.queue_key)
            await self.redis.delete(self.task_set_key)
            logger.info("队列已清空")
        except Exception as e:
            logger.error(f"清空队列失败: {e}")

    async def get_all_tasks(self) -> list:
        """获取队列中的所有任务

        Returns:
            list: 任务列表，每个元素为(node_id, priority)元组
        """
        try:
            tasks = await self.redis.zrange(self.queue_key, 0, -1, withscores=True)
            return [(int(node_id), priority) for node_id, priority in tasks]
        except Exception as e:
            logger.error(f"获取所有任务失败: {e}")
            return []
