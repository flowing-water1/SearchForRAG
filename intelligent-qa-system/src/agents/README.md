# 工作流节点技术文档

> 返回 [项目概览文档](../../TECHNICAL_REFERENCE.md)

## 📍 相关文档导航
- **[核心模块文档](../core/README.md)** - 查看工作流节点使用的配置、状态和工作流定义
- **[工具模块文档](../utils/README.md)** - 查看节点使用的客户端、日志和错误处理工具
- **[项目根目录](../../TECHNICAL_REFERENCE.md)** - 返回项目完整概览

## 🔗 相关核心组件
- [AgentState定义](../core/README.md#2-状态定义-statepy) - 所有节点共享的状态接口
- [工作流引擎](../core/README.md#3-基础工作流-workflowpy) - 节点的执行环境
- [LightRAG客户端](../utils/README.md#5-lightrag客户端-lightrag_clientpy) - 检索节点的核心依赖
- [错误处理系统](../utils/README.md#3-错误处理框架-error_handlingpy) - 节点的容错机制

---

## 模块概述

工作流节点模块 (src/agents/) 实现了智能问答系统的核心AI代理，每个节点负责工作流中的特定步骤。基于LangGraph框架，这些节点通过状态传递协同工作，实现完整的Agentic RAG流程。

### 模块结构
```
src/agents/
├── __init__.py               # 模块初始化
├── query_analysis.py        # 查询分析节点
├── lightrag_retrieval.py    # LightRAG检索节点
├── quality_assessment.py    # 质量评估节点
├── web_search.py            # 网络搜索节点
└── answer_generation.py     # 答案生成节点
```

### 工作流执行顺序
```
用户查询 → 查询分析 → LightRAG检索 → 质量评估 → [条件路由] → 答案生成
                                        ↓
                                    网络搜索 → 答案生成
```

---

## 节点详解

### 1. 查询分析节点 (query_analysis.py)

**主要功能**: 分析用户查询，确定查询类型并选择最适合的LightRAG检索模式。

#### 核心函数: query_analysis_node

```python
def query_analysis_node(state: AgentState) -> Dict[str, Any]:
    """
    查询分析节点
    
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

#### 查询类型分类

**FACTUAL (事实性查询)**
- 特征：寻找具体事实、定义、概念
- 检索模式：`local` (向量相似度检索)
- 示例：
  - "什么是机器学习？"
  - "Python的语法特点"
  - "深度学习的定义"

**RELATIONAL (关系性查询)**
- 特征：探索实体间关系、影响、联系
- 检索模式：`global` (图谱关系检索)
- 示例：
  - "OpenAI和微软的关系"
  - "AI对就业市场的影响"
  - "各大科技公司在AI领域的竞争"

**ANALYTICAL (分析性查询)**
- 特征：需要综合分析、推理、多维信息
- 检索模式：`hybrid` (混合检索)
- 示例：
  - "分析AI发展趋势"
  - "比较不同机器学习算法"
  - "评估某项技术的优劣"

#### 实现细节

**LLM分析提示词构建**
```python
def _build_analysis_prompt(user_query: str) -> str:
    """构建查询分析提示词"""
    return f"""
请分析以下查询并返回JSON格式结果：

查询: {user_query}

请判断查询类型并选择检索模式：

1. FACTUAL (事实性) - 寻找具体定义、概念 → 使用 local 模式
2. RELATIONAL (关系性) - 探索实体关系、影响 → 使用 global 模式  
3. ANALYTICAL (分析性) - 需要综合分析推理 → 使用 hybrid 模式

返回格式：
{{
  "query_type": "FACTUAL|RELATIONAL|ANALYTICAL",
  "lightrag_mode": "local|global|hybrid", 
  "key_entities": ["实体1", "实体2"],
  "processed_query": "优化后的查询",
  "reasoning": "选择原因说明"
}}
"""
```

**结果验证机制**
```python
def _validate_analysis_result(analysis: dict) -> dict:
    """验证分析结果的有效性"""
    
    # 默认值设定
    defaults = {
        "query_type": "ANALYTICAL",
        "lightrag_mode": "hybrid", 
        "key_entities": [],
        "processed_query": "",
        "reasoning": "分析结果验证失败，使用默认配置"
    }
    
    # 验证必需字段
    required_fields = ["query_type", "lightrag_mode", "key_entities", "processed_query"]
    
    for field in required_fields:
        if field not in analysis:
            analysis[field] = defaults[field]
    
    # 验证查询类型
    valid_types = ["FACTUAL", "RELATIONAL", "ANALYTICAL"]
    if analysis["query_type"] not in valid_types:
        analysis["query_type"] = "ANALYTICAL"
        analysis["lightrag_mode"] = "hybrid"
    
    # 验证检索模式
    valid_modes = ["local", "global", "hybrid"]
    if analysis["lightrag_mode"] not in valid_modes:
        analysis["lightrag_mode"] = "hybrid"
    
    return analysis
```

#### 使用示例

```python
from src.agents.query_analysis import query_analysis_node
from src.core.state import AgentState

# 构建输入状态
initial_state: AgentState = {
    "user_query": "OpenAI和微软的合作关系如何？",
    "session_id": "session_123"
}

# 执行查询分析
result = query_analysis_node(initial_state)

print(f"查询类型: {result['query_type']}")        # RELATIONAL
print(f"检索模式: {result['lightrag_mode']}")     # global  
print(f"关键实体: {result['key_entities']}")      # ["OpenAI", "微软"]
print(f"优化查询: {result['processed_query']}")   # 优化后的查询文本
```

---

### 2. LightRAG检索节点 (lightrag_retrieval.py)

**主要功能**: 使用LightRAG执行智能检索，支持local/global/hybrid三种模式。

#### 核心函数: lightrag_retrieval_node

```python
def lightrag_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    LightRAG检索节点
    
    根据查询分析结果，使用对应的LightRAG检索模式：
    - local模式: 基于向量相似性的语义检索
    - global模式: 基于图谱的关系检索
    - hybrid模式: 结合向量和图谱的混合检索
    """
```

#### 检索模式详解

**Local模式 (向量检索)**
- 原理：基于向量相似度匹配
- 适用：事实性查询、定义查找
- 优势：快速、精确匹配
- 特点：返回语义相关的文档片段

**Global模式 (图谱检索)**
- 原理：基于知识图谱关系遍历
- 适用：关系性查询、影响分析
- 优势：发现复杂关联关系
- 特点：返回实体间的关系信息

**Hybrid模式 (混合检索)**
- 原理：结合向量检索和图谱检索
- 适用：复杂分析性查询
- 优势：综合信息覆盖最全面
- 特点：平衡精确性和关联性

#### 质量评分机制

```python
def _calculate_retrieval_quality(content: str, mode: str) -> float:
    """
    计算检索质量分数
    
    评分因子:
    - 内容长度和完整性 (40%)
    - 检索模式匹配度 (30%) 
    - 结果相关性 (30%)
    
    Returns:
        float: 质量分数 (0.0-1.0)
    """
    if not content:
        return 0.0
    
    # 基础内容质量 (长度因子)
    content_score = min(len(content) / 1000, 1.0)  # 1000字符为满分
    
    # 模式匹配度加权
    mode_weights = {
        "local": 0.8,   # 向量检索通常质量较稳定
        "global": 0.7,  # 图谱检索质量依赖关系完整性
        "hybrid": 0.9   # 混合模式综合性最好
    }
    mode_score = mode_weights.get(mode, 0.5)
    
    # 综合评分
    final_score = (content_score * 0.6) + (mode_score * 0.4)
    return min(final_score, 1.0)
```

#### 错误处理机制

```python
# 检索异常处理
try:
    result = query_lightrag_sync(processed_query, retrieval_mode)
    retrieval_time = time.time() - start_time
    
    if result.get("success", False):
        # 成功处理逻辑
        return {
            "lightrag_results": {...},
            "retrieval_score": quality_score,
            "retrieval_success": True
        }
    else:
        # 失败处理逻辑  
        logger.error(f"❌ LightRAG 检索失败: {result.get('error', '未知错误')}")
        return {
            "lightrag_results": {...},
            "retrieval_score": 0.0,
            "retrieval_success": False
        }
        
except Exception as e:
    # 异常处理逻辑
    logger.error(f"❌ LightRAG 检索异常: {e}")
    return {
        "lightrag_results": {...},
        "retrieval_score": 0.0, 
        "retrieval_success": False
    }
```

#### 使用示例

```python
from src.agents.lightrag_retrieval import lightrag_retrieval_node

# 输入状态（来自查询分析节点）
state_with_analysis = {
    "user_query": "什么是深度学习？",
    "query_type": "FACTUAL",
    "lightrag_mode": "local",
    "processed_query": "深度学习的定义和基本概念"
}

# 执行检索
retrieval_result = lightrag_retrieval_node(state_with_analysis)

print(f"检索成功: {retrieval_result['retrieval_success']}")
print(f"质量分数: {retrieval_result['retrieval_score']:.2f}")
print(f"内容长度: {len(retrieval_result['lightrag_results']['content'])}")
```

---

### 3. 质量评估节点 (quality_assessment.py)

**主要功能**: 评估LightRAG检索结果的质量，决定是否需要网络搜索补充。

#### 核心函数: quality_assessment_node

```python
def quality_assessment_node(state: AgentState) -> Dict[str, Any]:
    """
    质量评估节点
    
    评估维度:
    - 检索成功率 (30%)
    - 内容完整性 (25%) 
    - 实体覆盖度 (20%)
    - 模式有效性 (15%)
    - 查询特异性 (10%)
    """
```

#### 多维度评估体系

**评估维度权重配置**
```python
weights = {
    "retrieval_score": 0.3,        # 检索质量分数
    "content_completeness": 0.25,   # 内容完整性
    "entity_coverage": 0.2,         # 实体覆盖度
    "mode_effectiveness": 0.15,     # 模式有效性
    "query_specificity": 0.1        # 查询特异性
}
```

**综合评估逻辑**
```python
def _comprehensive_quality_assessment(state: AgentState) -> QualityAssessment:
    """综合质量评估"""
    
    # 评估各个维度
    factors = {
        "retrieval_score": _evaluate_retrieval_score(state),
        "content_completeness": _evaluate_content_completeness(state), 
        "entity_coverage": _evaluate_entity_coverage(state),
        "mode_effectiveness": _evaluate_mode_effectiveness(state),
        "query_specificity": _evaluate_query_specificity(state)
    }
    
    # 加权计算综合分数
    weighted_score = sum(
        factors[factor] * weights[factor] 
        for factor in factors
    )
    
    # 动态阈值计算
    dynamic_threshold = _calculate_dynamic_threshold(state.get("query_type", "ANALYTICAL"))
    
    # 决策是否需要网络搜索
    need_web_search = weighted_score < dynamic_threshold
    
    return QualityAssessment(
        confidence_score=weighted_score,
        confidence_breakdown=factors,
        need_web_search=need_web_search,
        threshold=dynamic_threshold,
        reason=_generate_assessment_reason(factors, weighted_score, dynamic_threshold)
    )
```

#### 评估维度详解

**1. 检索成功率评估**
```python
def _evaluate_retrieval_score(state: AgentState) -> float:
    """评估检索成功率"""
    if not state.get("retrieval_success", False):
        return 0.0
    
    retrieval_score = state.get("retrieval_score", 0.0)
    return min(retrieval_score, 1.0)
```

**2. 内容完整性评估**
```python
def _evaluate_content_completeness(state: AgentState) -> float:
    """评估内容完整性"""
    lightrag_results = state.get("lightrag_results", {})
    content = lightrag_results.get("content", "")
    
    if not content:
        return 0.0
    
    # 内容长度评分
    length_score = min(len(content) / 800, 1.0)  # 800字符为基准
    
    # 结构完整性评分 (简单启发式)
    structure_indicators = [
        "。" in content,  # 包含完整句子
        len(content.split()) > 10,  # 词汇量充足
        not content.endswith("..."),  # 内容不截断
    ]
    structure_score = sum(structure_indicators) / len(structure_indicators)
    
    return (length_score * 0.7) + (structure_score * 0.3)
```

**3. 实体覆盖度评估**
```python
def _evaluate_entity_coverage(state: AgentState) -> float:
    """评估关键实体覆盖度"""
    key_entities = state.get("key_entities", [])
    if not key_entities:
        return 1.0  # 没有关键实体要求时认为完全覆盖
    
    lightrag_results = state.get("lightrag_results", {})
    content = lightrag_results.get("content", "").lower()
    
    # 检查实体在内容中的出现
    covered_entities = 0
    for entity in key_entities:
        if entity.lower() in content:
            covered_entities += 1
    
    coverage_ratio = covered_entities / len(key_entities)
    return coverage_ratio
```

**4. 模式有效性评估**
```python
def _evaluate_mode_effectiveness(state: AgentState) -> float:
    """评估检索模式有效性"""
    query_type = state.get("query_type", "ANALYTICAL")
    lightrag_mode = state.get("lightrag_mode", "hybrid")
    
    # 模式匹配度评分
    optimal_modes = {
        "FACTUAL": "local",
        "RELATIONAL": "global", 
        "ANALYTICAL": "hybrid"
    }
    
    if optimal_modes.get(query_type) == lightrag_mode:
        return 1.0  # 完美匹配
    elif lightrag_mode == "hybrid":
        return 0.8  # hybrid模式通用性好
    else:
        return 0.6  # 部分匹配
```

**5. 查询特异性评估**
```python
def _evaluate_query_specificity(state: AgentState) -> float:
    """评估查询特异性"""
    user_query = state.get("user_query", "")
    
    # 查询复杂度指标
    complexity_indicators = [
        len(user_query) > 20,  # 查询长度
        "?" in user_query,     # 明确问题
        any(word in user_query.lower() for word in ["如何", "为什么", "什么", "分析"]),  # 问询词
        len(user_query.split()) > 5,  # 词汇数量
    ]
    
    complexity_score = sum(complexity_indicators) / len(complexity_indicators)
    return complexity_score
```

#### 动态阈值机制

```python
def _calculate_dynamic_threshold(query_type: str) -> float:
    """根据查询类型计算动态阈值"""
    
    base_thresholds = {
        "FACTUAL": 0.7,      # 事实性查询要求高精确度
        "RELATIONAL": 0.6,   # 关系性查询要求中等精确度
        "ANALYTICAL": 0.5    # 分析性查询容忍度更高
    }
    
    return base_thresholds.get(query_type, 0.6)
```

#### 使用示例

```python
from src.agents.quality_assessment import quality_assessment_node

# 输入状态（来自检索节点）
state_with_retrieval = {
    "user_query": "深度学习和机器学习的区别",
    "query_type": "ANALYTICAL", 
    "lightrag_mode": "hybrid",
    "key_entities": ["深度学习", "机器学习"],
    "lightrag_results": {
        "content": "深度学习是机器学习的一个子集...(800字内容)",
        "mode": "hybrid"
    },
    "retrieval_success": True,
    "retrieval_score": 0.85
}

# 执行质量评估
assessment_result = quality_assessment_node(state_with_retrieval)

print(f"综合置信度: {assessment_result['confidence_score']:.2f}")
print(f"需要网络搜索: {assessment_result['need_web_search']}")
print(f"评估原因: {assessment_result['assessment_reason']}")

# 查看详细分解
for factor, score in assessment_result['confidence_breakdown'].items():
    print(f"  {factor}: {score:.2f}")
```

---

### 4. 网络搜索节点 (web_search.py)

**主要功能**: 当本地信息不足时，使用Tavily API进行网络搜索补充。

#### 核心函数: web_search_node

```python
def web_search_node(state: AgentState) -> Dict[str, Any]:
    """
    网络搜索节点
    
    搜索策略:
    - 根据查询类型调整搜索深度
    - 动态调整结果数量
    - 优化搜索查询
    - 结果过滤和排序
    """
```

#### 条件执行机制

```python
# 检查是否需要网络搜索
need_web_search = state.get("need_web_search", False)
if not need_web_search:
    logger.info("无需网络搜索，跳过此节点")
    return {"web_results": []}

# 检查API密钥配置
if not config.TAVILY_API_KEY:
    logger.error("Tavily API密钥未配置，无法进行网络搜索")
    return {
        "web_results": [],
        "web_search_summary": "API密钥未配置，网络搜索失败"
    }
```

#### 搜索策略优化

**查询优化机制**
```python
def _build_search_query(state: AgentState) -> str:
    """构建优化的搜索查询"""
    user_query = state.get("user_query", "")
    query_type = state.get("query_type", "ANALYTICAL")
    key_entities = state.get("key_entities", [])
    
    # 基础查询优化
    optimized_query = user_query
    
    # 根据查询类型添加修饰词
    if query_type == "FACTUAL":
        optimized_query = f"什么是 {optimized_query} 定义 概念"
    elif query_type == "RELATIONAL": 
        optimized_query = f"{optimized_query} 关系 影响 联系"
    elif query_type == "ANALYTICAL":
        optimized_query = f"{optimized_query} 分析 趋势 评估"
    
    # 添加关键实体增强
    if key_entities:
        entity_string = " ".join(key_entities[:3])  # 最多3个实体
        optimized_query = f"{optimized_query} {entity_string}"
    
    return optimized_query
```

**搜索参数配置**
```python
def _get_search_parameters(state: AgentState) -> dict:
    """根据查询类型配置搜索参数"""
    query_type = state.get("query_type", "ANALYTICAL")
    
    # 基础搜索参数
    base_params = {
        "max_results": 5,
        "search_depth": "basic",
        "include_answer": True,
        "include_raw_content": False
    }
    
    # 根据查询类型调整参数
    if query_type == "FACTUAL":
        base_params.update({
            "max_results": 3,  # 事实性查询需要精确结果
            "search_depth": "basic"
        })
    elif query_type == "RELATIONAL":
        base_params.update({
            "max_results": 5,  # 关系性查询需要多个来源
            "search_depth": "advanced"
        })
    elif query_type == "ANALYTICAL":
        base_params.update({
            "max_results": 7,  # 分析性查询需要全面信息
            "search_depth": "advanced"
        })
    
    return base_params
```

#### 搜索执行机制

```python
def _execute_web_search(state: AgentState) -> List[Dict[str, Any]]:
    """执行网络搜索"""
    
    # 构建搜索查询和参数
    search_query = _build_search_query(state)
    search_params = _get_search_parameters(state)
    
    logger.info(f"搜索查询: {search_query}")
    logger.info(f"搜索参数: {search_params}")
    
    try:
        # 初始化Tavily搜索客户端
        tavily = TavilySearchAPIWrapper(api_key=config.TAVILY_API_KEY)
        
        # 执行搜索
        search_results = tavily.search(
            query=search_query,
            **search_params
        )
        
        # 处理搜索结果
        if search_results and isinstance(search_results, list):
            return search_results
        else:
            logger.warning(f"搜索返回格式异常: {type(search_results)}")
            return []
            
    except Exception as e:
        logger.error(f"Tavily搜索执行失败: {e}")
        return []
```

#### 结果处理和过滤

```python
def _process_search_results(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """处理和过滤搜索结果"""
    
    processed_results = []
    
    for result in search_results:
        try:
            # 提取标准化字段
            processed_result = {
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "url": result.get("url", ""),
                "score": result.get("score", 0.0),
                "source_type": "web_search",
                "published_date": result.get("published_date", ""),
                "raw_content": result.get("raw_content", "")
            }
            
            # 内容质量过滤
            if len(processed_result["content"]) < 50:
                continue  # 跳过内容过短的结果
            
            if not processed_result["title"]:
                continue  # 跳过没有标题的结果
            
            processed_results.append(processed_result)
            
        except Exception as e:
            logger.warning(f"处理搜索结果时出错: {e}")
            continue
    
    # 按分数排序
    processed_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 限制结果数量
    return processed_results[:5]
```

#### 使用示例

```python
from src.agents.web_search import web_search_node

# 输入状态（来自质量评估节点）
state_needing_search = {
    "user_query": "2024年AI最新发展趋势",
    "query_type": "ANALYTICAL",
    "need_web_search": True,
    "key_entities": ["AI", "人工智能", "2024"],
    "confidence_score": 0.4  # 低于阈值，需要搜索
}

# 执行网络搜索
search_result = web_search_node(state_needing_search)

print(f"搜索结果数量: {len(search_result['web_results'])}")
print(f"搜索摘要: {search_result['web_search_summary']}")

# 查看搜索结果
for i, result in enumerate(search_result['web_results']):
    print(f"\n结果 {i+1}:")
    print(f"  标题: {result['title']}")
    print(f"  分数: {result['score']:.2f}")
    print(f"  URL: {result['url']}")
    print(f"  内容: {result['content'][:100]}...")
```

---

### 5. 答案生成节点 (answer_generation.py)

**主要功能**: 整合所有信息源，生成最终答案，提供来源标注。

#### 核心函数: answer_generation_node

```python
def answer_generation_node(state: AgentState) -> Dict[str, Any]:
    """
    答案生成节点
    
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

#### 信息源整合机制

**上下文信息收集**
```python
def _collect_context_information(state: AgentState) -> Dict[str, Any]:
    """收集所有上下文信息"""
    
    context_info = {
        "context_parts": [],
        "source_types": [],
        "primary_source": None,
        "supplementary_sources": []
    }
    
    # 1. 收集LightRAG检索结果
    lightrag_results = state.get("lightrag_results", {})
    if lightrag_results.get("content"):
        context_info["context_parts"].append({
            "content": lightrag_results["content"],
            "source": "lightrag_knowledge",
            "mode": lightrag_results.get("mode", "unknown"),
            "priority": 1  # 最高优先级
        })
        context_info["primary_source"] = "lightrag_knowledge"
        context_info["source_types"].append("本地知识库")
    
    # 2. 收集网络搜索结果
    web_results = state.get("web_results", [])
    for web_result in web_results[:3]:  # 最多使用前3个搜索结果
        context_info["context_parts"].append({
            "content": web_result.get("content", ""),
            "title": web_result.get("title", ""),
            "url": web_result.get("url", ""),
            "source": "web_search", 
            "priority": 2  # 次要优先级
        })
        if "网络搜索" not in context_info["source_types"]:
            context_info["source_types"].append("网络搜索")
        context_info["supplementary_sources"].append("web_search")
    
    # 3. 统计信息源
    context_info["total_sources"] = len(context_info["context_parts"])
    context_info["has_local_knowledge"] = any(
        part["source"] == "lightrag_knowledge" 
        for part in context_info["context_parts"]
    )
    context_info["has_web_supplement"] = any(
        part["source"] == "web_search" 
        for part in context_info["context_parts"]
    )
    
    return context_info
```

#### 答案生成提示词构建

```python
def _build_answer_prompt(state: AgentState, context_info: Dict[str, Any]) -> str:
    """构建答案生成提示词"""
    
    user_query = state.get("user_query", "")
    query_type = state.get("query_type", "ANALYTICAL")
    lightrag_mode = state.get("lightrag_mode", "hybrid")
    
    # 构建上下文内容
    context_sections = []
    
    for i, context_part in enumerate(context_info["context_parts"]):
        source_type = context_part["source"]
        content = context_part["content"]
        
        if source_type == "lightrag_knowledge":
            context_sections.append(f"【本地知识库 - {context_part.get('mode', 'unknown')}模式】\n{content}")
        elif source_type == "web_search":
            title = context_part.get("title", "网络资料")
            context_sections.append(f"【网络搜索结果 - {title}】\n{content}")
    
    # 构建完整提示词
    prompt = f"""
请基于以下信息回答用户问题，要求准确、全面、有条理。

用户问题: {user_query}
查询类型: {query_type}
检索模式: {lightrag_mode}

参考信息:
{chr(10).join(context_sections)}

回答要求:
1. 直接回答用户问题，避免重复问题内容
2. 优先使用本地知识库信息，用网络信息补充
3. 保持回答的逻辑清晰和结构完整
4. 如果信息不足，诚实说明局限性
5. 根据查询类型调整回答风格：
   - FACTUAL: 提供准确定义和事实
   - RELATIONAL: 重点阐述关系和影响
   - ANALYTICAL: 进行深入分析和总结

请生成回答：
"""
    
    return prompt
```

#### LLM答案生成

```python
def _generate_answer_with_llm(answer_prompt: str) -> str:
    """使用LLM生成答案"""
    
    try:
        # 初始化LLM客户端
        llm = ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL
        )
        
        # 生成答案
        response = llm.invoke(answer_prompt)
        final_answer = response.content.strip()
        
        # 答案质量检查
        if len(final_answer) < 50:
            return "抱歉，生成的答案过短，请重新提问或提供更多上下文。"
        
        return final_answer
        
    except Exception as e:
        logger.error(f"LLM答案生成失败: {e}")
        return f"抱歉，答案生成过程中发生错误: {str(e)}"
```

#### 答案置信度计算

```python
def _calculate_answer_confidence(state: AgentState, context_info: Dict[str, Any]) -> float:
    """计算答案置信度"""
    
    confidence_factors = []
    
    # 1. 信息源质量因子 (40%)
    source_quality = 0.0
    if context_info.get("has_local_knowledge"):
        source_quality += 0.7  # 本地知识库贡献
    if context_info.get("has_web_supplement"):
        source_quality += 0.3  # 网络搜索贡献
    confidence_factors.append(("source_quality", source_quality, 0.4))
    
    # 2. 信息源数量因子 (20%)
    source_count = context_info.get("total_sources", 0)
    source_count_score = min(source_count / 3.0, 1.0)  # 3个来源为满分
    confidence_factors.append(("source_count", source_count_score, 0.2))
    
    # 3. 检索成功率因子 (25%)
    retrieval_success = state.get("retrieval_success", False)
    retrieval_score = state.get("retrieval_score", 0.0) if retrieval_success else 0.0
    confidence_factors.append(("retrieval_quality", retrieval_score, 0.25))
    
    # 4. 质量评估因子 (15%)
    confidence_score = state.get("confidence_score", 0.0)
    confidence_factors.append(("confidence_assessment", confidence_score, 0.15))
    
    # 加权计算总置信度
    total_confidence = sum(
        score * weight 
        for _, score, weight in confidence_factors
    )
    
    return min(total_confidence, 1.0)
```

#### 信息来源整理

```python
def _organize_sources(context_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """整理信息来源列表"""
    
    sources = []
    
    for context_part in context_info["context_parts"]:
        source_info = {
            "type": context_part["source"],
            "confidence": 0.0
        }
        
        if context_part["source"] == "lightrag_knowledge":
            source_info.update({
                "content": context_part["content"][:200] + "...",  # 截取预览
                "mode": context_part.get("mode", "unknown"),
                "confidence": 0.8
            })
        elif context_part["source"] == "web_search":
            source_info.update({
                "title": context_part.get("title", "网络资料"),
                "url": context_part.get("url", ""),
                "content": context_part["content"][:200] + "...",
                "confidence": 0.6
            })
        
        sources.append(source_info)
    
    # 按置信度排序
    sources.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    return sources
```

#### 使用示例

```python
from src.agents.answer_generation import answer_generation_node

# 输入状态（包含所有前序节点结果）
complete_state = {
    "user_query": "深度学习和机器学习有什么区别？",
    "query_type": "ANALYTICAL",
    "lightrag_mode": "hybrid",
    "lightrag_results": {
        "content": "深度学习是机器学习的一个子领域...(详细内容)",
        "mode": "hybrid"
    },
    "retrieval_success": True,
    "retrieval_score": 0.85,
    "confidence_score": 0.75,
    "need_web_search": True,
    "web_results": [
        {
            "title": "深度学习vs机器学习：完整对比指南",
            "content": "深度学习使用神经网络...(网络内容)",
            "url": "https://example.com/article",
            "score": 0.9
        }
    ]
}

# 执行答案生成
final_result = answer_generation_node(complete_state)

print(f"最终答案:\n{final_result['final_answer']}")
print(f"\n答案置信度: {final_result['answer_confidence']:.2f}")
print(f"使用的信息源数量: {final_result['context_used']}")
print(f"检索模式: {final_result['lightrag_mode_used']}")

# 查看信息来源
print(f"\n信息来源:")
for i, source in enumerate(final_result['sources']):
    print(f"  {i+1}. {source['type']} (置信度: {source.get('confidence', 0):.2f})")
    if source.get('title'):
        print(f"     标题: {source['title']}")
    if source.get('url'):
        print(f"     链接: {source['url']}")
```

---

## 节点协作机制

### 状态传递流程

1. **查询分析** → 识别查询类型，选择检索模式
2. **LightRAG检索** → 执行本地知识检索，评估质量
3. **质量评估** → 多维度评估，决定是否需要补充搜索
4. **网络搜索** (条件性) → 补充最新信息
5. **答案生成** → 整合所有信息，生成最终答案

### 错误处理策略

**节点级错误处理**
- 每个节点都有独立的异常捕获
- 失败时返回默认值，不中断整个流程
- 详细的错误日志记录

**工作流级容错机制**
- 某个节点失败不影响后续节点执行
- 智能降级处理 (如检索失败时直接进行网络搜索)
- 多重备选方案

### 性能优化策略

**并行处理可能**
- 查询分析和某些预处理可以并行
- 网络搜索可以异步执行
- 缓存机制减少重复计算

**资源管理**
- 合理的LLM调用次数控制
- 网络搜索结果数量限制
- 内存使用优化

---

## 扩展开发指南

### 添加新节点

1. **创建节点文件**
```python
# src/agents/new_node.py
def new_node_function(state: AgentState) -> Dict[str, Any]:
    """新节点功能描述"""
    
    # 获取所需的状态信息
    input_data = state.get("input_field", "")
    
    # 执行节点逻辑
    try:
        result = process_data(input_data)
        
        return {
            "new_field": result,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"新节点执行失败: {e}")
        return {
            "new_field": "",
            "success": False
        }
```

2. **更新状态定义**
```python
# 在 src/core/state.py 中添加新字段
class AgentState(TypedDict):
    # 现有字段...
    new_field: str
    success: bool
```

3. **在工作流中注册**
```python
# 在 workflow.py 或 enhanced_workflow.py 中
def _add_nodes(self):
    # 现有节点...
    self.graph.add_node("new_node", new_node_function)

def _add_edges(self):
    # 添加连接
    self.graph.add_edge("previous_node", "new_node")
    self.graph.add_edge("new_node", "next_node")
```

### 节点功能扩展

**增强查询分析**
- 添加更复杂的查询分类逻辑
- 支持多语言查询分析
- 集成意图识别模型

**优化检索策略**
- 实现adaptive检索模式
- 添加检索结果排序算法
- 支持多轮检索

**增强质量评估**
- 添加更多评估维度
- 实现机器学习评估模型
- 支持用户反馈学习

**扩展搜索功能**
- 支持多个搜索引擎
- 添加搜索结果去重
- 实现智能搜索策略

**优化答案生成**
- 支持不同答案风格
- 添加多轮对话能力
- 实现答案个性化

---

## 故障排除

### 常见问题诊断

**查询分析失败**
```python
# 检查LLM配置
from src.core.config import config

def test_query_analysis():
    if not config.LLM_API_KEY:
        print("❌ LLM API密钥未配置")
        return False
    
    # 测试简单查询分析
    from src.agents.query_analysis import query_analysis_node
    
    test_state = {"user_query": "什么是AI？", "session_id": "test"}
    try:
        result = query_analysis_node(test_state)
        print("✅ 查询分析正常")
        return True
    except Exception as e:
        print(f"❌ 查询分析失败: {e}")
        return False
```

**检索节点问题**
```python
def test_lightrag_retrieval():
    # 检查LightRAG客户端
    from src.utils.lightrag_client import query_lightrag_sync
    
    try:
        result = query_lightrag_sync("测试查询", "local")
        if result.get("success"):
            print("✅ LightRAG检索正常")
        else:
            print(f"❌ LightRAG检索失败: {result.get('error')}")
    except Exception as e:
        print(f"❌ LightRAG检索异常: {e}")
```

**网络搜索问题**
```python
def test_web_search():
    from src.core.config import config
    
    if not config.TAVILY_API_KEY:
        print("❌ Tavily API密钥未配置")
        return False
    
    # 测试搜索功能
    try:
        from tavily import TavilySearchAPIWrapper
        tavily = TavilySearchAPIWrapper(api_key=config.TAVILY_API_KEY)
        results = tavily.search("AI发展", max_results=1)
        print("✅ 网络搜索正常")
        return True
    except Exception as e:
        print(f"❌ 网络搜索失败: {e}")
        return False
```

### 性能调优建议

**节点执行时间优化**
- 监控每个节点的执行时间
- 优化LLM调用参数
- 实现结果缓存机制

**内存使用优化**
- 及时清理大型数据结构
- 控制上下文信息大小
- 优化状态数据传递

**并发性能提升**
- 使用异步处理
- 实现节点间并行执行
- 优化I/O操作

---

**📝 说明**: 本文档详细介绍了所有工作流节点的实现细节。如需了解其他模块，请查看对应的技术文档。