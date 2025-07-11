"""
工具模块
包含系统通用工具函数、日志记录、错误处理和监控功能
"""

from .helpers import (
    setup_logger, format_sources, calculate_confidence,
    generate_session_id, generate_query_id, validate_query,
    safe_json_parse, truncate_text, ensure_directory,
    get_file_hash, format_timestamp, sanitize_filename,
    measure_execution_time, retry_with_exponential_backoff,
    deep_merge_dicts, get_nested_value, set_nested_value,
    record_performance_metric, get_performance_stats,
    clear_performance_metrics
)

from .lightrag_client import (
    LightRAGClient, lightrag_client,
    initialize_lightrag, query_lightrag, query_lightrag_sync,
    insert_documents_to_lightrag
)

from .document_processor import (
    document_processor,
    process_documents,
    ingest_documents
)

from .advanced_logging import (
    get_logging_system, get_performance_logger, get_error_tracker,
    audit_log, log_performance, log_errors,
    performance_context, error_context,
    record_metric, get_system_metrics, get_metric,
    initialize_logging, shutdown_logging, cleanup_logs
)

from .error_handling import (
    SystemError, ConfigurationError, DatabaseError, NetworkError,
    APIError, ValidationError, ExternalServiceError,
    ErrorSeverity, ErrorCategory,
    ErrorHandler, RetryHandler, CircuitBreaker, ErrorRecoveryStrategy,
    handle_errors, retry_on_failure, circuit_breaker,
    handle_global_error, register_recovery_strategy, attempt_global_recovery,
    ErrorContext
)

from .system_monitoring import (
    HealthStatus, HealthCheck, SystemMonitor, ApplicationHealthChecker,
    get_system_monitor, get_app_health_checker,
    initialize_monitoring, shutdown_monitoring,
    get_system_health, get_detailed_health_report
)

__all__ = [
    # 辅助函数
    'setup_logger', 'format_sources', 'calculate_confidence',
    'generate_session_id', 'generate_query_id', 'validate_query',
    'safe_json_parse', 'truncate_text', 'ensure_directory',
    'get_file_hash', 'format_timestamp', 'sanitize_filename',
    'measure_execution_time', 'retry_with_exponential_backoff',
    'deep_merge_dicts', 'get_nested_value', 'set_nested_value',
    'record_performance_metric', 'get_performance_stats',
    'clear_performance_metrics',
    
    # LightRAG 客户端
    'LightRAGClient', 'lightrag_client',
    'initialize_lightrag', 'query_lightrag', 'query_lightrag_sync',
    'insert_documents_to_lightrag',
    
    # 文档处理
    'document_processor', 'process_documents', 'ingest_documents',
    
    # 高级日志记录
    'get_logging_system', 'get_performance_logger', 'get_error_tracker',
    'audit_log', 'log_performance', 'log_errors',
    'performance_context', 'error_context',
    'record_metric', 'get_system_metrics', 'get_metric',
    'initialize_logging', 'shutdown_logging', 'cleanup_logs',
    
    # 错误处理
    'SystemError', 'ConfigurationError', 'DatabaseError', 'NetworkError',
    'APIError', 'ValidationError', 'ExternalServiceError',
    'ErrorSeverity', 'ErrorCategory',
    'ErrorHandler', 'RetryHandler', 'CircuitBreaker', 'ErrorRecoveryStrategy',
    'handle_errors', 'retry_on_failure', 'circuit_breaker',
    'handle_global_error', 'register_recovery_strategy', 'attempt_global_recovery',
    'ErrorContext',
    
    # 系统监控
    'HealthStatus', 'HealthCheck', 'SystemMonitor', 'ApplicationHealthChecker',
    'get_system_monitor', 'get_app_health_checker',
    'initialize_monitoring', 'shutdown_monitoring',
    'get_system_health', 'get_detailed_health_report'
]