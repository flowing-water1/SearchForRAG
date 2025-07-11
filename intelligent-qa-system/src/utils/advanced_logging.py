"""
高级日志系统
提供结构化日志记录、性能监控和错误追踪
"""

import logging
import logging.handlers
import json
import time
import traceback
import functools
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from pathlib import Path
import os
import sys
from contextlib import contextmanager

from ..core.config import config


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为结构化格式"""
        
        # 基础日志信息
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加额外字段
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
            
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
            
        if hasattr(record, 'query_id'):
            log_entry["query_id"] = record.query_id
            
        if hasattr(record, 'processing_time'):
            log_entry["processing_time"] = record.processing_time
            
        # 异常信息
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # 性能指标
        if hasattr(record, 'metrics'):
            log_entry["metrics"] = record.metrics
            
        return json.dumps(log_entry, ensure_ascii=False)


class PerformanceLogger:
    """性能监控日志器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_time = None
        self.metrics = {}
    
    def start_operation(self, operation_name: str, **kwargs):
        """开始操作计时"""
        self.start_time = time.time()
        self.metrics = {
            "operation": operation_name,
            "start_time": self.start_time,
            **kwargs
        }
        
        self.logger.info(
            f"开始操作: {operation_name}",
            extra={"metrics": self.metrics}
        )
    
    def end_operation(self, success: bool = True, **kwargs):
        """结束操作计时"""
        if self.start_time:
            end_time = time.time()
            duration = end_time - self.start_time
            
            self.metrics.update({
                "end_time": end_time,
                "duration": duration,
                "success": success,
                **kwargs
            })
            
            level = logging.INFO if success else logging.ERROR
            message = f"操作{'成功' if success else '失败'}: {self.metrics.get('operation', 'unknown')}"
            
            self.logger.log(
                level,
                message,
                extra={"metrics": self.metrics}
            )
            
            return duration
        return None
    
    def log_metric(self, metric_name: str, value: Any, **kwargs):
        """记录指标"""
        metric_data = {
            "metric": metric_name,
            "value": value,
            "timestamp": time.time(),
            **kwargs
        }
        
        self.logger.info(
            f"指标记录: {metric_name} = {value}",
            extra={"metrics": metric_data}
        )


class ErrorTracker:
    """错误追踪器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.error_counts = {}
        self.error_patterns = {}
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """追踪错误"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # 更新错误计数
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # 记录错误详情
        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "error_count": self.error_counts[error_type],
            "context": context or {},
            "traceback": traceback.format_exc()
        }
        
        self.logger.error(
            f"错误追踪: {error_type} - {error_message}",
            extra={"error_data": error_data},
            exc_info=True
        )
        
        return error_data
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": dict(self.error_counts),
            "most_common_error": max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None
        }


class LoggingSystem:
    """日志系统管理器"""
    
    def __init__(self):
        self.loggers = {}
        self.handlers = {}
        self.performance_loggers = {}
        self.error_trackers = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志系统"""
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 创建处理器
        self._create_handlers(log_dir)
        
        # 设置格式化器
        self._setup_formatters()
        
        # 应用处理器
        self._apply_handlers(root_logger)
    
    def _create_handlers(self, log_dir: Path):
        """创建日志处理器"""
        
        # 1. 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        self.handlers["console"] = console_handler
        
        # 2. 文件处理器 - 通用日志
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "system.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        self.handlers["file"] = file_handler
        
        # 3. 错误日志处理器
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        self.handlers["error"] = error_handler
        
        # 4. 性能日志处理器
        performance_handler = logging.handlers.RotatingFileHandler(
            log_dir / "performance.log",
            maxBytes=10*1024*1024,
            backupCount=3,
            encoding="utf-8"
        )
        performance_handler.setLevel(logging.INFO)
        self.handlers["performance"] = performance_handler
        
        # 5. 审计日志处理器
        audit_handler = logging.handlers.RotatingFileHandler(
            log_dir / "audit.log",
            maxBytes=10*1024*1024,
            backupCount=10,
            encoding="utf-8"
        )
        audit_handler.setLevel(logging.INFO)
        self.handlers["audit"] = audit_handler
    
    def _setup_formatters(self):
        """设置格式化器"""
        
        # 控制台格式化器 - 简洁格式
        console_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.handlers["console"].setFormatter(console_formatter)
        
        # 文件格式化器 - 详细格式
        file_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.handlers["file"].setFormatter(file_formatter)
        
        # 结构化格式化器 - JSON格式
        structured_formatter = StructuredFormatter()
        self.handlers["error"].setFormatter(structured_formatter)
        self.handlers["performance"].setFormatter(structured_formatter)
        self.handlers["audit"].setFormatter(structured_formatter)
    
    def _apply_handlers(self, root_logger: logging.Logger):
        """应用处理器到日志器"""
        
        # 添加所有处理器到根日志器
        for handler in self.handlers.values():
            root_logger.addHandler(handler)
        
        # 特定日志器配置
        self._configure_specific_loggers()
    
    def _configure_specific_loggers(self):
        """配置特定的日志器"""
        
        # 性能日志器
        performance_logger = logging.getLogger("performance")
        performance_logger.addHandler(self.handlers["performance"])
        performance_logger.setLevel(logging.INFO)
        
        # 审计日志器
        audit_logger = logging.getLogger("audit")
        audit_logger.addHandler(self.handlers["audit"])
        audit_logger.setLevel(logging.INFO)
        
        # 错误日志器
        error_logger = logging.getLogger("error")
        error_logger.addHandler(self.handlers["error"])
        error_logger.setLevel(logging.ERROR)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志器"""
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]
    
    def get_performance_logger(self, name: str) -> PerformanceLogger:
        """获取性能日志器"""
        if name not in self.performance_loggers:
            logger = self.get_logger(f"performance.{name}")
            self.performance_loggers[name] = PerformanceLogger(logger)
        return self.performance_loggers[name]
    
    def get_error_tracker(self, name: str) -> ErrorTracker:
        """获取错误追踪器"""
        if name not in self.error_trackers:
            logger = self.get_logger(f"error.{name}")
            self.error_trackers[name] = ErrorTracker(logger)
        return self.error_trackers[name]
    
    def audit_log(self, action: str, user_id: str = None, details: Dict[str, Any] = None):
        """记录审计日志"""
        audit_logger = logging.getLogger("audit")
        
        audit_data = {
            "action": action,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        audit_logger.info(
            f"审计: {action}",
            extra={"audit_data": audit_data}
        )


# 全局日志系统实例
_logging_system = None


def get_logging_system() -> LoggingSystem:
    """获取全局日志系统实例"""
    global _logging_system
    if _logging_system is None:
        _logging_system = LoggingSystem()
    return _logging_system


def setup_logger(name: str) -> logging.Logger:
    """设置日志器 - 向后兼容"""
    return get_logging_system().get_logger(name)


def get_performance_logger(name: str) -> PerformanceLogger:
    """获取性能日志器"""
    return get_logging_system().get_performance_logger(name)


def get_error_tracker(name: str) -> ErrorTracker:
    """获取错误追踪器"""
    return get_logging_system().get_error_tracker(name)


def audit_log(action: str, user_id: str = None, **details):
    """记录审计日志"""
    get_logging_system().audit_log(action, user_id, details)


# 装饰器
def log_performance(operation_name: str = None):
    """性能日志装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            perf_logger = get_performance_logger(func.__module__)
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            perf_logger.start_operation(op_name)
            try:
                result = func(*args, **kwargs)
                perf_logger.end_operation(success=True)
                return result
            except Exception as e:
                perf_logger.end_operation(success=False, error=str(e))
                raise
        return wrapper
    return decorator


def log_errors(logger_name: str = None):
    """错误日志装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            error_tracker = get_error_tracker(logger_name or func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],
                    "kwargs": str(kwargs)[:200]
                }
                error_tracker.track_error(e, context)
                raise
        return wrapper
    return decorator


@contextmanager
def performance_context(operation_name: str, logger_name: str = None):
    """性能监控上下文管理器"""
    perf_logger = get_performance_logger(logger_name or "default")
    
    perf_logger.start_operation(operation_name)
    try:
        yield perf_logger
        perf_logger.end_operation(success=True)
    except Exception as e:
        perf_logger.end_operation(success=False, error=str(e))
        raise


@contextmanager
def error_context(context_name: str, logger_name: str = None):
    """错误追踪上下文管理器"""
    error_tracker = get_error_tracker(logger_name or "default")
    
    try:
        yield error_tracker
    except Exception as e:
        context = {"context": context_name}
        error_tracker.track_error(e, context)
        raise


# 系统指标收集
class SystemMetrics:
    """系统指标收集器"""
    
    def __init__(self):
        self.metrics = {}
        self.logger = setup_logger("system.metrics")
    
    def record_metric(self, name: str, value: Any, tags: Dict[str, str] = None):
        """记录指标"""
        metric_data = {
            "name": name,
            "value": value,
            "timestamp": time.time(),
            "tags": tags or {}
        }
        
        self.metrics[name] = metric_data
        self.logger.info(f"指标: {name} = {value}", extra={"metrics": metric_data})
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return dict(self.metrics)
    
    def get_metric(self, name: str) -> Optional[Any]:
        """获取特定指标"""
        return self.metrics.get(name, {}).get("value")


# 全局指标收集器
_system_metrics = SystemMetrics()


def record_metric(name: str, value: Any, **tags):
    """记录系统指标"""
    _system_metrics.record_metric(name, value, tags)


def get_system_metrics() -> Dict[str, Any]:
    """获取系统指标"""
    return _system_metrics.get_metrics()


def get_metric(name: str) -> Optional[Any]:
    """获取特定指标"""
    return _system_metrics.get_metric(name)


# 日志清理工具
def cleanup_logs(days: int = 30):
    """清理过期日志文件"""
    log_dir = Path("logs")
    if not log_dir.exists():
        return
    
    import time
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    
    for log_file in log_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            log_file.unlink()
            print(f"删除过期日志: {log_file}")


# 初始化日志系统
def initialize_logging():
    """初始化日志系统"""
    get_logging_system()
    audit_log("system_start", details={"version": "1.0.0"})


# 关闭日志系统
def shutdown_logging():
    """关闭日志系统"""
    audit_log("system_stop")
    
    # 刷新所有处理器
    for handler in logging.getLogger().handlers:
        handler.flush()
        handler.close()


# 导出函数
__all__ = [
    "setup_logger",
    "get_performance_logger",
    "get_error_tracker",
    "audit_log",
    "log_performance",
    "log_errors",
    "performance_context",
    "error_context",
    "record_metric",
    "get_system_metrics",
    "get_metric",
    "initialize_logging",
    "shutdown_logging",
    "cleanup_logs"
]