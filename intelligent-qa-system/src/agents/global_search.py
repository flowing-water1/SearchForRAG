"""
全局检索节点 (Global Search)
专门处理关系性查询的图检索，使用 LightRAG Global 模式
主要依靠 Neo4j 图数据库进行关系推理和图遍历检索
"""

from typing import Dict, Any
import time

from ..core.state import AgentState
from ..utils.simple_logger import get_simple_logger
from ..utils.lightrag_client import query_lightrag

logger = get_simple_logger(__name__)

async def global_search_node(state: AgentState) -> Dict[str, Any]:
    """
    全局检索节点 - LightRAG Global 模式
    
    专门处理关系性查询，主要使用Neo4j图数据库进行关系推理检索。
    适用于探索实体间关系、影响、联系、趋势等复杂关联信息。
    
    检索策略：
    - 主要数据源：Neo4j 图存储 (Neo4JStorage)
    - 检索算法：图遍历和关系推理
    - 优势：发现复杂实体关系和深层关联
    - 适用场景：关系查询、影响分析、实体关联、趋势探索
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典
    """
    processed_query = state.get("processed_query", state["user_query"])
    query_type = state.get("query_type", "RELATIONAL")
    
    logger.info(f"🕸️ 开始全局图检索 (Neo4j图数据库)")
    logger.info(f"查询类型: {query_type}")
    logger.info(f"查询内容: {processed_query[:100]}...")
    logger.info(f"🎯 检索策略: 图遍历关系推理 (Neo4j Graph)")
    
    start_time = time.time()
    
    try:
        # 固定使用 global 模式进行检索
        result = await query_lightrag(processed_query, "global")
        
        retrieval_time = time.time() - start_time
        
        if result.get("success", False):
            content = result.get("content", "")
            
            # 获取存储后端信息和模式描述
            storage_backend = result.get("storage_backend", {})
            data_source = result.get("data_source", "unknown")
            retrieval_path = result.get("retrieval_path", "unknown")
            mode_description = result.get("mode_description", {})
            
            # 计算全局检索的质量分数
            quality_score = _calculate_global_quality(content, processed_query)
            
            logger.info(f"✅ Neo4j图遍历检索完成 ({retrieval_time:.2f}s)")
            logger.info(f"📊 检索到内容长度: {len(content)} 字符")
            logger.info(f"🎯 关系推理质量分数: {quality_score:.2f}")
            logger.info(f"💾 主要数据源: Neo4j 图数据库")
            
            return {
                "lightrag_results": {
                    "content": content,
                    "mode": "global",
                    "query": processed_query,
                    "source": "lightrag_global",
                    "retrieval_time": retrieval_time,
                    "node_type": "global_search",
                    # 突出图检索特性
                    "storage_backend": storage_backend,
                    "data_source": data_source,
                    "retrieval_path": retrieval_path,
                    "mode_description": mode_description,
                    # 为前端显示提供专门的图检索描述
                    "display_info": {
                        "algorithm_name": "知识图谱关系遍历",
                        "primary_storage": "Neo4j 图数据库",
                        "storage_type": "Neo4j Graph (主要) + PostgreSQL (备用)",
                        "complexity": "高复杂度，深度推理",
                        "best_for": "关系性查询、影响分析、实体关联推理",
                        "search_method": "图遍历和关系路径发现",
                        "data_focus": "实体关系网络和连接模式"
                    }
                },
                "retrieval_score": quality_score,
                "retrieval_success": True,
                "lightrag_mode_used": "global",
                "primary_database": "Neo4j"
            }
        else:
            error_msg = result.get("error", "Neo4j图检索失败")
            logger.error(f"❌ Neo4j图检索失败: {error_msg}")
            
            return {
                "lightrag_results": {
                    "content": "",
                    "mode": "global",
                    "query": processed_query,
                    "source": "lightrag_global",
                    "error": error_msg,
                    "retrieval_time": retrieval_time,
                    "node_type": "global_search"
                },
                "retrieval_score": 0.0,
                "retrieval_success": False,
                "lightrag_mode_used": "global",
                "primary_database": "Neo4j"
            }
            
    except Exception as e:
        retrieval_time = time.time() - start_time
        logger.error(f"❌ Neo4j图检索异常: {str(e)}")
        
        return {
            "lightrag_results": {
                "content": "",
                "mode": "global", 
                "query": processed_query,
                "source": "lightrag_global",
                "error": f"图检索异常: {str(e)}",
                "retrieval_time": retrieval_time,
                "node_type": "global_search"
            },
            "retrieval_score": 0.0,
            "retrieval_success": False,
            "lightrag_mode_used": "global",
            "primary_database": "Neo4j"
        }

def _calculate_global_quality(content: str, query: str) -> float:
    """
    计算全局图检索的质量分数
    
    专门评估图遍历和关系推理的效果，重点关注：
    - 关系发现能力
    - 实体连接深度
    - 多层次关联分析
    - 影响路径识别
    
    Args:
        content: 检索到的内容
        query: 查询内容
        
    Returns:
        质量分数 (0.0-1.0)
    """
    if not content or len(content.strip()) == 0:
        return 0.0
    
    # 基础分数基于内容长度（图检索通常内容更丰富，关系更复杂）
    length_score = min(len(content) / 1500, 1.0) * 0.2  # 图检索通常产生更长、更复杂的内容
    
    # 图检索质量评估因子
    graph_quality_factors = {
        "has_relationships": 0.25,        # 包含关系描述（图检索的核心）
        "has_connections": 0.2,           # 包含连接信息（图遍历的体现）
        "has_influences": 0.15,           # 包含影响关系（因果推理）
        "has_multiple_entities": 0.15,    # 涉及多个实体（网络效应）
        "has_path_reasoning": 0.15        # 路径推理能力
    }
    
    relationship_score = 0.0
    content_lower = content.lower()
    query_lower = query.lower()
    
    # 检查是否包含关系描述（图检索的核心优势）
    relationship_indicators = [
        "关系", "联系", "连接", "影响", "导致", "因为", "由于", "相关", "关联", "相互作用",
        "relationship", "connection", "influence", "affect", "cause", "due to", 
        "related", "associated", "between", "among", "interaction", "correlation"
    ]
    relationship_count = sum(1 for indicator in relationship_indicators if indicator in content_lower)
    if relationship_count >= 3:  # 图检索应该有丰富的关系词汇
        relationship_score += graph_quality_factors["has_relationships"]
    
    # 检查是否包含连接信息（图遍历的体现）
    connection_indicators = [
        "与", "和", "同", "之间", "通过", "连接到", "链接", "桥梁", "纽带", "网络",
        "via", "through", "with", "and", "between", "connects to", "links", "network", "pathway"
    ]
    connection_count = sum(1 for indicator in connection_indicators if indicator in content_lower)
    if connection_count >= 3:  # 图检索应该体现多层连接
        relationship_score += graph_quality_factors["has_connections"]
    
    # 检查是否包含影响关系（因果推理能力）
    influence_indicators = [
        "影响", "促进", "推动", "阻碍", "帮助", "支持", "反对", "制约", "推进", "阻止",
        "influence", "promote", "drive", "hinder", "help", "support", "oppose", "constraint",
        "导致", "引起", "造成", "产生", "触发", "激发", "brings about", "leads to", "results in"
    ]
    influence_count = sum(1 for indicator in influence_indicators if indicator in content_lower)
    if influence_count >= 2:  # 图检索应该发现因果关系
        relationship_score += graph_quality_factors["has_influences"]
    
    # 检查是否涉及多个实体（网络效应评估）
    import re
    # 查找可能的实体（大写开头的词或者专有名词）
    entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
    chinese_entities = re.findall(r'[\u4e00-\u9fff]{2,}', content)
    total_entities = len(set(entities + chinese_entities))
    
    if total_entities >= 4:  # 图检索应该涉及更多实体
        relationship_score += graph_quality_factors["has_multiple_entities"]
    
    # 检查路径推理能力（多跳关系）
    path_indicators = [
        "通过.*到", "从.*经过.*到", "路径", "步骤", "过程", "链条", "序列",
        "path", "through.*to", "from.*via.*to", "sequence", "chain", "process", "pathway"
    ]
    path_patterns = [
        r'从.{1,20}到.{1,20}',  # 从A到B的模式
        r'通过.{1,20}实现',     # 通过A实现B的模式
        r'经过.{1,20}过程'      # 经过A过程的模式
    ]
    
    has_path_reasoning = any(indicator in content_lower for indicator in path_indicators)
    has_path_patterns = any(re.search(pattern, content) for pattern in path_patterns)
    
    if has_path_reasoning or has_path_patterns:
        relationship_score += graph_quality_factors["has_path_reasoning"]
    
    # 查询相关性评估（针对关系性查询优化）
    query_keywords = query_lower.split()
    content_matches = sum(1 for keyword in query_keywords if keyword in content_lower)
    relevance_score = min(content_matches / max(len(query_keywords), 1), 1.0) * 0.2
    
    # 结构复杂性评估（图检索应该产生结构化的关系描述）
    structure_score = 0.0
    
    # 检查逻辑结构词（关系描述的逻辑性）
    structure_indicators = [
        "首先", "其次", "然后", "最后", "因此", "所以", "同时", "另外", "此外",
        "first", "second", "then", "finally", "therefore", "meanwhile", "additionally"
    ]
    structure_count = sum(1 for indicator in structure_indicators if indicator in content_lower)
    if structure_count >= 2:
        structure_score += 0.1
    
    # 检查是否有层次化的关系描述
    if len(content) > 400 and content.count('\n') >= 2:  # 有一定长度和结构
        structure_score += 0.1
    
    # 图检索信息密度评估（关系密度）
    density_score = 0.0
    total_words = len(content.split())
    if total_words > 0:
        relationship_density = relationship_count / total_words
        if relationship_density > 0.05:  # 关系词密度较高
            density_score = 0.1
    
    total_score = (length_score + relationship_score + relevance_score + 
                   structure_score + density_score)
    return min(total_score, 1.0)

def get_global_search_info() -> Dict[str, Any]:
    """
    获取全局检索节点信息
    
    Returns:
        节点信息字典
    """
    return {
        "node_name": "global_search",
        "description": "Neo4j图检索节点",
        "retrieval_mode": "global",
        "primary_database": "Neo4j",
        "storage_technology": "Neo4j Graph Database",
        "suitable_for": [
            "关系性查询",
            "实体关联查询",
            "影响分析查询",
            "趋势探索查询",
            "多跳关系推理",
            "网络分析查询"
        ],
        "strengths": [
            "关系推理能力强",
            "实体连接发现",
            "图谱深度遍历",
            "复杂关联分析",
            "多层次关系网络",
            "路径发现能力"
        ],
        "limitations": [
            "依赖图谱质量",
            "检索时间较长",
            "可能过度扩展",
            "需要高质量实体抽取"
        ],
        "algorithm_details": {
            "graph_traversal": "多跳关系遍历",
            "reasoning_method": "图结构推理",
            "relationship_types": "多元关系网络",
            "storage_format": "Neo4j原生图存储"
        }
    }

def get_global_search_statistics() -> Dict[str, Any]:
    """
    获取全局检索统计信息（为后续监控预留）
    
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
            "RELATIONAL": 0
        },
        "graph_search_metrics": {
            "relationship_extraction_count": 0,
            "entity_discovery_count": 0,
            "average_path_length": 0.0,
            "neo4j_performance": "N/A"
        }
    } 