"""
配置管理模块
"""

import os
from dataclasses import dataclass
from typing import Dict


@dataclass
class Neo4jConfig:
    """Neo4j配置"""
    uri: str
    user: str
    password: str


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str
    port: int
    password: str
    db: int


@dataclass
class MySQLConfig:
    """MySQL配置"""
    host: str
    user: str
    password: str
    database: str
    charset: str


@dataclass
class APIConfig:
    """API配置"""
    base_url: str
    node_list_url: str
    rate_limit: int
    rate_limit_window: int
    max_retries: int
    retry_backoff: int
    cooldown_429: int
    request_delay_min: float
    request_delay_max: float


@dataclass
class PriorityConfig:
    """优先级配置"""
    high: int
    normal: int
    low: int


@dataclass
class Settings:
    """总配置类"""
    neo4j: Neo4jConfig
    redis: RedisConfig
    mysql: MySQLConfig
    api: APIConfig
    priority: PriorityConfig

    @classmethod
    def load(cls) -> 'Settings':
        """加载配置"""
        return cls(
            neo4j=Neo4jConfig(
                uri='bolt://121.41.230.15:7687',
                user='neo4j',
                password='0595'
            ),
            redis=RedisConfig(
                host='121.41.230.15',
                port=6379,
                password='0595',
                db=0
            ),
            mysql=MySQLConfig(
                host='121.41.230.15',
                user='root',
                password='0595',
                database='allStarLink',
                charset='utf8mb4'
            ),
            api=APIConfig(
                base_url='https://stats.allstarlink.org/api/stats',
                node_list_url='http://stats.allstarlink.org/api/stats/nodeList',
                rate_limit=int(os.getenv('RATE_LIMIT', '10')),
                rate_limit_window=60,
                max_retries=3,
                retry_backoff=2,
                cooldown_429=int(os.getenv('COOLDOWN_429', '60')),
                request_delay_min=float(os.getenv('REQUEST_DELAY_MIN', '4.0')),
                request_delay_max=float(os.getenv('REQUEST_DELAY_MAX', '6.0'))
            ),
            priority=PriorityConfig(
                high=100,
                normal=50,
                low=10
            )
        )
