"""
性能测试套件
测试系统的性能、负载和压力承受能力
使用 HKUDS/LightRAG 框架进行测试
"""

import unittest
import time
import concurrent.futures
import statistics
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.advanced_logging import setup_logger, record_metric, get_performance_logger
from src.utils.error_handling import ErrorHandler, RetryHandler
from src.utils.helpers import validate_query, safe_json_parse, calculate_confidence


class TestLoggingPerformance(unittest.TestCase):
    """日志记录性能测试"""
    
    def setUp(self):
        """测试设置"""
        self.logger = setup_logger("performance_test")
        self.perf_logger = get_performance_logger("performance_test")
    
    def test_basic_logging_performance(self):
        """测试基础日志记录性能"""
        iterations = 1000
        
        # 测试日志记录速度
        start_time = time.time()
        for i in range(iterations):
            self.logger.info(f"Test message {i}")
        end_time = time.time()
        
        duration = end_time - start_time
        rate = iterations / duration
        
        # 验证性能指标
        self.assertLess(duration, 5.0)  # 应该在5秒内完成
        self.assertGreater(rate, 100)   # 每秒至少100条日志
        
        print(f"日志记录性能: {rate:.2f} 条/秒")
    
    def test_performance_logging_overhead(self):
        """测试性能日志记录开销"""
        iterations = 100
        
        # 测试性能日志记录开销
        start_time = time.time()
        for i in range(iterations):
            self.perf_logger.start_operation(f"test_operation_{i}")
            time.sleep(0.001)  # 模拟短操作
            self.perf_logger.end_operation(success=True)
        end_time = time.time()
        
        duration = end_time - start_time
        overhead = duration - (iterations * 0.001)  # 减去模拟操作时间
        
        # 验证开销
        self.assertLess(overhead, 1.0)  # 开销应该小于1秒
        print(f"性能日志记录开销: {overhead:.3f}秒")
    
    def test_concurrent_logging_performance(self):
        """测试并发日志记录性能"""
        iterations = 500
        threads = 4
        
        def log_messages(thread_id):
            logger = setup_logger(f"thread_{thread_id}")
            for i in range(iterations):
                logger.info(f"Thread {thread_id} message {i}")
        
        # 测试并发日志记录
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(log_messages, i) for i in range(threads)]
            concurrent.futures.wait(futures)
        end_time = time.time()
        
        duration = end_time - start_time
        total_messages = iterations * threads
        rate = total_messages / duration
        
        # 验证并发性能
        self.assertLess(duration, 10.0)  # 应该在10秒内完成
        self.assertGreater(rate, 50)     # 每秒至少50条日志
        
        print(f"并发日志记录性能: {rate:.2f} 条/秒")
    
    def test_metric_recording_performance(self):
        """测试指标记录性能"""
        iterations = 1000
        
        # 测试指标记录速度
        start_time = time.time()
        for i in range(iterations):
            record_metric(f"test_metric_{i % 10}", float(i))
        end_time = time.time()
        
        duration = end_time - start_time
        rate = iterations / duration
        
        # 验证性能
        self.assertLess(duration, 2.0)   # 应该在2秒内完成
        self.assertGreater(rate, 200)    # 每秒至少200个指标
        
        print(f"指标记录性能: {rate:.2f} 个/秒")


class TestErrorHandlingPerformance(unittest.TestCase):
    """错误处理性能测试"""
    
    def setUp(self):
        """测试设置"""
        self.error_handler = ErrorHandler("performance_test")
        self.retry_handler = RetryHandler(max_retries=3, backoff_factor=0.1)
    
    def test_error_handling_performance(self):
        """测试错误处理性能"""
        iterations = 100
        
        # 测试错误处理速度
        start_time = time.time()
        for i in range(iterations):
            try:
                raise ValueError(f"Test error {i}")
            except Exception as e:
                self.error_handler.handle_error(e, {"iteration": i})
        end_time = time.time()
        
        duration = end_time - start_time
        rate = iterations / duration
        
        # 验证性能
        self.assertLess(duration, 5.0)   # 应该在5秒内完成
        self.assertGreater(rate, 10)     # 每秒至少10个错误处理
        
        print(f"错误处理性能: {rate:.2f} 个/秒")
    
    def test_retry_handler_performance(self):
        """测试重试处理器性能"""
        iterations = 50
        
        def failing_function():
            if failing_function.call_count < 2:
                failing_function.call_count += 1
                raise ValueError("Temporary failure")
            failing_function.call_count = 0
            return "Success"
        
        failing_function.call_count = 0
        
        # 测试重试处理性能
        start_time = time.time()
        for i in range(iterations):
            try:
                result = self.retry_handler.retry_with_backoff(failing_function)
            except Exception:
                pass
        end_time = time.time()
        
        duration = end_time - start_time
        rate = iterations / duration
        
        # 验证性能
        self.assertLess(duration, 10.0)  # 应该在10秒内完成
        self.assertGreater(rate, 2)      # 每秒至少2个重试处理
        
        print(f"重试处理性能: {rate:.2f} 个/秒")


class TestUtilityPerformance(unittest.TestCase):
    """工具函数性能测试"""
    
    def test_query_validation_performance(self):
        """测试查询验证性能"""
        iterations = 1000
        test_queries = [
            "这是一个正常的查询",
            "What is machine learning?",
            "机器学习的发展历史和未来趋势",
            "如何使用Python进行数据分析",
            "人工智能在医疗领域的应用"
        ]
        
        # 测试查询验证速度
        start_time = time.time()
        for i in range(iterations):
            query = test_queries[i % len(test_queries)]
            valid, error = validate_query(query)
        end_time = time.time()
        
        duration = end_time - start_time
        rate = iterations / duration
        
        # 验证性能
        self.assertLess(duration, 1.0)    # 应该在1秒内完成
        self.assertGreater(rate, 500)     # 每秒至少500个验证
        
        print(f"查询验证性能: {rate:.2f} 个/秒")
    
    def test_json_parsing_performance(self):
        """测试JSON解析性能"""
        iterations = 1000
        test_jsons = [
            '{"key": "value"}',
            '{"name": "test", "value": 123}',
            '{"array": [1, 2, 3], "nested": {"key": "value"}}',
            '{"complex": {"deep": {"nested": "value"}}}',
            'invalid json'
        ]
        
        # 测试JSON解析速度
        start_time = time.time()
        for i in range(iterations):
            json_str = test_jsons[i % len(test_jsons)]
            result = safe_json_parse(json_str)
        end_time = time.time()
        
        duration = end_time - start_time
        rate = iterations / duration
        
        # 验证性能
        self.assertLess(duration, 1.0)    # 应该在1秒内完成
        self.assertGreater(rate, 500)     # 每秒至少500个解析
        
        print(f"JSON解析性能: {rate:.2f} 个/秒")
    
    def test_confidence_calculation_performance(self):
        """测试置信度计算性能"""
        iterations = 10000
        
        # 测试置信度计算速度
        start_time = time.time()
        for i in range(iterations):
            confidence = calculate_confidence(
                0.8, 500, 0.9, 0.7
            )
        end_time = time.time()
        
        duration = end_time - start_time
        rate = iterations / duration
        
        # 验证性能
        self.assertLess(duration, 1.0)     # 应该在1秒内完成
        self.assertGreater(rate, 5000)     # 每秒至少5000个计算
        
        print(f"置信度计算性能: {rate:.2f} 个/秒")


class TestConcurrencyPerformance(unittest.TestCase):
    """并发性能测试"""
    
    def test_concurrent_error_handling(self):
        """测试并发错误处理"""
        iterations = 50
        threads = 4
        
        def handle_errors(thread_id):
            handler = ErrorHandler(f"thread_{thread_id}")
            for i in range(iterations):
                try:
                    raise ValueError(f"Error from thread {thread_id}, iteration {i}")
                except Exception as e:
                    handler.handle_error(e, {"thread": thread_id, "iteration": i})
        
        # 测试并发错误处理
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(handle_errors, i) for i in range(threads)]
            concurrent.futures.wait(futures)
        end_time = time.time()
        
        duration = end_time - start_time
        total_errors = iterations * threads
        rate = total_errors / duration
        
        # 验证并发性能
        self.assertLess(duration, 10.0)   # 应该在10秒内完成
        self.assertGreater(rate, 5)       # 每秒至少5个错误处理
        
        print(f"并发错误处理性能: {rate:.2f} 个/秒")
    
    def test_concurrent_utility_operations(self):
        """测试并发工具操作"""
        iterations = 100
        threads = 4
        
        def utility_operations(thread_id):
            for i in range(iterations):
                # 查询验证
                validate_query(f"Thread {thread_id} query {i}")
                
                # JSON解析
                safe_json_parse(f'{{"thread": {thread_id}, "iteration": {i}}}')
                
                # 置信度计算
                calculate_confidence(0.8, 500, 0.9, 0.7)
        
        # 测试并发工具操作
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(utility_operations, i) for i in range(threads)]
            concurrent.futures.wait(futures)
        end_time = time.time()
        
        duration = end_time - start_time
        total_operations = iterations * threads * 3  # 3 operations per iteration
        rate = total_operations / duration
        
        # 验证并发性能
        self.assertLess(duration, 5.0)    # 应该在5秒内完成
        self.assertGreater(rate, 100)     # 每秒至少100个操作
        
        print(f"并发工具操作性能: {rate:.2f} 个/秒")


class TestMemoryPerformance(unittest.TestCase):
    """内存性能测试"""
    
    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量操作
        logger = setup_logger("memory_test")
        error_handler = ErrorHandler("memory_test")
        
        for i in range(1000):
            logger.info(f"Memory test message {i}")
            
            try:
                raise ValueError(f"Test error {i}")
            except Exception as e:
                error_handler.handle_error(e, {"iteration": i})
            
            # 每100次迭代检查内存
            if i % 100 == 0:
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                # 内存增长不应该超过50MB
                self.assertLess(memory_growth, 50)
        
        # 最终内存检查
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        print(f"内存使用: 初始 {initial_memory:.2f}MB, 最终 {final_memory:.2f}MB, 增长 {total_growth:.2f}MB")
        
        # 总内存增长不应该超过100MB
        self.assertLess(total_growth, 100)


class TestThroughputPerformance(unittest.TestCase):
    """吞吐量性能测试"""
    
    def test_system_throughput(self):
        """测试系统吞吐量"""
        iterations = 100
        
        # 模拟完整的处理流程
        logger = setup_logger("throughput_test")
        error_handler = ErrorHandler("throughput_test")
        
        processing_times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            # 模拟查询验证
            query = f"测试查询 {i}"
            valid, error = validate_query(query)
            
            if valid:
                # 模拟JSON处理
                json_data = safe_json_parse(f'{{"query": "{query}", "iteration": {i}}}')
                
                # 模拟置信度计算
                confidence = calculate_confidence(0.8, 500, 0.9, 0.7)
                
                # 记录日志
                logger.info(f"处理查询 {i}: 置信度 {confidence:.2f}")
            else:
                # 处理错误
                error_handler.handle_error(ValueError(error), {"query": query})
            
            processing_time = time.time() - start_time
            processing_times.append(processing_time)
        
        # 计算性能指标
        avg_time = statistics.mean(processing_times)
        throughput = 1.0 / avg_time
        
        # 验证吞吐量
        self.assertLess(avg_time, 0.1)     # 平均处理时间应该小于100ms
        self.assertGreater(throughput, 10)  # 每秒至少处理10个请求
        
        print(f"系统吞吐量: {throughput:.2f} 请求/秒")
        print(f"平均处理时间: {avg_time*1000:.2f}ms")


class TestStressTest(unittest.TestCase):
    """压力测试"""
    
    def test_high_load_stability(self):
        """测试高负载稳定性"""
        iterations = 1000
        threads = 8
        
        def stress_worker(worker_id):
            logger = setup_logger(f"stress_worker_{worker_id}")
            error_handler = ErrorHandler(f"stress_worker_{worker_id}")
            
            for i in range(iterations):
                try:
                    # 模拟复杂操作
                    validate_query(f"Worker {worker_id} query {i}")
                    safe_json_parse(f'{{"worker": {worker_id}, "iteration": {i}}}')
                    calculate_confidence(0.8, 500, 0.9, 0.7)
                    
                    logger.info(f"Worker {worker_id} processed item {i}")
                    
                    # 偶尔抛出错误
                    if i % 50 == 0:
                        raise ValueError(f"Stress test error from worker {worker_id}")
                        
                except Exception as e:
                    error_handler.handle_error(e, {"worker": worker_id, "iteration": i})
        
        # 执行压力测试
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(stress_worker, i) for i in range(threads)]
            concurrent.futures.wait(futures)
        end_time = time.time()
        
        duration = end_time - start_time
        total_operations = iterations * threads
        rate = total_operations / duration
        
        # 验证压力测试结果
        self.assertLess(duration, 60.0)    # 应该在60秒内完成
        self.assertGreater(rate, 50)       # 每秒至少50个操作
        
        print(f"压力测试性能: {rate:.2f} 操作/秒")
        print(f"总耗时: {duration:.2f}秒")


def run_performance_tests():
    """运行性能测试"""
    print("🚀 开始性能测试")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestLoggingPerformance,
        TestErrorHandlingPerformance,
        TestUtilityPerformance,
        TestConcurrencyPerformance,
        TestMemoryPerformance,
        TestThroughputPerformance,
        TestStressTest
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 所有性能测试通过！")
    else:
        print("❌ 部分性能测试失败")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    run_performance_tests()