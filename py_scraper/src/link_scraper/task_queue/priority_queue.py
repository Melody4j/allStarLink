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
    - 支持批量操作
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        """初始化优先级队列

        Args:
            redis_client: Redis异步客户端实例
        """
        self.redis: redis.Redis = redis_client
        self.queue_key: str = QUEUE_KEY
        self.task_set_key: str = TASK_SET_KEY
        self._batch_lock_key: str = f"{QUEUE_KEY}:batch_lock"

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
            # 检查批量锁，如果批量操作正在进行，则不允许出队
            if await self.is_batch_locked():
                logger.debug("批量操作正在进行，暂时不允许从队列取数据")
                return None

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

    async def contains(self, node_id: int) -> bool:
        """检查节点是否已在队列中

        Args:
            node_id: 节点ID

        Returns:
            bool: 节点是否在队列中
        """
        try:
            exists = await self.redis.sismember(self.task_set_key, str(node_id))
            return bool(exists)
        except Exception as e:
            logger.error(f"检查节点是否存在失败: {e}")
            return False

    async def batch_enqueue(self, nodes: List[tuple]) -> int:
        """批量将节点加入优先级队列

        Args:
            nodes: 节点列表，每个元素为(node_id, priority)元组

        Returns:
            int: 成功加入队列的节点数量
        """
        if not nodes:
            return 0

        try:
            # 使用pipeline批量插入
            pipe = self.redis.pipeline()
            count = 0

            for node_id, priority in nodes:
                # 检查节点是否已在任务集合中
                exists = await self.redis.sismember(self.task_set_key, str(node_id))
                if not exists:
                    # 添加到有序集合和集合
                    pipe.zadd(self.queue_key, {str(node_id): priority})
                    pipe.sadd(self.task_set_key, str(node_id))
                    count += 1

            # 执行批量操作
            await pipe.execute()
            logger.debug(f"批量入队成功，添加了 {count} 个节点")
            return count

        except Exception as e:
            logger.error(f"批量入队失败: {e}")
            return 0

    async def acquire_batch_lock(self) -> bool:
        """获取批量操作锁

        在开始批量插入前调用，获取锁后会阻止dequeue操作
        锁会在120秒后自动过期

        Returns:
            bool: 是否成功获取锁
        """
        try:
            # 使用SET NX EX命令获取锁，120秒超时
            result = await self.redis.set(
                self._batch_lock_key,
                "locked",
                nx=True,
                ex=120
            )
            if result:
                logger.info("批量操作锁已获取，将阻止dequeue操作")
            return bool(result)
        except Exception as e:
            logger.error(f"获取批量锁失败: {e}")
            return False

    async def release_batch_lock(self) -> None:
        """释放批量操作锁

        在所有节点批量插入完成后调用，允许dequeue操作继续
        """
        try:
            await self.redis.delete(self._batch_lock_key)
            logger.info("批量操作锁已释放，允许dequeue操作")
        except Exception as e:
            logger.error(f"释放批量锁失败: {e}")

    async def _acquire_batch_lock(self) -> bool:
        """获取批量操作锁

        使用Redis的SET命令实现分布式锁，设置30秒超时

        Returns:
            bool: 是否成功获取锁
        """
        try:
            # 使用SET NX EX命令获取锁，30秒超时
            result = await self.redis.set(
                self._batch_lock_key,
                "locked",
                nx=True,
                ex=30
            )
            return bool(result)
        except Exception as e:
            logger.error(f"获取批量锁失败: {e}")
            return False

    async def _release_batch_lock(self) -> None:
        """释放批量操作锁"""
        try:
            await self.redis.delete(self._batch_lock_key)
            logger.debug("批量锁已释放")
        except Exception as e:
            logger.error(f"释放批量锁失败: {e}")

    async def is_batch_locked(self) -> bool:
        """检查批量操作锁状态

        Returns:
            bool: 批量锁是否已被获取
        """
        try:
            exists = await self.redis.exists(self._batch_lock_key)
            return bool(exists)
        except Exception as e:
            logger.error(f"检查批量锁状态失败: {e}")
            return False
