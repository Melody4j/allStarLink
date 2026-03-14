"""Configuration management."""

import os
from dataclasses import dataclass


@dataclass
class Neo4jConfig:
    uri: str
    user: str
    password: str


@dataclass
class RedisConfig:
    host: str
    port: int
    password: str
    db: int


@dataclass
class MySQLConfig:
    host: str
    user: str
    password: str
    database: str
    charset: str


@dataclass
class NetworkRuntimeConfig:
    """跨 source 共享的网络访问控制参数。"""

    rate_limit: int
    rate_limit_window: int
    max_retries: int
    retry_backoff: int
    cooldown_429: int
    request_delay_min: float
    request_delay_max: float


@dataclass
class AllStarLinkSourceConfig:
    """AllStarLink 数据源接口配置。"""

    node_details_url: str
    node_online_list_url: str


@dataclass
class PriorityConfig:
    high: int
    normal: int
    low: int


@dataclass
class TaskScheduleConfig:
    """单个任务的启停与调度参数。"""

    enabled: bool
    mode: str
    interval_seconds: int | None = None
    timeout_seconds: float | None = None
    cooldown_seconds: float = 5.0
    max_consecutive_failures: int = 3


@dataclass
class AllStarLinkTasksConfig:
    """AllStarLink 下各任务的配置集合。"""

    node_topology: TaskScheduleConfig
    node_list_snapshot: TaskScheduleConfig


@dataclass
class SourceRuntimeConfig:
    """source 级运行配置。"""

    enabled: bool
    max_parallel_jobs: int


@dataclass
class AllStarLinkRuntimeConfig(SourceRuntimeConfig):
    """AllStarLink 模块配置。"""

    source: AllStarLinkSourceConfig
    tasks: AllStarLinkTasksConfig


@dataclass
class SchedulerConfig:
    """统一调度器配置。"""

    shutdown_timeout_seconds: int
    max_total_jobs: int


@dataclass
class Settings:
    neo4j: Neo4jConfig
    redis: RedisConfig
    mysql: MySQLConfig
    network: NetworkRuntimeConfig
    priority: PriorityConfig
    scheduler: SchedulerConfig
    allstarlink: AllStarLinkRuntimeConfig
    source_name: str

    @classmethod
    def load(cls) -> "Settings":
        """统一加载运行配置。"""

        return cls(
            neo4j=Neo4jConfig(
                uri="bolt://121.41.230.15:7687",
                user="neo4j",
                password="0595",
            ),
            redis=RedisConfig(
                host="121.41.230.15",
                port=6379,
                password="0595",
                db=0,
            ),
            mysql=MySQLConfig(
                host="121.41.230.15",
                user="root",
                password="0595",
                database="allStarLink",
                charset="utf8mb4",
            ),
            network=NetworkRuntimeConfig(
                rate_limit=int(os.getenv("RATE_LIMIT", "10")),
                rate_limit_window=60,
                max_retries=3,
                retry_backoff=2,
                cooldown_429=int(os.getenv("COOLDOWN_429", "60")),
                request_delay_min=float(os.getenv("REQUEST_DELAY_MIN", "4.0")),
                request_delay_max=float(os.getenv("REQUEST_DELAY_MAX", "6.0")),
            ),
            priority=PriorityConfig(
                high=100,
                normal=50,
                low=10,
            ),
            scheduler=SchedulerConfig(
                shutdown_timeout_seconds=int(os.getenv("SCHEDULER_SHUTDOWN_TIMEOUT_SECONDS", "30")),
                max_total_jobs=int(os.getenv("SCHEDULER_MAX_TOTAL_JOBS", "10")),
            ),
            allstarlink=AllStarLinkRuntimeConfig(
                enabled=_read_bool_env("ALLSTARLINK_ENABLED", True),
                max_parallel_jobs=int(os.getenv("ALLSTARLINK_MAX_PARALLEL_JOBS", "2")),
                source=AllStarLinkSourceConfig(
                    node_details_url=os.getenv(
                        "ALLSTARLINK_NODE_DETAILS_URL",
                        "https://stats.allstarlink.org/api/stats",
                    ),
                    node_online_list_url=os.getenv(
                        "ALLSTARLINK_NODE_ONLINE_LIST_URL",
                        "http://stats.allstarlink.org/api/stats/nodeList",
                    ),
                ),
                tasks=AllStarLinkTasksConfig(
                    node_topology=TaskScheduleConfig(
                        enabled=_read_bool_env("ALLSTARLINK_NODE_TOPOLOGY_ENABLED", True),
                        mode=os.getenv("ALLSTARLINK_NODE_TOPOLOGY_MODE", "continuous").strip().lower()
                        or "continuous",
                        interval_seconds=None,
                        timeout_seconds=float(
                            os.getenv("ALLSTARLINK_NODE_TOPOLOGY_TIMEOUT_SECONDS", "0")
                        )
                        or None,
                        cooldown_seconds=float(
                            os.getenv("ALLSTARLINK_NODE_TOPOLOGY_COOLDOWN_SECONDS", "5")
                        ),
                        max_consecutive_failures=int(
                            os.getenv("ALLSTARLINK_NODE_TOPOLOGY_MAX_CONSECUTIVE_FAILURES", "3")
                        ),
                    ),
                    node_list_snapshot=TaskScheduleConfig(
                        enabled=_read_bool_env("ALLSTARLINK_NODE_LIST_SNAPSHOT_ENABLED", True),
                        mode=os.getenv("ALLSTARLINK_NODE_LIST_SNAPSHOT_MODE", "interval").strip().lower()
                        or "interval",
                        interval_seconds=int(
                            os.getenv("ALLSTARLINK_NODE_LIST_SNAPSHOT_INTERVAL_SECONDS", "3600")
                        ),
                        timeout_seconds=float(
                            os.getenv("ALLSTARLINK_NODE_LIST_SNAPSHOT_TIMEOUT_SECONDS", "0")
                        )
                        or None,
                        cooldown_seconds=float(
                            os.getenv("ALLSTARLINK_NODE_LIST_SNAPSHOT_COOLDOWN_SECONDS", "5")
                        ),
                        max_consecutive_failures=int(
                            os.getenv("ALLSTARLINK_NODE_LIST_SNAPSHOT_MAX_CONSECUTIVE_FAILURES", "3")
                        ),
                    ),
                ),
            ),
            source_name=os.getenv("SOURCE_NAME", "allstarlink").strip().lower() or "allstarlink",
        )


def _read_bool_env(name: str, default: bool) -> bool:
    """把常见的环境变量开关值统一解析为 bool。"""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
