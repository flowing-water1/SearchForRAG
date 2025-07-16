"""
本地检索节点 (Local Search)
专门处理事实性查询的向量检索，使用 LightRAG Local 模式
主要依靠 PostgreSQL 向量数据库进行语义相似性检索
"""

from typing import Dict, Any
import time

from ..core.state import AgentState
from ..utils.simple_logger import get_simple_logger
from ..utils.lightrag_client import query_lightrag

logger = get_simple_logger(__name__)

async def local_search_node(state: AgentState) -> Dict[str, Any]:
    """
    本地检索节点 - LightRAG Local 模式
    
    专门处理事实性查询，主要使用PostgreSQL向量数据库进行语义相似性检索。
    适用于寻找具体事实、定义、概念等明确信息。
    
    检索策略：
    - 主要数据源：PostgreSQL 向量存储 (PGVectorStorage)
    - 检索算法：向量相似度匹配
    - 优势：快速精确的语义检索
    - 适用场景：事实查询、定义查询、概念解释
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典
    """
    processed_query = state.get("processed_query", state["user_query"])
    query_type = state.get("query_type", "FACTUAL")
    
    logger.info(f"🔍 开始本地向量检索 (PostgreSQL向量数据库)")
    logger.info(f"查询类型: {query_type}")
    logger.info(f"查询内容: {processed_query[:100]}...")
    logger.info(f"🎯 检索策略: 向量相似度匹配 (PostgreSQL PGVector)")
    
    start_time = time.time()
    
    try:
        # 固定使用 local 模式进行检索
        result = await query_lightrag(processed_query, "local")
        
        retrieval_time = time.time() - start_time
        
        if result.get("success", False):
            content = result.get("content", "")
            
            # 获取存储后端信息和模式描述
            storage_backend = result.get("storage_backend", {})
            data_source = result.get("data_source", "unknown")
            retrieval_path = result.get("retrieval_path", "unknown")
            mode_description = result.get("mode_description", {})
            
            # 计算本地检索的质量分数
            quality_score = _calculate_local_quality(content, processed_query)
            
            logger.info(f"✅ PostgreSQL向量检索完成 ({retrieval_time:.2f}s)")
            logger.info(f"📊 检索到内容长度: {len(content)} 字符")
            logger.info(f"🎯 向量检索质量分数: {quality_score:.2f}")
            logger.info(f"💾 主要数据源: PostgreSQL 向量存储")
            
            return {
                "lightrag_results": {
                    "content": content,
                    "mode": "local",
                    "query": processed_query,
                    "source": "lightrag_local",
                    "retrieval_time": retrieval_time,
                    "node_type": "local_search",
                    # 突出向量检索特性
                    "storage_backend": storage_backend,
                    "data_source": data_source,
                    "retrieval_path": retrieval_path,
                    "mode_description": mode_description,
                    # 为前端显示提供专门的向量检索描述
                    "display_info": {
                        "algorithm_name": "向量相似度检索",
                        "primary_storage": "PostgreSQL 向量数据库",
                        "storage_type": "PostgreSQL PGVector (主要) + Neo4j (备用)",
                        "complexity": "低复杂度，快速检索",
                        "best_for": "事实性查询、具体概念定义、语义匹配",
                        "search_method": "嵌入向量语义相似性匹配",
                        "data_focus": "文档片段的向量表示"
                    }
                },
                "retrieval_score": quality_score,
                "retrieval_success": True,
                "lightrag_mode_used": "local",
                "primary_database": "PostgreSQL"
            }
        else:
            error_msg = result.get("error", "PostgreSQL向量检索失败")
            logger.error(f"❌ PostgreSQL向量检索失败: {error_msg}")
            
            return {
                "lightrag_results": {
                    "content": "",
                    "mode": "local",
                    "query": processed_query,
                    "source": "lightrag_local",
                    "error": error_msg,
                    "retrieval_time": retrieval_time,
                    "node_type": "local_search"
                },
                "retrieval_score": 0.0,
                "retrieval_success": False,
                "lightrag_mode_used": "local",
                "primary_database": "PostgreSQL"
            }
            
    except Exception as e:
        retrieval_time = time.time() - start_time
        logger.error(f"❌ PostgreSQL向量检索异常: {str(e)}")
        
        return {
            "lightrag_results": {
                "content": "",
                "mode": "local", 
                "query": processed_query,
                "source": "lightrag_local",
                "error": f"向量检索异常: {str(e)}",
                "retrieval_time": retrieval_time,
                "node_type": "local_search"
            },
            "retrieval_score": 0.0,
            "retrieval_success": False,
            "lightrag_mode_used": "local",
            "primary_database": "PostgreSQL"
        }

def _calculate_local_quality(content: str, query: str) -> float:
    """
    计算本地向量检索的质量分数
    
    专门评估向量相似性检索的效果，重点关注：
    - 语义匹配度
    - 事实信息完整性
    - 定义和概念的准确性
    
    Args:
        content: 检索到的内容
        query: 查询内容
        
    Returns:
        质量分数 (0.0-1.0)
    """
    if not content or len(content.strip()) == 0:
        return 0.0
    
    # 基础分数基于内容长度（向量检索通常返回精确匹配的片段）
    length_score = min(len(content) / 800, 1.0) * 0.3  # 向量检索内容通常较为精炼
    
    # 向量检索质量评估因子
    vector_quality_factors = {
        "has_specific_facts": 0.25,     # 包含具体事实（向量检索的强项）
        "has_definitions": 0.2,         # 包含定义（向量检索的强项）
        "semantic_relevance": 0.15,     # 语义相关性（向量检索的核心）
        "factual_accuracy": 0.1         # 事实准确性指标
    }
    
    quality_score = 0.0
    content_lower = content.lower()
    query_lower = query.lower()
    
    # 检查是否包含具体事实（向量检索的优势）
    fact_indicators = [
        "是", "为", "等于", "定义为", "包括", "由", "consists", "defined as", "means", "包含",
        "数据", "统计", "研究", "报告", "实验"
    ]
    fact_count = sum(1 for indicator in fact_indicators if indicator in content_lower)
    if fact_count >= 2:
        quality_score += vector_quality_factors["has_specific_facts"]
    
    # 检查是否包含定义（向量检索的优势）
    definition_indicators = [
        "定义", "含义", "是指", "refers to", "definition", "meaning", "即", "指的是", "表示"
    ]
    if any(indicator in content_lower for indicator in definition_indicators):
        quality_score += vector_quality_factors["has_definitions"]
    
    # 语义相关性评估（向量检索的核心优势）
    query_keywords = query_lower.split()
    content_matches = sum(1 for keyword in query_keywords if keyword in content_lower)
    semantic_score = min(content_matches / max(len(query_keywords), 1), 1.0)
    if semantic_score > 0.6:  # 高语义匹配度
        quality_score += vector_quality_factors["semantic_relevance"]
    
    # 事实准确性评估（数字、日期、具体数据）
    import re
    has_numbers = bool(re.search(r'\d+', content))
    has_dates = bool(re.search(r'\d{4}年|\d{4}-\d{2}|\d{4}/\d{2}', content))
    if has_numbers or has_dates:
        quality_score += vector_quality_factors["factual_accuracy"]
    
    # 内容完整性评估（向量检索应该返回完整的信息片段）
    completeness_score = 0.0
    if len(content) > 100:  # 有足够的信息量
        completeness_score += 0.15
    
    # 检查是否是完整的句子或段落
    if content.count('。') >= 1 or content.count('.') >= 1:
        completeness_score += 0.15
    
    total_score = length_score + quality_score + completeness_score
    return min(total_score, 1.0)

def get_local_search_info() -> Dict[str, Any]:
    """
    获取本地检索节点信息
    
    Returns:
        节点信息字典
    """
    return {
        "node_name": "local_search",
        "description": "PostgreSQL向量检索节点",
        "retrieval_mode": "local",
        "primary_database": "PostgreSQL",
        "storage_technology": "PGVector",
        "suitable_for": [
            "事实性查询",
            "定义查询", 
            "概念解释",
            "具体数据查询",
            "语义相似性搜索"
        ],
        "strengths": [
            "快速语义匹配",
            "精确事实检索",
            "向量相似性强",
            "PostgreSQL高性能",
            "精确语义理解"
        ],
        "limitations": [
            "缺乏关系推理",
            "无法处理复杂关联",
            "依赖向量质量",
            "局限于片段级检索"
        ],
        "algorithm_details": {
            "embedding_model": "OpenAI text-embedding-ada-002",
            "similarity_metric": "余弦相似度",
            "index_type": "HNSW索引",
            "storage_format": "PostgreSQL pgvector扩展"
        }
    }

def get_local_search_statistics() -> Dict[str, Any]:
    """
    获取本地检索统计信息（为后续监控预留）
    
    Returns:
        统计数据字典
    """
    return {
        "total_queries": 0,
        "successful_queries": 0,
        "failed_queries": 0,
        "average_retrieval_time": 0.0,
        "average_quality_score": 0.0,
        "query_types_handled": {
            "FACTUAL": 0
        },
        "vector_search_metrics": {
            "average_similarity_score": 0.0,
            "high_confidence_matches": 0,
            "postgresql_performance": "N/A"
        }
    } 