"""
数据库基类
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseDatabaseManager(ABC):
    """数据库基类，定义通用接口"""

    @abstractmethod
    async def connect(self) -> None:
        """建立数据库连接"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭数据库连接"""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """初始化数据库（创建约束、索引等）"""
        pass

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
