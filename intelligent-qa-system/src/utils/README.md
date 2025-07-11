# 工具模块技术文档

> 返回 [项目概览文档](../../TECHNICAL_REFERENCE.md)

## 📍 相关文档导航
- **[核心模块文档](../core/README.md)** - 查看工具模块支持的核心配置和状态管理
- **[工作流节点文档](../agents/README.md)** - 查看工具模块在各节点中的使用
- **[项目根目录](../../TECHNICAL_REFERENCE.md)** - 返回项目完整概览

## 🔗 工具与系统集成
- [配置系统](../core/README.md#1-配置管理系统-configpy) - 工具模块的配置来源
- [AgentState接口](../core/README.md#2-状态定义-statepy) - 工具模块处理的数据结构
- [查询分析节点](../agents/README.md#1-查询分析节点-query_analysispy) - 使用simple_logger和error_handling
- [检索节点](../agents/README.md#2-lightrag检索节点-lightrag_retrievalpy) - 核心依赖lightrag_client
- [质量评估节点](../agents/README.md#3-质量评估节点-quality_assessmentpy) - 使用helpers模块进行评估
- [答案生成节点](../agents/README.md#5-答案生成节点-answer_generationpy) - 使用advanced_logging和helpers

---

## 模块概述

工具模块 (src/utils/) 提供了智能问答系统的核心支撑功能，包括客户端封装、日志系统、错误处理、系统监控等重要组件。这些工具确保系统的可靠性、可观测性和可维护性。

### 模块结构
```
src/utils/
├── __init__.py                 # 模块初始化
├── lightrag_client.py          # LightRAG客户端封装
├── kg_llm_client.py           # 知识图谱LLM客户端
├── document_processor.py      # 文档处理器
├── simple_logger.py           # 简单日志系统
├── advanced_logging.py        # 高级日志系统
├── error_handling.py          # 错误处理框架
├── system_monitoring.py       # 系统监控
└── helpers.py                 # 通用辅助函数
```

### 依赖关系层次
```
simple_logger.py (基础层)
    ↓
advanced_logging.py + error_handling.py (中间层)
    ↓  
system_monitoring.py + helpers.py (应用层)
    ↓
lightrag_client.py + document_processor.py (业务层)
```

---

## 文件详解

### 1. 简单日志系统 (simple_logger.py)

**主要功能**: 提供轻量级、零依赖的日志记录功能，避免循环导入问题。

#### 核心函数: get_simple_logger

```python
def get_simple_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    创建简单的日志记录器，避免循环导入
    
    特点:
    - 零外部依赖
    - 防重复添加处理器
    - 标准格式化输出
    - 防止日志传播
    """
```

#### 实现特点

**避免重复处理器**
```python
# 检查是否已有处理器
if logger.handlers:
    return logger  # 直接返回已配置的日志器
```

**标准化格式**
```python
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

**防止日志传播**
```python
logger.propagate = False  # 避免重复输出到根日志器
```

#### 使用场景
- LightRAG客户端初始化
- 各个agents节点的基础日志
- 避免循环导入的模块间通信
- 系统启动阶段的日志记录

#### 使用示例

```python
from src.utils.simple_logger import get_simple_logger

# 创建日志器
logger = get_simple_logger(__name__)

# 基础日志记录
logger.info("LightRAG客户端初始化")
logger.warning("配置项缺失，使用默认值")
logger.error("连接数据库失败")
```

---

### 2. 高级日志系统 (advanced_logging.py)

**主要功能**: 提供结构化JSON日志、性能监控、错误追踪和审计日志功能。

#### 核心类: StructuredFormatter

```python
class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器
    
    输出JSON格式日志，包含:
    - 基础日志信息 (时间戳、级别、消息等)
    - 业务字段 (用户ID、会话ID、查询ID)
    - 性能指标 (处理时间、操作指标)
    - 异常信息 (异常类型、消息、堆栈跟踪)
    """
```

**JSON日志结构**
```json
{
  "timestamp": "2024-01-20T10:30:45.123456",
  "level": "INFO",
  "logger": "src.agents.query_analysis",
  "message": "查询分析完成",
  "module": "query_analysis",
  "function": "query_analysis_node",
  "line": 67,
  "user_id": "user123",
  "session_id": "session456",
  "query_id": "query789",
  "processing_time": 0.156,
  "metrics": {
    "operation": "query_analysis",
    "tokens_used": 150,
    "confidence": 0.85
  }
}
```

#### 核心类: PerformanceLogger

```python
class PerformanceLogger:
    """性能监控日志器
    
    功能:
    - 操作计时和性能指标收集
    - 自动记录开始/结束时间
    - 成功/失败状态追踪
    - 详细性能数据记录
    """
```

**性能监控使用**
```python
perf_logger = get_performance_logger(__name__)

# 开始操作计时
perf_logger.start_operation("lightrag_retrieval", mode="hybrid", query_length=45)

# 执行业务逻辑
result = perform_retrieval()

# 结束操作计时
perf_logger.end_operation(
    success=True, 
    results_count=5, 
    confidence_score=0.85
)
```

#### 核心类: ErrorTracker

```python
class ErrorTracker:
    """错误追踪器
    
    功能:
    - 错误记录和分类统计
    - 异常堆栈跟踪
    - 错误趋势分析
    - 自动告警机制
    """
```

#### 装饰器函数

**性能日志装饰器**
```python
@log_performance("node_execution")
def query_analysis_node(state: AgentState) -> Dict[str, Any]:
    """自动记录节点执行性能"""
    # 节点业务逻辑
    return result  # 自动记录执行时间和成功状态
```

**错误日志装饰器**
```python
@log_errors("lightrag_query")
def query_lightrag_sync(query: str, mode: str) -> dict:
    """自动捕获和记录查询错误"""
    # 查询逻辑，异常会被自动捕获和记录
    return result
```

#### 监控和审计函数

**指标记录**
```python
def record_metric(name: str, value: float, **tags) -> None:
    """记录业务指标
    
    示例:
    - record_metric("query_latency", 0.156, query_type="FACTUAL")
    - record_metric("retrieval_score", 0.85, mode="hybrid")
    - record_metric("confidence_score", 0.72, has_web_search=True)
    """
```

**审计日志**
```python
def audit_log(action: str, user: str = "system", details: dict = None) -> None:
    """记录审计事件
    
    示例:
    - audit_log("user_query", user="user123", details={"query": "AI trends"})
    - audit_log("workflow_execution", details={"duration": 2.5, "nodes": 5})
    - audit_log("config_change", user="admin", details={"field": "threshold"})
    """
```

#### 上下文管理器

```python
@contextmanager
def performance_context(operation_name: str, logger_name: str):
    """性能监控上下文管理器"""
    perf_logger = get_performance_logger(logger_name)
    perf_logger.start_operation(operation_name)
    
    try:
        yield perf_logger
        perf_logger.end_operation(success=True)
    except Exception as e:
        perf_logger.end_operation(success=False, error=str(e))
        raise

# 使用示例
with performance_context("database_query", __name__) as perf:
    result = execute_database_query()
    perf.add_metric("rows_returned", len(result))
```

---

### 3. 错误处理框架 (error_handling.py)

**主要功能**: 提供综合错误处理机制，包括自定义异常、重试机制和熔断器。

#### 错误分类体系

**错误严重程度**
```python
class ErrorSeverity(Enum):
    LOW = "low"         # 轻微错误，不影响主要功能
    MEDIUM = "medium"   # 中等错误，部分功能受影响
    HIGH = "high"       # 严重错误，主要功能不可用
    CRITICAL = "critical"  # 致命错误，系统无法正常运行
```

**错误类别**
```python
class ErrorCategory(Enum):
    SYSTEM = "system"              # 系统内部错误
    NETWORK = "network"            # 网络连接错误
    DATABASE = "database"          # 数据库相关错误
    API = "api"                   # 外部API调用错误
    VALIDATION = "validation"      # 数据验证错误
    AUTHENTICATION = "authentication"  # 身份验证错误
    PERMISSION = "permission"      # 权限相关错误
    CONFIGURATION = "configuration"  # 配置错误
    EXTERNAL_SERVICE = "external_service"  # 外部服务错误
    USER_INPUT = "user_input"      # 用户输入错误
```

#### 核心异常类: SystemError

```python
class SystemError(Exception):
    """系统基础异常类
    
    提供统一的错误接口:
    - 错误消息和用户友好提示
    - 错误分类和严重程度
    - 恢复建议和详细信息
    - 时间戳和错误编码
    """
    
    def __init__(self, 
                 message: str,
                 error_code: str = None,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 details: Dict[str, Any] = None,
                 recovery_suggestions: List[str] = None,
                 user_message: str = None):
```

**具体异常类型**
```python
class ConfigurationError(SystemError):
    """配置错误 - 系统配置不正确或缺失"""

class DatabaseError(SystemError):
    """数据库错误 - 数据库连接或查询失败"""
    
class NetworkError(SystemError):
    """网络错误 - 网络连接或通信失败"""
    
class APIError(SystemError):
    """API错误 - 外部API调用失败"""
    
class ValidationError(SystemError):
    """验证错误 - 输入数据验证失败"""
```

#### 错误处理器: ErrorHandler

```python
class ErrorHandler:
    """统一错误处理器
    
    功能:
    - 错误分类和标准化处理
    - 生成用户友好的错误消息
    - 记录详细的错误日志
    - 执行错误恢复策略
    """
    
    def handle_error(self, error: Exception, context: dict = None) -> dict:
        """处理错误并返回标准化结果"""
```

#### 重试机制: RetryHandler

```python
class RetryHandler:
    """智能重试处理器
    
    功能:
    - 指数退避算法
    - 最大重试次数控制
    - 特定异常类型的重试策略
    - 重试状态记录
    """
    
    def retry_with_backoff(self, 
                          func: callable, 
                          max_retries: int = 3,
                          backoff_factor: float = 1.0,
                          *args, **kwargs):
        """执行带退避的重试逻辑"""
```

#### 熔断器: CircuitBreaker

```python
class CircuitBreaker:
    """熔断器模式实现
    
    状态:
    - CLOSED: 正常状态，允许请求通过
    - OPEN: 熔断状态，直接拒绝请求
    - HALF_OPEN: 半开状态，允许少量请求测试
    
    功能:
    - 故障检测和自动熔断
    - 自动恢复和状态转换
    - 失败率和超时控制
    """
```

#### 装饰器使用

**基础错误处理**
```python
@handle_errors(reraise=False, return_on_error={"error": "操作失败"})
def risky_operation():
    """可能失败的操作，自动处理错误"""
    # 业务逻辑
    pass
```

**重试装饰器**
```python
@retry_on_failure(max_retries=3, backoff_factor=2.0)
def unreliable_api_call():
    """不稳定的API调用，自动重试"""
    # API调用逻辑
    pass
```

#### 使用示例

```python
from src.utils.error_handling import (
    SystemError, ConfigurationError, ErrorHandler, 
    RetryHandler, CircuitBreaker
)

# 抛出自定义异常
if not config.LLM_API_KEY:
    raise ConfigurationError(
        "LLM API密钥未配置",
        error_code="CONFIG_MISSING_API_KEY",
        recovery_suggestions=[
            "检查.env文件中的LLM_API_KEY设置",
            "确认API密钥格式正确",
            "验证API密钥是否有效"
        ]
    )

# 使用错误处理器
error_handler = ErrorHandler()
try:
    result = risky_operation()
except Exception as e:
    error_info = error_handler.handle_error(e, context={"operation": "test"})
    print(f"错误处理结果: {error_info}")

# 使用重试处理器
retry_handler = RetryHandler()
result = retry_handler.retry_with_backoff(
    unreliable_function,
    max_retries=3,
    backoff_factor=2.0
)

# 使用熔断器
circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
try:
    result = circuit_breaker.call(external_service_call)
except Exception as e:
    print(f"熔断器保护: {e}")
```

---

### 4. 系统监控 (system_monitoring.py)

**主要功能**: 提供系统健康检查、性能监控和状态报告功能。

#### 健康状态枚举

```python
class HealthStatus(Enum):
    HEALTHY = "healthy"     # 系统正常运行
    WARNING = "warning"     # 存在潜在问题
    ERROR = "error"        # 存在明确错误
    CRITICAL = "critical"  # 严重故障状态
```

#### 核心数据类: HealthCheck

```python
@dataclass
class HealthCheck:
    """健康检查结果的标准化表示
    
    字段:
    - name: 检查项目名称
    - status: 健康状态
    - message: 状态描述信息
    - details: 详细检查数据
    - timestamp: 检查执行时间
    - execution_time: 检查耗时
    """
```

#### 核心类: SystemMonitor

```python
class SystemMonitor:
    """系统监控器
    
    功能:
    - 注册和管理健康检查项
    - 定期执行系统监控
    - 收集和存储性能指标
    - 告警阈值管理
    - 监控数据历史记录
    """
```

**告警阈值配置**
```python
alert_thresholds = {
    "cpu_usage": 80.0,        # CPU使用率告警阈值
    "memory_usage": 85.0,     # 内存使用率告警阈值
    "disk_usage": 90.0,       # 磁盘使用率告警阈值
    "response_time": 5.0,     # 响应时间告警阈值(秒)
    "error_rate": 0.1         # 错误率告警阈值(10%)
}
```

#### 健康检查注册

```python
def register_health_check(self, name: str, check_func: Callable) -> None:
    """注册自定义健康检查
    
    示例:
    monitor.register_health_check("database", check_database_health)
    monitor.register_health_check("api_endpoints", check_api_health)
    monitor.register_health_check("cache_status", check_cache_health)
    """
```

#### 系统指标收集

```python
def _collect_system_metrics(self):
    """收集系统性能指标"""
    
    # CPU使用率
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # 内存使用情况
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    
    # 磁盘使用情况
    disk = psutil.disk_usage('/')
    disk_usage = (disk.used / disk.total) * 100
    
    # 记录指标
    self.add_metric("cpu_usage", cpu_usage)
    self.add_metric("memory_usage", memory_usage)
    self.add_metric("disk_usage", disk_usage)
```

#### 核心类: ApplicationHealthChecker

```python
class ApplicationHealthChecker:
    """应用级健康检查器
    
    检查项目:
    - 数据库连接状态
    - 外部API可用性
    - 缓存系统状态
    - 配置有效性
    - 依赖服务状态
    """
```

**数据库健康检查**
```python
def check_database_connection(self) -> HealthCheck:
    """检查数据库连接健康状态"""
    
    start_time = time.time()
    
    try:
        # PostgreSQL连接检查
        postgres_status = self._check_postgres()
        
        # Neo4j连接检查
        neo4j_status = self._check_neo4j()
        
        # 综合评估
        if postgres_status and neo4j_status:
            status = HealthStatus.HEALTHY
            message = "所有数据库连接正常"
        elif postgres_status or neo4j_status:
            status = HealthStatus.WARNING
            message = "部分数据库连接异常"
        else:
            status = HealthStatus.ERROR
            message = "数据库连接全部失败"
            
        return HealthCheck(
            name="database_connection",
            status=status,
            message=message,
            details={
                "postgres": postgres_status,
                "neo4j": neo4j_status
            },
            timestamp=datetime.now(),
            execution_time=time.time() - start_time
        )
        
    except Exception as e:
        return HealthCheck(
            name="database_connection",
            status=HealthStatus.CRITICAL,
            message=f"数据库健康检查失败: {str(e)}",
            details={"error": str(e)},
            timestamp=datetime.now(),
            execution_time=time.time() - start_time
        )
```

**API端点健康检查**
```python
def check_api_endpoints(self) -> HealthCheck:
    """检查外部API端点可用性"""
    
    api_results = {}
    
    # OpenAI API检查
    api_results["openai"] = self._test_openai_api()
    
    # Tavily API检查
    api_results["tavily"] = self._test_tavily_api()
    
    # 评估整体状态
    healthy_apis = sum(1 for result in api_results.values() if result["status"] == "healthy")
    total_apis = len(api_results)
    
    if healthy_apis == total_apis:
        status = HealthStatus.HEALTHY
        message = "所有API端点正常"
    elif healthy_apis >= total_apis * 0.5:
        status = HealthStatus.WARNING
        message = f"{healthy_apis}/{total_apis} API端点可用"
    else:
        status = HealthStatus.ERROR
        message = f"多数API端点不可用 ({healthy_apis}/{total_apis})"
    
    return HealthCheck(
        name="api_endpoints",
        status=status,
        message=message,
        details=api_results,
        timestamp=datetime.now(),
        execution_time=0.0  # 实际计算执行时间
    )
```

#### 监控启动和控制

```python
# 启动系统监控
monitor = SystemMonitor()

# 注册健康检查
monitor.register_health_check("database", app_health_checker.check_database_connection)
monitor.register_health_check("api_endpoints", app_health_checker.check_api_endpoints)

# 启动定期监控 (每60秒执行一次)
monitor.start_monitoring(interval=60)

# 获取当前系统健康状态
health_report = monitor.get_system_health()
print(f"系统整体状态: {health_report['overall_status']}")
```

#### 使用示例

```python
from src.utils.system_monitoring import (
    SystemMonitor, ApplicationHealthChecker, 
    HealthStatus, get_system_health
)

# 创建监控实例
monitor = SystemMonitor()
health_checker = ApplicationHealthChecker()

# 注册自定义健康检查
def check_custom_service():
    """自定义服务健康检查"""
    try:
        # 执行服务检查逻辑
        result = ping_custom_service()
        
        return HealthCheck(
            name="custom_service",
            status=HealthStatus.HEALTHY if result else HealthStatus.ERROR,
            message="自定义服务状态检查",
            details={"response_time": result.get("latency", 0)},
            timestamp=datetime.now(),
            execution_time=0.1
        )
    except Exception as e:
        return HealthCheck(
            name="custom_service",
            status=HealthStatus.CRITICAL,
            message=f"服务检查失败: {str(e)}",
            details={"error": str(e)},
            timestamp=datetime.now(),
            execution_time=0.0
        )

monitor.register_health_check("custom_service", check_custom_service)

# 获取完整的健康报告
health_report = get_system_health()
print(json.dumps(health_report, indent=2, ensure_ascii=False))
```

---

### 5. LightRAG客户端 (lightrag_client.py)

**主要功能**: 封装LightRAG操作，管理PostgreSQL和Neo4j连接，提供统一的检索接口。

#### 自定义LLM函数

**主LLM函数**
```python
def custom_llm_func(prompt: str, **kwargs) -> str:
    """自定义LLM函数，支持不同的base_url和API key
    
    特点:
    - 使用主LLM配置 (对话和推理)
    - 支持自定义base_url
    - 完整的错误处理
    - 调用日志记录
    """
```

**向量专用LLM函数**
```python
def custom_vector_llm_func(prompt: str, **kwargs) -> str:
    """向量提取专用LLM函数
    
    特点:
    - 使用向量LLM配置 (文档分块和语义理解)
    - 低温度设置保证一致性
    - 优化的token限制
    - 高效处理大量文档
    """
```

**嵌入函数**
```python
def custom_embedding_func(texts: list[str]) -> list[list[float]]:
    """自定义嵌入函数
    
    特点:
    - 支持自定义embedding服务
    - 批量文本向量化
    - 维度参数配置
    - 错误重试机制
    """
```

#### 核心类: LightRAGClient

```python
class LightRAGClient:
    """LightRAG客户端封装类
    
    功能:
    - 管理LightRAG实例生命周期
    - 处理数据库连接和回退机制
    - 提供统一的检索接口
    - 健康检查和状态监控
    - 支持多种LLM配置
    """
```

#### 数据库后端管理

**PostgreSQL支持**
```python
async def _check_pgvector(self) -> bool:
    """检查PostgreSQL pgvector扩展可用性"""
    
    try:
        # 测试连接
        conn = psycopg2.connect(config.postgres_url)
        cursor = conn.cursor()
        
        # 检查pgvector扩展
        cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        has_pgvector = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return has_pgvector
        
    except Exception as e:
        logger.error(f"PostgreSQL检查失败: {e}")
        return False
```

**Neo4j支持**
```python
async def _check_neo4j(self) -> bool:
    """检查Neo4j连接可用性"""
    
    try:
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
        )
        
        # 测试连接
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]
            
        driver.close()
        return test_value == 1
        
    except Exception as e:
        logger.error(f"Neo4j检查失败: {e}")
        return False
```

**自动回退机制**
```python
async def initialize(self) -> bool:
    """初始化LightRAG实例，支持自动回退"""
    
    # 优先尝试完整配置 (PostgreSQL + Neo4j)
    if await self._check_pgvector() and await self._check_neo4j():
        storage_config = {
            "vector_storage": "postgresql",
            "graph_storage": "neo4j"
        }
        logger.info("使用PostgreSQL+Neo4j完整配置")
        
    # 回退到部分配置
    elif await self._check_pgvector():
        storage_config = {
            "vector_storage": "postgresql", 
            "graph_storage": "networkx"  # 内存图存储
        }
        logger.warning("Neo4j不可用，回退到PostgreSQL+NetworkX")
        
    elif await self._check_neo4j():
        storage_config = {
            "vector_storage": "nano_vectordb",  # 文件向量存储
            "graph_storage": "neo4j"
        }
        logger.warning("PostgreSQL不可用，回退到NanoVectorDB+Neo4j")
        
    # 最小化配置
    else:
        storage_config = {
            "vector_storage": "nano_vectordb",
            "graph_storage": "networkx"
        }
        logger.warning("数据库不可用，使用最小化配置")
    
    # 初始化LightRAG实例
    self.rag_instance = LightRAG(
        working_dir=config.RAG_STORAGE_DIR,
        llm_model_func=custom_llm_func,
        vector_llm_model_func=custom_vector_llm_func,
        embedding_func=custom_embedding_func,
        **storage_config
    )
    
    self._initialized = True
    return True
```

#### 查询接口

**统一查询方法**
```python
async def query(self, query: str, mode: str = "hybrid") -> dict:
    """执行LightRAG查询
    
    Args:
        query: 查询文本
        mode: 检索模式 ("local", "global", "hybrid")
        
    Returns:
        dict: 标准化查询结果
        {
            "success": bool,
            "content": str,
            "mode": str,
            "error": str  # 仅在失败时存在
        }
    """
```

**同步查询包装**
```python
def query_lightrag_sync(query: str, mode: str) -> dict:
    """同步LightRAG查询包装函数
    
    用于在同步环境中调用异步LightRAG查询
    适用于agents节点中的直接调用
    """
    
    try:
        # 获取或创建事件循环
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 执行异步查询
        if not lightrag_client._initialized:
            loop.run_until_complete(lightrag_client.initialize())
        
        result = loop.run_until_complete(
            lightrag_client.query(query, mode)
        )
        
        return result
        
    except Exception as e:
        logger.error(f"同步查询失败: {e}")
        return {
            "success": False,
            "content": "",
            "mode": mode,
            "error": str(e)
        }
```

#### 文档管理

**文档插入**
```python
async def insert_document(self, document: str, metadata: dict = None) -> bool:
    """插入文档到知识库
    
    流程:
    1. 文档预处理和清洗
    2. 智能分块处理
    3. 向量化和索引
    4. 知识图谱构建
    5. 存储到指定后端
    """
```

**批量文档处理**
```python
async def insert_documents_batch(self, documents: List[str], batch_size: int = 10) -> dict:
    """批量插入文档
    
    特点:
    - 分批处理避免内存溢出
    - 并行处理提高效率
    - 错误隔离和恢复
    - 进度跟踪和报告
    """
```

#### 健康检查

```python
async def get_health_status(self) -> dict:
    """获取LightRAG客户端健康状态"""
    
    health_info = {
        "initialized": self._initialized,
        "backend_status": {},
        "storage_usage": {},
        "last_query_time": self._last_query_time,
        "total_queries": self._query_count
    }
    
    if self._initialized:
        # 检查存储后端状态
        health_info["backend_status"]["postgresql"] = await self._check_pgvector()
        health_info["backend_status"]["neo4j"] = await self._check_neo4j()
        
        # 获取存储使用情况
        health_info["storage_usage"] = await self._get_storage_usage()
    
    return health_info
```

#### 使用示例

```python
from src.utils.lightrag_client import lightrag_client, query_lightrag_sync
import asyncio

# 异步使用示例
async def async_example():
    # 初始化客户端
    await lightrag_client.initialize()
    
    # 执行查询
    result = await lightrag_client.query("什么是机器学习？", mode="local")
    
    if result["success"]:
        print(f"查询结果: {result['content']}")
    else:
        print(f"查询失败: {result['error']}")
    
    # 插入文档
    success = await lightrag_client.insert_document(
        "机器学习是人工智能的一个分支...",
        metadata={"source": "教科书", "chapter": "第一章"}
    )
    
    print(f"文档插入: {'成功' if success else '失败'}")

# 同步使用示例 (在agents节点中)
def sync_example():
    # 直接同步调用
    result = query_lightrag_sync("深度学习的应用领域", mode="hybrid")
    
    if result["success"]:
        print(f"检索内容: {result['content'][:200]}...")
    else:
        print(f"检索失败: {result['error']}")

# 健康检查示例
async def health_check_example():
    health = await lightrag_client.get_health_status()
    
    print(f"客户端状态: {'已初始化' if health['initialized'] else '未初始化'}")
    print(f"PostgreSQL状态: {health['backend_status']['postgresql']}")
    print(f"Neo4j状态: {health['backend_status']['neo4j']}")
    print(f"总查询次数: {health['total_queries']}")
```

---

### 6. 辅助函数模块 (helpers.py)

**主要功能**: 提供通用的辅助函数，集成高级日志记录和错误处理。

#### 信息源格式化

```python
@handle_errors(reraise=False, return_on_error="")
def format_sources(sources: List[Dict[str, Any]]) -> str:
    """格式化信息来源为用户友好的文本
    
    支持的来源类型:
    - lightrag_knowledge: 本地知识库
    - web_search: 网络搜索结果
    - knowledge_graph: 知识图谱信息
    """
```

**格式化示例输出**
```
1. 本地知识库 (hybrid模式, 置信度: 0.85)
2. 网络搜索: [深度学习发展趋势](https://example.com/article) - example.com (评分: 0.92)
3. 知识图谱 (实体数: 15)
```

#### 置信度计算

```python
def calculate_confidence(
    retrieval_score: float,
    content_length: int, 
    entity_coverage: float,
    mode_effectiveness: float,
    additional_factors: Dict[str, float] = None
) -> float:
    """计算综合置信度分数
    
    算法:
    - 基础权重分配
    - 动态因子调整
    - 归一化处理
    - 边界值控制
    """
```

**置信度计算公式**
```python
# 基础权重
weights = {
    "retrieval_score": 0.35,      # 检索质量最重要
    "content_length": 0.25,       # 内容充实度
    "entity_coverage": 0.20,      # 实体覆盖率
    "mode_effectiveness": 0.20    # 模式有效性
}

# 长度因子计算
length_factor = min(content_length / 800, 1.0)  # 800字符为基准

# 实体覆盖度归一化
entity_factor = max(0, min(entity_coverage, 1.0))

# 综合评分
confidence = (
    retrieval_score * weights["retrieval_score"] +
    length_factor * weights["content_length"] +
    entity_factor * weights["entity_coverage"] +
    mode_effectiveness * weights["mode_effectiveness"]
)
```

#### 数据验证和处理

**查询验证**
```python
def validate_query(query: str) -> tuple[bool, str]:
    """验证用户查询的有效性
    
    验证规则:
    - 长度限制 (5-1000字符)
    - 恶意内容检测
    - 特殊字符过滤
    - 语言检测
    """
    
    if not query or not query.strip():
        return False, "查询不能为空"
    
    query = query.strip()
    
    # 长度检查
    if len(query) < 5:
        return False, "查询太短，至少需要5个字符"
    
    if len(query) > 1000:
        return False, "查询太长，最多1000个字符"
    
    # 恶意内容检测 (简单实现)
    malicious_patterns = [
        r'<script[^>]*>.*?</script>',  # JavaScript注入
        r'javascript:',               # JavaScript协议
        r'on\w+\s*=',                # HTML事件属性
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "查询包含不安全内容"
    
    return True, "查询有效"
```

**JSON安全解析**
```python
def safe_json_parse(json_str: str, default_value=None, logger_name: str = None):
    """安全的JSON解析，带错误处理
    
    特点:
    - 异常安全
    - 默认值处理
    - 日志记录
    - 类型验证
    """
    
    if not json_str:
        return default_value
    
    try:
        result = json.loads(json_str)
        return result
        
    except json.JSONDecodeError as e:
        if logger_name:
            logger = setup_logger(logger_name)
            logger.warning(f"JSON解析失败: {e}")
        
        return default_value
    
    except Exception as e:
        if logger_name:
            logger = setup_logger(logger_name)
            logger.error(f"JSON解析异常: {e}")
        
        return default_value
```

#### 文本处理工具

**智能文本截断**
```python
def smart_truncate(text: str, max_length: int, preserve_words: bool = True) -> str:
    """智能文本截断，保持语义完整性
    
    特点:
    - 保持词汇完整性
    - 智能断句
    - 省略号添加
    - 多语言支持
    """
    
    if len(text) <= max_length:
        return text
    
    # 基础截断
    truncated = text[:max_length]
    
    if preserve_words:
        # 查找最后一个完整词汇边界
        last_space = truncated.rfind(' ')
        last_punct = max(
            truncated.rfind('。'),
            truncated.rfind('！'), 
            truncated.rfind('？'),
            truncated.rfind('.')
        )
        
        # 选择最佳截断点
        if last_punct > last_space and last_punct > max_length * 0.8:
            truncated = truncated[:last_punct + 1]
        elif last_space > max_length * 0.7:
            truncated = truncated[:last_space]
    
    # 添加省略号
    if len(truncated) < len(text):
        truncated += "..."
    
    return truncated
```

#### ID生成和会话管理

**会话ID生成**
```python
def generate_session_id(prefix: str = "sess") -> str:
    """生成唯一会话ID
    
    格式: {prefix}_{timestamp}_{random}
    示例: sess_20240120_103045_a1b2c3
    """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = str(uuid.uuid4())[:6]
    
    return f"{prefix}_{timestamp}_{random_suffix}"

def generate_query_id(session_id: str = None) -> str:
    """生成查询ID"""
    
    if session_id:
        # 基于会话ID生成
        query_suffix = str(uuid.uuid4())[:8]
        return f"{session_id}_q_{query_suffix}"
    else:
        # 独立查询ID
        return f"query_{int(time.time())}_{str(uuid.uuid4())[:8]}"
```

#### 性能工具

**时间格式化**
```python
def format_duration(seconds: float) -> str:
    """将秒数格式化为人类可读的时间"""
    
    if seconds < 0.001:
        return f"{seconds*1000000:.0f}μs"
    elif seconds < 1:
        return f"{seconds*1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes}m {seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours}h {minutes}m {seconds:.0f}s"
```

**文件大小格式化**
```python
def format_file_size(bytes_size: int) -> str:
    """格式化文件大小"""
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    
    return f"{bytes_size:.1f} PB"
```

#### 使用示例

```python
from src.utils.helpers import (
    format_sources, calculate_confidence, validate_query,
    safe_json_parse, smart_truncate, generate_session_id,
    format_duration
)

# 信息源格式化
sources = [
    {"type": "lightrag_knowledge", "mode": "hybrid", "confidence": 0.85},
    {"type": "web_search", "title": "AI趋势", "url": "https://example.com", "score": 0.92}
]
formatted = format_sources(sources)
print(formatted)

# 置信度计算
confidence = calculate_confidence(
    retrieval_score=0.85,
    content_length=1200,
    entity_coverage=0.8,
    mode_effectiveness=0.9
)
print(f"综合置信度: {confidence:.2f}")

# 查询验证
is_valid, message = validate_query("什么是深度学习？")
print(f"查询有效性: {is_valid}, 消息: {message}")

# 会话管理
session_id = generate_session_id("demo")
query_id = generate_query_id(session_id)
print(f"会话ID: {session_id}")
print(f"查询ID: {query_id}")

# 时间格式化
duration = 1.234
print(f"处理时间: {format_duration(duration)}")
```

---

## 模块集成和依赖关系

### 内部依赖层次

**基础层**
- `simple_logger.py` - 提供基础日志功能

**中间层**  
- `advanced_logging.py` - 依赖simple_logger，提供高级日志
- `error_handling.py` - 依赖advanced_logging，提供错误处理

**应用层**
- `system_monitoring.py` - 依赖logging和error_handling
- `helpers.py` - 依赖logging和error_handling

**业务层**
- `lightrag_client.py` - 依赖所有基础工具
- `document_processor.py` - 依赖logging和helpers

### 外部依赖关系

**被依赖模块**
- `src/core/` - 配置和状态定义
- `src/agents/` - 所有工作流节点
- `main_app.py` 和 `streamlit_app.py` - 应用层

**依赖的外部库**
- `lightrag` - RAG框架
- `psycopg2` - PostgreSQL连接
- `neo4j` - Neo4j图数据库驱动
- `psutil` - 系统监控
- `tavily-python` - 网络搜索API

### 模块初始化顺序

1. **simple_logger** - 基础日志系统
2. **advanced_logging** - 高级日志和性能监控
3. **error_handling** - 错误处理框架
4. **system_monitoring** - 系统监控 (可选，后台运行)
5. **lightrag_client** - 业务核心客户端
6. **helpers** - 通用辅助工具

---

## 性能优化建议

### 日志系统优化

**异步日志处理**
```python
# 使用异步日志处理器避免阻塞
handler = logging.handlers.QueueHandler(log_queue)
logger.addHandler(handler)

# 后台线程处理日志队列
log_processor = logging.handlers.QueueListener(
    log_queue, file_handler, console_handler
)
log_processor.start()
```

**日志级别控制**
```python
# 生产环境降低日志级别
if config.DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO
```

### LightRAG客户端优化

**连接池管理**
```python
# 数据库连接池
connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1, maxconn=20,
    dsn=config.postgres_url
)
```

**查询缓存**
```python
# 查询结果缓存 (简单LRU缓存)
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(query_hash: str, mode: str):
    return lightrag_query(query, mode)
```

### 监控系统优化

**批量指标处理**
```python
# 批量提交指标减少I/O
metrics_buffer = []
if len(metrics_buffer) >= batch_size:
    submit_metrics_batch(metrics_buffer)
    metrics_buffer.clear()
```

**采样监控**
```python
# 高频操作采样监控
if random.random() < sampling_rate:
    record_metric("operation_latency", duration)
```

---

## 故障排除指南

### 常见问题诊断

**LightRAG客户端初始化失败**
```python
# 诊断数据库连接问题
async def diagnose_lightrag_issues():
    print("🔍 诊断LightRAG客户端问题...")
    
    # 检查配置
    if not config.LLM_API_KEY:
        print("❌ LLM_API_KEY未配置")
    
    # 检查数据库连接
    postgres_ok = await lightrag_client._check_pgvector()
    neo4j_ok = await lightrag_client._check_neo4j()
    
    print(f"PostgreSQL状态: {'✅' if postgres_ok else '❌'}")
    print(f"Neo4j状态: {'✅' if neo4j_ok else '❌'}")
    
    if not postgres_ok and not neo4j_ok:
        print("⚠️  所有数据库不可用，将使用文件存储")
```

**系统监控异常**
```python
# 检查监控系统状态
def check_monitoring_health():
    try:
        monitor = SystemMonitor()
        health = monitor.get_system_health()
        print(f"监控系统状态: {health['status']}")
        
        for check_name, result in health['checks'].items():
            status_icon = "✅" if result['status'] == 'healthy' else "❌"
            print(f"  {status_icon} {check_name}: {result['message']}")
            
    except Exception as e:
        print(f"❌ 监控系统检查失败: {e}")
```

**日志系统问题**
```python
# 验证日志系统配置
def verify_logging_setup():
    # 测试简单日志
    simple_logger = get_simple_logger("test_simple")
    simple_logger.info("简单日志测试")
    
    # 测试高级日志
    advanced_logger = setup_logger("test_advanced")
    advanced_logger.info("高级日志测试", extra={"test_field": "test_value"})
    
    # 测试性能日志
    perf_logger = get_performance_logger("test_perf")
    perf_logger.start_operation("test_operation")
    time.sleep(0.1)
    perf_logger.end_operation(success=True)
    
    print("✅ 日志系统测试完成")
```

### 调试和开发建议

**启用详细日志**
```python
# 开发环境配置
import logging
logging.basicConfig(level=logging.DEBUG)

# 或者通过环境变量
os.environ["LOG_LEVEL"] = "DEBUG"
```

**性能分析**
```python
# 使用性能上下文分析瓶颈
with performance_context("slow_operation", __name__) as perf:
    # 执行可能很慢的操作
    result = slow_function()
    perf.add_metric("items_processed", len(result))
```

**错误追踪**
```python
# 使用错误追踪装饰器
@log_errors("critical_operation")
def critical_function():
    # 关键业务逻辑
    pass
```

---

**📝 说明**: 本文档详细介绍了utils模块的所有组件。这些工具模块是系统稳定运行的重要保障，提供了完整的可观测性和可维护性支持。