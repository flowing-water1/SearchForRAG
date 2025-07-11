"""
系统监控和健康检查模块
提供全面的系统监控、健康检查和故障诊断功能
"""

import time
import traceback
import psutil
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
import queue

from .advanced_logging import setup_logger, audit_log, record_metric
from .error_handling import SystemError, handle_errors, ErrorCategory, ErrorSeverity
from ..core.config import config


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    execution_time: float
    

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.logger = setup_logger(f"{__name__}.system_monitor")
        self.health_checks = {}
        self.metrics_history = {}
        self.alert_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
            "response_time": 5.0,
            "error_rate": 0.1
        }
        self.monitoring_enabled = True
        self.monitoring_thread = None
        self.metrics_queue = queue.Queue()
        
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """注册健康检查"""
        self.health_checks[name] = check_func
        self.logger.info(f"注册健康检查: {name}")
    
    def start_monitoring(self, interval: int = 60):
        """启动系统监控"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.logger.warning("监控线程已在运行")
            return
        
        self.monitoring_enabled = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logger.info(f"系统监控已启动，间隔: {interval}秒")
        audit_log("system_monitoring_started", details={"interval": interval})
    
    def stop_monitoring(self):
        """停止系统监控"""
        self.monitoring_enabled = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("系统监控已停止")
        audit_log("system_monitoring_stopped")
    
    def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self.monitoring_enabled:
            try:
                # 收集系统指标
                self._collect_system_metrics()
                
                # 执行健康检查
                self._run_health_checks()
                
                # 处理指标队列
                self._process_metrics_queue()
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self._record_metric("cpu_usage", cpu_percent)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            self._record_metric("memory_usage", memory.percent)
            self._record_metric("memory_available", memory.available)
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self._record_metric("disk_usage", disk_percent)
            
            # 网络统计
            net_io = psutil.net_io_counters()
            self._record_metric("network_bytes_sent", net_io.bytes_sent)
            self._record_metric("network_bytes_recv", net_io.bytes_recv)
            
            # 进程信息
            process = psutil.Process()
            self._record_metric("process_cpu_percent", process.cpu_percent())
            self._record_metric("process_memory_percent", process.memory_percent())
            
        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
    
    def _run_health_checks(self):
        """运行健康检查"""
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = check_func()
                execution_time = time.time() - start_time
                
                if isinstance(result, HealthCheck):
                    health_check = result
                else:
                    # 兼容简单返回值
                    health_check = HealthCheck(
                        name=name,
                        status=HealthStatus.HEALTHY if result else HealthStatus.ERROR,
                        message=str(result) if isinstance(result, str) else "健康检查完成",
                        details={},
                        timestamp=datetime.now(),
                        execution_time=execution_time
                    )
                
                self._record_health_check(health_check)
                
            except Exception as e:
                self.logger.error(f"健康检查失败 {name}: {e}")
                health_check = HealthCheck(
                    name=name,
                    status=HealthStatus.ERROR,
                    message=f"健康检查异常: {str(e)}",
                    details={"error": str(e), "traceback": traceback.format_exc()},
                    timestamp=datetime.now(),
                    execution_time=0.0
                )
                self._record_health_check(health_check)
    
    def _record_health_check(self, health_check: HealthCheck):
        """记录健康检查结果"""
        # 记录到指标历史
        if health_check.name not in self.metrics_history:
            self.metrics_history[health_check.name] = []
        
        self.metrics_history[health_check.name].append({
            "timestamp": health_check.timestamp,
            "status": health_check.status.value,
            "message": health_check.message,
            "execution_time": health_check.execution_time
        })
        
        # 记录指标
        record_metric(
            f"health_check_{health_check.name}",
            1 if health_check.status == HealthStatus.HEALTHY else 0,
            status=health_check.status.value
        )
        
        # 检查是否需要告警
        if health_check.status in [HealthStatus.ERROR, HealthStatus.CRITICAL]:
            self._trigger_alert(health_check)
    
    def _record_metric(self, name: str, value: float):
        """记录指标"""
        timestamp = datetime.now()
        
        if name not in self.metrics_history:
            self.metrics_history[name] = []
        
        self.metrics_history[name].append({
            "timestamp": timestamp,
            "value": value
        })
        
        # 保持历史记录在合理范围内
        if len(self.metrics_history[name]) > 1000:
            self.metrics_history[name] = self.metrics_history[name][-1000:]
        
        # 记录到全局指标系统
        record_metric(name, value)
        
        # 检查阈值
        self._check_thresholds(name, value)
    
    def _check_thresholds(self, metric_name: str, value: float):
        """检查指标阈值"""
        if metric_name in self.alert_thresholds:
            threshold = self.alert_thresholds[metric_name]
            
            if value > threshold:
                self.logger.warning(f"指标 {metric_name} 超过阈值: {value} > {threshold}")
                
                # 触发告警
                alert_info = {
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "timestamp": datetime.now().isoformat()
                }
                
                audit_log("metric_threshold_exceeded", details=alert_info)
    
    def _trigger_alert(self, health_check: HealthCheck):
        """触发告警"""
        alert_info = {
            "check_name": health_check.name,
            "status": health_check.status.value,
            "message": health_check.message,
            "timestamp": health_check.timestamp.isoformat(),
            "details": health_check.details
        }
        
        self.logger.error(f"健康检查告警: {health_check.name} - {health_check.message}")
        audit_log("health_check_alert", details=alert_info)
    
    def _process_metrics_queue(self):
        """处理指标队列"""
        while not self.metrics_queue.empty():
            try:
                metric = self.metrics_queue.get_nowait()
                self._record_metric(metric["name"], metric["value"])
            except queue.Empty:
                break
            except Exception as e:
                self.logger.error(f"处理指标队列错误: {e}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        health_summary = {
            "overall_status": HealthStatus.HEALTHY.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "metrics": {}
        }
        
        # 汇总健康检查结果
        for name in self.health_checks.keys():
            if name in self.metrics_history:
                recent_checks = self.metrics_history[name][-5:]  # 最近5次检查
                if recent_checks:
                    latest_check = recent_checks[-1]
                    health_summary["checks"][name] = latest_check
                    
                    # 更新整体状态
                    if latest_check["status"] == HealthStatus.CRITICAL.value:
                        health_summary["overall_status"] = HealthStatus.CRITICAL.value
                    elif latest_check["status"] == HealthStatus.ERROR.value and health_summary["overall_status"] != HealthStatus.CRITICAL.value:
                        health_summary["overall_status"] = HealthStatus.ERROR.value
                    elif latest_check["status"] == HealthStatus.WARNING.value and health_summary["overall_status"] == HealthStatus.HEALTHY.value:
                        health_summary["overall_status"] = HealthStatus.WARNING.value
        
        # 汇总系统指标
        for metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
            if metric_name in self.metrics_history:
                recent_metrics = self.metrics_history[metric_name][-5:]
                if recent_metrics:
                    latest_metric = recent_metrics[-1]
                    health_summary["metrics"][metric_name] = latest_metric["value"]
        
        return health_summary
    
    def get_metrics_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取指标历史"""
        if metric_name not in self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            metric for metric in self.metrics_history[metric_name]
            if metric["timestamp"] >= cutoff_time
        ]
    
    def set_alert_threshold(self, metric_name: str, threshold: float):
        """设置告警阈值"""
        self.alert_thresholds[metric_name] = threshold
        self.logger.info(f"设置告警阈值: {metric_name} = {threshold}")
    
    def add_metric(self, name: str, value: float):
        """添加指标到队列"""
        self.metrics_queue.put({"name": name, "value": value})


class ApplicationHealthChecker:
    """应用程序健康检查器"""
    
    def __init__(self):
        self.logger = setup_logger(f"{__name__}.app_health_checker")
        
    def check_database_connection(self) -> HealthCheck:
        """检查数据库连接"""
        start_time = time.time()
        
        try:
            # 检查 PostgreSQL 连接
            postgres_status = self._check_postgres_connection()
            
            # 检查 Neo4j 连接
            neo4j_status = self._check_neo4j_connection()
            
            execution_time = time.time() - start_time
            
            if postgres_status and neo4j_status:
                return HealthCheck(
                    name="database_connection",
                    status=HealthStatus.HEALTHY,
                    message="数据库连接正常",
                    details={"postgres": postgres_status, "neo4j": neo4j_status},
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
            else:
                return HealthCheck(
                    name="database_connection",
                    status=HealthStatus.ERROR,
                    message="数据库连接失败",
                    details={"postgres": postgres_status, "neo4j": neo4j_status},
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return HealthCheck(
                name="database_connection",
                status=HealthStatus.ERROR,
                message=f"数据库连接检查失败: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                execution_time=execution_time
            )
    
    def _check_postgres_connection(self) -> bool:
        """检查 PostgreSQL 连接"""
        try:
            import psycopg2
            conn = psycopg2.connect(config.postgres_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"PostgreSQL 连接检查失败: {e}")
            return False
    
    def _check_neo4j_connection(self) -> bool:
        """检查 Neo4j 连接"""
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(**config.neo4j_config)
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            return True
        except Exception as e:
            self.logger.error(f"Neo4j 连接检查失败: {e}")
            return False
    
    def check_api_endpoints(self) -> HealthCheck:
        """检查 API 端点"""
        start_time = time.time()
        
        try:
            # 检查 OpenAI API
            openai_status = self._check_openai_api()
            
            # 检查 Tavily API
            tavily_status = self._check_tavily_api()
            
            execution_time = time.time() - start_time
            
            if openai_status and tavily_status:
                return HealthCheck(
                    name="api_endpoints",
                    status=HealthStatus.HEALTHY,
                    message="API 端点正常",
                    details={"openai": openai_status, "tavily": tavily_status},
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
            else:
                return HealthCheck(
                    name="api_endpoints",
                    status=HealthStatus.WARNING,
                    message="部分 API 端点不可用",
                    details={"openai": openai_status, "tavily": tavily_status},
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return HealthCheck(
                name="api_endpoints",
                status=HealthStatus.ERROR,
                message=f"API 端点检查失败: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                execution_time=execution_time
            )
    
    def _check_openai_api(self) -> bool:
        """检查 OpenAI API"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            
            # 简单的 API 调用测试
            response = client.models.list()
            return bool(response)
            
        except Exception as e:
            self.logger.error(f"OpenAI API 检查失败: {e}")
            return False
    
    def _check_tavily_api(self) -> bool:
        """检查 Tavily API"""
        try:
            from tavily import TavilySearchAPIWrapper
            
            if not config.TAVILY_API_KEY:
                return False
            
            tavily_search = TavilySearchAPIWrapper(
                tavily_api_key=config.TAVILY_API_KEY
            )
            
            # 简单的搜索测试
            results = tavily_search.search("test", max_results=1)
            return bool(results)
            
        except Exception as e:
            self.logger.error(f"Tavily API 检查失败: {e}")
            return False
    
    def check_lightrag_status(self) -> HealthCheck:
        """检查 LightRAG 状态"""
        start_time = time.time()
        
        try:
            from ..utils.lightrag_client import lightrag_client
            
            status = lightrag_client.get_status()
            execution_time = time.time() - start_time
            
            if status.get("initialized", False):
                return HealthCheck(
                    name="lightrag_status",
                    status=HealthStatus.HEALTHY,
                    message="LightRAG 状态正常",
                    details=status,
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
            else:
                return HealthCheck(
                    name="lightrag_status",
                    status=HealthStatus.WARNING,
                    message="LightRAG 未完全初始化",
                    details=status,
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return HealthCheck(
                name="lightrag_status",
                status=HealthStatus.ERROR,
                message=f"LightRAG 状态检查失败: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                execution_time=execution_time
            )
    
    def check_workflow_status(self) -> HealthCheck:
        """检查工作流状态"""
        start_time = time.time()
        
        try:
            from ..core.workflow import get_workflow
            
            workflow = get_workflow()
            workflow_info = workflow.get_workflow_info()
            performance_stats = workflow.get_performance_stats()
            
            execution_time = time.time() - start_time
            
            if workflow_info.get("initialized", False):
                return HealthCheck(
                    name="workflow_status",
                    status=HealthStatus.HEALTHY,
                    message="工作流状态正常",
                    details={
                        "workflow_info": workflow_info,
                        "performance_stats": performance_stats
                    },
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
            else:
                return HealthCheck(
                    name="workflow_status",
                    status=HealthStatus.ERROR,
                    message="工作流未初始化",
                    details={"workflow_info": workflow_info},
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return HealthCheck(
                name="workflow_status",
                status=HealthStatus.ERROR,
                message=f"工作流状态检查失败: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                execution_time=execution_time
            )


# 全局监控器实例
_system_monitor = SystemMonitor()
_app_health_checker = ApplicationHealthChecker()


def get_system_monitor() -> SystemMonitor:
    """获取系统监控器"""
    return _system_monitor


def get_app_health_checker() -> ApplicationHealthChecker:
    """获取应用健康检查器"""
    return _app_health_checker


def initialize_monitoring():
    """初始化监控系统"""
    monitor = get_system_monitor()
    checker = get_app_health_checker()
    
    # 注册健康检查
    monitor.register_health_check("database_connection", checker.check_database_connection)
    monitor.register_health_check("api_endpoints", checker.check_api_endpoints)
    monitor.register_health_check("lightrag_status", checker.check_lightrag_status)
    monitor.register_health_check("workflow_status", checker.check_workflow_status)
    
    # 启动监控
    monitor.start_monitoring(interval=300)  # 5分钟间隔
    
    logger = setup_logger(__name__)
    logger.info("监控系统已初始化")
    audit_log("monitoring_system_initialized")


def shutdown_monitoring():
    """关闭监控系统"""
    monitor = get_system_monitor()
    monitor.stop_monitoring()
    
    logger = setup_logger(__name__)
    logger.info("监控系统已关闭")
    audit_log("monitoring_system_shutdown")


def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态"""
    return get_system_monitor().get_system_health()


def get_detailed_health_report() -> Dict[str, Any]:
    """获取详细健康报告"""
    monitor = get_system_monitor()
    
    return {
        "system_health": monitor.get_system_health(),
        "cpu_history": monitor.get_metrics_history("cpu_usage", hours=1),
        "memory_history": monitor.get_metrics_history("memory_usage", hours=1),
        "disk_history": monitor.get_metrics_history("disk_usage", hours=1),
        "alert_thresholds": monitor.alert_thresholds,
        "monitoring_enabled": monitor.monitoring_enabled
    }


# 导出
__all__ = [
    "HealthStatus",
    "HealthCheck",
    "SystemMonitor",
    "ApplicationHealthChecker",
    "get_system_monitor",
    "get_app_health_checker",
    "initialize_monitoring",
    "shutdown_monitoring",
    "get_system_health",
    "get_detailed_health_report"
]