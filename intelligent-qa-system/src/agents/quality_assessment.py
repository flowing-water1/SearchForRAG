"""
质量评估节点
评估 LightRAG 检索结果的质量，决定是否需要网络搜索补充
"""

from typing import Dict, Any, Tuple

from ..core.config import config
from ..core.state import AgentState, QualityAssessment
from ..utils.simple_logger import get_simple_logger

logger = get_simple_logger(__name__)

def quality_assessment_node(state: AgentState) -> Dict[str, Any]:
    """
    质量评估节点
    
    评估 LightRAG 检索结果的质量，决定是否需要网络搜索补充：
    - 分析检索结果的完整性、相关性、可信度
    - 根据查询类型设置动态阈值
    - 综合评估是否需要外部信息补充
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典
    """
    logger.info("开始质量评估...")
    
    # 获取检索结果
    lightrag_results = state.get("lightrag_results", {})
    retrieval_success = state.get("retrieval_success", False)
    retrieval_score = state.get("retrieval_score", 0.0)
    
    # 如果检索失败，必须进行网络搜索
    if not retrieval_success:
        logger.warning("LightRAG 检索失败，必须进行网络搜索")
        return {
            "confidence_score": 0.0,
            "confidence_breakdown": {
                "retrieval_score": 0.0,
                "content_completeness": 0.0,
                "entity_coverage": 0.0,
                "mode_effectiveness": 0.0
            },
            "need_web_search": True,
            "confidence_threshold": config.CONFIDENCE_THRESHOLD,
            "assessment_reason": "LightRAG检索失败，需要网络搜索补充"
        }
    
    # 执行综合质量评估
    assessment = _comprehensive_quality_assessment(state)
    
    # 记录评估结果
    logger.info(f"质量评估完成:")
    logger.info(f"  - 综合置信度: {assessment.confidence_score:.2f}")
    logger.info(f"  - 置信度阈值: {assessment.threshold:.2f}")
    logger.info(f"  - 需要网络搜索: {assessment.need_web_search}")
    logger.info(f"  - 评估原因: {assessment.reason}")
    
    # 记录详细分解
    for factor, score in assessment.confidence_breakdown.items():
        logger.debug(f"    {factor}: {score:.2f}")
    
    return {
        "confidence_score": assessment.confidence_score,
        "confidence_breakdown": assessment.confidence_breakdown,
        "need_web_search": assessment.need_web_search,
        "confidence_threshold": assessment.threshold,
        "assessment_reason": assessment.reason
    }

def _comprehensive_quality_assessment(state: AgentState) -> QualityAssessment:
    """
    综合质量评估
    
    Args:
        state: 当前工作流状态
        
    Returns:
        质量评估结果
    """
    # 评估各个维度
    factors = {
        "retrieval_score": _evaluate_retrieval_score(state),
        "content_completeness": _evaluate_content_completeness(state),
        "entity_coverage": _evaluate_entity_coverage(state),
        "mode_effectiveness": _evaluate_mode_effectiveness(state),
        "query_specificity": _evaluate_query_specificity(state)
    }
    
    # 权重配置
    weights = {
        "retrieval_score": 0.3,
        "content_completeness": 0.25,
        "entity_coverage": 0.2,
        "mode_effectiveness": 0.15,
        "query_specificity": 0.1
    }
    
    # 计算加权综合分数
    confidence_score = sum(factors[factor] * weights[factor] for factor in factors)
    
    # 根据查询类型设置动态阈值
    threshold = _get_dynamic_threshold(state)
    
    # 决定是否需要网络搜索
    need_web_search = confidence_score < threshold
    
    # 生成评估原因
    reason = _generate_assessment_reason(confidence_score, threshold, factors)
    
    return QualityAssessment(
        confidence_score=confidence_score,
        confidence_breakdown=factors,
        need_web_search=need_web_search,
        threshold=threshold,
        reason=reason
    )

def _evaluate_retrieval_score(state: AgentState) -> float:
    """评估检索基础分数"""
    return state.get("retrieval_score", 0.0)

def _evaluate_content_completeness(state: AgentState) -> float:
    """评估内容完整性"""
    lightrag_results = state.get("lightrag_results", {})
    content = lightrag_results.get("content", "")
    
    if not content:
        return 0.0
    
    content_length = len(content.strip())
    
    # 基于内容长度的完整性评估
    if content_length >= 1500:
        return 1.0
    elif content_length >= 1000:
        return 0.9
    elif content_length >= 500:
        return 0.7
    elif content_length >= 200:
        return 0.5
    elif content_length >= 100:
        return 0.3
    else:
        return 0.1

def _evaluate_entity_coverage(state: AgentState) -> float:
    """评估关键实体覆盖度"""
    expected_entities = state.get("key_entities", [])
    if not expected_entities:
        return 1.0  # 没有预期实体时返回满分
    
    lightrag_results = state.get("lightrag_results", {})
    content = lightrag_results.get("content", "").lower()
    
    if not content:
        return 0.0
    
    # 检查关键实体是否在检索结果中被提及
    covered_entities = 0
    for entity in expected_entities:
        if entity.lower() in content:
            covered_entities += 1
    
    coverage = covered_entities / len(expected_entities)
    return coverage

def _evaluate_mode_effectiveness(state: AgentState) -> float:
    """评估检索模式的有效性"""
    query_type = state.get("query_type", "")
    lightrag_mode = state.get("lightrag_mode", "")
    
    # 检查模式与查询类型的匹配度
    ideal_matches = {
        "FACTUAL": "local",
        "RELATIONAL": "global",
        "ANALYTICAL": "hybrid"
    }
    
    ideal_mode = ideal_matches.get(query_type)
    
    if ideal_mode == lightrag_mode:
        return 1.0  # 完美匹配
    elif lightrag_mode == "hybrid":
        return 0.8  # hybrid模式通常表现良好
    else:
        return 0.6  # 次优匹配

def _evaluate_query_specificity(state: AgentState) -> float:
    """评估查询特异性"""
    user_query = state.get("user_query", "")
    processed_query = state.get("processed_query", "")
    
    # 基于查询长度和复杂度的简单评估
    query_length = len(user_query.split())
    
    if query_length >= 10:
        return 1.0  # 详细查询
    elif query_length >= 5:
        return 0.8  # 中等查询
    elif query_length >= 3:
        return 0.6  # 简单查询
    else:
        return 0.4  # 过于简单的查询

def _get_dynamic_threshold(state: AgentState) -> float:
    """
    根据查询类型获取动态阈值
    
    Args:
        state: 当前工作流状态
        
    Returns:
        动态阈值
    """
    query_type = state.get("query_type", "ANALYTICAL")
    
    # 基础阈值
    base_threshold = config.CONFIDENCE_THRESHOLD
    
    # 根据查询类型调整阈值
    type_adjustments = {
        "FACTUAL": 0.1,      # 事实查询要求较高置信度
        "RELATIONAL": 0.0,   # 关系查询使用基准阈值
        "ANALYTICAL": -0.1   # 分析查询允许较低置信度
    }
    
    adjustment = type_adjustments.get(query_type, 0.0)
    threshold = base_threshold + adjustment
    
    # 确保阈值在合理范围内
    return max(0.3, min(0.9, threshold))

def _generate_assessment_reason(
    confidence_score: float,
    threshold: float,
    factors: Dict[str, float]
) -> str:
    """
    生成评估原因说明
    
    Args:
        confidence_score: 置信度分数
        threshold: 阈值
        factors: 各因素分数
        
    Returns:
        评估原因说明
    """
    # 基础原因
    base_reason = f"置信度 {confidence_score:.2f} {'<' if confidence_score < threshold else '>='} 阈值 {threshold:.2f}"
    
    # 分析主要影响因素
    sorted_factors = sorted(factors.items(), key=lambda x: x[1])
    lowest_factor, lowest_score = sorted_factors[0]
    highest_factor, highest_score = sorted_factors[-1]
    
    # 生成详细原因
    detailed_reasons = []
    
    if lowest_score < 0.5:
        factor_names = {
            "retrieval_score": "检索质量",
            "content_completeness": "内容完整性",
            "entity_coverage": "实体覆盖度",
            "mode_effectiveness": "模式有效性",
            "query_specificity": "查询特异性"
        }
        factor_name = factor_names.get(lowest_factor, lowest_factor)
        detailed_reasons.append(f"{factor_name}偏低({lowest_score:.2f})")
    
    if highest_score > 0.8:
        factor_names = {
            "retrieval_score": "检索质量",
            "content_completeness": "内容完整性",
            "entity_coverage": "实体覆盖度",
            "mode_effectiveness": "模式有效性",
            "query_specificity": "查询特异性"
        }
        factor_name = factor_names.get(highest_factor, highest_factor)
        detailed_reasons.append(f"{factor_name}较高({highest_score:.2f})")
    
    if detailed_reasons:
        return f"{base_reason}；{'; '.join(detailed_reasons)}"
    else:
        return base_reason

def get_assessment_guidelines() -> Dict[str, Any]:
    """
    获取评估指南
    
    Returns:
        评估指南信息
    """
    return {
        "factors": {
            "retrieval_score": {
                "description": "LightRAG检索的基础质量分数",
                "weight": 0.3,
                "range": "0.0 - 1.0"
            },
            "content_completeness": {
                "description": "检索内容的完整性",
                "weight": 0.25,
                "range": "0.0 - 1.0"
            },
            "entity_coverage": {
                "description": "关键实体的覆盖程度",
                "weight": 0.2,
                "range": "0.0 - 1.0"
            },
            "mode_effectiveness": {
                "description": "检索模式的有效性",
                "weight": 0.15,
                "range": "0.0 - 1.0"
            },
            "query_specificity": {
                "description": "查询的特异性",
                "weight": 0.1,
                "range": "0.0 - 1.0"
            }
        },
        "thresholds": {
            "FACTUAL": "基础阈值 + 0.1",
            "RELATIONAL": "基础阈值",
            "ANALYTICAL": "基础阈值 - 0.1"
        },
        "decisions": {
            "need_web_search": "置信度 < 阈值",
            "direct_answer": "置信度 >= 阈值"
        }
    }