"""全局配置模块。"""

from .constants import BATCH_NO_SUFFIX, TASK_QUEUE_SUFFIX, TASK_SET_SUFFIX
from .settings import Settings

__all__ = ["Settings", "TASK_QUEUE_SUFFIX", "TASK_SET_SUFFIX", "BATCH_NO_SUFFIX"]
