
"""
辅助函数

提供通用的辅助函数：
1. 解析连接模式字符串
2. 验证坐标有效性
3. 清理字符串
"""

import re
from typing import Dict, Optional
from ..config.constants import CONNECTION_PREFIXES, CONNECTION_DIRECTION_UNKNOWN


def parse_connection_modes(connection_modes: str) -> Dict[str, str]:
    """解析连接模式字符串

    将连接模式字符串（如"T62340,T68245"）解析为节点ID到连接方向的映射

    Args:
        connection_modes: 连接模式字符串

    Returns:
        Dict[str, str]: 节点ID到连接方向的映射
    """
    connection_dict = {}

    if not connection_modes:
        return connection_dict

    for item in connection_modes.split(','):
        if not item:
            continue

        # 提取前缀和节点ID
        prefix = item[0] if item else ''
        node_id = item[1:] if len(item) > 1 else ''

        if node_id.isdigit():
            connection_dict[node_id] = CONNECTION_PREFIXES.get(prefix, CONNECTION_DIRECTION_UNKNOWN)

    return connection_dict


def validate_coordinates(lat: float, lon: float) -> bool:
    """验证坐标有效性

    Args:
        lat: 纬度
        lon: 经度

    Returns:
        bool: 坐标是否有效
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def sanitize_string(value: Optional[str]) -> str:
    """清理字符串

    去除字符串中的特殊字符和多余空格

    Args:
        value: 要清理的字符串

    Returns:
        str: 清理后的字符串
    """
    if not value:
        return ''

    # 去除前后空格
    value = value.strip()

    # 移除控制字符（不包括null字节）
    value = re.sub(r'[\x01-\x1F\x7F-\x9F]', '', value)

    return value
