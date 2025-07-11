# 智能问答系统技术参考文档

## 文档版本信息
- **版本**: v1.1.0
- **创建日期**: 2024-01-15
- **最后更新**: 2024-01-20
- **适用范围**: 面向AI助手和开发者的完整技术参考
- **重要更新**: 已切换至正确的HKUDS/LightRAG框架

## 文档目标
本文档旨在为其他AI助手和开发者提供完整的系统技术参考，包含每个文件、类、函数的详细功能描述，以及模块间的依赖关系。类似于Python的`--help`功能，但针对整个项目系统。

**重要说明**: 系统已从错误的LightRAG框架切换至正确的HKUDS/LightRAG框架 (https://github.com/HKUDS/LightRAG)。

---

## 1. 项目架构概览

### 1.1 系统架构图
```
intelligent-qa-system/
├── src/                         # 源代码目录
│   ├── core/                   # 核心配置和工作流
│   │   ├── config.py           # 统一配置管理
│   │   ├── state.py            # LangGraph状态定义
│   │   ├── workflow.py         # 基础工作流编排
│   │   └── enhanced_workflow.py # 增强工作流编排
│   ├── agents/                  # LangGraph工作流节点
│   │   ├── query_analysis.py   # 查询分析节点
│   │   ├── lightrag_retrieval.py # LightRAG检索节点
│   │   ├── quality_assessment.py # 质量评估节点
│   │   ├── web_search.py       # 网络搜索节点
│   │   └── answer_generation.py # 答案生成节点
│   ├── utils/                   # 工具模块
│   │   ├── lightrag_client.py  # LightRAG客户端
│   │   ├── kg_llm_client.py    # 知识图谱LLM客户端
│   │   ├── document_processor.py # 文档处理器
│   │   ├── simple_logger.py    # 简单日志系统
│   │   ├── advanced_logging.py # 高级日志系统
│   │   ├── error_handling.py   # 错误处理
│   │   ├── system_monitoring.py # 系统监控
│   │   └── helpers.py          # 辅助函数
│   └── frontend/               # 前端相关组件
├── tests/                       # 测试套件
├── scripts/                     # 脚本工具
├── docs/                        # 文档目录
├── rag_storage/                 # LightRAG存储目录
├── main_app.py                  # 主Streamlit应用
├── streamlit_app.py             # 简化版Streamlit应用
├── test_workflow.py             # 工作流测试
├── test_error_handling.py       # 错误处理测试
├── requirements.txt             # 依赖列表
├── setup.sh                     # 一键部署脚本
├── start.sh                     # 启动脚本
└── README.md                    # 项目说明
```

### 1.2 技术栈说明
- **LightRAG**: 轻量级RAG框架，支持local/global/hybrid检索模式
- **LangGraph**: 智能工作流编排，状态管理和条件路由
- **PostgreSQL + pgvector**: 向量数据库，存储文档embeddings (支持回退到NanoVectorDB)
- **Neo4j**: 图数据库，存储知识图谱 (支持回退到NetworkX)
- **Streamlit**: Web前端界面 (两个版本：完整版和简化版)
- **OpenAI API**: 支持多种LLM配置
  - 主LLM: 用于对话和推理
  - 知识图谱LLM: 用于实体关系提取
  - 向量LLM: 用于文档分块和语义理解
  - Embedding API: 用于文本向量化
- **Tavily API**: 网络搜索服务

### 1.3 多层LLM配置架构
系统支持灵活的多层LLM配置，可针对不同任务使用不同的模型：
- **主LLM** (LLM_MODEL): 处理用户对话和最终答案生成
- **知识图谱LLM** (KG_LLM_MODEL): 专门处理实体关系提取，默认使用gpt-4o
- **向量LLM** (VECTOR_LLM_MODEL): 处理文档分块和语义理解，默认使用gpt-4o-mini
- **嵌入模型** (EMBEDDING_MODEL): 文本向量化，支持自定义embedding服务

---

## 2. 核心模块详解 (src/core/)

### 2.1 配置管理 (src/core/config.py)

#### 文件功能
统一管理系统所有配置参数，包括数据库连接、API密钥、系统设置等。支持多层LLM配置和灵活的数据库后端选择。

#### 核心类: Config
```python
class Config:
    """
    统一配置管理类
    
    功能:
    - 从环境变量加载配置
    - 提供配置访问接口
    - 管理敏感信息
    - 支持多层LLM配置
    - 配置验证和默认值处理
    """
```

#### 主要配置类别

##### 基础系统配置
- `SYSTEM_NAME`: 系统名称
- `VERSION`: 版本号
- `DEBUG`: 调试模式
- `LOG_LEVEL`: 日志级别

##### 多层LLM配置
- `LLM_API_KEY`: 主LLM API密钥
- `LLM_BASE_URL`: 主LLM基础URL
- `LLM_MODEL`: 主LLM模型名称
- `KG_LLM_API_KEY`: 知识图谱LLM API密钥
- `KG_LLM_BASE_URL`: 知识图谱LLM基础URL
- `KG_LLM_MODEL`: 知识图谱LLM模型名称
- `VECTOR_LLM_API_KEY`: 向量LLM API密钥
- `VECTOR_LLM_BASE_URL`: 向量LLM基础URL
- `VECTOR_LLM_MODEL`: 向量LLM模型名称
- `EMBEDDING_API_KEY`: 嵌入API密钥
- `EMBEDDING_BASE_URL`: 嵌入API基础URL
- `EMBEDDING_MODEL`: 嵌入模型名称

##### 数据库配置
- `POSTGRES_HOST`: PostgreSQL主机地址
- `POSTGRES_PORT`: PostgreSQL端口
- `POSTGRES_DB`: PostgreSQL数据库名
- `POSTGRES_USER`: PostgreSQL用户名
- `POSTGRES_PASSWORD`: PostgreSQL密码
- `NEO4J_URI`: Neo4j连接URI
- `NEO4J_USERNAME`: Neo4j用户名
- `NEO4J_PASSWORD`: Neo4j密码

##### LightRAG配置
- `RAG_STORAGE_DIR`: LightRAG存储目录
- `DOCS_DIR`: 文档目录
- `CHUNK_SIZE`: 基础分块大小
- `VECTOR_CHUNK_SIZE`: 向量分块大小
- `KG_CHUNK_SIZE`: 知识图谱分块大小
- `CONFIDENCE_THRESHOLD`: 置信度阈值

##### 网络搜索配置
- `TAVILY_API_KEY`: Tavily搜索API密钥
- `WEB_SEARCH_TIMEOUT`: 网络搜索超时时间
- `WEB_SEARCH_MAX_RETRIES`: 网络搜索最大重试次数

#### 核心方法
```python
@property
def postgres_url(self) -> str:
    """
    构建PostgreSQL连接URL
    
    Returns:
        str: 完整的PostgreSQL连接字符串
    """
    
@property
def neo4j_config(self) -> dict:
    """
    获取Neo4j连接配置
    
    Returns:
        dict: Neo4j连接配置字典
    """

@property
def kg_llm_config(self) -> dict:
    """
    获取知识图谱LLM配置
    
    Returns:
        dict: 知识图谱LLM配置字典
    """

@property
def vector_llm_config(self) -> dict:
    """
    获取向量LLM配置
    
    Returns:
        dict: 向量LLM配置字典
    """

def validate_config(self) -> tuple[bool, list[str]]:
    """
    验证配置完整性
    
    Returns:
        tuple: (是否有效, 错误列表)
    """
```

#### 依赖关系
- **被依赖**: 所有模块都依赖此配置
- **依赖**: python-dotenv (加载.env文件)

### 2.2 状态定义 (src/core/state.py)

#### 文件功能
定义LangGraph工作流中使用的状态结构，规范数据在节点间的传递格式。

#### 核心类: AgentState
```python
class AgentState(TypedDict):
    """
    LangGraph工作流状态定义
    
    功能:
    - 定义节点间数据传递格式
    - 确保类型安全
    - 提供状态结构文档
    """
```

#### 状态字段详解
```python
# 输入字段
user_query: str              # 用户原始查询
session_id: str             # 会话ID
query_id: str               # 查询ID

# 查询分析结果
query_type: Literal["FACTUAL", "RELATIONAL", "ANALYTICAL"]
lightrag_mode: Literal["local", "global", "hybrid"]
key_entities: list[str]     # 关键实体列表
processed_query: str        # 处理后的查询
mode_reasoning: str         # 模式选择原因

# 检索结果
lightrag_results: dict      # LightRAG检索结果
retrieval_success: bool     # 检索是否成功
retrieval_score: float      # 检索质量分数
retrieval_time: float       # 检索耗时

# 质量评估
confidence_score: float     # 整体置信度
need_web_search: bool      # 是否需要网络搜索
assessment_reason: str     # 评估说明
confidence_breakdown: dict # 置信度分解

# 网络搜索
web_results: list[dict]    # 网络搜索结果
web_search_summary: str   # 搜索摘要
search_time: float        # 搜索耗时

# 最终输出
final_answer: str         # 最终答案
sources: list[dict]       # 信息来源
answer_confidence: float  # 答案置信度
processing_time: float    # 总处理时间
workflow_path: list[str]  # 工作流路径
context_used: int         # 使用的上下文数量
```

#### 依赖关系
- **被依赖**: 所有agents模块
- **依赖**: typing_extensions

### 2.3 工作流系统 (src/core/workflow.py & enhanced_workflow.py)

#### 文件功能
系统提供两个层次的工作流实现：
- **workflow.py**: 基础工作流实现，提供核心功能
- **enhanced_workflow.py**: 增强版工作流，集成全面的错误处理和监控

#### 核心类: IntelligentQAWorkflow (基础版)
```python
class IntelligentQAWorkflow:
    """
    智能问答工作流管理器
    
    基于 LangGraph 实现的 Agentic RAG 工作流，支持：
    - 智能查询分析和路由
    - 多模式 LightRAG 检索
    - 质量评估和决策
    - 网络搜索补充
    - 答案生成和整合
    """
```

#### 核心类: EnhancedIntelligentQAWorkflow (增强版)
```python
class EnhancedIntelligentQAWorkflow:
    """
    增强版智能问答工作流管理器
    
    集成了全面的错误处理、性能监控和日志记录功能
    - 全面的错误处理和重试机制
    - 详细的性能监控和统计
    - 节点执行审计日志
    - 熔断器和健康检查
    """
```

#### 主要方法

##### 初始化方法
```python
def __init__(self):
    """
    初始化工作流
    
    功能:
    - 初始化LangGraph
    - 配置节点和边
    - 设置错误处理
    - 初始化性能统计
    """
```

##### 核心接口方法
```python
def query(self, query_text: str, config: dict = None) -> dict:
    """
    同步查询接口
    
    Args:
        query_text: 用户查询文本
        config: 可选配置参数
        
    Returns:
        dict: 查询结果，包含答案、来源、置信度等
        
    功能:
    - 执行完整的工作流
    - 处理错误和异常
    - 返回结构化结果
    """

async def query_async(self, query_text: str, config: dict = None) -> dict:
    """
    异步查询接口
    
    Args:
        query_text: 用户查询文本
        config: 可选配置参数
        
    Returns:
        dict: 查询结果
        
    功能:
    - 异步执行工作流
    - 支持并发查询
    - 非阻塞处理
    """

def query_stream(self, query_text: str, config: dict = None) -> Iterator[dict]:
    """
    流式查询接口
    
    Args:
        query_text: 用户查询文本
        config: 可选配置参数
        
    Yields:
        dict: 每个处理步骤的结果
        
    功能:
    - 实时返回处理进度
    - 支持流式显示
    - 可中断处理
    """
```

##### 管理方法
```python
def get_workflow_info(self) -> dict:
    """
    获取工作流信息
    
    Returns:
        dict: 工作流基本信息
        
    包含:
    - 工作流名称和版本
    - 节点数量和类型
    - 初始化状态
    """

def get_performance_stats(self) -> dict:
    """
    获取性能统计
    
    Returns:
        dict: 性能统计数据
        
    包含:
    - 查询总数和成功率
    - 平均响应时间
    - 节点执行统计
    - 错误统计
    """
```

#### 工作流构建逻辑
```python
def _initialize_workflow(self):
    """
    初始化工作流图
    
    功能:
    - 添加所有节点
    - 配置节点间连接
    - 设置条件路由
    - 编译工作流
    """
```

#### 依赖关系
- **依赖**: 所有agents模块, core.state, core.config
- **被依赖**: main_app.py

---

## 3. 工作流节点详解 (src/agents/)

### 3.1 查询分析节点 (src/agents/query_analysis.py)

#### 文件功能
分析用户查询，识别查询类型，选择最适合的LightRAG检索模式。

#### 核心函数: query_analysis_node
```python
def query_analysis_node(state: AgentState) -> AgentState:
    """
    查询分析节点
    
    Args:
        state: 包含用户查询的状态对象
        
    Returns:
        AgentState: 更新后的状态，包含分析结果
        
    功能:
    1. 分析查询意图和类型
    2. 选择最佳LightRAG检索模式
    3. 提取关键实体
    4. 优化查询文本
    
    查询类型映射:
    - FACTUAL → local模式 (向量检索)
    - RELATIONAL → global模式 (图检索)
    - ANALYTICAL → hybrid模式 (混合检索)
    """
```

#### 辅助函数
```python
def _analyze_query_intent(query: str) -> dict:
    """
    分析查询意图
    
    Args:
        query: 用户查询文本
        
    Returns:
        dict: 分析结果，包含类型和实体
        
    功能:
    - 使用LLM分析查询意图
    - 提取关键实体
    - 确定查询复杂度
    """

def _select_lightrag_mode(query_type: str) -> str:
    """
    选择LightRAG检索模式
    
    Args:
        query_type: 查询类型
        
    Returns:
        str: 选择的检索模式
        
    映射规则:
    - FACTUAL → local
    - RELATIONAL → global
    - ANALYTICAL → hybrid
    """
```

#### 依赖关系
- **依赖**: langchain_openai, core.config, core.state
- **调用**: enhanced_workflow.py

### 3.2 LightRAG检索节点 (src/agents/lightrag_retrieval.py)

#### 文件功能
执行LightRAG检索，支持三种检索模式，计算检索质量分数。

#### 核心函数: lightrag_retrieval_node
```python
def lightrag_retrieval_node(state: AgentState) -> AgentState:
    """
    LightRAG检索节点
    
    Args:
        state: 包含查询和检索模式的状态
        
    Returns:
        AgentState: 更新后的状态，包含检索结果
        
    功能:
    1. 根据选定模式执行检索
    2. 计算检索质量分数
    3. 记录检索时间
    4. 处理检索错误
    
    检索模式:
    - local: 向量相似度检索
    - global: 图谱关系检索
    - hybrid: 混合检索
    """
```

#### 辅助函数
```python
def query_lightrag_sync(query: str, mode: str) -> dict:
    """
    同步LightRAG查询
    
    Args:
        query: 查询文本
        mode: 检索模式
        
    Returns:
        dict: 检索结果
        
    功能:
    - 调用LightRAG API
    - 处理同步查询
    - 返回结构化结果
    """

def _calculate_retrieval_quality(results: dict, mode: str) -> float:
    """
    计算检索质量分数
    
    Args:
        results: 检索结果
        mode: 检索模式
        
    Returns:
        float: 质量分数 (0.0-1.0)
        
    评分因子:
    - 内容长度和完整性
    - 检索模式匹配度
    - 结果相关性
    """
```

#### 依赖关系
- **依赖**: utils.lightrag_client, core.config, core.state
- **调用**: enhanced_workflow.py

### 3.3 质量评估节点 (src/agents/quality_assessment.py)

#### 文件功能
评估LightRAG检索结果的质量，决定是否需要网络搜索补充。

#### 核心函数: quality_assessment_node
```python
def quality_assessment_node(state: AgentState) -> AgentState:
    """
    质量评估节点
    
    Args:
        state: 包含检索结果的状态
        
    Returns:
        AgentState: 更新后的状态，包含质量评估结果
        
    功能:
    1. 多因子质量评估
    2. 动态阈值调整
    3. 决策网络搜索必要性
    4. 提供详细评估说明
    
    评估维度:
    - 内容完整性 (30%)
    - 实体覆盖度 (20%)
    - 检索成功率 (40%)
    - 模式有效性 (10%)
    """
```

#### 辅助函数
```python
def _evaluate_content_completeness(results: dict) -> float:
    """
    评估内容完整性
    
    Args:
        results: 检索结果
        
    Returns:
        float: 完整性分数
        
    评估标准:
    - 内容长度充足性
    - 信息结构完整性
    - 关键信息覆盖度
    """

def _evaluate_entity_coverage(state: AgentState) -> float:
    """
    评估实体覆盖度
    
    Args:
        state: 当前状态
        
    Returns:
        float: 覆盖度分数
        
    功能:
    - 检查关键实体是否被提及
    - 计算覆盖率
    - 评估实体相关性
    """

def _calculate_dynamic_threshold(query_type: str) -> float:
    """
    计算动态阈值
    
    Args:
        query_type: 查询类型
        
    Returns:
        float: 动态阈值
        
    阈值策略:
    - FACTUAL: 0.7 (高要求)
    - RELATIONAL: 0.6 (中等要求)
    - ANALYTICAL: 0.5 (较低要求)
    """
```

#### 依赖关系
- **依赖**: core.config, core.state, utils.helpers
- **调用**: enhanced_workflow.py

### 3.4 网络搜索节点 (src/agents/web_search.py)

#### 文件功能
当本地知识不足时，使用Tavily API进行网络搜索补充。

#### 核心函数: web_search_node
```python
def web_search_node(state: AgentState) -> AgentState:
    """
    网络搜索节点
    
    Args:
        state: 包含搜索需求的状态
        
    Returns:
        AgentState: 更新后的状态，包含搜索结果
        
    功能:
    1. 条件性执行搜索
    2. 优化搜索策略
    3. 结果过滤和排序
    4. 错误处理和重试
    
    搜索策略:
    - 根据查询类型调整搜索深度
    - 动态调整结果数量
    - 优化搜索查询
    """
```

#### 辅助函数
```python
def _optimize_search_query(query: str, query_type: str) -> str:
    """
    优化搜索查询
    
    Args:
        query: 原始查询
        query_type: 查询类型
        
    Returns:
        str: 优化后的搜索查询
        
    优化策略:
    - 添加时间限制
    - 优化关键词
    - 添加上下文信息
    """

def _filter_and_rank_results(results: list, query: str) -> list:
    """
    过滤和排序搜索结果
    
    Args:
        results: 原始搜索结果
        query: 查询文本
        
    Returns:
        list: 过滤排序后的结果
        
    功能:
    - 相关性过滤
    - 质量排序
    - 去重处理
    """
```

#### 依赖关系
- **依赖**: tavily-python, core.config, core.state
- **调用**: enhanced_workflow.py

### 3.5 答案生成节点 (src/agents/answer_generation.py)

#### 文件功能
整合所有信息源，生成最终答案，提供来源标注。

#### 核心函数: answer_generation_node
```python
def answer_generation_node(state: AgentState) -> AgentState:
    """
    答案生成节点
    
    Args:
        state: 包含所有信息源的状态
        
    Returns:
        AgentState: 更新后的状态，包含最终答案
        
    功能:
    1. 多源信息整合
    2. 智能答案生成
    3. 来源标注和追踪
    4. 置信度计算
    
    信息源优先级:
    1. LightRAG本地知识 (优先)
    2. 网络搜索结果 (补充)
    3. 图谱关系信息 (增强)
    """
```

#### 辅助函数
```python
def _integrate_information_sources(state: AgentState) -> str:
    """
    整合信息源
    
    Args:
        state: 当前状态
        
    Returns:
        str: 整合后的上下文
        
    功能:
    - 信息去重和融合
    - 来源权重计算
    - 上下文构建
    """

def _generate_answer_with_sources(context: str, query: str) -> dict:
    """
    生成带来源标注的答案
    
    Args:
        context: 整合后的上下文
        query: 用户查询
        
    Returns:
        dict: 答案和来源信息
        
    功能:
    - 答案生成
    - 来源追踪
    - 置信度评估
    """

def _calculate_answer_confidence(state: AgentState) -> float:
    """
    计算答案置信度
    
    Args:
        state: 当前状态
        
    Returns:
        float: 答案置信度
        
    计算因子:
    - 信息源质量
    - 信息源数量
    - 一致性程度
    """
```

#### 依赖关系
- **依赖**: langchain_openai, core.config, core.state, utils.helpers
- **调用**: enhanced_workflow.py

---

## 4. 工具模块详解 (src/utils/)

### 4.0 工具模块概述
工具模块提供了完整的支持组件：
- **lightrag_client.py**: LightRAG客户端封装
- **kg_llm_client.py**: 知识图谱LLM客户端
- **document_processor.py**: 文档处理器
- **simple_logger.py**: 简单日志系统
- **advanced_logging.py**: 高级日志系统
- **error_handling.py**: 错误处理框架
- **system_monitoring.py**: 系统监控
- **helpers.py**: 通用辅助函数

### 4.1 LightRAG客户端 (src/utils/lightrag_client.py)

#### 文件功能
封装LightRAG操作，管理PostgreSQL和Neo4j连接，提供统一的检索接口。支持多种数据库后端的自动回退机制。

#### 核心函数

##### 自定义LLM函数
```python
def custom_llm_func(prompt: str, **kwargs) -> str:
    """
    自定义LLM函数，支持不同的base_url和API key
    """

def custom_vector_llm_func(prompt: str, **kwargs) -> str:
    """
    向量提取专用LLM函数，使用向量LLM配置
    """

def custom_embedding_func(texts: list[str]) -> list[list[float]]:
    """
    自定义嵌入函数，支持不同的base_url和API key
    """
```

#### 核心类: LightRAGClient
```python
class LightRAGClient:
    """
    LightRAG客户端封装类
    
    功能:
    - 管理LightRAG实例
    - 处理数据库连接和回退机制
    - 提供统一的检索接口
    - 健康检查和监控
    - 支持多种LLM配置
    """
```

#### 主要方法

##### 初始化方法
```python
async def initialize(self) -> bool:
    """
    初始化LightRAG客户端
    
    Returns:
        bool: 初始化是否成功
        
    功能:
    - 检查数据库连接
    - 初始化LightRAG实例
    - 设置存储后端
    - 配置embedding模型
    """
```

##### 文档操作方法
```python
async def insert_document(self, document: str, metadata: dict = None) -> bool:
    """
    插入文档到知识库
    
    Args:
        document: 文档内容
        metadata: 文档元数据
        
    Returns:
        bool: 插入是否成功
        
    功能:
    - 文档预处理
    - 向量化处理
    - 图谱构建
    - 数据存储
    """

async def query(self, query: str, mode: str = "hybrid") -> dict:
    """
    查询知识库
    
    Args:
        query: 查询文本
        mode: 检索模式
        
    Returns:
        dict: 查询结果
        
    功能:
    - 多模式检索
    - 结果排序
    - 质量评估
    - 错误处理
    """
```

##### 健康检查方法
```python
async def get_health_status(self) -> dict:
    """
    获取客户端健康状态
    
    Returns:
        dict: 健康状态信息
        
    检查项目:
    - PostgreSQL连接状态
    - Neo4j连接状态
    - LightRAG实例状态
    - 存储空间使用情况
    """
```

##### 私有方法
```python
async def _check_pgvector(self) -> bool:
    """
    检查PostgreSQL pgvector扩展
    
    Returns:
        bool: pgvector是否可用
    """

async def _check_neo4j(self) -> bool:
    """
    检查Neo4j连接
    
    Returns:
        bool: Neo4j是否可用
    """
```

#### 依赖关系
- **依赖**: lightrag, psycopg2, neo4j, core.config
- **被依赖**: agents.lightrag_retrieval

### 4.2 知识图谱LLM客户端 (src/utils/kg_llm_client.py)

#### 文件功能
专门为知识图谱构建优化的LLM客户端，提供实体关系提取的专用接口。

#### 核心功能
- 实体关系提取优化
- 图谱构建专用提示词
- 结构化输出处理
- 知识图谱质量控制

### 4.3 文档处理器 (src/utils/document_processor.py)

#### 文件功能
处理各种格式的文档，提供文档分块、预处理和向量化准备功能。

#### 核心功能
- 多格式文档解析
- 智能文档分块
- 文档预处理和清洗
- 向量化准备

### 4.4 简单日志系统 (src/utils/simple_logger.py)

#### 文件功能
提供轻量级的日志记录功能，避免循环导入问题。

#### 核心函数
```python
def get_simple_logger(name: str) -> logging.Logger:
    """
    获取简单日志记录器
    
    Args:
        name: 日志器名称
        
    Returns:
        logging.Logger: 配置好的日志器
    """
```

#### 依赖关系
- **依赖**: logging
- **被依赖**: lightrag_client, agents模块

### 4.5 高级日志系统 (src/utils/advanced_logging.py)

#### 文件功能
提供结构化JSON日志、性能监控、错误追踪和审计日志功能。

#### 核心类

##### StructuredFormatter
```python
class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式化器
    
    功能:
    - 输出JSON格式日志
    - 添加结构化字段
    - 支持自定义字段
    """
```

##### PerformanceLogger
```python
class PerformanceLogger:
    """
    性能日志记录器
    
    功能:
    - 操作计时
    - 性能指标收集
    - 统计分析
    """
```

##### ErrorTracker
```python
class ErrorTracker:
    """
    错误追踪器
    
    功能:
    - 错误记录和分类
    - 堆栈跟踪
    - 错误统计
    """
```

#### 主要函数

##### 日志设置函数
```python
def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    设置结构化日志记录器
    
    Args:
        name: 日志器名称
        level: 日志级别
        
    Returns:
        logging.Logger: 配置好的日志器
        
    功能:
    - 创建日志器
    - 配置处理器
    - 设置格式化器
    """

def get_performance_logger(name: str) -> PerformanceLogger:
    """
    获取性能日志记录器
    
    Args:
        name: 日志器名称
        
    Returns:
        PerformanceLogger: 性能日志器实例
    """

def get_error_tracker(name: str) -> ErrorTracker:
    """
    获取错误追踪器
    
    Args:
        name: 追踪器名称
        
    Returns:
        ErrorTracker: 错误追踪器实例
    """
```

##### 装饰器函数
```python
def log_performance(operation_name: str):
    """
    性能日志装饰器
    
    Args:
        operation_name: 操作名称
        
    功能:
    - 自动记录函数执行时间
    - 记录成功/失败状态
    - 异常捕获和记录
    """

def log_errors(error_context: str):
    """
    错误日志装饰器
    
    Args:
        error_context: 错误上下文
        
    功能:
    - 自动捕获和记录错误
    - 提供错误上下文
    - 错误分类和统计
    """
```

##### 监控函数
```python
def record_metric(name: str, value: float, **tags) -> None:
    """
    记录指标
    
    Args:
        name: 指标名称
        value: 指标值
        **tags: 标签
        
    功能:
    - 记录自定义指标
    - 支持标签分类
    - 时间序列存储
    """

def audit_log(action: str, user: str, details: dict = None) -> None:
    """
    记录审计日志
    
    Args:
        action: 操作行为
        user: 用户标识
        details: 详细信息
        
    功能:
    - 记录用户操作
    - 安全审计
    - 合规性支持
    """
```

#### 依赖关系
- **依赖**: logging, json, datetime, core.config
- **被依赖**: 所有模块

### 4.3 错误处理 (src/utils/error_handling.py)

#### 文件功能
提供综合错误处理机制，包括自定义异常、重试机制和熔断器。

#### 核心类

##### 自定义异常基类
```python
class SystemError(Exception):
    """
    系统错误基类
    
    功能:
    - 统一错误接口
    - 错误分类和编码
    - 恢复建议
    """
    
    def __init__(self, message: str, error_code: str = None, 
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        """
        初始化系统错误
        
        Args:
            message: 错误消息
            error_code: 错误编码
            category: 错误类别
            severity: 错误严重程度
        """
```

##### 具体异常类
```python
class ConfigurationError(SystemError):
    """配置错误"""
    pass

class DatabaseError(SystemError):
    """数据库错误"""
    pass

class NetworkError(SystemError):
    """网络错误"""
    pass

class APIError(SystemError):
    """API错误"""
    pass

class ValidationError(SystemError):
    """验证错误"""
    pass
```

##### 错误处理器
```python
class ErrorHandler:
    """
    错误处理器
    
    功能:
    - 错误分类和处理
    - 错误记录和报告
    - 恢复策略执行
    """
    
    def handle_error(self, error: Exception, context: dict = None) -> dict:
        """
        处理错误
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            dict: 处理结果
            
        功能:
        - 错误分类和编码
        - 生成用户友好消息
        - 记录错误日志
        - 返回处理结果
        """
```

##### 重试处理器
```python
class RetryHandler:
    """
    重试处理器
    
    功能:
    - 智能重试机制
    - 指数退避算法
    - 最大重试限制
    """
    
    def retry_with_backoff(self, func: callable, *args, **kwargs):
        """
        带退避的重试执行
        
        Args:
            func: 要重试的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        功能:
        - 执行函数
        - 捕获异常
        - 计算退避时间
        - 重试执行
        """
```

##### 熔断器
```python
class CircuitBreaker:
    """
    熔断器
    
    功能:
    - 故障检测
    - 熔断保护
    - 自动恢复
    """
    
    def call(self, func: callable, *args, **kwargs):
        """
        熔断器调用
        
        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        功能:
        - 检查熔断器状态
        - 执行函数调用
        - 记录成功/失败
        - 状态转换
        """
```

#### 装饰器函数
```python
def handle_errors(reraise: bool = True, return_on_error = None):
    """
    错误处理装饰器
    
    Args:
        reraise: 是否重新抛出异常
        return_on_error: 错误时的返回值
        
    功能:
    - 自动错误处理
    - 灵活的错误响应
    - 错误记录
    """

def retry_on_failure(max_retries: int = 3, backoff_factor: float = 1.0):
    """
    失败重试装饰器
    
    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
        
    功能:
    - 自动重试
    - 指数退避
    - 异常传播
    """
```

#### 依赖关系
- **依赖**: logging, time, functools, core.config
- **被依赖**: 所有模块

### 4.4 系统监控 (src/utils/system_monitoring.py)

#### 文件功能
提供系统健康检查、性能监控和状态报告功能。

#### 核心类

##### HealthCheck
```python
class HealthCheck:
    """
    健康检查结果
    
    功能:
    - 检查结果封装
    - 状态标准化
    - 详细信息记录
    """
    
    def __init__(self, name: str, status: HealthStatus, 
                 message: str, details: dict = None,
                 timestamp: float = None, execution_time: float = None):
        """
        初始化健康检查结果
        
        Args:
            name: 检查名称
            status: 健康状态
            message: 状态消息
            details: 详细信息
            timestamp: 检查时间戳
            execution_time: 执行时间
        """
```

##### SystemMonitor
```python
class SystemMonitor:
    """
    系统监控器
    
    功能:
    - 健康检查管理
    - 性能指标收集
    - 状态报告生成
    """
    
    def register_health_check(self, name: str, check_func: callable) -> None:
        """
        注册健康检查
        
        Args:
            name: 检查名称
            check_func: 检查函数
            
        功能:
        - 注册检查函数
        - 配置检查参数
        - 调度检查执行
        """
    
    def get_system_health(self) -> dict:
        """
        获取系统健康状态
        
        Returns:
            dict: 系统健康报告
            
        功能:
        - 执行所有健康检查
        - 汇总检查结果
        - 生成健康报告
        """
    
    def add_metric(self, name: str, value: float, tags: dict = None) -> None:
        """
        添加性能指标
        
        Args:
            name: 指标名称
            value: 指标值
            tags: 指标标签
            
        功能:
        - 记录指标值
        - 添加时间戳
        - 存储到队列
        """
```

##### ApplicationHealthChecker
```python
class ApplicationHealthChecker:
    """
    应用健康检查器
    
    功能:
    - 数据库连接检查
    - API服务检查
    - 依赖服务检查
    """
    
    def check_database_connection(self) -> HealthCheck:
        """
        检查数据库连接
        
        Returns:
            HealthCheck: 数据库连接状态
            
        检查项目:
        - PostgreSQL连接
        - Neo4j连接
        - 连接池状态
        """
    
    def check_api_endpoints(self) -> HealthCheck:
        """
        检查API端点
        
        Returns:
            HealthCheck: API服务状态
            
        检查项目:
        - OpenAI API可用性
        - Tavily API可用性
        - 响应时间
        """
```

#### 全局函数
```python
def get_system_health() -> dict:
    """
    获取系统健康状态
    
    Returns:
        dict: 系统健康报告
        
    功能:
    - 执行标准健康检查
    - 收集系统指标
    - 生成健康报告
    """

def get_system_monitor() -> SystemMonitor:
    """
    获取系统监控器实例
    
    Returns:
        SystemMonitor: 监控器实例
    """
```

#### 依赖关系
- **依赖**: psutil, threading, queue, core.config
- **被依赖**: enhanced_workflow, main_app

### 4.5 辅助函数 (src/utils/helpers.py)

#### 文件功能
提供通用的辅助函数，包括查询验证、数据处理、格式化等。

#### 核心函数

##### 查询处理函数
```python
def validate_query(query: str) -> tuple[bool, str]:
    """
    验证查询有效性
    
    Args:
        query: 用户查询
        
    Returns:
        tuple: (是否有效, 错误消息)
        
    验证规则:
    - 长度限制
    - 恶意内容检测
    - 格式验证
    """

def preprocess_query(query: str) -> str:
    """
    预处理查询
    
    Args:
        query: 原始查询
        
    Returns:
        str: 处理后的查询
        
    处理步骤:
    - 去除多余空格
    - 标准化标点
    - 敏感词过滤
    """
```

##### 数据处理函数
```python
def safe_json_parse(json_str: str, default = None):
    """
    安全JSON解析
    
    Args:
        json_str: JSON字符串
        default: 解析失败时的默认值
        
    Returns:
        解析结果或默认值
        
    功能:
    - 异常安全解析
    - 默认值处理
    - 错误日志记录
    """

def truncate_text(text: str, max_length: int) -> str:
    """
    截断文本
    
    Args:
        text: 要截断的文本
        max_length: 最大长度
        
    Returns:
        str: 截断后的文本
        
    功能:
    - 智能截断
    - 保持完整性
    - 添加省略号
    """
```

##### 置信度计算函数
```python
def calculate_confidence(retrieval_score: float, content_length: int, 
                        entity_match: float, query_complexity: float) -> float:
    """
    计算综合置信度
    
    Args:
        retrieval_score: 检索分数
        content_length: 内容长度
        entity_match: 实体匹配度
        query_complexity: 查询复杂度
        
    Returns:
        float: 综合置信度
        
    计算公式:
    - 加权平均算法
    - 动态权重调整
    - 归一化处理
    """
```

##### 格式化函数
```python
def format_sources(sources: list) -> str:
    """
    格式化信息源
    
    Args:
        sources: 信息源列表
        
    Returns:
        str: 格式化后的信息源描述
        
    功能:
    - 分类显示
    - 优先级排序
    - 美化格式
    """

def format_processing_time(seconds: float) -> str:
    """
    格式化处理时间
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 人类可读的时间格式
        
    功能:
    - 单位转换
    - 精度控制
    - 人性化显示
    """
```

##### ID生成函数
```python
def generate_session_id() -> str:
    """
    生成会话ID
    
    Returns:
        str: 唯一会话ID
        
    功能:
    - UUID生成
    - 时间戳前缀
    - 唯一性保证
    """

def generate_query_id() -> str:
    """
    生成查询ID
    
    Returns:
        str: 唯一查询ID
        
    功能:
    - 短ID生成
    - 可读性优化
    - 冲突避免
    """
```

##### 字典操作函数
```python
def deep_merge_dicts(dict1: dict, dict2: dict) -> dict:
    """
    深度合并字典
    
    Args:
        dict1: 第一个字典
        dict2: 第二个字典
        
    Returns:
        dict: 合并后的字典
        
    功能:
    - 递归合并
    - 类型检查
    - 冲突处理
    """

def get_nested_value(data: dict, path: str, default = None):
    """
    获取嵌套字典值
    
    Args:
        data: 字典数据
        path: 路径字符串 (如 "a.b.c")
        default: 默认值
        
    Returns:
        嵌套值或默认值
        
    功能:
    - 路径解析
    - 安全访问
    - 默认值处理
    """

def set_nested_value(data: dict, path: str, value) -> None:
    """
    设置嵌套字典值
    
    Args:
        data: 字典数据
        path: 路径字符串
        value: 要设置的值
        
    功能:
    - 路径创建
    - 值设置
    - 类型检查
    """
```

#### 依赖关系
- **依赖**: json, uuid, datetime, re, core.config
- **被依赖**: 所有模块

---

## 5. 主应用系统

### 5.1 应用文件概述
系统提供两个Streamlit应用：
- **main_app.py**: 功能完整的主应用，包含高级界面和功能
- **streamlit_app.py**: 简化版应用，提供基础的问答界面

### 5.2 主应用 (main_app.py)

#### 文件功能
完整的Streamlit应用，提供丰富的Web界面，集成所有功能模块，包含系统监控和管理功能。

#### 核心功能
- 现代化的界面设计和CSS样式
- 完整的系统状态监控
- 详细的查询历史管理
- 实时性能指标显示
- 高级配置和控制面板
- 流式查询处理和显示

#### 主要组件

##### 初始化函数
```python
def initialize_session_state():
    """初始化会话状态"""

async def initialize_system():
    """异步初始化系统"""
```

##### 界面渲染函数
```python
def render_header():
    """渲染页面头部"""

def render_system_status():
    """渲染系统状态"""

def render_sidebar():
    """渲染侧边栏"""

def render_chat_interface():
    """渲染聊天界面"""
```

### 5.3 简化应用 (streamlit_app.py)

#### 文件功能
简化版的Streamlit应用，提供基础的问答界面，适合快速部署和基本使用。

#### 核心功能
- 简洁的问答界面
- 基础的系统状态显示
- 流式查询处理
- 配置设置面板
- 对话历史管理

#### 主要组件

##### 核心函数
```python
def initialize_system():
    """初始化系统"""

def render_sidebar():
    """渲染侧边栏"""

def render_chat_history():
    """渲染对话历史"""

def process_query_stream(query: str):
    """处理流式查询"""
```

#### 核心函数

##### 应用初始化
```python
def init_app():
    """
    初始化应用
    
    功能:
    - 配置Streamlit
    - 初始化工作流
    - 设置会话状态
    - 加载样式
    """
```

##### 页面渲染
```python
def render_main_page():
    """
    渲染主页面
    
    功能:
    - 查询输入界面
    - 结果显示区域
    - 系统状态面板
    - 历史记录管理
    """

def render_sidebar():
    """
    渲染侧边栏
    
    功能:
    - 系统配置
    - 健康检查
    - 统计信息
    - 帮助信息
    """
```

##### 查询处理
```python
def process_user_query(query: str):
    """
    处理用户查询
    
    Args:
        query: 用户查询
        
    功能:
    - 查询验证
    - 工作流执行
    - 结果显示
    - 错误处理
    """

def display_streaming_results(workflow_stream):
    """
    显示流式结果
    
    Args:
        workflow_stream: 工作流流式输出
        
    功能:
    - 实时进度显示
    - 步骤详情展示
    - 结果格式化
    - 交互式组件
    """
```

##### 系统管理
```python
def display_system_status():
    """
    显示系统状态
    
    功能:
    - 健康检查结果
    - 性能指标
    - 连接状态
    - 资源使用情况
    """

def manage_query_history():
    """
    管理查询历史
    
    功能:
    - 历史记录存储
    - 历史查询展示
    - 快速重用
    - 历史清理
    """
```

### 5.3 依赖关系
- **依赖**: streamlit, 所有core和utils模块
- **被依赖**: 无 (应用入口)

---

## 6. 模块依赖关系图

### 6.1 核心依赖关系
```
main_app.py / streamlit_app.py
    ├── core.workflow (基础版) 或 core.enhanced_workflow (增强版)
    ├── utils.system_monitoring
    ├── utils.helpers
    └── utils.lightrag_client

core.workflow / core.enhanced_workflow
    ├── core.config
    ├── core.state
    ├── agents.query_analysis
    ├── agents.lightrag_retrieval
    ├── agents.quality_assessment
    ├── agents.web_search
    ├── agents.answer_generation
    └── utils.simple_logger / utils.advanced_logging

agents.* (所有节点)
    ├── core.config
    ├── core.state
    ├── utils.helpers
    ├── utils.simple_logger (避免循环导入)
    └── utils.error_handling

utils.lightrag_client
    ├── core.config
    ├── utils.simple_logger
    └── utils.error_handling

utils.kg_llm_client
    ├── core.config
    └── utils.simple_logger

utils.document_processor
    ├── core.config
    └── utils.simple_logger

utils.* (高级工具模块)
    ├── core.config
    └── utils.simple_logger
```

### 6.2 数据流向
```
用户输入 (main_app.py)
    ↓
enhanced_workflow.query()
    ↓
query_analysis_node (agents.query_analysis)
    ↓
lightrag_retrieval_node (agents.lightrag_retrieval)
    ├── → lightrag_client.query()
    └── → PostgreSQL & Neo4j
    ↓
quality_assessment_node (agents.quality_assessment)
    ↓
web_search_node (agents.web_search) [条件性]
    └── → Tavily API
    ↓
answer_generation_node (agents.answer_generation)
    ↓
最终结果 (main_app.py)
```

### 6.3 配置传播
```
.env 文件
    ↓
core.config.Config
    ↓
所有模块 (通过 from core.config import config)
```

### 6.4 日志和监控流
```
所有模块操作
    ↓
utils.advanced_logging
    ├── → 结构化日志文件
    └── → 性能指标

utils.system_monitoring
    ├── → 健康检查
    └── → 系统状态

utils.error_handling
    ├── → 错误处理
    └── → 错误恢复
```

---

## 7. 接口规范

### 7.1 工作流接口
```python
# 主查询接口
def query(query_text: str, config: dict = None) -> dict:
    """
    Returns:
    {
        "final_answer": str,
        "sources": list[dict],
        "confidence_score": float,
        "processing_time": float,
        "workflow_path": list[str]
    }
    """

# 流式查询接口
def query_stream(query_text: str, config: dict = None) -> Iterator[dict]:
    """
    Yields:
    {
        "step": str,
        "status": str,
        "data": dict,
        "timestamp": float
    }
    """
```

### 7.2 节点接口
```python
# 所有节点统一接口
def node_function(state: AgentState) -> AgentState:
    """
    Args:
        state: 输入状态
        
    Returns:
        state: 更新后的状态
    """
```

### 7.3 工具接口
```python
# LightRAG客户端接口
async def query(query: str, mode: str = "hybrid") -> dict:
    """
    Returns:
    {
        "success": bool,
        "content": str,
        "mode": str,
        "error": str  # 仅在失败时
    }
    """

# 健康检查接口
def get_system_health() -> dict:
    """
    Returns:
    {
        "overall_status": str,
        "timestamp": float,
        "checks": dict,
        "metrics": dict
    }
    """
```

---

## 8. 错误码参考

### 8.1 系统错误码
```python
ERROR_CODES = {
    # 配置错误 (1000-1099)
    "CONFIG_INVALID": 1001,
    "CONFIG_MISSING": 1002,
    
    # 数据库错误 (1100-1199)
    "DB_CONNECTION_FAILED": 1101,
    "DB_QUERY_FAILED": 1102,
    
    # API错误 (1200-1299)
    "API_KEY_INVALID": 1201,
    "API_RATE_LIMIT": 1202,
    
    # 网络错误 (1300-1399)
    "NETWORK_TIMEOUT": 1301,
    "NETWORK_CONNECTION_ERROR": 1302,
    
    # 验证错误 (1400-1499)
    "VALIDATION_FAILED": 1401,
    "QUERY_TOO_SHORT": 1402,
    
    # 工作流错误 (1500-1599)
    "WORKFLOW_INIT_FAILED": 1501,
    "WORKFLOW_EXECUTION_FAILED": 1502
}
```

### 8.2 错误处理流程
```python
try:
    # 操作代码
    result = perform_operation()
except SystemError as e:
    # 自定义错误处理
    error_info = {
        "error_code": e.error_code,
        "message": str(e),
        "category": e.category,
        "severity": e.severity,
        "recovery_suggestions": e.recovery_suggestions
    }
    logger.error("Operation failed", extra=error_info)
except Exception as e:
    # 通用错误处理
    error_handler.handle_error(e, context)
```

---

## 9. 使用示例

### 9.1 基本使用
```python
# 基础版工作流
from src.core.workflow import get_workflow

# 获取工作流实例
workflow = get_workflow()

# 执行查询
result = workflow.run("什么是机器学习？")

# 查看结果
print(f"答案: {result['final_answer']}")
print(f"置信度: {result['answer_confidence']}")
print(f"来源: {result['sources']}")

# 增强版工作流
from src.core.enhanced_workflow import get_workflow as get_enhanced_workflow

# 获取增强版工作流实例
enhanced_workflow = get_enhanced_workflow()

# 执行查询
result = enhanced_workflow.run("什么是机器学习？")
```

### 9.2 异步处理
```python
import asyncio
from src.core.workflow import query_async

# 异步查询
async def async_query():
    result = await query_async("分析AI的发展趋势")
    return result

# 运行异步查询
result = asyncio.run(async_query())
```

### 9.3 流式处理
```python
from src.core.workflow import query_stream

# 流式查询
for step in query_stream("分析AI的发展趋势"):
    print(f"步骤: {step.get('step', 'unknown')}")
    print(f"状态: {step.get('status', 'unknown')}")
    if step.get('data'):
        print(f"数据: {step['data']}")
```

### 9.4 LightRAG客户端使用
```python
from src.utils.lightrag_client import lightrag_client, initialize_lightrag
import asyncio

# 初始化LightRAG
async def init_and_query():
    await initialize_lightrag()
    
    # 查询
    result = await lightrag_client.query("什么是机器学习？", mode="hybrid")
    print(f"结果: {result}")

asyncio.run(init_and_query())
```

### 9.5 错误处理
```python
from src.utils.error_handling import handle_errors

@handle_errors(reraise=False, return_on_error={"error": "查询失败"})
def safe_query(query_text: str):
    from src.core.workflow import query
    return query(query_text)

result = safe_query("测试查询")
```

### 9.6 监控使用
```python
from src.utils.system_monitoring import get_system_health

# 获取系统健康状态
health = get_system_health()
print(f"系统状态: {health['overall_status']}")
print(f"检查结果: {health['checks']}")

# 获取工作流信息
from src.core.workflow import get_workflow_info
info = get_workflow_info()
print(f"工作流信息: {info}")
```

---

## 10. 开发指南

### 10.1 添加新节点
1. 在`src/agents/`目录创建新文件
2. 实现节点函数，遵循统一接口规范
3. 在`enhanced_workflow.py`中注册节点
4. 配置节点连接和路由
5. 添加相应测试

### 10.2 扩展工具模块
1. 在`src/utils/`目录创建新文件
2. 实现工具类或函数
3. 添加错误处理和日志记录
4. 更新依赖关系
5. 编写使用文档

### 10.3 配置管理
1. 在`.env`文件添加新配置项
2. 在`core.config.py`中定义配置属性
3. 在相关模块中使用配置
4. 添加配置验证
5. 更新文档

### 10.4 测试指南
1. 单元测试：测试独立功能
2. 集成测试：测试模块协作
3. 端到端测试：测试完整流程
4. 性能测试：测试系统性能
5. 错误测试：测试错误处理

---

## 11. 部署参考

### 11.1 环境要求
- Python 3.8+
- PostgreSQL 12+ (with pgvector)
- Neo4j 5.0+
- 8GB+ RAM (推荐)
- 4+ CPU cores

### 11.2 一键部署
```bash
# 运行一键部署脚本
./setup.sh

# 编辑环境配置
nano .env

# 启动应用
./start.sh
```

### 11.3 手动部署
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env

# 启动应用 (选择其中一个)
streamlit run main_app.py          # 完整版应用
streamlit run streamlit_app.py     # 简化版应用
```

### 11.4 配置设置
主要配置项：
```bash
# 基础LLM配置
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4

# 知识图谱LLM配置
KG_LLM_API_KEY=your_kg_api_key
KG_LLM_BASE_URL=https://api.openai.com/v1
KG_LLM_MODEL=gpt-4o

# 向量LLM配置
VECTOR_LLM_API_KEY=your_vector_api_key
VECTOR_LLM_BASE_URL=https://api.openai.com/v1
VECTOR_LLM_MODEL=gpt-4o-mini

# 嵌入配置
EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-v1

# 搜索配置
TAVILY_API_KEY=your_tavily_api_key

# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_DB=searchforrag
POSTGRES_USER=searchforrag
POSTGRES_PASSWORD=your_password
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your_neo4j_password
```

### 11.5 测试系统
```bash
# 运行综合测试
python test_error_handling.py

# 运行工作流测试
python test_workflow.py

# 运行测试脚本
./test_runner.sh
```

---

## 12. 故障排除

### 12.1 常见问题

#### 配置问题
- 检查`.env`文件是否正确
- 验证API密钥有效性
- 确认数据库连接参数

#### 连接问题
- 检查数据库服务状态
- 验证网络连接
- 确认端口开放

#### 性能问题
- 检查系统资源使用
- 优化查询参数
- 调整并发设置

### 12.2 日志分析
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log

# 查看性能日志
tail -f logs/performance.log
```

### 12.3 监控检查
```python
# 检查系统健康
from src.utils.system_monitoring import get_system_health
health = get_system_health()
print(health)

# 检查工作流状态
from src.core.enhanced_workflow import get_workflow
workflow = get_workflow()
info = workflow.get_workflow_info()
print(info)
```

---

## 13. 版本更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 实现核心RAG功能
- 集成LangGraph工作流
- 添加Streamlit界面
- 完善错误处理和日志系统

### v1.1.0 (当前版本)
- 增加双工作流支持（基础版和增强版）
- 实现多层LLM配置架构
- 添加知识图谱专用LLM客户端
- 增强数据库后端回退机制
- 优化文档处理和分块策略
- 改进简单日志系统避免循环导入
- 增加双Streamlit应用支持
- 完善一键部署脚本
- 增强系统监控和健康检查

### 技术改进
- 支持PostgreSQL+pgvector和Neo4j的自动回退
- 优化嵌入函数和向量处理
- 改进查询分析和模式选择
- 增强错误处理和重试机制
- 完善性能监控和统计
- 优化配置验证和默认值处理

---

## 14. 项目文件总览

### 核心文件
- `main_app.py`: 完整功能主应用
- `streamlit_app.py`: 简化版应用
- `setup.sh`: 一键部署脚本
- `start.sh`: 启动脚本
- `requirements.txt`: 依赖管理

### 配置文件
- `.env`: 环境变量配置
- `src/core/config.py`: 配置管理
- `src/core/state.py`: 状态定义

### 工作流文件
- `src/core/workflow.py`: 基础工作流
- `src/core/enhanced_workflow.py`: 增强工作流

### 节点文件
- `src/agents/query_analysis.py`: 查询分析
- `src/agents/lightrag_retrieval.py`: LightRAG检索
- `src/agents/quality_assessment.py`: 质量评估
- `src/agents/web_search.py`: 网络搜索
- `src/agents/answer_generation.py`: 答案生成

### 工具文件
- `src/utils/lightrag_client.py`: LightRAG客户端
- `src/utils/kg_llm_client.py`: 知识图谱LLM客户端
- `src/utils/document_processor.py`: 文档处理器
- `src/utils/simple_logger.py`: 简单日志系统
- `src/utils/advanced_logging.py`: 高级日志系统
- `src/utils/error_handling.py`: 错误处理框架
- `src/utils/system_monitoring.py`: 系统监控
- `src/utils/helpers.py`: 通用辅助函数

### 测试文件
- `test_workflow.py`: 工作流测试
- `test_error_handling.py`: 错误处理测试
- `test_runner.sh`: 测试运行脚本

---

## 15. 联系信息

如有技术问题或改进建议，请通过以下方式联系：

- 项目仓库: [GitHub链接]
- 技术文档: [文档链接]
- 问题反馈: [Issues链接]

---

**文档结束**

此文档提供了智能问答系统的完整技术参考，准确反映了当前项目的实际架构和实现细节。开发者和AI助手可以通过此文档快速理解系统架构、配置选项和使用方法。文档已根据实际项目代码进行了全面更新和修正。