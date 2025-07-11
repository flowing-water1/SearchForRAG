# 核心模块技术文档

> 返回 [项目概览文档](../../TECHNICAL_REFERENCE.md)

## 📍 相关文档导航
- **[工作流节点文档](../agents/README.md)** - 查看如何使用这些核心组件构建工作流节点
- **[工具模块文档](../utils/README.md)** - 查看核心模块使用的辅助工具和客户端
- **[项目根目录](../../TECHNICAL_REFERENCE.md)** - 返回项目完整概览

---

## 模块概述

核心模块 (src/core/) 是智能问答系统的基础架构，包含配置管理、状态定义和工作流编排的核心实现。所有其他模块都依赖于核心模块提供的基础功能。

### 模块结构
```
src/core/
├── __init__.py               # 模块初始化
├── config.py                 # 统一配置管理
├── state.py                  # LangGraph状态定义
├── workflow.py               # 基础工作流实现
└── enhanced_workflow.py      # 增强工作流实现
```

---

## 文件详解

### 1. 配置管理 (config.py)

**主要功能**: 统一管理系统所有配置参数，支持多层LLM配置架构。

#### 核心类: Config

```python
class Config:
    """统一配置管理类，支持多层LLM配置"""
```

#### 配置分类

**基础系统配置**
- `SYSTEM_NAME`: "智能问答系统"
- `VERSION`: "1.0.0" 
- `DEBUG`: 调试模式开关
- `LOG_LEVEL`: 日志级别 (INFO)

**多层LLM配置**
- `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL`: 主LLM配置
- `KG_LLM_*`: 知识图谱专用LLM配置 (默认gpt-4o)
- `VECTOR_LLM_*`: 向量处理专用LLM配置 (默认gpt-4o-mini)
- `EMBEDDING_*`: 嵌入模型配置

**数据库配置**
- `POSTGRES_*`: PostgreSQL连接参数
- `NEO4J_*`: Neo4j图数据库连接参数

**LightRAG配置**
- `RAG_STORAGE_DIR`: 存储目录路径
- `CHUNK_SIZE`/`VECTOR_CHUNK_SIZE`/`KG_CHUNK_SIZE`: 分块配置
- `CONFIDENCE_THRESHOLD`: 质量评估阈值

**网络搜索配置**
- `TAVILY_API_KEY`: Tavily搜索API密钥
- `WEB_SEARCH_TIMEOUT`: 搜索超时时间

#### 关键方法

##### 数据库连接
```python
@property
def postgres_url(self) -> str:
    """构建PostgreSQL连接URL"""
    return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode={self.POSTGRES_SSL_MODE}"

@property  
def neo4j_config(self) -> dict:
    """获取Neo4j连接配置字典"""
    return {
        "uri": self.NEO4J_URI,
        "auth": (self.NEO4J_USERNAME, self.NEO4J_PASSWORD),
        "database": self.NEO4J_DATABASE
    }
```

##### LLM配置
```python
@property
def kg_llm_config(self) -> dict:
    """获取知识图谱LLM配置"""
    return {
        "api_key": self.KG_LLM_API_KEY,
        "base_url": self.KG_LLM_BASE_URL,
        "model": self.KG_LLM_MODEL,
        "temperature": self.KG_LLM_TEMPERATURE,
        "max_tokens": self.KG_LLM_MAX_TOKENS
    }

@property
def vector_llm_config(self) -> dict:
    """获取向量LLM配置"""
    return {
        "api_key": self.VECTOR_LLM_API_KEY,
        "base_url": self.VECTOR_LLM_BASE_URL,
        "model": self.VECTOR_LLM_MODEL,
        "temperature": self.VECTOR_LLM_TEMPERATURE,
        "max_tokens": self.VECTOR_LLM_MAX_TOKENS
    }
```

##### 配置验证
```python
def validate_config(self) -> tuple[bool, list[str]]:
    """验证配置完整性
    
    Returns:
        tuple: (是否有效, 错误列表)
    """
```

验证项目包括:
- 基础LLM配置完整性
- 知识图谱LLM配置有效性
- 向量LLM配置正确性
- 数据库连接参数
- 分块配置合理性

#### 使用示例

```python
from src.core.config import config

# 检查配置有效性
is_valid, errors = config.validate_config()
if not is_valid:
    print("配置错误:", errors)

# 获取数据库连接
postgres_url = config.postgres_url
neo4j_config = config.neo4j_config

# 获取LLM配置
kg_config = config.kg_llm_config
vector_config = config.vector_llm_config
```

---

### 2. 状态定义 (state.py)

**主要功能**: 定义LangGraph工作流中的状态结构和数据类。

#### 核心类: AgentState

```python
class AgentState(TypedDict):
    """智能问答系统的全局状态定义"""
```

#### 状态字段分类

**输入字段**
- `user_query: str` - 用户原始查询
- `processed_query: str` - 处理后的查询
- `session_id: str` - 会话标识符

**查询分析结果**
- `query_type: Literal["FACTUAL", "RELATIONAL", "ANALYTICAL"]` - 查询类型分类
- `lightrag_mode: Literal["local", "global", "hybrid"]` - 检索模式选择
- `key_entities: List[str]` - 提取的关键实体
- `mode_reasoning: str` - 模式选择的推理过程

**检索结果**
- `lightrag_results: Dict[str, Any]` - LightRAG检索的原始结果
- `retrieval_score: float` - 检索质量评分 (0.0-1.0)
- `retrieval_success: bool` - 检索是否成功执行

**质量评估**
- `confidence_score: float` - 综合置信度评分
- `confidence_breakdown: Dict[str, float]` - 置信度详细分解
- `need_web_search: bool` - 是否需要网络搜索补充
- `confidence_threshold: float` - 动态置信度阈值
- `assessment_reason: str` - 质量评估的详细原因

**网络搜索**
- `web_results: Optional[List[Dict[str, Any]]]` - 网络搜索结果列表
- `web_search_summary: Optional[str]` - 搜索结果摘要

**最终输出**
- `final_answer: str` - 最终生成的答案
- `sources: List[Dict[str, Any]]` - 信息来源的详细列表
- `context_used: int` - 使用的上下文信息数量
- `lightrag_mode_used: str` - 实际使用的检索模式
- `answer_confidence: float` - 答案的置信度评分

#### 辅助数据类

**QueryAnalysisResult**
```python
@dataclass
class QueryAnalysisResult:
    """查询分析结果的结构化表示"""
    query_type: str
    lightrag_mode: str
    key_entities: List[str]
    processed_query: str
    reasoning: str
```

**LightRAGResult**
```python
@dataclass
class LightRAGResult:
    """LightRAG检索结果的标准化格式"""
    content: str
    mode: str
    success: bool
    query: str
    source: str
    error: Optional[str] = None
```

**QualityAssessment**
```python
@dataclass
class QualityAssessment:
    """质量评估结果的详细信息"""
    confidence_score: float
    confidence_breakdown: Dict[str, float]
    need_web_search: bool
    threshold: float
    reason: str
```

**WebSearchResult**
```python
@dataclass
class WebSearchResult:
    """网络搜索结果的标准格式"""
    title: str
    content: str
    url: str
    score: float
    source_type: str = "web_search"
```

**SourceInfo**
```python
@dataclass
class SourceInfo:
    """信息来源的统一表示"""
    type: str  # "lightrag_knowledge", "web_search", "knowledge_graph"
    content: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    confidence: Optional[float] = None
    mode: Optional[str] = None
    query: Optional[str] = None
```

#### 使用示例

```python
from src.core.state import AgentState, QueryAnalysisResult

# 初始化状态
initial_state: AgentState = {
    "user_query": "什么是机器学习？",
    "session_id": "session_123",
    "query_type": "",
    "lightrag_mode": "",
    # ... 其他字段
}

# 创建查询分析结果
analysis_result = QueryAnalysisResult(
    query_type="FACTUAL",
    lightrag_mode="local",
    key_entities=["机器学习"],
    processed_query="机器学习的定义和基本概念",
    reasoning="这是一个事实性查询，适合使用local模式"
)
```

---

### 3. 基础工作流 (workflow.py)

**主要功能**: 实现基于LangGraph的智能问答工作流编排。

#### 核心类: IntelligentQAWorkflow

```python
class IntelligentQAWorkflow:
    """智能问答工作流管理器
    
    基于 LangGraph 实现的 Agentic RAG 工作流，支持：
    - 智能查询分析和路由
    - 多模式 LightRAG 检索
    - 质量评估和决策
    - 网络搜索补充
    - 答案生成和整合
    """
```

#### 工作流架构

**节点组成**
1. **query_analysis** - 查询分析节点
2. **lightrag_retrieval** - LightRAG检索节点
3. **quality_assessment** - 质量评估节点
4. **web_search** - 网络搜索节点 (条件性)
5. **answer_generation** - 答案生成节点

**路由逻辑**
```
用户查询 → 查询分析 → LightRAG检索 → 质量评估 → [条件路由] → 答案生成
                                        ↓
                                    网络搜索 → 答案生成
```

#### 主要方法

**初始化方法**
```python
def __init__(self):
    """初始化工作流
    - 创建LangGraph状态图
    - 添加所有节点
    - 配置节点连接和条件路由
    - 编译工作流图
    """

def _initialize_workflow(self):
    """初始化工作流图"""

def _add_nodes(self):
    """添加所有工作流节点"""

def _add_edges(self):
    """配置节点间的连接和条件路由"""

def _compile_workflow(self):
    """编译工作流为可执行图"""
```

**条件路由方法**
```python
def _should_use_web_search(self, state: AgentState) -> str:
    """决定是否需要网络搜索
    
    Args:
        state: 当前工作流状态
        
    Returns:
        str: 下一个节点名称 ("web_search" 或 "answer_generation")
        
    决策逻辑:
    - 检查 need_web_search 标志
    - 评估 confidence_score 水平
    - 返回适当的路由决策
    """
```

**执行方法**
```python
async def arun(self, 
               user_query: str, 
               config_override: Optional[Dict[str, Any]] = None,
               thread_id: Optional[str] = None) -> Dict[str, Any]:
    """异步运行工作流
    
    Args:
        user_query: 用户查询文本
        config_override: 可选的配置覆盖
        thread_id: 会话线程ID
        
    Returns:
        Dict: 工作流执行结果
        
    功能:
    - 初始化状态
    - 执行完整工作流
    - 处理错误和异常
    - 返回结构化结果
    """
```

#### 使用示例

```python
from src.core.workflow import IntelligentQAWorkflow
import asyncio

# 创建工作流实例
workflow = IntelligentQAWorkflow()

# 异步执行查询
async def run_query():
    result = await workflow.arun("什么是深度学习？")
    return result

# 运行查询
result = asyncio.run(run_query())
print(f"答案: {result['final_answer']}")
print(f"置信度: {result['answer_confidence']}")
```

---

### 4. 增强工作流 (enhanced_workflow.py)

**主要功能**: 在基础工作流基础上集成综合错误处理、性能监控和审计日志。

#### 核心类: EnhancedIntelligentQAWorkflow

```python
class EnhancedIntelligentQAWorkflow:
    """增强版智能问答工作流管理器
    
    集成了全面的错误处理、性能监控和日志记录功能
    """
```

#### 增强功能

**错误处理**
- 装饰器模式的错误处理
- 自动重试机制
- 熔断器保护
- 详细错误分类和记录

**性能监控**
- 节点执行时间统计
- 工作流整体性能分析
- 实时性能指标收集
- 性能瓶颈识别

**审计日志**
- 节点执行审计
- 用户操作记录
- 系统状态变更追踪
- 合规性支持

#### 扩展属性

```python
def __init__(self):
    # 基础属性
    self.workflow_id = str(uuid.uuid4())
    
    # 性能统计
    self.performance_stats = {
        "total_queries": 0,
        "successful_queries": 0,
        "failed_queries": 0,
        "average_response_time": 0.0,
        "node_performance": {}
    }
```

#### 节点包装机制

```python
def _wrap_node(self, node_func, node_name: str):
    """包装节点函数以增加错误处理和性能监控
    
    功能:
    - 自动性能计时
    - 错误捕获和处理
    - 审计日志记录
    - 指标数据收集
    """
```

#### 性能管理方法

```python
def _update_node_performance(self, node_name: str, execution_time: float, success: bool):
    """更新节点性能统计"""

def get_performance_stats(self) -> dict:
    """获取详细的性能统计信息"""

def get_workflow_info(self) -> dict:
    """获取工作流基本信息和状态"""
```

#### 使用示例

```python
from src.core.enhanced_workflow import EnhancedIntelligentQAWorkflow

# 创建增强版工作流
enhanced_workflow = EnhancedIntelligentQAWorkflow()

# 执行查询并获取详细统计
result = await enhanced_workflow.arun("分析AI的发展趋势")

# 查看性能统计
stats = enhanced_workflow.get_performance_stats()
print(f"总查询数: {stats['total_queries']}")
print(f"成功率: {stats['successful_queries'] / stats['total_queries'] * 100:.1f}%")
print(f"平均响应时间: {stats['average_response_time']:.2f}s")

# 查看工作流信息
info = enhanced_workflow.get_workflow_info()
print(f"工作流ID: {info['workflow_id']}")
print(f"初始化状态: {info['is_initialized']}")
```

---

## 模块依赖关系

### 内部依赖
```
config.py (基础)
    ↓
state.py (依赖config进行验证)
    ↓
workflow.py (依赖config和state)
    ↓
enhanced_workflow.py (依赖所有core模块)
```

### 外部依赖

**配置模块依赖**
- `python-dotenv`: 环境变量加载
- `pathlib`: 路径处理

**状态模块依赖**
- `typing_extensions`: 类型定义
- `dataclasses`: 数据类支持

**工作流模块依赖**
- `langgraph`: 工作流编排框架
- `asyncio`: 异步处理支持

**增强工作流依赖**
- `uuid`: 唯一标识符生成
- `time`: 性能计时
- 所有utils模块的高级功能

### 被依赖模块
- `src/agents/` - 所有工作流节点
- `src/utils/` - 工具模块
- `main_app.py` - 主应用
- `streamlit_app.py` - 简化应用

---

## 配置最佳实践

### 环境变量配置
```env
# .env 文件示例

# 基础LLM配置
LLM_API_KEY=your_openai_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4

# 知识图谱LLM (更强模型)
KG_LLM_MODEL=gpt-4o
KG_LLM_TEMPERATURE=0.1
KG_LLM_MAX_TOKENS=4000

# 向量LLM (高效模型)
VECTOR_LLM_MODEL=gpt-4o-mini
VECTOR_LLM_TEMPERATURE=0.0
VECTOR_LLM_MAX_TOKENS=2000

# 嵌入配置
EMBEDDING_MODEL=text-embedding-v1
EMBEDDING_DIM=1536

# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_DB=searchforrag
POSTGRES_USER=searchforrag
POSTGRES_PASSWORD=your_secure_password

NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your_neo4j_password

# 搜索配置
TAVILY_API_KEY=your_tavily_api_key

# LightRAG配置
RAG_WORKING_DIR=./rag_storage
CONFIDENCE_THRESHOLD=0.7
```

### 配置验证示例
```python
from src.core.config import config

def validate_system_config():
    """验证系统配置的完整性"""
    is_valid, errors = config.validate_config()
    
    if not is_valid:
        print("❌ 配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ 配置验证通过")
    return True

# 运行验证
if validate_system_config():
    print("系统可以正常启动")
else:
    print("请检查配置文件")
```

---

## 故障排除

### 常见问题

**1. 配置加载失败**
```python
# 检查 .env 文件是否存在
import os
from pathlib import Path

env_file = Path(".env")
if not env_file.exists():
    print("❌ .env 文件不存在")
else:
    print("✅ .env 文件存在")
```

**2. LLM配置错误**
```python
# 验证LLM配置
from src.core.config import config

def test_llm_configs():
    configs = [
        ("主LLM", config.LLM_API_KEY, config.LLM_MODEL),
        ("知识图谱LLM", config.KG_LLM_API_KEY, config.KG_LLM_MODEL),
        ("向量LLM", config.VECTOR_LLM_API_KEY, config.VECTOR_LLM_MODEL)
    ]
    
    for name, api_key, model in configs:
        if not api_key:
            print(f"❌ {name} API密钥未设置")
        else:
            print(f"✅ {name} 配置正常 (模型: {model})")

test_llm_configs()
```

**3. 工作流初始化失败**
```python
# 诊断工作流问题
from src.core.enhanced_workflow import EnhancedIntelligentQAWorkflow

try:
    workflow = EnhancedIntelligentQAWorkflow()
    print("✅ 工作流初始化成功")
    
    # 获取工作流信息
    info = workflow.get_workflow_info()
    print(f"工作流ID: {info['workflow_id']}")
    print(f"节点数量: {info['node_count']}")
    
except Exception as e:
    print(f"❌ 工作流初始化失败: {e}")
    import traceback
    traceback.print_exc()
```

### 调试技巧

**启用调试模式**
```env
# .env 文件中添加
DEBUG=true
LOG_LEVEL=DEBUG
```

**查看详细日志**
```python
from src.core.config import config
import logging

# 设置详细日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug("这是调试信息")
logger.info("这是信息日志")
```

---

## 扩展指南

### 添加新配置项

1. **在config.py中添加配置**
```python
# 新增配置项
NEW_FEATURE_ENABLED = os.getenv("NEW_FEATURE_ENABLED", "false").lower() == "true"
NEW_FEATURE_PARAM = os.getenv("NEW_FEATURE_PARAM", "default_value")
```

2. **更新验证方法**
```python
def validate_config(self) -> tuple[bool, list[str]]:
    errors = []
    
    # 添加新配置验证
    if self.NEW_FEATURE_ENABLED and not self.NEW_FEATURE_PARAM:
        errors.append("NEW_FEATURE_PARAM is required when NEW_FEATURE_ENABLED is true")
    
    return len(errors) == 0, errors
```

### 扩展状态定义

1. **添加新状态字段**
```python
class AgentState(TypedDict):
    # 现有字段...
    
    # 新增字段
    new_feature_data: Optional[Dict[str, Any]]
    new_metric: float
```

2. **创建对应数据类**
```python
@dataclass
class NewFeatureResult:
    """新功能结果的数据结构"""
    status: str
    data: Dict[str, Any]
    timestamp: float
```

### 添加工作流节点

1. **创建节点函数**
```python
def new_feature_node(state: AgentState) -> Dict[str, Any]:
    """新功能节点
    
    Args:
        state: 当前状态
        
    Returns:
        Dict: 更新的状态字段
    """
    # 节点逻辑实现
    return {
        "new_feature_data": {"status": "processed"},
        "new_metric": 0.95
    }
```

2. **在工作流中注册**
```python
def _add_nodes(self):
    """添加工作流节点"""
    # 现有节点...
    
    # 添加新节点
    self.graph.add_node("new_feature", new_feature_node)

def _add_edges(self):
    """配置节点连接"""
    # 现有连接...
    
    # 添加新节点连接
    self.graph.add_edge("existing_node", "new_feature")
    self.graph.add_edge("new_feature", "next_node")
```

---

## 性能优化

### 配置优化
- 合理设置LLM的`max_tokens`参数
- 根据任务特点选择适当的`temperature`值
- 优化数据库连接池大小

### 工作流优化
- 使用异步方法提高并发性能
- 实现智能缓存减少重复计算
- 优化节点间数据传递效率

### 监控和调优
- 使用增强工作流的性能统计功能
- 定期分析节点执行时间
- 根据统计数据调整系统参数

---

**📝 说明**: 本文档详细介绍了核心模块的所有组件。如需了解其他模块，请查看对应的技术文档。