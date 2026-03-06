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
            # 使用有序集合实现优先级队列
            await self.redis.zadd(self.queue_key, {str(node_id): priority})
            # 记录任务集合，用于去重
            await self.redis.sadd(self.task_set_key, str(node_id))
            logger.info(f"Redis队列操作: 节点 {node_id} 已加入优先级队列，优先级分数: {priority}（连接数）")
            return True
        except Exception as e:
            logger.error(f"Redis队列操作失败: 节点 {node_id} 入队异常 - {e}")
            return False

    async def dequeue(self) -> Optional[int]:
        """从优先级队列中取出最高优先级的节点ID

        Returns:
            Optional[int]: 节点ID，如果队列为空则返回None
        """
        try:
            # 从有序集合中取出分数最高的元素
            result = await self.redis.zpopmax(self.queue_key)
            if result:
                node_id = int(result[0][0])
                # 从任务集合中移除
                await self.redis.srem(self.task_set_key, str(node_id))
                logger.info(f"Redis队列操作: 从队列中取出节点 {node_id} 进行处理")
                return node_id
            logger.debug("Redis队列操作: 队列为空，暂无待处理节点")
            return None
        except Exception as e:
            logger.error(f"Redis队列操作失败: 出队异常 - {e}")
            return None

    async def get_size(self) -> int:
        """获取队列大小

        Returns:
            int: 队列中的任务数量
        """
        try:
            size = await self.redis.zcard(self.queue_key)
            logger.debug(f"Redis队列状态: 当前队列大小为 {size} 个任务")
            return size
        except Exception as e:
            logger.error(f"Redis队列操作失败: 获取队列大小异常 - {e}")
            return 0

    async def remove(self, node_id: int) -> bool:
        """从队列中移除指定节点

        Args:
            node_id: 要移除的节点ID

        Returns:
            bool: 是否成功移除
        """
        try:
            await self.redis.zrem(self.queue_key, str(node_id))
            await self.redis.srem(self.task_set_key, str(node_id))
            logger.info(f"Redis队列操作: 已从队列中移除节点 {node_id}")
            return True
        except Exception as e:
            logger.error(f"Redis队列操作失败: 移除节点 {node_id} 异常 - {e}")
            return False

    async def contains(self, node_id: int) -> bool:
        """检查节点是否在队列中

        Args:
            node_id: 节点ID

        Returns:
            bool: 节点是否在队列中
        """
        try:
            exists = await self.redis.sismember(self.task_set_key, str(node_id))
            logger.debug(f"Redis队列操作: 检查节点 {node_id} 是否在队列中 - {exists}")
            return exists
        except Exception as e:
            logger.error(f"Redis队列操作失败: 检查节点 {node_id} 是否存在异常 - {e}")
            return False

    async def clear(self) -> None:
        """清空队列和任务集合

        用于系统启动时清理旧数据
        """
        try:
            await self.redis.delete(self.queue_key)
            await self.redis.delete(self.task_set_key)
            logger.info("Redis队列操作: 已清空Redis优先级队列和任务集合")
        except Exception as e:
            logger.error(f"Redis队列操作失败: 清空队列异常 - {e}")
