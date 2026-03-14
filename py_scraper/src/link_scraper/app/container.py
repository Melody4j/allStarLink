"""
Infrastructure container for building and closing the application context.
"""

import redis.asyncio as redis

from ..config.settings import Settings
from ..database.mysql_manager import RelationalStorageManager
from ..database.neo4j_manager import GraphStorageManager
from ..task_queue.priority_queue import RedisPriorityQueue
from ..utils.batch_manager import BatchManager
from ..utils.rate_limiter import RateLimiter
from .context import AppContext


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def build_context(self) -> AppContext:
        # container 层负责固定基础设施的实例化顺序，
        # 业务任务不再直接关心 Redis / MySQL / Neo4j 如何创建。
        redis_client = redis.Redis(
            host=self.settings.redis.host,
            port=self.settings.redis.port,
            password=self.settings.redis.password,
            db=self.settings.redis.db,
            decode_responses=True,
        )

        graph_storage_manager = GraphStorageManager(
            uri=self.settings.neo4j.uri,
            user=self.settings.neo4j.user,
            password=self.settings.neo4j.password,
        )
        await graph_storage_manager.connect()
        await graph_storage_manager.initialize()

        relational_storage_manager = RelationalStorageManager(
            host=self.settings.mysql.host,
            user=self.settings.mysql.user,
            password=self.settings.mysql.password,
            database=self.settings.mysql.database,
            charset=self.settings.mysql.charset,
        )
        await relational_storage_manager.connect()
        await relational_storage_manager.initialize()

        priority_queue = RedisPriorityQueue(redis_client, self.settings.source_name)
        rate_limiter = RateLimiter(
            max_requests=self.settings.network.rate_limit,
            time_window=self.settings.network.rate_limit_window,
        )
        # batch_manager 依赖 Redis，因此放在 Redis client 初始化之后构建。
        batch_manager = BatchManager(redis_client, self.settings.source_name)

        return AppContext(
            settings=self.settings,
            redis_client=redis_client,
            relational_storage_manager=relational_storage_manager,
            graph_storage_manager=graph_storage_manager,
            priority_queue=priority_queue,
            rate_limiter=rate_limiter,
            batch_manager=batch_manager,
        )

    async def close_context(self, context: AppContext) -> None:
        # 关闭顺序与构建顺序相反，避免任务退出时引用已关闭的底层连接。
        await context.redis_client.close()
        await context.graph_storage_manager.close()
        await context.relational_storage_manager.close()
