"""
LightRAG 检索基础库
提供共享的检索功能和工具函数，供专门检索节点使用
已弃用：lightrag_retrieval_node 已分化为 local_search, global_search, hybrid_search
"""

from typing import Dict, Any
import time

from ..core.state import AgentState, LightRAGResult
from ..utils.simple_logger import get_simple_logger
from ..utils.lightrag_client import query_lightrag_sync

logger = get_simple_logger(__name__)

# ==================== 已弃用的节点函数 ====================
# 此函数已被分化为 local_search_node, global_search_node, hybrid_search_node
# 保留此函数仅为向后兼容，建议使用专门的检索节点

def lightrag_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    LightRAG 检索节点 (已弃用)
    
    此函数已被分化为三个专门的检索节点：
    - local_search_node (事实性查询的向量检索)
    - global_search_node (关系性查询的图检索)  
    - hybrid_search_node (复杂查询的混合检索)
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典
    """
    logger.warning("lightrag_retrieval_node 已弃用，请使用专门的检索节点")
    
    retrieval_mode = state.get("lightrag_mode", "hybrid")
    processed_query = state.get("processed_query", state["user_query"])
    
    logger.info(f"使用兼容模式进行 LightRAG 检索 (模式: {retrieval_mode})")
    
    # 为向后兼容，仍然提供基本功能
    start_time = time.time()
    
    try:
        result = query_lightrag_sync(processed_query, retrieval_mode)
        retrieval_time = time.time() - start_time
        
        if result.get("success", False):
            content = result.get("content", "")
            quality_score = calculate_basic_quality(content, retrieval_mode)
            
            logger.info(f"✅ 兼容模式检索完成 ({retrieval_time:.2f}s)")
            
            return {
                "lightrag_results": {
                    "content": content,
                    "mode": retrieval_mode,
                    "query": processed_query,
                    "source": "lightrag_legacy",
                    "retrieval_time": retrieval_time
                },
                "retrieval_score": quality_score,
                "retrieval_success": True,
                "lightrag_mode_used": retrieval_mode
            }
        else:
            error_msg = result.get("error", "检索失败")
            logger.error(f"❌ 兼容模式检索失败: {error_msg}")
            
            return {
                "lightrag_results": {
                    "content": "",
                    "mode": retrieval_mode,
                    "query": processed_query,
                    "source": "lightrag_legacy",
                    "error": error_msg,
                    "retrieval_time": retrieval_time
                },
                "retrieval_score": 0.0,
                "retrieval_success": False,
                "lightrag_mode_used": retrieval_mode
            }
            
    except Exception as e:
        retrieval_time = time.time() - start_time
        logger.error(f"❌ 兼容模式检索异常: {e}")
        
        return {
            "lightrag_results": {
                "content": "",
                "mode": retrieval_mode,
                "query": processed_query,
                "source": "lightrag_legacy",
                "error": str(e),
                "retrieval_time": retrieval_time
            },
            "retrieval_score": 0.0,
            "retrieval_success": False,
            "lightrag_mode_used": retrieval_mode
        }

# ==================== 共享工具函数 ====================

def calculate_basic_quality(content: str, mode: str) -> float:
    """
    计算基础的检索质量分数
    
    Args:
        content: 检索到的内容
        mode: 检索模式
        
    Returns:
        质量分数 (0.0 - 1.0)
    """
    if not content or len(content.strip()) < 10:
        return 0.0
    
    # 基于内容长度的基础分数
    content_length = len(content.strip())
    
    if content_length >= 1000:
        length_score = 0.9
    elif content_length >= 500:
        length_score = 0.8
    elif content_length >= 200:
        length_score = 0.7
    elif content_length >= 100:
        length_score = 0.6
    elif content_length >= 50:
        length_score = 0.4
    else:
        length_score = 0.2
    
    # 模式复杂度奖励
    mode_bonus = {
        "local": 0.05,    # 向量检索相对简单
        "global": 0.1,    # 图检索更复杂
        "hybrid": 0.15    # 混合检索最全面
    }.get(mode, 0.05)
    
    return min(length_score + mode_bonus, 1.0)

def get_retrieval_mode_info() -> Dict[str, Dict[str, Any]]:
    """
    获取检索模式信息
    
    Returns:
        检索模式信息字典
    """
    return {
        "local": {
            "name": "本地向量检索",
            "description": "基于向量相似性的语义检索",
            "suitable_for": ["事实性查询", "定义查询", "概念解释"],
            "node_name": "local_search"
        },
        "global": {
            "name": "全局图检索", 
            "description": "基于知识图谱的关系检索",
            "suitable_for": ["关系性查询", "实体关联", "影响分析"],
            "node_name": "global_search"
        },
        "hybrid": {
            "name": "混合检索",
            "description": "结合向量和图检索的综合检索",
            "suitable_for": ["复杂分析查询", "多维度信息", "深度研究"],
            "node_name": "hybrid_search"
        }
    }

def get_retrieval_statistics() -> Dict[str, Any]:
    """
    获取检索统计信息
    
    Returns:
        统计数据字典
    """
    return {
        "legacy_usage_count": 0,
        "migration_info": {
            "status": "节点已分化",
            "new_nodes": ["local_search", "global_search", "hybrid_search"],
            "recommendation": "请使用专门的检索节点以获得更好的性能"
        }
    }