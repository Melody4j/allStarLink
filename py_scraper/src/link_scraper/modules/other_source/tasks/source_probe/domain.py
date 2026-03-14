"""
OtherSource 探测任务领域模型。
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OtherSourceProbeResult:
    """记录一次 second source 探测结果。"""

    source_name: str
    checked_at: datetime
    success: bool
    message: str
