"""
LangGraph 状态定义
定义智能问答系统的状态结构
"""

from typing import List, Optional, Dict, Any, Literal
from typing_extensions import TypedDict
from dataclasses import dataclass

class AgentState(TypedDict):
    """
    智能问答系统的全局状态定义
    
    这个状态会在整个 LangGraph 工作流中传递和更新
    """
    
    # 用户输入
    user_query: str                    # 原始用户查询
    processed_query: str               # 处理后的查询
    session_id: str                    # 会话ID
    
    # 查询分析结果
    query_type: Literal["FACTUAL", "RELATIONAL", "ANALYTICAL"]  # 查询类型
    lightrag_mode: Literal["naive", "local", "global", "hybrid", "mix"]  # HKUDS/LightRAG检索模式
    key_entities: List[str]            # 关键实体列表
    mode_reasoning: str                # 模式选择原因
    
    # HKUDS/LightRAG检索结果
    lightrag_results: Dict[str, Any]   # HKUDS/LightRAG检索结果
    retrieval_score: float             # 检索质量分数
    retrieval_success: bool            # 检索是否成功
    
    # 质量评估结果
    confidence_score: float            # 置信度分数
    confidence_breakdown: Dict[str, float]  # 置信度详细分解
    need_web_search: bool              # 是否需要网络搜索
    confidence_threshold: float        # 置信度阈值
    assessment_reason: str             # 评估原因
    
    # 网络搜索结果
    web_results: Optional[List[Dict[str, Any]]]  # 网络搜索结果
    web_search_summary: Optional[str]           # 网络搜索摘要
    
    # 最终输出
    final_answer: str                  # 最终答案
    sources: List[Dict[str, Any]]      # 信息来源列表
    context_used: int                  # 使用的信息源数量
    lightrag_mode_used: str            # 实际使用的HKUDS/LightRAG模式
    answer_confidence: float           # 答案置信度

@dataclass
class QueryAnalysisResult:
    """查询分析结果"""
    query_type: str
    lightrag_mode: str
    key_entities: List[str]
    processed_query: str
    reasoning: str

@dataclass
class LightRAGResult:
    """LightRAG检索结果"""
    content: str
    mode: str
    success: bool
    query: str
    source: str
    error: Optional[str] = None

@dataclass
class QualityAssessment:
    """质量评估结果"""
    confidence_score: float
    confidence_breakdown: Dict[str, float]
    need_web_search: bool
    threshold: float
    reason: str

@dataclass
class WebSearchResult:
    """网络搜索结果"""
    title: str
    content: str
    url: str
    score: float
    source_type: str = "web_search"

@dataclass
class SourceInfo:
    """信息来源信息"""
    type: str  # "lightrag_knowledge", "web_search", "knowledge_graph"
    content: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    confidence: Optional[float] = None
    mode: Optional[str] = None
    query: Optional[str] = None