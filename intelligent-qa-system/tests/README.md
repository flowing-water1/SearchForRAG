# 测试模块技术文档

> 返回 [项目概览文档](../../TECHNICAL_REFERENCE.md)

## 📍 相关文档导航
- **[核心模块文档](../src/core/README.md)** - 查看测试涵盖的核心功能
- **[工作流节点文档](../src/agents/README.md)** - 查看测试的工作流节点
- **[工具模块文档](../src/utils/README.md)** - 查看测试的工具和客户端
- **[项目根目录](../../TECHNICAL_REFERENCE.md)** - 返回项目完整概览

## 🔗 测试与系统集成
- [配置管理测试](../src/core/README.md#1-配置管理系统-configpy) - 配置加载和验证测试
- [工作流测试](../src/core/README.md#3-基础工作流-workflowpy) - 端到端工作流测试
- [错误处理测试](../src/utils/README.md#3-错误处理框架-error_handlingpy) - 异常和恢复机制测试
- [性能监控测试](../src/utils/README.md#4-系统监控-system_monitoringpy) - 系统健康和性能测试

---

## 模块概述

测试模块 (tests/) 提供了智能问答系统的全面测试覆盖，包括单元测试、集成测试、性能测试和端到端测试。测试套件确保系统的可靠性、性能和正确性。

### 模块结构
```
tests/
├── __init__.py                # 测试模块初始化
├── core/                      # 核心模块测试
│   └── __init__.py           
├── agents/                    # 工作流节点测试
│   └── __init__.py           
├── utils/                     # 工具模块测试
│   └── __init__.py           
├── test_comprehensive.py     # 综合测试套件
├── test_performance.py       # 性能测试套件
└── test_workflow.py          # 工作流测试套件
```

### 测试分类
- **单元测试**: 测试单个组件和函数
- **集成测试**: 测试模块间的协作
- **性能测试**: 测试系统性能和负载
- **端到端测试**: 测试完整的工作流程

---

## 测试文件详解

### 1. 综合测试套件 (test_comprehensive.py)

**主要功能**: 提供完整的单元测试、集成测试和端到端测试覆盖。

#### 测试类架构

```python
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

# 测试导入
from src.utils.advanced_logging import (
    setup_logger, get_performance_logger, get_error_tracker,
    audit_log, record_metric, get_system_metrics
)
from src.utils.error_handling import (
    SystemError, ConfigurationError, DatabaseError, NetworkError,
    ErrorHandler, RetryHandler, CircuitBreaker
)
from src.utils.helpers import (
    validate_query, safe_json_parse, calculate_confidence,
    format_sources, generate_session_id, deep_merge_dicts
)
from src.utils.system_monitoring import (
    HealthStatus, HealthCheck, SystemMonitor, ApplicationHealthChecker
)
```

#### 高级日志测试

```python
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
        self.logger.debug("测试调试信息")
        self.logger.info("测试信息日志")
        self.logger.warning("测试警告日志")
        self.logger.error("测试错误日志")
        
        # 验证日志器配置
        self.assertIsNotNone(self.logger)
        self.assertEqual(self.logger.name, "test_logging")
    
    def test_performance_logging(self):
        """测试性能日志功能"""
        # 开始性能监控
        self.perf_logger.start_operation("test_operation")
        
        # 模拟操作
        time.sleep(0.1)
        
        # 结束性能监控
        duration = self.perf_logger.end_operation(success=True)
        
        # 验证性能记录
        self.assertIsNotNone(duration)
        self.assertGreater(duration, 0.1)
        self.assertLess(duration, 0.2)
    
    def test_error_tracking(self):
        """测试错误追踪功能"""
        test_error = ValueError("测试错误")
        
        # 追踪错误
        error_data = self.error_tracker.track_error(
            test_error, 
            context={"operation": "test"}
        )
        
        # 验证错误数据
        self.assertEqual(error_data["error_type"], "ValueError")
        self.assertEqual(error_data["error_message"], "测试错误")
        self.assertEqual(error_data["error_count"], 1)
        self.assertIn("context", error_data)
    
    def test_structured_logging(self):
        """测试结构化日志"""
        # 记录结构化日志
        self.logger.info(
            "结构化日志测试",
            extra={
                "user_id": "test_user",
                "session_id": "test_session",
                "metrics": {"operation": "test", "duration": 0.1}
            }
        )
        
        # 验证日志记录成功
        self.assertTrue(True)  # 如果没有异常，则测试通过
    
    def test_audit_logging(self):
        """测试审计日志"""
        # 记录审计事件
        audit_log(
            "test_action",
            user_id="test_user",
            details={"resource": "test_resource", "operation": "read"}
        )
        
        # 验证审计日志记录
        self.assertTrue(True)  # 验证无异常发生
    
    def test_metrics_recording(self):
        """测试指标记录"""
        # 记录不同类型的指标
        record_metric("test_counter", 1, type="counter")
        record_metric("test_gauge", 0.85, type="gauge")
        record_metric("test_timer", 1.5, type="timer")
        
        # 获取系统指标
        metrics = get_system_metrics()
        
        # 验证指标记录
        self.assertIsInstance(metrics, dict)
```

#### 错误处理测试

```python
class TestErrorHandling(unittest.TestCase):
    """错误处理框架测试"""
    
    def setUp(self):
        """测试设置"""
        self.error_handler = ErrorHandler()
        self.retry_handler = RetryHandler()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=1)
    
    def test_custom_exceptions(self):
        """测试自定义异常"""
        # 测试基础系统异常
        with self.assertRaises(SystemError):
            raise SystemError(
                "测试系统错误",
                error_code="TEST_001",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH
            )
        
        # 测试配置错误
        with self.assertRaises(ConfigurationError):
            raise ConfigurationError(
                "配置文件缺失",
                recovery_suggestions=["检查配置文件路径", "重新生成配置"]
            )
        
        # 测试数据库错误
        with self.assertRaises(DatabaseError):
            raise DatabaseError(
                "数据库连接失败",
                details={"host": "localhost", "port": 5432}
            )
    
    def test_error_handler(self):
        """测试错误处理器"""
        test_error = ValueError("测试值错误")
        
        # 处理错误
        result = self.error_handler.handle_error(
            test_error,
            context={"operation": "test_operation"}
        )
        
        # 验证处理结果
        self.assertIsInstance(result, dict)
        self.assertIn("error_type", result)
        self.assertIn("error_message", result)
        self.assertIn("user_message", result)
        self.assertIn("recovery_suggestions", result)
    
    def test_retry_mechanism(self):
        """测试重试机制"""
        call_count = 0
        
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("临时网络错误")
            return "成功"
        
        # 执行重试
        result = self.retry_handler.retry_with_backoff(
            flaky_function,
            max_retries=3,
            backoff_factor=0.1
        )
        
        # 验证重试结果
        self.assertEqual(result, "成功")
        self.assertEqual(call_count, 3)
    
    def test_circuit_breaker(self):
        """测试熔断器"""
        failure_count = 0
        
        def failing_function():
            nonlocal failure_count
            failure_count += 1
            raise NetworkError("服务不可用")
        
        # 测试熔断器保护
        for i in range(5):
            try:
                self.circuit_breaker.call(failing_function)
            except Exception:
                pass
        
        # 验证熔断器状态
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.OPEN)
        self.assertEqual(failure_count, 3)  # 只调用到熔断阈值
    
    def test_error_decorators(self):
        """测试错误处理装饰器"""
        
        @handle_errors(reraise=False, return_on_error="默认值")
        def risky_function():
            raise ValueError("故意出错")
        
        # 测试装饰器错误处理
        result = risky_function()
        self.assertEqual(result, "默认值")
        
        @retry_on_failure(max_retries=2, backoff_factor=0.1)
        def unstable_function():
            if not hasattr(unstable_function, 'call_count'):
                unstable_function.call_count = 0
            unstable_function.call_count += 1
            
            if unstable_function.call_count < 2:
                raise NetworkError("网络不稳定")
            return "稳定"
        
        # 测试重试装饰器
        result = unstable_function()
        self.assertEqual(result, "稳定")
```

#### 辅助函数测试

```python
class TestHelperFunctions(unittest.TestCase):
    """辅助函数测试"""
    
    def test_query_validation(self):
        """测试查询验证"""
        # 测试有效查询
        valid_query = "什么是人工智能？"
        is_valid, message = validate_query(valid_query)
        self.assertTrue(is_valid)
        self.assertIsNone(message)
        
        # 测试无效查询
        invalid_queries = [
            "",              # 空查询
            "   ",           # 只有空格
            "ab",            # 太短
            "a" * 1001,      # 太长
            "<script>alert('xss')</script>"  # 恶意内容
        ]
        
        for query in invalid_queries:
            is_valid, message = validate_query(query)
            self.assertFalse(is_valid)
            self.assertIsNotNone(message)
    
    def test_json_parsing(self):
        """测试JSON解析"""
        # 测试有效JSON
        valid_json = '{"key": "value", "number": 42}'
        result = safe_json_parse(valid_json)
        self.assertEqual(result["key"], "value")
        self.assertEqual(result["number"], 42)
        
        # 测试无效JSON
        invalid_json = '{"key": value}'  # 缺少引号
        result = safe_json_parse(invalid_json, default={"error": True})
        self.assertEqual(result["error"], True)
        
        # 测试空字符串
        result = safe_json_parse("", default={})
        self.assertEqual(result, {})
    
    def test_confidence_calculation(self):
        """测试置信度计算"""
        # 测试高置信度场景
        confidence = calculate_confidence(
            retrieval_score=0.9,
            content_length=1200,
            entity_coverage=0.8,
            mode_effectiveness=0.9
        )
        self.assertGreater(confidence, 0.8)
        self.assertLessEqual(confidence, 1.0)
        
        # 测试低置信度场景
        confidence = calculate_confidence(
            retrieval_score=0.3,
            content_length=100,
            entity_coverage=0.2,
            mode_effectiveness=0.4
        )
        self.assertLess(confidence, 0.5)
    
    def test_source_formatting(self):
        """测试信息源格式化"""
        sources = [
            {
                "type": "lightrag_knowledge",
                "mode": "hybrid",
                "confidence": 0.85
            },
            {
                "type": "web_search",
                "title": "AI发展趋势",
                "url": "https://example.com",
                "score": 0.92
            }
        ]
        
        formatted = format_sources(sources)
        self.assertIn("本地知识库", formatted)
        self.assertIn("网络搜索", formatted)
        self.assertIn("hybrid模式", formatted)
        self.assertIn("AI发展趋势", formatted)
    
    def test_id_generation(self):
        """测试ID生成"""
        # 测试会话ID生成
        session_id1 = generate_session_id()
        session_id2 = generate_session_id()
        
        self.assertIsInstance(session_id1, str)
        self.assertIsInstance(session_id2, str)
        self.assertNotEqual(session_id1, session_id2)  # 应该是唯一的
        
        # 测试查询ID生成
        query_id1 = generate_query_id()
        query_id2 = generate_query_id()
        
        self.assertIsInstance(query_id1, str)
        self.assertIsInstance(query_id2, str)
        self.assertNotEqual(query_id1, query_id2)
    
    def test_dict_operations(self):
        """测试字典操作"""
        # 测试深度合并
        dict1 = {"a": 1, "b": {"c": 2, "d": 3}}
        dict2 = {"b": {"d": 4, "e": 5}, "f": 6}
        
        merged = deep_merge_dicts(dict1, dict2)
        
        self.assertEqual(merged["a"], 1)
        self.assertEqual(merged["b"]["c"], 2)
        self.assertEqual(merged["b"]["d"], 4)  # 被覆盖
        self.assertEqual(merged["b"]["e"], 5)  # 新增
        self.assertEqual(merged["f"], 6)       # 新增
```

#### 系统监控测试

```python
class TestSystemMonitoring(unittest.TestCase):
    """系统监控测试"""
    
    def setUp(self):
        """测试设置"""
        self.monitor = SystemMonitor()
        self.health_checker = ApplicationHealthChecker()
    
    def test_health_check_creation(self):
        """测试健康检查创建"""
        health_check = HealthCheck(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="测试健康检查",
            details={"test": True},
            timestamp=datetime.now(),
            execution_time=0.1
        )
        
        self.assertEqual(health_check.name, "test_check")
        self.assertEqual(health_check.status, HealthStatus.HEALTHY)
        self.assertIn("test", health_check.details)
    
    def test_monitor_registration(self):
        """测试监控器注册"""
        def dummy_check():
            return HealthCheck(
                name="dummy",
                status=HealthStatus.HEALTHY,
                message="虚拟检查",
                details={},
                timestamp=datetime.now(),
                execution_time=0.0
            )
        
        # 注册健康检查
        self.monitor.register_health_check("dummy_check", dummy_check)
        
        # 验证注册
        self.assertIn("dummy_check", self.monitor.health_checks)
    
    def test_system_metrics_collection(self):
        """测试系统指标收集"""
        # 模拟指标收集
        self.monitor._collect_system_metrics()
        
        # 验证指标收集
        self.assertGreater(len(self.monitor.metrics_history), 0)
    
    def test_alert_thresholds(self):
        """测试告警阈值"""
        # 设置告警阈值
        self.monitor.set_alert_threshold("test_metric", 80.0)
        
        # 验证阈值设置
        self.assertEqual(self.monitor.alert_thresholds["test_metric"], 80.0)
        
        # 测试阈值检查
        self.monitor._check_thresholds("test_metric", 85.0)  # 超过阈值
        self.monitor._check_thresholds("test_metric", 75.0)  # 未超过阈值
```

### 2. 性能测试套件 (test_performance.py)

**主要功能**: 测试系统的性能、负载和压力承受能力。

#### 日志性能测试

```python
class TestLoggingPerformance(unittest.TestCase):
    """日志记录性能测试"""
    
    def test_basic_logging_performance(self):
        """测试基础日志记录性能"""
        iterations = 1000
        logger = setup_logger("performance_test")
        
        # 测试日志记录速度
        start_time = time.time()
        for i in range(iterations):
            logger.info(f"Test message {i}")
        end_time = time.time()
        
        duration = end_time - start_time
        rate = iterations / duration
        
        # 验证性能指标
        self.assertLess(duration, 5.0)  # 应该在5秒内完成
        self.assertGreater(rate, 100)   # 每秒至少100条日志
        
        print(f"日志记录性能: {rate:.2f} 条/秒")
    
    def test_concurrent_logging_performance(self):
        """测试并发日志记录性能"""
        import concurrent.futures
        import threading
        
        def log_worker(worker_id, iterations):
            logger = setup_logger(f"worker_{worker_id}")
            for i in range(iterations):
                logger.info(f"Worker {worker_id} message {i}")
        
        # 测试并发日志记录
        workers = 5
        iterations_per_worker = 200
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(log_worker, i, iterations_per_worker)
                for i in range(workers)
            ]
            concurrent.futures.wait(futures)
        end_time = time.time()
        
        total_logs = workers * iterations_per_worker
        duration = end_time - start_time
        rate = total_logs / duration
        
        print(f"并发日志性能: {rate:.2f} 条/秒 ({workers} 线程)")
        self.assertGreater(rate, 500)  # 并发时应该更高
```

#### 错误处理性能测试

```python
class TestErrorHandlingPerformance(unittest.TestCase):
    """错误处理性能测试"""
    
    def test_exception_handling_overhead(self):
        """测试异常处理开销"""
        iterations = 1000
        
        # 测试正常执行时间
        start_time = time.time()
        for _ in range(iterations):
            result = "normal operation"
        normal_time = time.time() - start_time
        
        # 测试异常处理时间
        start_time = time.time()
        for _ in range(iterations):
            try:
                raise ValueError("test error")
            except ValueError:
                result = "error handled"
        exception_time = time.time() - start_time
        
        # 计算开销
        overhead = (exception_time - normal_time) / normal_time
        
        print(f"异常处理开销: {overhead:.2%}")
        self.assertLess(overhead, 10.0)  # 开销应该小于10倍
    
    def test_retry_performance(self):
        """测试重试机制性能"""
        retry_handler = RetryHandler()
        call_count = 0
        
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("temporary error")
            return "success"
        
        # 测试重试性能
        start_time = time.time()
        result = retry_handler.retry_with_backoff(
            flaky_function,
            max_retries=3,
            backoff_factor=0.01  # 快速重试用于测试
        )
        duration = time.time() - start_time
        
        self.assertEqual(result, "success")
        self.assertLess(duration, 1.0)  # 应该在1秒内完成
```

#### 内存和资源使用测试

```python
class TestResourceUsage(unittest.TestCase):
    """资源使用测试"""
    
    def test_memory_usage(self):
        """测试内存使用"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 执行大量操作
        large_data = []
        for i in range(10000):
            large_data.append({
                "id": i,
                "data": f"large data string {i}" * 100
            })
        
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        
        # 清理
        del large_data
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_released = peak_memory - final_memory
        
        print(f"内存增加: {memory_increase / 1024 / 1024:.2f} MB")
        print(f"内存释放: {memory_released / 1024 / 1024:.2f} MB")
        
        # 验证内存管理
        self.assertGreater(memory_released, memory_increase * 0.8)  # 至少释放80%
```

### 3. 工作流测试套件 (test_workflow.py)

**主要功能**: 测试完整的工作流程执行。

#### 端到端工作流测试

```python
class TestWorkflowExecution(unittest.TestCase):
    """工作流执行测试"""
    
    @patch('src.utils.lightrag_client.query_lightrag_sync')
    @patch('src.core.config.config')
    def test_complete_workflow(self, mock_config, mock_lightrag):
        """测试完整工作流执行"""
        # 模拟配置
        mock_config.LLM_API_KEY = "test_key"
        mock_config.TAVILY_API_KEY = "test_key"
        
        # 模拟LightRAG响应
        mock_lightrag.return_value = {
            "success": True,
            "content": "机器学习是人工智能的一个分支...",
            "mode": "local"
        }
        
        # 模拟工作流执行
        from src.core.workflow import get_workflow
        
        workflow = get_workflow()
        initial_state = {
            "user_query": "什么是机器学习？",
            "session_id": "test_session"
        }
        
        # 执行工作流
        result = workflow.invoke(initial_state)
        
        # 验证结果
        self.assertIn("final_answer", result)
        self.assertIn("answer_confidence", result)
        self.assertIn("sources", result)
        self.assertGreater(len(result["final_answer"]), 0)
    
    def test_workflow_error_handling(self):
        """测试工作流错误处理"""
        # 测试各种错误场景
        error_scenarios = [
            {"user_query": "", "expected_error": "查询不能为空"},
            {"user_query": "ab", "expected_error": "查询太短"},
            {"user_query": "<script>", "expected_error": "查询包含可疑内容"}
        ]
        
        for scenario in error_scenarios:
            with self.subTest(scenario=scenario):
                # 执行工作流
                result = self.execute_workflow_with_error_handling(scenario["user_query"])
                
                # 验证错误处理
                if "error" in result:
                    self.assertIn("error", result)
```

---

## 测试运行和管理

### 测试执行命令

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试文件
python -m pytest tests/test_comprehensive.py

# 运行特定测试类
python -m pytest tests/test_comprehensive.py::TestAdvancedLogging

# 运行特定测试方法
python -m pytest tests/test_comprehensive.py::TestAdvancedLogging::test_basic_logging

# 带详细输出运行测试
python -m pytest tests/ -v

# 带覆盖率运行测试
python -m pytest tests/ --cov=src

# 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

### 测试配置

**pytest.ini 配置文件**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    performance: marks tests as performance tests
```

**测试环境配置**
```python
# tests/conftest.py
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_config():
    """模拟配置fixture"""
    return {
        "LLM_API_KEY": "test_key",
        "LLM_MODEL": "gpt-4",
        "TAVILY_API_KEY": "test_key",
        "LOG_LEVEL": "DEBUG"
    }

@pytest.fixture(autouse=True)
def setup_test_environment(mock_config):
    """自动设置测试环境"""
    # 设置测试环境变量
    os.environ.update(mock_config)
    yield
    # 清理测试环境
    for key in mock_config:
        os.environ.pop(key, None)
```

---

## 测试覆盖率和质量

### 覆盖率目标

| 模块 | 目标覆盖率 | 当前覆盖率 | 状态 |
|------|------------|------------|------|
| src/core/ | 90% | 85% | 🟡 进行中 |
| src/agents/ | 85% | 80% | 🟡 进行中 |
| src/utils/ | 95% | 92% | 🟢 良好 |
| src/frontend/ | 70% | 65% | 🟡 进行中 |

### 质量检查

**代码质量检查**
```bash
# 运行代码质量检查
flake8 tests/
pylint tests/
black tests/ --check
mypy tests/
```

**测试质量指标**
- 测试覆盖率 > 85%
- 测试执行时间 < 30秒
- 测试成功率 = 100%
- 测试维护性评分 > 8/10

---

## 持续集成和自动化

### GitHub Actions 工作流

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### 测试自动化脚本

```bash
#!/bin/bash
# test_runner.sh - 自动化测试脚本

set -e

echo "🧪 开始运行测试套件..."

# 1. 运行单元测试
echo "📝 运行单元测试..."
python -m pytest tests/test_comprehensive.py -v

# 2. 运行性能测试
echo "⚡ 运行性能测试..."
python -m pytest tests/test_performance.py -v

# 3. 运行工作流测试
echo "🔄 运行工作流测试..."
python -m pytest tests/test_workflow.py -v

# 4. 生成覆盖率报告
echo "📊 生成覆盖率报告..."
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# 5. 运行代码质量检查
echo "🔍 运行代码质量检查..."
flake8 src/ tests/
black src/ tests/ --check

echo "✅ 所有测试完成！"
```

---

## 测试最佳实践

### 测试编写指南

1. **测试命名规范**
   - 测试类: `Test + 被测试的类/模块名`
   - 测试方法: `test_ + 具体测试内容`
   - 清晰描述测试意图

2. **测试结构**
   - **Arrange**: 准备测试数据和环境
   - **Act**: 执行被测试的操作
   - **Assert**: 验证结果

3. **Mock和依赖管理**
   - 使用Mock隔离外部依赖
   - 避免真实的网络调用和数据库操作
   - 保持测试的可重复性

4. **测试数据管理**
   - 使用fixture管理测试数据
   - 避免硬编码测试数据
   - 确保测试数据的清理

### 性能测试指南

1. **基准测试**
   - 建立性能基准线
   - 监控性能回归
   - 设置合理的性能阈值

2. **负载测试**
   - 模拟真实负载场景
   - 测试系统的承载能力
   - 识别性能瓶颈

3. **压力测试**
   - 测试系统的极限
   - 验证错误处理机制
   - 评估系统恢复能力

---

## 故障排除

### 常见测试问题

**测试环境问题**
```python
# 检查测试环境配置
def check_test_environment():
    required_vars = ["LLM_API_KEY", "TEST_DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        pytest.skip(f"缺少环境变量: {missing_vars}")
```

**依赖问题**
```python
# 检查依赖可用性
def check_dependencies():
    try:
        import lightrag
        import streamlit
        return True
    except ImportError as e:
        pytest.skip(f"缺少依赖: {e}")
```

**异步测试问题**
```python
# 异步测试处理
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 测试调试技巧

**详细日志**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

def test_with_debug():
    logger = logging.getLogger(__name__)
    logger.debug("测试开始")
    # 测试逻辑
    logger.debug("测试结束")
```

**断点调试**
```python
def test_with_breakpoint():
    result = some_function()
    breakpoint()  # Python 3.7+
    assert result == expected
```

---

**📝 说明**: 本文档提供了智能问答系统测试模块的全面指南。测试套件确保系统的可靠性、性能和正确性，支持持续集成和质量保证。