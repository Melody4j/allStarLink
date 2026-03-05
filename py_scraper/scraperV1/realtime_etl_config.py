#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllStarLink 准实时ETL配置文件
"""

import os
from typing import Dict, Any

# ==================== 数据库配置 ====================
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '121.41.230.15'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', '0595'),
    'database': os.getenv('MYSQL_DATABASE', 'allStarLink'),
    'charset': 'utf8mb4'
}

# ==================== API配置 ====================
API_CONFIG = {
    'node_list_url': "https://www.allstarlink.org/nodelist/nodelist-server.php",
    'map_data_url': "https://stats.allstarlink.org/api/stats/mapData",
    'request_timeout': 30,
    'retry_attempts': 3,
    'retry_delay': 5
}

# ==================== ETL配置 ====================
ETL_CONFIG = {
    # 地理位移阈值（度）
    'geo_move_threshold': 0.005,

    # 数据库连接池配置
    'db_pool_size': 5,
    'db_max_overflow': 10,
    'db_pool_recycle': 3600,

    # 批处理配置
    'batch_size': 1000,
    'max_batch_retry': 3,

    # 默认时间间隔
    'default_ods_interval_minutes': 60,
    'cycle_interval_seconds': 60,

    # 监控配置
    'stats_report_interval_cycles': 10,

    # 日志配置
    'log_level': 'INFO',
    'log_format': '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
}

# ==================== 数据库表配置 ====================
TABLE_CONFIG = {
    'ods_table': 'ods_asl_nodes_snapshot',
    'dwd_table': 'dwd_node_events_fact',
    'dim_table': 'dim_nodes'
}

# ==================== 字段映射配置 ====================
FIELD_MAPPING = {
    # 原始字段到标准字段的映射
    'api_to_standard': {
        'name': 'node_id',
        'User_ID': 'owner',
        'callsign': 'callsign',
        'node_frequency': 'frequency',
        'node_tone': 'tone',
        'Location': 'location',
        'SiteName': 'site',
        'Affiliation': 'affiliation',
        'regseconds': 'regseconds'
    },

    # 核心比较字段
    'core_columns': [
        'node_id', 'owner', 'callsign', 'frequency', 'tone',
        'location', 'site', 'affiliation', 'last_seen',
        'latitude', 'longitude', 'is_active'
    ],

    # DIM表字段
    'dim_columns': [
        'node_id', 'owner', 'callsign', 'frequency', 'tone',
        'location', 'site', 'affiliation', 'last_seen',
        'latitude', 'longitude', 'is_active', 'update_time'
    ]
}

# ==================== 事件类型配置 ====================
EVENT_TYPES = {
    'status_change': {
        'name': 'status_change',
        'attr_name': 'is_active',
        'description': '节点状态变化'
    },
    'geo_move': {
        'name': 'geo_move',
        'attr_name': 'coordinates',
        'description': '节点地理位置移动'
    }
}

def get_database_url() -> str:
    """构建数据库连接URL"""
    return (f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
            f"{DB_CONFIG['host']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}")

def get_config_summary() -> Dict[str, Any]:
    """获取配置摘要"""
    return {
        'database': {
            'host': DB_CONFIG['host'],
            'database': DB_CONFIG['database'],
            'user': DB_CONFIG['user']
        },
        'etl': {
            'geo_threshold': ETL_CONFIG['geo_move_threshold'],
            'batch_size': ETL_CONFIG['batch_size'],
            'default_ods_interval': ETL_CONFIG['default_ods_interval_minutes']
        },
        'tables': TABLE_CONFIG
    }

if __name__ == "__main__":
    # 配置文件测试
    import json
    print("Configuration Summary:")
    print(json.dumps(get_config_summary(), indent=2, ensure_ascii=False))
    print(f"\nDatabase URL: {get_database_url()}")