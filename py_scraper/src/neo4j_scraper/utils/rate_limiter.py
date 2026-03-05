"""
速率限制器

负责管理API请求的速率限制，确保不超过API的请求限制：
1. 记录请求时间戳
2. 检查是否可以发起请求
3. 清理过期的请求记录
"""

import logging
import time
from typing import List

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器

    使用滑动窗口算法实现速率限制：
    - 维护一个请求时间戳列表
    - 只保留时间窗口内的请求记录
    - 检查当前请求数是否超过限制

    用途：
    - 防止触发API的速率限制
    - 避免被封禁
    - 确保合规使用API
    """

    def __init__(self, max_requests: int, time_window: int) -> None:
        """初始化速率限制器

        Args:
            max_requests: 时间窗口内允许的最大请求数
            time_window: 时间窗口长度（秒）
        """
        self.max_requests: int = max_requests
        self.time_window: int = time_window
        self.requests: List[float] = []

    async def can_make_request(self) -> bool:
        """检查是否可以发起请求

        执行流程：
        1. 获取当前时间
        2. 清理过期的请求记录
        3. 检查当前请求数是否超过限制
        4. 如果未超过限制，记录本次请求并返回True
        5. 如果超过限制，返回False

        Returns:
            bool: 是否可以发起请求
        """
        now = time.time()

        # 移除时间窗口外的请求记录
        self._cleanup_old_requests(now)

        # 检查是否超过速率限制
        if len(self.requests) >= self.max_requests:
            logger.debug(f"达到速率限制: {len(self.requests)}/{self.max_requests} "
                        f"在 {self.time_window} 秒内")
            return False

        # 记录本次请求
        self.requests.append(now)
        return True

    def _cleanup_old_requests(self, now: float) -> None:
        """清理过期的请求记录

        Args:
            now: 当前时间戳
        """
        # 只保留时间窗口内的请求记录
        self.requests = [t for t in self.requests 
                      if now - t < self.time_window]

    def get_request_count(self) -> int:
        """获取当前时间窗口内的请求数

        Returns:
            int: 当前请求数
        """
        now = time.time()
        self._cleanup_old_requests(now)
        return len(self.requests)

    def get_remaining_time(self) -> float:
        """获取距离下次可请求的剩余时间

        Returns:
            float: 剩余时间（秒），如果可以立即请求则返回0
        """
        now = time.time()
        self._cleanup_old_requests(now)

        if len(self.requests) < self.max_requests:
            return 0.0

        # 计算最早请求的过期时间
        oldest_request = self.requests[0]
        return max(0.0, oldest_request + self.time_window - now)
