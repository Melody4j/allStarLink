"""Redis 优先级队列。"""

import logging
from typing import List, Optional

import redis.asyncio as redis

from ..config.constants import TASK_QUEUE_SUFFIX, TASK_SET_SUFFIX

logger = logging.getLogger(__name__)


class RedisPriorityQueue:
    """基于 Redis 的优先级队列。

    队列键按 `source_name` 隔离，避免多个数据源共用同一组 Redis 状态。
    """

    def __init__(self, redis_client: redis.Redis, source_name: str) -> None:
        self.redis = redis_client
        self.source_name = (source_name or "default").strip().lower()
        self.queue_key = f"{self.source_name}:{TASK_QUEUE_SUFFIX}"
        self.task_set_key = f"{self.source_name}:{TASK_SET_SUFFIX}"
        self._batch_lock_key = f"{self.queue_key}:batch_lock"

    async def enqueue(self, node_id: int, priority: int) -> bool:
        try:
            exists = await self.redis.sismember(self.task_set_key, str(node_id))
            if exists:
                logger.debug("节点 %s 已在队列中，跳过", node_id)
                return False

            await self.redis.zadd(self.queue_key, {str(node_id): priority})
            await self.redis.sadd(self.task_set_key, str(node_id))
            return True
        except Exception as exc:
            logger.error("入队失败: %s", exc)
            return False

    async def dequeue(self) -> Optional[int]:
        try:
            if await self.is_batch_locked():
                return None

            result = await self.redis.zpopmax(self.queue_key)
            if not result:
                return None

            node_id = int(result[0][0])
            await self.redis.srem(self.task_set_key, str(node_id))
            return node_id
        except Exception as exc:
            logger.error("出队失败: %s", exc)
            return None

    async def get_size(self) -> int:
        try:
            return await self.redis.zcard(self.queue_key)
        except Exception as exc:
            logger.error("获取队列大小失败: %s", exc)
            return 0

    async def clear(self) -> None:
        try:
            await self.redis.delete(self.queue_key)
            await self.redis.delete(self.task_set_key)
        except Exception as exc:
            logger.error("清空队列失败: %s", exc)

    async def get_all_tasks(self) -> list:
        try:
            tasks = await self.redis.zrange(self.queue_key, 0, -1, withscores=True)
            return [(int(node_id), priority) for node_id, priority in tasks]
        except Exception as exc:
            logger.error("获取所有任务失败: %s", exc)
            return []

    async def contains(self, node_id: int) -> bool:
        try:
            exists = await self.redis.sismember(self.task_set_key, str(node_id))
            return bool(exists)
        except Exception as exc:
            logger.error("检查节点是否存在失败: %s", exc)
            return False

    async def batch_enqueue(self, nodes: List[tuple]) -> int:
        if not nodes:
            return 0

        try:
            pipe = self.redis.pipeline()
            count = 0
            for node_id, priority in nodes:
                exists = await self.redis.sismember(self.task_set_key, str(node_id))
                if not exists:
                    pipe.zadd(self.queue_key, {str(node_id): priority})
                    pipe.sadd(self.task_set_key, str(node_id))
                    count += 1
            await pipe.execute()
            return count
        except Exception as exc:
            logger.error("批量入队失败: %s", exc)
            return 0

    async def acquire_batch_lock(self) -> bool:
        try:
            result = await self.redis.set(self._batch_lock_key, "locked", nx=True, ex=120)
            return bool(result)
        except Exception as exc:
            logger.error("获取批量锁失败: %s", exc)
            return False

    async def release_batch_lock(self) -> None:
        try:
            await self.redis.delete(self._batch_lock_key)
        except Exception as exc:
            logger.error("释放批量锁失败: %s", exc)

    async def is_batch_locked(self) -> bool:
        try:
            exists = await self.redis.exists(self._batch_lock_key)
            return bool(exists)
        except Exception as exc:
            logger.error("检查批量锁状态失败: %s", exc)
            return False
