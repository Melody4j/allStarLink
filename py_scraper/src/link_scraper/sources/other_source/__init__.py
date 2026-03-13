"""
第二数据源 adapter 骨架。
"""

from .client import OtherSourceClient
from .mapper import OtherSourceMapper
from .parser import OtherSourceParser

__all__ = ["OtherSourceClient", "OtherSourceParser", "OtherSourceMapper"]

