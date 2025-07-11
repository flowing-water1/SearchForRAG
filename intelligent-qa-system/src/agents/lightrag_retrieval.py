"""
LightRAG 检索节点
使用 LightRAG 执行智能检索，支持 local/global/hybrid 三种模式
"""

from typing import Dict, Any
import time

from ..core.config import config
from ..core.state import AgentState, LightRAGResult
from ..utils.simple_logger import get_simple_logger
from ..utils.lightrag_client import query_lightrag_sync

logger = get_simple_logger(__name__)

def lightrag_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    LightRAG 检索节点
    
    根据查询分析结果，使用对应的 LightRAG 检索模式获取相关信息：
    - local模式: 基于向量相似性的语义检索
    - global模式: 基于图谱的关系检索
    - hybrid模式: 结合向量和图谱的混合检索
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典
    """
    retrieval_mode = state.get("lightrag_mode", "hybrid")
    processed_query = state.get("processed_query", state["user_query"])
    
    logger.info(f"开始 LightRAG 检索 (模式: {retrieval_mode})")
    logger.info(f"查询: {processed_query[:100]}...")
    
    start_time = time.time()
    
    try:
        # 执行 LightRAG 检索
        result = query_lightrag_sync(processed_query, retrieval_mode)
        
        retrieval_time = time.time() - start_time
        
        if result.get("success", False):
            content = result.get("content", "")
            
            # 计算检索质量分数
            quality_score = _calculate_retrieval_quality(content, retrieval_mode)
            
            logger.info(f"✅ LightRAG 检索完成 ({retrieval_time:.2f}s)")
            logger.info(f"检索到内容长度: {len(content)} 字符")
            logger.info(f"质量分数: {quality_score:.2f}")
            
            return {
                "lightrag_results": {
                    "content": content,
                    "mode": retrieval_mode,
                    "query": processed_query,
                    "source": "lightrag",
                    "retrieval_time": retrieval_time
                },
                "retrieval_score": quality_score,
                "retrieval_success": True
            }
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"❌ LightRAG 检索失败: {error_msg}")
            
            return {
                "lightrag_results": {
                    "content": "",
                    "mode": retrieval_mode,
                    "query": processed_query,
                    "source": "lightrag",
                    "error": error_msg,
                    "retrieval_time": retrieval_time
                },
                "retrieval_score": 0.0,
                "retrieval_success": False
            }
            
    except Exception as e:
        retrieval_time = time.time() - start_time
        logger.error(f"❌ LightRAG 检索异常: {e}")
        
        return {
            "lightrag_results": {
                "content": "",
                "mode": retrieval_mode,
                "query": processed_query,
                "source": "lightrag",
                "error": str(e),
                "retrieval_time": retrieval_time
            },
            "retrieval_score": 0.0,
            "retrieval_success": False
        }

def _calculate_retrieval_quality(content: str, mode: str) -> float:
    """
    计算 LightRAG 检索结果的质量分数
    
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
    
    # 内容长度评分 (基于经验值)
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
    
    # 内容质量评估
    quality_indicators = _assess_content_quality(content)
    quality_score = sum(quality_indicators.values()) / len(quality_indicators)
    
    # 综合计算
    final_score = (length_score * 0.4 + quality_score * 0.4 + mode_bonus * 0.2)
    
    return min(final_score, 1.0)

def _assess_content_quality(content: str) -> Dict[str, float]:
    """
    评估内容质量的多个指标
    
    Args:
        content: 内容文本
        
    Returns:
        质量指标字典
    """
    indicators = {}
    
    # 1. 信息密度 (非空行比例)
    lines = content.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    indicators['information_density'] = len(non_empty_lines) / max(len(lines), 1)
    
    # 2. 结构化程度 (是否包含标题、列表等)
    structure_markers = ['#', '*', '-', '1.', '2.', '•']
    structure_score = 0
    for marker in structure_markers:
        if marker in content:
            structure_score += 0.2
    indicators['structure_score'] = min(structure_score, 1.0)
    
    # 3. 专业术语密度 (大写词汇比例，简单估算)
    words = content.split()
    capitalized_words = [word for word in words if word.istitle() and len(word) > 2]
    indicators['terminology_density'] = min(len(capitalized_words) / max(len(words), 1) * 10, 1.0)
    
    # 4. 内容连贯性 (段落数量评估)
    paragraphs = [p for p in content.split('\n\n') if p.strip()]
    if len(paragraphs) > 1:
        indicators['coherence'] = min(len(paragraphs) / 10, 1.0)
    else:
        indicators['coherence'] = 0.5
    
    # 5. 信息完整性 (是否包含解释性内容)
    explanation_keywords = ['因为', '由于', '所以', '因此', '例如', '比如', '包括', '具体来说']
    explanation_count = sum(1 for keyword in explanation_keywords if keyword in content)
    indicators['completeness'] = min(explanation_count / 5, 1.0)
    
    return indicators

def get_retrieval_mode_info() -> Dict[str, Dict[str, Any]]:
    """
    获取检索模式信息
    
    Returns:
        检索模式信息字典
    """
    return {
        "local": {
            "name": "本地模式",
            "description": "基于向量相似性的语义检索",
            "best_for": "事实性查询、定义查询、具体信息查找",
            "advantages": ["精确匹配", "快速响应", "语义理解"],
            "example_queries": [
                "什么是机器学习？",
                "Python的基本语法",
                "深度学习的定义"
            ]
        },
        "global": {
            "name": "全局模式", 
            "description": "基于图谱的关系检索",
            "best_for": "关系性查询、实体联系、影响分析",
            "advantages": ["关系推理", "图谱遍历", "实体连接"],
            "example_queries": [
                "谁发明了机器学习？",
                "A和B之间的关系",
                "机器学习的发展历史"
            ]
        },
        "hybrid": {
            "name": "混合模式",
            "description": "结合向量和图谱的混合检索",
            "best_for": "复杂查询、综合分析、多维度问题",
            "advantages": ["全面覆盖", "多角度分析", "最佳效果"],
            "example_queries": [
                "机器学习的发展趋势及其影响",
                "比较不同算法的优缺点",
                "AI技术的现状和未来"
            ]
        }
    }

def get_retrieval_statistics() -> Dict[str, Any]:
    """
    获取检索统计信息（未来可扩展）
    
    Returns:
        检索统计信息
    """
    return {
        "total_queries": 0,
        "mode_usage": {
            "local": 0,
            "global": 0,
            "hybrid": 0
        },
        "average_quality_score": 0.0,
        "average_retrieval_time": 0.0
    }