"""
简单日志模块 - 零依赖，避免循环导入
"""

import logging
import sys
from typing import Optional


def get_simple_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    创建简单的日志记录器，避免循环导入
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建控制台处理器
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(handler)
    
    # 防止日志消息传播到根日志记录器
    logger.propagate = False
    
    return logger