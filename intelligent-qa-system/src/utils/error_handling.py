"""
综合错误处理系统
提供统一的异常处理、错误恢复和用户友好的错误信息
"""

import functools
import traceback
import sys
from typing import Any, Dict, Optional, Callable, Type, List, Union
from enum import Enum
import json
import time
from datetime import datetime

from .advanced_logging import setup_logger, get_error_tracker, audit_log


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    API = "api"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"
    USER_INPUT = "user_input"
    LIGHTRAG = "lightrag"  # LightRAG 相关错误


class SystemError(Exception):
    """系统基础异常类"""
    
    def __init__(self, 
                 message: str,
                 error_code: str = None,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 details: Dict[str, Any] = None,
                 recovery_suggestions: List[str] = None,
                 user_message: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.recovery_suggestions = recovery_suggestions or []
        self.user_message = user_message or self._generate_user_message()
        self.timestamp = datetime.now().isoformat()
    
    def _generate_user_message(self) -> str:
        """生成用户友好的错误信息"""
        user_messages = {
            ErrorCategory.SYSTEM: "系统内部错误，请稍后重试",
            ErrorCategory.NETWORK: "网络连接错误，请检查网络连接",
            ErrorCategory.DATABASE: "数据库连接错误，请稍后重试",
            ErrorCategory.API: "API 调用错误，请检查配置",
            ErrorCategory.VALIDATION: "输入数据验证失败，请检查输入",
            ErrorCategory.AUTHENTICATION: "身份验证失败，请检查凭据",
            ErrorCategory.PERMISSION: "权限不足，请联系管理员",
            ErrorCategory.CONFIGURATION: "配置错误，请检查系统配置",
            ErrorCategory.EXTERNAL_SERVICE: "外部服务错误，请稍后重试",
            ErrorCategory.USER_INPUT: "输入错误，请检查您的输入",
            ErrorCategory.LIGHTRAG: "智能检索系统错误，请稍后重试"
        }
        return user_messages.get(self.category, "发生未知错误")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "recovery_suggestions": self.recovery_suggestions,
            "timestamp": self.timestamp
        }


class ConfigurationError(SystemError):
    """配置错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class DatabaseError(SystemError):
    """数据库错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class NetworkError(SystemError):
    """网络错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class APIError(SystemError):
    """API 错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ValidationError(SystemError):
    """验证错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class ExternalServiceError(SystemError):
    """外部服务错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class LightRAGError(SystemError):
    """HKUDS/LightRAG 相关错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.LIGHTRAG,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class LightRAGInitializationError(LightRAGError):
    """LightRAG 初始化错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"LightRAG 初始化失败: {message}",
            error_code="LIGHTRAG_INIT_FAILED",
            user_message="智能检索系统初始化失败，请检查配置",
            recovery_suggestions=[
                "检查 LightRAG 工作目录是否存在",
                "确认 OpenAI API 密钥配置正确",
                "检查 embedding 模型配置",
                "确认 LightRAG 依赖包正确安装"
            ],
            **kwargs
        )


class LightRAGRetrievalError(LightRAGError):
    """LightRAG 检索错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"LightRAG 检索失败: {message}",
            error_code="LIGHTRAG_RETRIEVAL_FAILED",
            user_message="智能检索失败，请稍后重试",
            recovery_suggestions=[
                "检查查询是否有效",
                "确认 LightRAG 实例已正确初始化",
                "检查网络连接",
                "尝试切换到其他检索模式"
            ],
            **kwargs
        )


class LightRAGInsertionError(LightRAGError):
    """LightRAG 插入错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"LightRAG 数据插入失败: {message}",
            error_code="LIGHTRAG_INSERTION_FAILED",
            user_message="文档插入失败，请检查输入",
            recovery_suggestions=[
                "检查文档内容是否有效",
                "确认文档格式正确",
                "检查存储空间是否充足",
                "尝试分批插入文档"
            ],
            **kwargs
        )


class LightRAGModeError(LightRAGError):
    """LightRAG 模式错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"LightRAG 模式错误: {message}",
            error_code="LIGHTRAG_MODE_ERROR",
            user_message="检索模式配置错误",
            recovery_suggestions=[
                "检查查询模式是否支持 (naive, local, global, hybrid, mix)",
                "确认模式参数正确",
                "尝试使用 hybrid 模式作为默认"
            ],
            **kwargs
        )


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, logger_name: str = None):
        self.logger = setup_logger(logger_name or "error_handler")
        self.error_tracker = get_error_tracker(logger_name or "error_handler")
        self.retry_config = {
            "max_retries": 3,
            "backoff_factor": 1.5,
            "retry_exceptions": (NetworkError, ExternalServiceError)
        }
    
    def handle_error(self, 
                    error: Exception,
                    context: Dict[str, Any] = None,
                    notify_user: bool = True) -> Dict[str, Any]:
        """处理错误"""
        
        # 追踪错误
        error_data = self.error_tracker.track_error(error, context)
        
        # 记录审计日志
        audit_log(
            "error_occurred",
            details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {}
            }
        )
        
        # 生成错误响应
        if isinstance(error, SystemError):
            error_response = error.to_dict()
        else:
            error_response = self._convert_standard_error(error)
        
        # 添加处理信息
        error_response.update({
            "handled": True,
            "handled_at": datetime.now().isoformat(),
            "context": context or {}
        })
        
        return error_response
    
    def _convert_standard_error(self, error: Exception) -> Dict[str, Any]:
        """转换标准异常为系统错误格式"""
        
        # 错误类型映射
        error_mappings = {
            ConnectionError: (ErrorCategory.NETWORK, ErrorSeverity.HIGH),
            TimeoutError: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            ValueError: (ErrorCategory.VALIDATION, ErrorSeverity.LOW),
            KeyError: (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM),
            FileNotFoundError: (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM),
            PermissionError: (ErrorCategory.PERMISSION, ErrorSeverity.HIGH),
            ImportError: (ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH),
            ModuleNotFoundError: (ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH)
        }
        
        error_type = type(error)
        category, severity = error_mappings.get(error_type, (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM))
        
        return {
            "error_code": error_type.__name__,
            "message": str(error),
            "user_message": self._generate_user_message(category),
            "category": category.value,
            "severity": severity.value,
            "details": {"original_error": str(error)},
            "recovery_suggestions": self._get_recovery_suggestions(error_type),
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_user_message(self, category: ErrorCategory) -> str:
        """生成用户友好的错误信息"""
        user_messages = {
            ErrorCategory.SYSTEM: "系统内部错误，请稍后重试",
            ErrorCategory.NETWORK: "网络连接错误，请检查网络连接",
            ErrorCategory.DATABASE: "数据库连接错误，请稍后重试",
            ErrorCategory.API: "API 调用错误，请检查配置",
            ErrorCategory.VALIDATION: "输入数据验证失败，请检查输入",
            ErrorCategory.AUTHENTICATION: "身份验证失败，请检查凭据",
            ErrorCategory.PERMISSION: "权限不足，请联系管理员",
            ErrorCategory.CONFIGURATION: "配置错误，请检查系统配置",
            ErrorCategory.EXTERNAL_SERVICE: "外部服务错误，请稍后重试",
            ErrorCategory.USER_INPUT: "输入错误，请检查您的输入",
            ErrorCategory.LIGHTRAG: "智能检索系统错误，请稍后重试"
        }
        return user_messages.get(category, "发生未知错误")
    
    def _get_recovery_suggestions(self, error_type: Type[Exception]) -> List[str]:
        """获取恢复建议"""
        suggestions = {
            ConnectionError: [
                "检查网络连接",
                "确认服务器地址正确",
                "检查防火墙设置",
                "稍后重试"
            ],
            TimeoutError: [
                "检查网络连接速度",
                "增加超时时间",
                "稍后重试"
            ],
            ValueError: [
                "检查输入数据格式",
                "确认参数值正确",
                "参考文档说明"
            ],
            KeyError: [
                "检查配置文件",
                "确认必要参数已设置",
                "参考配置示例"
            ],
            FileNotFoundError: [
                "检查文件路径",
                "确认文件存在",
                "检查文件权限"
            ],
            PermissionError: [
                "检查文件权限",
                "以管理员身份运行",
                "联系系统管理员"
            ],
            ImportError: [
                "检查依赖包是否安装",
                "运行 pip install -r requirements.txt",
                "检查 Python 路径"
            ]
        }
        return suggestions.get(error_type, ["检查系统配置", "查看日志详情", "联系技术支持"])


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 backoff_factor: float = 1.5,
                 retry_exceptions: tuple = None):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_exceptions = retry_exceptions or (NetworkError, ExternalServiceError, ConnectionError)
        self.logger = setup_logger("retry_handler")
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """带退避的重试"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.retry_exceptions as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    self.logger.error(f"重试失败，已达到最大重试次数: {attempt + 1}")
                    break
                
                wait_time = self.backoff_factor ** attempt
                self.logger.warning(f"操作失败，{wait_time:.1f}秒后进行第{attempt + 1}次重试: {str(e)}")
                time.sleep(wait_time)
            except Exception as e:
                # 不可重试的异常
                self.logger.error(f"不可重试的异常: {str(e)}")
                raise
        
        # 所有重试都失败
        raise last_exception


class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
        self.logger = setup_logger("circuit_breaker")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """调用函数并处理熔断"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                self.logger.info("熔断器状态: half-open")
            else:
                raise SystemError(
                    "服务熔断中，请稍后重试",
                    error_code="CIRCUIT_BREAKER_OPEN",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "closed"
        if self.logger:
            self.logger.debug("熔断器状态: closed")
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.logger.warning(f"熔断器触发，失败次数: {self.failure_count}")


# 装饰器
def handle_errors(logger_name: str = None,
                 return_on_error: Any = None,
                 reraise: bool = True):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(logger_name or func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args": str(args)[:200],
                    "kwargs": str(kwargs)[:200]
                }
                
                error_response = handler.handle_error(e, context)
                
                if reraise:
                    raise
                else:
                    return return_on_error
        
        return wrapper
    return decorator


def retry_on_failure(max_retries: int = 3,
                    backoff_factor: float = 1.5,
                    retry_exceptions: tuple = None):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_handler = RetryHandler(max_retries, backoff_factor, retry_exceptions)
            return retry_handler.retry_with_backoff(func, *args, **kwargs)
        return wrapper
    return decorator


def circuit_breaker(failure_threshold: int = 5,
                   recovery_timeout: int = 60,
                   expected_exception: Type[Exception] = Exception):
    """熔断器装饰器"""
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


# 错误恢复策略
class ErrorRecoveryStrategy:
    """错误恢复策略"""
    
    def __init__(self):
        self.strategies = {}
        self.logger = setup_logger("error_recovery")
    
    def register_strategy(self, 
                         error_type: Type[Exception],
                         recovery_func: Callable,
                         max_attempts: int = 3):
        """注册恢复策略"""
        self.strategies[error_type] = {
            "recovery_func": recovery_func,
            "max_attempts": max_attempts
        }
    
    def attempt_recovery(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """尝试错误恢复"""
        error_type = type(error)
        
        if error_type not in self.strategies:
            self.logger.warning(f"没有找到错误类型 {error_type.__name__} 的恢复策略")
            return False
        
        strategy = self.strategies[error_type]
        recovery_func = strategy["recovery_func"]
        max_attempts = strategy["max_attempts"]
        
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"尝试恢复错误 {error_type.__name__}，第 {attempt + 1} 次")
                result = recovery_func(error, context)
                
                if result:
                    self.logger.info(f"错误恢复成功: {error_type.__name__}")
                    return True
                
            except Exception as recovery_error:
                self.logger.error(f"错误恢复失败: {str(recovery_error)}")
        
        self.logger.error(f"错误恢复最终失败: {error_type.__name__}")
        return False


# 全局错误处理器
_global_error_handler = ErrorHandler("global")
_global_recovery_strategy = ErrorRecoveryStrategy()


def handle_global_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """处理全局错误"""
    return _global_error_handler.handle_error(error, context)


def register_recovery_strategy(error_type: Type[Exception], 
                              recovery_func: Callable,
                              max_attempts: int = 3):
    """注册全局恢复策略"""
    _global_recovery_strategy.register_strategy(error_type, recovery_func, max_attempts)


def attempt_global_recovery(error: Exception, context: Dict[str, Any] = None) -> bool:
    """尝试全局错误恢复"""
    return _global_recovery_strategy.attempt_recovery(error, context)


# 异常处理上下文管理器
class ErrorContext:
    """错误处理上下文管理器"""
    
    def __init__(self, 
                 operation_name: str,
                 logger_name: str = None,
                 handle_errors: bool = True,
                 attempt_recovery: bool = True):
        self.operation_name = operation_name
        self.handler = ErrorHandler(logger_name or "error_context")
        self.handle_errors = handle_errors
        self.attempt_recovery = attempt_recovery
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.handler.logger.info(f"开始操作: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0
        
        if exc_type is None:
            self.handler.logger.info(f"操作成功完成: {self.operation_name} ({duration:.2f}s)")
            return False
        
        # 处理异常
        context = {
            "operation": self.operation_name,
            "duration": duration
        }
        
        if self.handle_errors:
            self.handler.handle_error(exc_val, context)
        
        if self.attempt_recovery and self.handle_errors:
            recovery_successful = attempt_global_recovery(exc_val, context)
            if recovery_successful:
                self.handler.logger.info(f"操作恢复成功: {self.operation_name}")
                return True  # 抑制异常
        
        self.handler.logger.error(f"操作失败: {self.operation_name} ({duration:.2f}s)")
        return False  # 不抑制异常


# 导出
__all__ = [
    # 异常类
    "SystemError",
    "ConfigurationError", 
    "DatabaseError",
    "NetworkError",
    "APIError",
    "ValidationError",
    "ExternalServiceError",
    "LightRAGError",
    "LightRAGInitializationError",
    "LightRAGRetrievalError",
    "LightRAGInsertionError",
    "LightRAGModeError",
    # 枚举
    "ErrorSeverity",
    "ErrorCategory",
    # 处理器
    "ErrorHandler",
    "RetryHandler",
    "CircuitBreaker",
    "ErrorRecoveryStrategy",
    # 装饰器
    "handle_errors",
    "retry_on_failure",
    "circuit_breaker",
    # 全局函数
    "handle_global_error",
    "register_recovery_strategy",
    "attempt_global_recovery",
    # 上下文管理器
    "ErrorContext"
]