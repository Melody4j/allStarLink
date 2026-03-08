"""
常量定义模块
"""

from typing import Dict, List

# 队列键名
QUEUE_KEY: str = 'asl_task_queue'
TASK_SET_KEY: str = 'asl_task_set'

# 连接模式前缀
CONNECTION_PREFIXES: Dict[str, str] = {
    'T': 'Transceive',
    'R': 'RX Only',
    'L': 'Local',
    'P': 'Permanent'
}

# 节点类型关键词
NODE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    'Hub': ['HUB', 'SYSTEM', 'NETWORK'],
    'Repeater': []  # 通过频率模式识别
}

# 硬件类型关键词
HARDWARE_KEYWORDS: Dict[str, List[str]] = {
    'Personal Station': ['SHACK', 'HOME', 'RESIDENCE'],
    'Infrastructure': ['HUB', 'NETWORK', 'DATA CENTER', 'RACK'],
    'Embedded Node': ['PI', 'ORANGEPI', 'CLEARNODE', 'ARM', 'RASPBERRY PI']
}

# 默认值
DEFAULT_LATITUDE: float = 0.0
DEFAULT_LONGITUDE: float = 0.0
DEFAULT_TOTAL_KEYUPS: int = 0
DEFAULT_TOTAL_TX_TIME: int = 0
DEFAULT_CONNECTIONS: int = 0

# 节点类型（平台类型）
NODE_TYPE_ALLSTARLINK: str = 'allstarlink'
NODE_TYPE_OTHERS: str = 'others'

# 节点等级（原节点类型定义）
NODE_RANK_UNKNOWN: str = 'Unknown'
NODE_RANK_HUB: str = 'Hub'
NODE_RANK_REPEATER: str = 'Repeater'

# 硬件类型
HARDWARE_TYPE_UNKNOWN: str = 'Unknown'
HARDWARE_TYPE_PERSONAL: str = 'Personal Station'
HARDWARE_TYPE_INFRASTRUCTURE: str = 'Infrastructure'
HARDWARE_TYPE_EMBEDDED: str = 'Embedded Node'

# 连接状态
CONNECTION_STATUS_ACTIVE: str = 'Active'
CONNECTION_STATUS_INACTIVE: str = 'Inactive'

# 连接方向
CONNECTION_DIRECTION_UNKNOWN: str = 'Unknown'



# 失效关系清理阈值（分钟）
STALE_RELATIONSHIP_THRESHOLD: int = 15
