"""
日志工具

负责配置和管理应用程序的日志系统：
1. 配置日志格式和级别
2. 支持控制台和文件输出
3. 提供统一的日志获取接口
"""

import logging
import sys
from typing import Optional


class Logger:
    """日志管理器

    职责：
    - 配置日志格式
    - 设置日志级别
    - 创建控制台和文件处理器
    - 提供统一的日志获取接口
    """

    @staticmethod
    def setup(name: str, 
             level: int = logging.INFO,
             log_file: Optional[str] = None,
             format_string: Optional[str] = None) -> logging.Logger:
        """设置日志器

        Args:
            name: 日志器名称
            level: 日志级别
            log_file: 日志文件路径（可选）
            format_string: 自定义日志格式（可选）

        Returns:
            logging.Logger: 配置好的日志器
        """
        # 创建日志器
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        # 设置默认日志格式
        if not format_string:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        formatter = logging.Formatter(format_string)

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 如果指定了日志文件，创建文件处理器
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """获取日志器

        Args:
            name: 日志器名称

        Returns:
            logging.Logger: 日志器实例
        """
        return logging.getLogger(name)
