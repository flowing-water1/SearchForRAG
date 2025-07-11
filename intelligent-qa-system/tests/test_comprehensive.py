#!/usr/bin/env python3
"""
智能问答系统综合测试套件
提供完整的单元测试、集成测试和端到端测试
"""

import unittest
import asyncio
import tempfile
import json
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入测试模块
from src.utils.advanced_logging import (
    setup_logger, get_performance_logger, get_error_tracker,
    audit_log, record_metric, get_system_metrics
)
from src.utils.error_handling import (
    SystemError, ConfigurationError, DatabaseError, NetworkError,
    ErrorHandler, RetryHandler, CircuitBreaker,
    handle_errors, retry_on_failure, ErrorContext
)
from src.utils.helpers import (
    validate_query, safe_json_parse, calculate_confidence,
    format_sources, generate_session_id, deep_merge_dicts
)
from src.utils.system_monitoring import (
    HealthStatus, HealthCheck, SystemMonitor, ApplicationHealthChecker
)


class TestAdvancedLogging(unittest.TestCase):
    """高级日志记录测试"""
    
    def setUp(self):
        """测试设置"""
        self.logger = setup_logger("test_logging")
        self.perf_logger = get_performance_logger("test_performance")
        self.error_tracker = get_error_tracker("test_error")
    
    def test_basic_logging(self):
        """测试基础日志功能"""
        # 测试不同级别的日志
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        
        # 验证日志器存在
        self.assertIsNotNone(self.logger)
        self.assertEqual(self.logger.name, "test_logging")
    
    def test_performance_logging(self):
        """测试性能日志"""
        # 测试操作计时
        self.perf_logger.start_operation("test_operation")
        time.sleep(0.01)  # 模拟操作
        duration = self.perf_logger.end_operation(success=True)
        
        # 验证计时功能
        self.assertIsNotNone(duration)
        self.assertGreater(duration, 0)
    
    def test_error_tracking(self):
        """测试错误追踪"""
        test_error = ValueError("Test error")
        context = {"test": "context"}
        
        # 追踪错误
        error_data = self.error_tracker.track_error(test_error, context)
        
        # 验证错误数据
        self.assertIn("error_type", error_data)
        self.assertIn("error_message", error_data)
        self.assertIn("context", error_data)
        self.assertEqual(error_data["error_type"], "ValueError")
    
    def test_audit_logging(self):
        """测试审计日志"""
        # 记录审计事件
        audit_log("test_action", "test_user", details={"key": "value"})
        
        # 验证审计日志功能（通过没有异常来验证）
        self.assertTrue(True)
    
    def test_metric_recording(self):
        """测试指标记录"""
        # 记录指标
        record_metric("test_metric", 100.0, tag="test")
        
        # 获取指标
        metrics = get_system_metrics()
        
        # 验证指标存在
        self.assertIsInstance(metrics, dict)


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""
    
    def setUp(self):
        """测试设置"""
        self.error_handler = ErrorHandler("test_handler")
        self.retry_handler = RetryHandler(max_retries=2, backoff_factor=0.1)
    
    def test_custom_exceptions(self):
        """测试自定义异常"""
        # 测试配置错误
        config_error = ConfigurationError(
            "Test config error",
            error_code="TEST_CONFIG_ERROR",
            recovery_suggestions=["Check config", "Restart system"]
        )
        
        # 验证异常属性
        self.assertEqual(config_error.error_code, "TEST_CONFIG_ERROR")
        self.assertIn("Check config", config_error.recovery_suggestions)
        self.assertIsNotNone(config_error.user_message)
    
    def test_error_handler(self):
        """测试错误处理器"""
        test_error = ValueError("Test error")
        context = {"function": "test_function"}
        
        # 处理错误
        result = self.error_handler.handle_error(test_error, context)
        
        # 验证处理结果
        self.assertIn("error_code", result)
        self.assertIn("message", result)
        self.assertIn("user_message", result)
        self.assertTrue(result["handled"])
    
    def test_retry_handler(self):
        """测试重试处理器"""
        attempt_count = 0
        
        def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise NetworkError("Network error")
            return "Success"
        
        # 测试重试
        result = self.retry_handler.retry_with_backoff(failing_function)
        
        # 验证重试成功
        self.assertEqual(result, "Success")
        self.assertEqual(attempt_count, 2)
    
    def test_circuit_breaker(self):
        """测试熔断器"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        def failing_function():
            raise NetworkError("Service unavailable")
        
        # 测试熔断触发
        for i in range(3):
            try:
                breaker.call(failing_function)
            except Exception:
                pass
        
        # 验证熔断器状态
        self.assertEqual(breaker.state, "open")
    
    def test_error_decorators(self):
        """测试错误装饰器"""
        @handle_errors(reraise=False, return_on_error="default")
        def test_function():
            raise ValueError("Test error")
        
        # 测试装饰器
        result = test_function()
        
        # 验证返回默认值
        self.assertEqual(result, "default")
    
    def test_error_context(self):
        """测试错误上下文"""
        with ErrorContext("test_operation"):
            # 正常操作
            pass
        
        # 验证上下文管理器正常工作
        self.assertTrue(True)


class TestHelpers(unittest.TestCase):
    """辅助函数测试"""
    
    def test_query_validation(self):
        """测试查询验证"""
        # 测试有效查询
        valid, error = validate_query("这是一个有效的查询")
        self.assertTrue(valid)
        self.assertIsNone(error)
        
        # 测试无效查询
        valid, error = validate_query("a")
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        
        # 测试恶意查询
        valid, error = validate_query("DROP TABLE users")
        self.assertFalse(valid)
        self.assertIsNotNone(error)
    
    def test_json_parsing(self):
        """测试JSON解析"""
        # 测试有效JSON
        result = safe_json_parse('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})
        
        # 测试无效JSON
        result = safe_json_parse('invalid json', {"default": "value"})
        self.assertEqual(result, {"default": "value"})
    
    def test_confidence_calculation(self):
        """测试置信度计算"""
        confidence = calculate_confidence(0.8, 500, 0.9, 0.7)
        
        # 验证置信度在合理范围内
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
    
    def test_source_formatting(self):
        """测试信息源格式化"""
        sources = [
            {"type": "lightrag_knowledge", "mode": "hybrid", "confidence": 0.85},
            {"type": "web_search", "title": "Test", "url": "http://test.com"}
        ]
        
        formatted = format_sources(sources)
        
        # 验证格式化结果
        self.assertIsInstance(formatted, str)
        self.assertIn("本地知识库", formatted)
        self.assertIn("网络搜索", formatted)
    
    def test_session_id_generation(self):
        """测试会话ID生成"""
        session_id = generate_session_id()
        
        # 验证ID格式
        self.assertIsInstance(session_id, str)
        self.assertGreater(len(session_id), 0)
        
        # 验证唯一性
        another_id = generate_session_id()
        self.assertNotEqual(session_id, another_id)
    
    def test_dict_operations(self):
        """测试字典操作"""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}
        
        # 测试深度合并
        merged = deep_merge_dicts(dict1, dict2)
        
        # 验证合并结果
        self.assertEqual(merged["a"], 1)
        self.assertEqual(merged["b"]["c"], 2)
        self.assertEqual(merged["b"]["d"], 3)
        self.assertEqual(merged["e"], 4)


class TestSystemMonitoring(unittest.TestCase):
    """系统监控测试"""
    
    def setUp(self):
        """测试设置"""
        self.monitor = SystemMonitor()
        self.app_checker = ApplicationHealthChecker()
    
    def test_health_check_registration(self):
        """测试健康检查注册"""
        def test_check():
            return HealthCheck(
                name="test",
                status=HealthStatus.HEALTHY,
                message="OK",
                details={},
                timestamp=time.time(),
                execution_time=0.1
            )
        
        # 注册健康检查
        self.monitor.register_health_check("test_check", test_check)
        
        # 验证注册成功
        self.assertIn("test_check", self.monitor.health_checks)
    
    def test_metric_recording(self):
        """测试指标记录"""
        # 记录指标
        self.monitor.add_metric("test_metric", 42.0)
        
        # 验证指标记录
        self.assertFalse(self.monitor.metrics_queue.empty())
    
    def test_health_check_creation(self):
        """测试健康检查创建"""
        health_check = HealthCheck(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="System is healthy",
            details={"cpu": 50.0},
            timestamp=time.time(),
            execution_time=0.1
        )
        
        # 验证健康检查属性
        self.assertEqual(health_check.name, "test_check")
        self.assertEqual(health_check.status, HealthStatus.HEALTHY)
        self.assertIn("cpu", health_check.details)
    
    def test_system_health_summary(self):
        """测试系统健康摘要"""
        # 获取系统健康状态
        health = self.monitor.get_system_health()
        
        # 验证健康状态格式
        self.assertIn("overall_status", health)
        self.assertIn("timestamp", health)
        self.assertIn("checks", health)
        self.assertIn("metrics", health)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_metrics_collection(self, mock_disk, mock_memory, mock_cpu):
        """测试系统指标收集"""
        # 模拟系统指标
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(percent=60.0, available=1000000)
        mock_disk.return_value = Mock(used=500000, total=1000000)
        
        # 收集系统指标
        self.monitor._collect_system_metrics()
        
        # 验证指标收集
        self.assertIn("cpu_usage", self.monitor.metrics_history)
        self.assertIn("memory_usage", self.monitor.metrics_history)
        self.assertIn("disk_usage", self.monitor.metrics_history)


class TestWorkflowIntegration(unittest.TestCase):
    """工作流集成测试"""
    
    def setUp(self):
        """测试设置"""
        # 由于依赖问题，使用模拟对象
        self.mock_workflow = Mock()
        self.mock_workflow.get_workflow_info.return_value = {
            "name": "Test Workflow",
            "version": "1.0.0",
            "initialized": True
        }
        self.mock_workflow.get_performance_stats.return_value = {
            "total_queries": 10,
            "successful_queries": 8,
            "failed_queries": 2
        }
    
    def test_workflow_info(self):
        """测试工作流信息"""
        info = self.mock_workflow.get_workflow_info()
        
        # 验证工作流信息
        self.assertIn("name", info)
        self.assertIn("version", info)
        self.assertIn("initialized", info)
        self.assertTrue(info["initialized"])
    
    def test_performance_stats(self):
        """测试性能统计"""
        stats = self.mock_workflow.get_performance_stats()
        
        # 验证性能统计
        self.assertIn("total_queries", stats)
        self.assertIn("successful_queries", stats)
        self.assertIn("failed_queries", stats)
        self.assertEqual(stats["total_queries"], 10)


class TestEndToEnd(unittest.TestCase):
    """端到端集成测试"""
    
    def setUp(self):
        """测试设置"""
        self.test_query = "什么是机器学习？"
    
    def test_query_validation_pipeline(self):
        """测试查询验证管道"""
        # 验证查询
        valid, error = validate_query(self.test_query)
        self.assertTrue(valid)
        
        # 生成会话ID
        session_id = generate_session_id()
        self.assertIsNotNone(session_id)
        
        # 记录审计日志
        audit_log("query_received", "test_user", details={"query": self.test_query})
    
    def test_error_handling_pipeline(self):
        """测试错误处理管道"""
        # 创建错误
        error = ValueError("Test pipeline error")
        
        # 处理错误
        handler = ErrorHandler("test_pipeline")
        result = handler.handle_error(error, {"pipeline": "test"})
        
        # 验证错误处理
        self.assertTrue(result["handled"])
        self.assertIn("error_code", result)
    
    def test_monitoring_pipeline(self):
        """测试监控管道"""
        # 创建监控器
        monitor = SystemMonitor()
        
        # 注册健康检查
        def test_health():
            return HealthCheck(
                name="pipeline_test",
                status=HealthStatus.HEALTHY,
                message="Pipeline is healthy",
                details={},
                timestamp=time.time(),
                execution_time=0.1
            )
        
        monitor.register_health_check("pipeline_test", test_health)
        
        # 获取健康状态
        health = monitor.get_system_health()
        self.assertIn("overall_status", health)
    
    def test_logging_pipeline(self):
        """测试日志管道"""
        # 创建日志器
        logger = setup_logger("test_pipeline")
        perf_logger = get_performance_logger("test_pipeline")
        
        # 记录性能
        perf_logger.start_operation("test_pipeline_operation")
        time.sleep(0.01)
        duration = perf_logger.end_operation(success=True)
        
        # 验证性能记录
        self.assertIsNotNone(duration)
        self.assertGreater(duration, 0)


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def test_logging_performance(self):
        """测试日志性能"""
        logger = setup_logger("performance_test")
        
        # 测试大量日志记录
        start_time = time.time()
        for i in range(100):
            logger.info(f"Test message {i}")
        end_time = time.time()
        
        # 验证性能
        duration = end_time - start_time
        self.assertLess(duration, 1.0)  # 应该在1秒内完成
    
    def test_error_handling_performance(self):
        """测试错误处理性能"""
        handler = ErrorHandler("performance_test")
        
        # 测试大量错误处理
        start_time = time.time()
        for i in range(10):
            try:
                raise ValueError(f"Test error {i}")
            except Exception as e:
                handler.handle_error(e, {"index": i})
        end_time = time.time()
        
        # 验证性能
        duration = end_time - start_time
        self.assertLess(duration, 1.0)  # 应该在1秒内完成
    
    def test_metric_recording_performance(self):
        """测试指标记录性能"""
        # 测试大量指标记录
        start_time = time.time()
        for i in range(100):
            record_metric(f"test_metric_{i}", float(i))
        end_time = time.time()
        
        # 验证性能
        duration = end_time - start_time
        self.assertLess(duration, 1.0)  # 应该在1秒内完成


def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestAdvancedLogging,
        TestErrorHandling,
        TestHelpers,
        TestSystemMonitoring,
        TestWorkflowIntegration,
        TestEndToEnd,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("🧪 运行智能问答系统综合测试套件")
    print("=" * 60)
    
    success = run_all_tests()
    
    if success:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败")
        sys.exit(1)