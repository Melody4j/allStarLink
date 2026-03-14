"""全局基础常量。"""

# Redis 键名后缀。
# 具体键名前缀应由各 source 自己决定，避免多个数据源共用一组状态键。
TASK_QUEUE_SUFFIX: str = "task_queue"
TASK_SET_SUFFIX: str = "task_set"
BATCH_NO_SUFFIX: str = "current_batch_no"

# 跨模块仍可能复用的通用连接方向兜底值
CONNECTION_DIRECTION_UNKNOWN: str = "Unknown"

# 失效关系清理阈值（分钟）
STALE_RELATIONSHIP_THRESHOLD: int = 15
