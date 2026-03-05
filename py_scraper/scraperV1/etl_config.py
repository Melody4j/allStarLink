#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllStarLink ETL配置文件
集中管理ETL流水线的所有配置参数
"""

import os
from datetime import timedelta

# =============================================================================
# 数据库配置
# =============================================================================

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '121.41.230.15'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', '0595'),
    'database': os.getenv('DB_NAME', 'allStarLink'),
    'charset': os.getenv('DB_CHARSET', 'utf8mb4'),
    'port': int(os.getenv('DB_PORT', '3306'))
}

# 数据库连接池配置
DB_POOL_CONFIG = {
    'pool_pre_ping': True,
    'pool_recycle': 3600,  # 1小时重新连接
    'pool_size': 10,       # 连接池大小
    'max_overflow': 20,    # 最大溢出连接数
    'echo': False          # 是否输出SQL日志
}

# =============================================================================
# API配置
# =============================================================================

API_CONFIG = {
    'node_list_url': "https://www.allstarlink.org/nodelist/nodelist-server.php",
    'map_data_url': "https://stats.allstarlink.org/api/stats/mapData",
    'timeout': 30,         # 请求超时时间（秒）
    'retry_times': 3,      # 重试次数
    'retry_delay': 5       # 重试间隔（秒）
}

# =============================================================================
# ETL处理配置
# =============================================================================

ETL_CONFIG = {
    # 批处理配置
    'batch_size': 1000,              # 数据库批量操作大小
    'ods_chunk_size': 1000,          # ODS层分块写入大小
    'dim_chunk_size': 500,           # DIM层分块写入大小
    'dwd_chunk_size': 2000,          # DWD层分块写入大小

    # 事件检测配置
    'geo_move_threshold': 0.005,     # 地理位移阈值（度）约500米
    'coordinate_precision': 6,        # 坐标精度（小数位）

    # 数据质量配置
    'max_frequency': 30000.0,        # 最大有效频率（MHz）
    'min_frequency': 0.1,            # 最小有效频率（MHz）
    'invalid_coordinates': [(0.0, 0.0)],  # 无效坐标列表

    # 并发控制
    'max_workers': 4,                # 最大工作线程数
    'enable_parallel': True,         # 是否启用并行处理

    # 内存管理
    'max_memory_usage': '2GB',       # 最大内存使用量
    'enable_memory_monitor': True,   # 是否启用内存监控
    'memory_cleanup_threshold': 0.8  # 内存清理阈值
}

# =============================================================================
# 地理信息配置
# =============================================================================

GEO_CONFIG = {
    # 地理编码设置
    'enable_precise_geocoding': False,  # 是否启用精确地理编码（需要geopy）
    'geocoding_cache_size': 10000,      # 地理编码缓存大小
    'geocoding_timeout': 5,             # 地理编码超时时间

    # 区域边界配置（用于简化地理判断）
    'region_boundaries': {
        'north_america': {'lat': (15, 85), 'lon': (-180, -50)},
        'south_america': {'lat': (-56, 15), 'lon': (-82, -34)},
        'europe': {'lat': (35, 72), 'lon': (-10, 70)},
        'asia': {'lat': (-11, 80), 'lon': (25, 180)},
        'africa': {'lat': (-35, 38), 'lon': (-18, 52)},
        'oceania': {'lat': (-48, -9), 'lon': (110, 180)},
        'antarctica': {'lat': (-90, -60), 'lon': (-180, 180)}
    },

    # 国家识别配置
    'country_boundaries': {
        'united_states': {'lat': (24, 49), 'lon': (-125, -66)},
        'canada': {'lat': (41, 85), 'lon': (-141, -52)},
        'china': {'lat': (18, 54), 'lon': (73, 135)},
        'russia': {'lat': (41, 82), 'lon': (19, 180)},
        'australia': {'lat': (-44, -9), 'lon': (113, 154)},
        'brazil': {'lat': (-35, 5), 'lon': (-74, -34)}
    }
}

# =============================================================================
# 数据分类配置
# =============================================================================

CLASSIFICATION_CONFIG = {
    # 组织类型关键词
    'organization_keywords': [
        'club', 'arc', 'network', 'system', 'link', 'org', 'group', 'hub',
        'association', 'society', 'council', 'federation', 'alliance',
        'emergency', 'repeater', 'foundation', 'institute', 'center'
    ],

    # 域名后缀匹配
    'organization_domains': ['.org', '.net', '.com', '.edu', '.gov', '.mil'],

    # 排除的个人标识符
    'personal_indicators': ['personal', 'private', 'individual', 'home'],

    # 频率范围配置
    'frequency_bands': {
        'hf': (1.8, 30),          # 高频
        'vhf': (30, 300),         # 甚高频
        'uhf': (300, 3000),       # 特高频
        'microwave': (3000, 30000) # 微波
    }
}

# =============================================================================
# 日志配置
# =============================================================================

LOGGING_CONFIG = {
    'level': 'INFO',                  # 日志级别
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'log_file': 'etl_process.log',   # 日志文件名
    'max_file_size': 10485760,       # 日志文件最大大小（10MB）
    'backup_count': 5,               # 日志文件备份数量
    'enable_console': True,          # 是否输出到控制台
    'enable_file': True              # 是否输出到文件
}

# =============================================================================
# 监控和告警配置
# =============================================================================

MONITORING_CONFIG = {
    # 性能监控
    'enable_performance_monitor': True,  # 启用性能监控
    'performance_log_interval': 300,     # 性能日志间隔（秒）

    # 数据质量监控
    'data_quality_checks': {
        'min_node_count': 100,           # 最小节点数量
        'max_invalid_ratio': 0.1,        # 最大无效数据比例
        'min_online_ratio': 0.05         # 最小在线节点比例
    },

    # 告警配置
    'alert_config': {
        'enable_email_alert': False,     # 启用邮件告警
        'email_smtp_server': 'smtp.gmail.com',
        'email_smtp_port': 587,
        'email_from': '',
        'email_to': [],
        'alert_threshold': {
            'error_count': 10,           # 错误数量阈值
            'processing_time': 1800      # 处理时间阈值（秒）
        }
    }
}

# =============================================================================
# 调度配置
# =============================================================================

SCHEDULE_CONFIG = {
    'default_interval': 60,           # 默认执行间隔（分钟）
    'peak_hours_interval': 30,        # 高峰期执行间隔（分钟）
    'off_peak_hours_interval': 120,   # 非高峰期执行间隔（分钟）
    'peak_hours': [(9, 11), (14, 16), (19, 21)],  # 高峰期时间段
    'maintenance_window': (2, 4),     # 维护时间窗口（不执行ETL）
    'max_execution_time': 3600,       # 最大执行时间（秒）
    'enable_smart_scheduling': True   # 启用智能调度
}

# =============================================================================
# 开发和测试配置
# =============================================================================

DEV_CONFIG = {
    'debug_mode': False,              # 调试模式
    'test_mode': False,               # 测试模式
    'sample_size': 1000,              # 测试模式下的样本大小
    'enable_sql_debug': False,        # 启用SQL调试
    'enable_data_validation': True,   # 启用数据验证
    'dry_run': False                  # 干运行模式（不实际写入数据库）
}

# =============================================================================
# 动态配置函数
# =============================================================================

def get_database_url():
    """获取数据库连接URL"""
    return (f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
            f"?charset={DB_CONFIG['charset']}")

def get_batch_id_format():
    """获取批次ID格式"""
    return '%Y%m%d%H%M'

def is_peak_hour():
    """判断是否为高峰期"""
    from datetime import datetime
    current_hour = datetime.now().hour
    for start, end in SCHEDULE_CONFIG['peak_hours']:
        if start <= current_hour < end:
            return True
    return False

def get_dynamic_interval():
    """获取动态执行间隔"""
    if is_peak_hour():
        return SCHEDULE_CONFIG['peak_hours_interval']
    else:
        return SCHEDULE_CONFIG['off_peak_hours_interval']

def is_maintenance_window():
    """判断是否在维护时间窗口"""
    from datetime import datetime
    current_hour = datetime.now().hour
    start, end = SCHEDULE_CONFIG['maintenance_window']
    return start <= current_hour < end

# =============================================================================
# 配置验证函数
# =============================================================================

def validate_config():
    """验证配置参数的合法性"""
    errors = []

    # 验证数据库配置
    if not all([DB_CONFIG['host'], DB_CONFIG['user'], DB_CONFIG['database']]):
        errors.append("数据库配置不完整")

    # 验证API配置
    if ETL_CONFIG['batch_size'] <= 0:
        errors.append("批处理大小必须大于0")

    if ETL_CONFIG['geo_move_threshold'] <= 0:
        errors.append("地理位移阈值必须大于0")

    # 验证日志配置
    if LOGGING_CONFIG['level'] not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        errors.append("日志级别配置错误")

    return errors

def print_config_summary():
    """打印配置摘要"""
    print("=== AllStarLink ETL 配置摘要 ===")
    print(f"数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"批处理大小: {ETL_CONFIG['batch_size']}")
    print(f"地理位移阈值: {ETL_CONFIG['geo_move_threshold']}°")
    print(f"日志级别: {LOGGING_CONFIG['level']}")
    print(f"调试模式: {'开启' if DEV_CONFIG['debug_mode'] else '关闭'}")

    errors = validate_config()
    if errors:
        print("\n⚠️  配置警告:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✓ 配置验证通过")

if __name__ == "__main__":
    print_config_summary()