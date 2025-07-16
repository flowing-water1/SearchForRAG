"""
策略路由节点
根据查询分析结果，决定使用哪种 LightRAG 检索策略

升级到LangGraph结构化输出技术:
- 使用Pydantic RouteDecision模型确保路由决策的一致性
- 添加自动验证和错误修正机制
- 进一步提升系统可靠性
"""

from typing import Dict, Any

from ..core.state import AgentState
from ..utils.simple_logger import get_simple_logger
from ..schemas import RouteDecision, QueryType, LightRAGMode

logger = get_simple_logger(__name__)

def strategy_route_node(state: AgentState) -> Dict[str, Any]:
    """
    策略路由节点 (升级版)
    
    根据查询分析节点的结果，决定使用哪种检索策略：
    - FACTUAL (事实性) → local_search: 本地向量检索
    - RELATIONAL (关系性) → global_search: 全局图检索  
    - ANALYTICAL (分析性) → hybrid_search: 混合检索
    
    升级特性：
    - 使用Pydantic RouteDecision模型确保类型安全
    - 自动验证和修正路由决策
    - 增强的错误处理和日志记录
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典，主要确认路由决策
    """
    try:
        # 提取状态信息
        query_type = state.get("query_type", "ANALYTICAL")
        lightrag_mode = state.get("lightrag_mode", "hybrid")
        user_query = state.get("user_query", "")
        
        logger.info(f"🚦 策略路由决策: 查询类型={query_type}, LightRAG模式={lightrag_mode}")
        logger.info(f"查询内容: {user_query[:100]}...")
        
        # 🎯 使用结构化方法创建和验证路由决策
        route_decision = _create_validated_route_decision(
            query_type=query_type,
            lightrag_mode=lightrag_mode,
            user_query=user_query
        )
        
        logger.info(f"✅ 结构化路由决策完成: {route_decision.query_type} → {route_decision.lightrag_mode} → {route_decision.next_node}")
        
        # 🔄 保持兼容性：转换为字典格式返回
        return route_decision.to_dict()
        
    except Exception as e:
        logger.error(f"❌ 策略路由失败: {e}")
        
        # 🛡️ fallback到安全的默认路由
        fallback_decision = RouteDecision(
            lightrag_mode="hybrid",
            query_type=state.get("query_type", "ANALYTICAL"),
            next_node="hybrid_search",
            route_decision={
                "input_query_type": state.get("query_type", "ANALYTICAL"),
                "selected_mode": "hybrid",
                "target_node": "hybrid_search",
                "reasoning": f"路由决策失败，使用安全的hybrid模式。错误: {str(e)}"
            }
        )
        
        logger.info(f"🔄 使用fallback路由决策: hybrid_search")
        return fallback_decision.to_dict()


def _create_validated_route_decision(query_type: str, lightrag_mode: str, user_query: str) -> RouteDecision:
    """
    创建并验证路由决策
    
    Args:
        query_type: 查询类型
        lightrag_mode: LightRAG检索模式
        user_query: 用户查询
        
    Returns:
        验证后的RouteDecision实例
    """
    # 验证查询类型和检索模式的映射关系
    expected_mapping = {
        "FACTUAL": "local",
        "RELATIONAL": "global", 
        "ANALYTICAL": "hybrid"
    }
    
    expected_mode = expected_mapping.get(query_type, "hybrid")
    if lightrag_mode != expected_mode:
        logger.warning(f"🔧 检索模式不匹配: 期望{expected_mode}, 实际{lightrag_mode}")
        # 自动修正
        lightrag_mode = expected_mode
        logger.info(f"✅ 已自动修正为: {lightrag_mode}")
    
    # 路由决策映射
    route_mapping = {
        "local": "local_search",
        "global": "global_search",
        "hybrid": "hybrid_search",
        "naive": "local_search",    # 降级到local
        "mix": "hybrid_search"      # 降级到hybrid
    }
    
    next_node = route_mapping.get(lightrag_mode, "hybrid_search")
    
    # 🎯 创建结构化路由决策
    route_decision = RouteDecision(
        lightrag_mode=lightrag_mode,
        query_type=query_type,
        next_node=next_node,
        route_decision={
            "input_query_type": query_type,
            "selected_mode": lightrag_mode,
            "target_node": next_node,
            "reasoning": f"{query_type}类型查询使用{lightrag_mode}模式检索",
            "validation_status": "validated",
            "auto_corrected": lightrag_mode != expected_mapping.get(query_type, lightrag_mode)
        }
    )
    
    return route_decision

def get_strategy_route_mapping() -> Dict[str, str]:
    """
    获取策略路由映射关系
    
    Returns:
        策略映射字典
    """
    return {
        "FACTUAL": "local",     # 事实性查询 → 本地向量检索
        "RELATIONAL": "global", # 关系性查询 → 全局图检索
        "ANALYTICAL": "hybrid"  # 分析性查询 → 混合检索
    }

def validate_route_decision(query_type: str, lightrag_mode: str) -> bool:
    """
    验证路由决策是否合理 (升级版)
    
    Args:
        query_type: 查询类型
        lightrag_mode: LightRAG检索模式
        
    Returns:
        是否为合理的路由决策
    """
    try:
        mapping = get_strategy_route_mapping()
        expected_mode = mapping.get(query_type)
        is_valid = lightrag_mode == expected_mode
        
        if not is_valid:
            logger.warning(f"🔍 路由决策验证失败: {query_type} → {lightrag_mode} (期望: {expected_mode})")
        else:
            logger.debug(f"✅ 路由决策验证通过: {query_type} → {lightrag_mode}")
            
        return is_valid
        
    except Exception as e:
        logger.error(f"❌ 路由决策验证异常: {e}")
        return False

def get_route_statistics() -> Dict[str, Any]:
    """
    获取路由统计信息（为后续监控预留）
    
    Returns:
        路由统计数据
    """
    return {
        "total_routes": 0,
        "route_distribution": {
            "local_search": 0,
            "global_search": 0, 
            "hybrid_search": 0
        },
        "accuracy_rate": 0.0,
        "correction_rate": 0.0
    } 