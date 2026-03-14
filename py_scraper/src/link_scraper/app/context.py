"""
Application context for V3 composition.
"""

from dataclasses import dataclass

import redis.asyncio as redis

from ..config.settings import Settings
from ..database.mysql_manager import RelationalStorageManager
from ..database.neo4j_manager import GraphStorageManager
from ..task_queue.priority_queue import RedisPriorityQueue
from ..utils.batch_manager import BatchManager
from ..utils.rate_limiter import RateLimiter


@dataclass
class AppContext:
    """V3 运行时上下文。

    这个对象把跨任务共享的基础设施集中收口，
    让 source module / task module 通过统一入口拿依赖，
    避免再次回到 `main.py` 手工拼装所有对象的旧结构。
    """

    settings: Settings
    redis_client: redis.Redis
    relational_storage_manager: RelationalStorageManager
    graph_storage_manager: GraphStorageManager
    priority_queue: RedisPriorityQueue
    rate_limiter: RateLimiter
    batch_manager: BatchManager
