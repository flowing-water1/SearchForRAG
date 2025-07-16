"""
混合检索节点 (Hybrid Search)
专门处理复杂分析性查询的混合检索，使用 LightRAG Hybrid 模式
综合利用 PostgreSQL 向量数据库和 Neo4j 图数据库的优势
"""

from typing import Dict, Any
import time

from ..core.state import AgentState
from ..utils.simple_logger import get_simple_logger
from ..utils.lightrag_client import query_lightrag

logger = get_simple_logger(__name__)

async def hybrid_search_node(state: AgentState) -> Dict[str, Any]:
    """
    混合检索节点 - LightRAG Hybrid 模式
    
    专门处理复杂分析性查询，综合利用PostgreSQL向量数据库和Neo4j图数据库。
    结合向量检索和图检索的优势，适用于需要综合分析、推理、多维信息整合的复杂查询。
    
    检索策略：
    - 双引擎数据源：PostgreSQL 向量存储 + Neo4j 图存储
    - 检索算法：向量相似性 + 图关系遍历的智能融合
    - 优势：最全面的信息覆盖和最深入的关系推理
    - 适用场景：复杂分析查询、多维评估、综合研究、深度理解
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典
    """
    processed_query = state.get("processed_query", state["user_query"])
    query_type = state.get("query_type", "ANALYTICAL")
    
    logger.info(f"🔬 开始混合检索 (PostgreSQL + Neo4j 双引擎)")
    logger.info(f"查询类型: {query_type}")
    logger.info(f"查询内容: {processed_query[:100]}...")
    logger.info(f"🎯 检索策略: 向量相似性 + 图关系遍历融合")
    
    start_time = time.time()
    
    try:
        # 固定使用 hybrid 模式进行检索
        result = await query_lightrag(processed_query, "hybrid")
        
        retrieval_time = time.time() - start_time
        
        if result.get("success", False):
            content = result.get("content", "")
            
            # 获取存储后端信息和模式描述
            storage_backend = result.get("storage_backend", {})
            data_source = result.get("data_source", "unknown")
            retrieval_path = result.get("retrieval_path", "unknown")
            mode_description = result.get("mode_description", {})
            
            # 计算混合检索的质量分数
            quality_score = _calculate_hybrid_quality(content, processed_query)
            
            logger.info(f"✅ 双引擎混合检索完成 ({retrieval_time:.2f}s)")
            logger.info(f"📊 检索到内容长度: {len(content)} 字符")
            logger.info(f"🎯 综合分析质量分数: {quality_score:.2f}")
            logger.info(f"💾 双数据源: PostgreSQL向量 + Neo4j图谱")
            
            return {
                "lightrag_results": {
                    "content": content,
                    "mode": "hybrid",
                    "query": processed_query,
                    "source": "lightrag_hybrid",
                    "retrieval_time": retrieval_time,
                    "node_type": "hybrid_search",
                    # 突出混合检索特性
                    "storage_backend": storage_backend,
                    "data_source": data_source,
                    "retrieval_path": retrieval_path,
                    "mode_description": mode_description,
                    # 为前端显示提供专门的混合检索描述
                    "display_info": {
                        "algorithm_name": "向量检索 + 图谱遍历组合",
                        "primary_storage": "PostgreSQL + Neo4j 双引擎",
                        "storage_type": "PostgreSQL PGVector + Neo4j Graph (并行融合)",
                        "complexity": "最高复杂度，最全面覆盖",
                        "best_for": "复杂分析查询、综合理解、多维评估",
                        "search_method": "语义相似性 + 关系推理的智能融合",
                        "data_focus": "向量语义 + 图关系的全维度整合"
                    }
                },
                "retrieval_score": quality_score,
                "retrieval_success": True,
                "lightrag_mode_used": "hybrid",
                "primary_database": "PostgreSQL+Neo4j"
            }
        else:
            error_msg = result.get("error", "双引擎混合检索失败")
            logger.error(f"❌ 双引擎混合检索失败: {error_msg}")
            
            return {
                "lightrag_results": {
                    "content": "",
                    "mode": "hybrid",
                    "query": processed_query,
                    "source": "lightrag_hybrid",
                    "error": error_msg,
                    "retrieval_time": retrieval_time,
                    "node_type": "hybrid_search"
                },
                "retrieval_score": 0.0,
                "retrieval_success": False,
                "lightrag_mode_used": "hybrid",
                "primary_database": "PostgreSQL+Neo4j"
            }
            
    except Exception as e:
        retrieval_time = time.time() - start_time
        logger.error(f"❌ 双引擎混合检索异常: {str(e)}")
        
        return {
            "lightrag_results": {
                "content": "",
                "mode": "hybrid", 
                "query": processed_query,
                "source": "lightrag_hybrid",
                "error": f"混合检索异常: {str(e)}",
                "retrieval_time": retrieval_time,
                "node_type": "hybrid_search"
            },
            "retrieval_score": 0.0,
            "retrieval_success": False,
            "lightrag_mode_used": "hybrid",
            "primary_database": "PostgreSQL+Neo4j"
        }

def _calculate_hybrid_quality(content: str, query: str) -> float:
    """
    计算混合检索的质量分数
    
    专门评估双引擎融合检索的效果，重点关注：
    - 信息综合性（向量检索贡献）
    - 关系复杂性（图检索贡献）
    - 分析深度（融合效果）
    - 多维覆盖（双引擎协同）
    
    Args:
        content: 检索到的内容
        query: 查询内容
        
    Returns:
        质量分数 (0.0-1.0)
    """
    if not content or len(content.strip()) == 0:
        return 0.0
    
    # 基础分数基于内容长度（混合检索通常产生最丰富、最全面的内容）
    length_score = min(len(content) / 2000, 1.0) * 0.15  # 混合检索内容通常最为丰富
    
    # 混合检索质量评估因子（体现双引擎协同优势）
    hybrid_quality_factors = {
        "has_facts": 0.15,                    # 包含事实信息（向量检索优势）
        "has_relationships": 0.15,            # 包含关系信息（图检索优势）
        "has_analysis": 0.2,                  # 包含分析内容（融合效果）
        "has_multiple_perspectives": 0.15,    # 多角度信息（双引擎覆盖）
        "has_depth": 0.15,                    # 深度分析（综合推理）
        "information_integration": 0.1        # 信息整合度（融合质量）
    }
    
    comprehensiveness_score = 0.0
    content_lower = content.lower()
    query_lower = query.lower()
    
    # 检查是否包含事实信息（体现向量检索的贡献）
    fact_indicators = [
        "数据", "统计", "研究", "报告", "调查", "实验", "证据", "定义", "含义",
        "data", "statistics", "research", "report", "survey", "experiment", "evidence",
        "definition", "meaning", "包括", "是指", "表示"
    ]
    fact_count = sum(1 for indicator in fact_indicators if indicator in content_lower)
    if fact_count >= 3:  # 混合检索应该有丰富的事实信息
        comprehensiveness_score += hybrid_quality_factors["has_facts"]
    
    # 检查是否包含关系信息（体现图检索的贡献）
    relationship_indicators = [
        "关系", "影响", "联系", "相关", "关联", "导致", "因为", "连接", "网络",
        "relationship", "influence", "connection", "related", "cause", "due to", "network"
    ]
    relationship_count = sum(1 for indicator in relationship_indicators if indicator in content_lower)
    if relationship_count >= 3:  # 混合检索应该有丰富的关系描述
        comprehensiveness_score += hybrid_quality_factors["has_relationships"]
    
    # 检查是否包含分析内容（体现融合分析能力）
    analysis_indicators = [
        "分析", "评估", "比较", "对比", "优缺点", "优势", "劣势", "趋势", "预测", "综合",
        "analysis", "evaluation", "comparison", "pros", "cons", "advantages", "disadvantages", 
        "trend", "prediction", "assess", "examine", "comprehensive", "synthesis"
    ]
    analysis_count = sum(1 for indicator in analysis_indicators if indicator in content_lower)
    if analysis_count >= 3:  # 混合检索应该提供深入分析
        comprehensiveness_score += hybrid_quality_factors["has_analysis"]
    
    # 检查是否包含多角度信息（体现双引擎的覆盖优势）
    perspective_indicators = [
        "角度", "方面", "层面", "维度", "观点", "看法", "认为", "perspective", "aspect", 
        "dimension", "viewpoint", "opinion", "believe", "think", "consider",
        "一方面", "另一方面", "同时", "然而", "但是", "不过", "此外", "另外"
    ]
    perspective_count = sum(1 for indicator in perspective_indicators if indicator in content_lower)
    if perspective_count >= 4:  # 混合检索应该提供多角度视角
        comprehensiveness_score += hybrid_quality_factors["has_multiple_perspectives"]
    
    # 检查是否有深度分析（体现综合推理能力）
    depth_indicators = [
        "深入", "详细", "具体", "进一步", "更", "深层", "根本", "本质", "机制",
        "deep", "detailed", "specific", "further", "more", "underlying", "fundamental", 
        "essence", "mechanism", "原因", "原理", "过程", "步骤", "逻辑"
    ]
    depth_count = sum(1 for indicator in depth_indicators if indicator in content_lower)
    if depth_count >= 2 and len(content) > 600:  # 混合检索应该提供深度内容
        comprehensiveness_score += hybrid_quality_factors["has_depth"]
    
    # 检查信息整合度（体现双引擎融合质量）
    integration_indicators = [
        "结合", "整合", "综合", "融合", "汇总", "归纳", "总结", "综述",
        "combine", "integrate", "synthesize", "merge", "summarize", "conclude", "overview"
    ]
    integration_count = sum(1 for indicator in integration_indicators if indicator in content_lower)
    if integration_count >= 2:  # 混合检索应该体现信息整合
        comprehensiveness_score += hybrid_quality_factors["information_integration"]
    
    # 查询相关性评估（混合检索应该有最高的相关性）
    query_keywords = query_lower.split()
    content_matches = sum(1 for keyword in query_keywords if keyword in content_lower)
    relevance_score = min(content_matches / max(len(query_keywords), 1), 1.0) * 0.15
    
    # 结构完整性评估（混合检索应该产生最完整的结构）
    structure_score = 0.0
    
    # 检查逻辑结构词（分析性内容的逻辑性）
    structure_indicators = [
        "首先", "其次", "然后", "最后", "总之", "综上", "因此", "所以", "同时",
        "first", "second", "third", "finally", "in conclusion", "therefore", "thus", "meanwhile"
    ]
    structure_count = sum(1 for indicator in structure_indicators if indicator in content_lower)
    if structure_count >= 3:  # 混合检索应该有最好的逻辑结构
        structure_score += 0.1
    
    # 检查段落结构（通过换行符判断内容组织）
    paragraphs = content.split('\n')
    meaningful_paragraphs = [p for p in paragraphs if len(p.strip()) > 80]
    if len(meaningful_paragraphs) >= 4:  # 混合检索应该有良好的段落组织
        structure_score += 0.1
    
    # 信息密度评估（混合检索应该提供最高的信息密度）
    density_score = 0.0
    if len(content) > 1000:  # 内容足够丰富
        # 计算信息密度（标点符号密度 + 关键词密度）
        punctuation_count = sum(1 for char in content if char in '.,;:!?。，；：！？')
        keyword_density = (fact_count + relationship_count + analysis_count) / len(content.split())
        
        if punctuation_count / len(content) > 0.03 and keyword_density > 0.05:
            density_score = 0.15  # 混合检索的密度奖励最高
    
    # 双引擎协同效果评估（特有的评估维度）
    synergy_score = 0.0
    # 如果同时具备事实信息和关系信息，说明双引擎协同良好
    if fact_count >= 2 and relationship_count >= 2:
        synergy_score += 0.1
    # 如果内容长度和质量都很高，说明融合效果好
    if len(content) > 800 and (fact_count + relationship_count + analysis_count) >= 6:
        synergy_score += 0.1
    
    total_score = (length_score + comprehensiveness_score + relevance_score + 
                   structure_score + density_score + synergy_score)
    return min(total_score, 1.0)

def get_hybrid_search_info() -> Dict[str, Any]:
    """
    获取混合检索节点信息
    
    Returns:
        节点信息字典
    """
    return {
        "node_name": "hybrid_search",
        "description": "PostgreSQL+Neo4j混合检索节点",
        "retrieval_mode": "hybrid",
        "primary_database": "PostgreSQL+Neo4j",
        "storage_technology": "PGVector + Neo4j Graph",
        "suitable_for": [
            "复杂分析性查询",
            "多维度信息查询",
            "综合评估查询",
            "深度研究查询",
            "全面理解查询",
            "跨领域整合查询"
        ],
        "strengths": [
            "综合向量和图检索优势",
            "信息覆盖面最广",
            "支持最复杂推理",
            "多角度信息整合",
            "最全面的关系发现",
            "最深入的语义理解"
        ],
        "limitations": [
            "检索时间最长",
            "计算资源消耗最大",
            "信息可能冗余",
            "需要强大的整合能力"
        ],
        "features": [
            "双引擎并行检索",
            "智能信息融合",
            "多层次信息检索",
            "上下文感知检索",
            "语义关系协同",
            "全维度信息覆盖"
        ],
        "algorithm_details": {
            "vector_component": "PostgreSQL PGVector语义检索",
            "graph_component": "Neo4j关系图遍历",
            "fusion_method": "智能权重融合算法",
            "optimization": "双引擎协同优化"
        }
    }

def get_hybrid_search_statistics() -> Dict[str, Any]:
    """
    获取混合检索统计信息（为后续监控预留）
    
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
            "ANALYTICAL": 0
        },
        "hybrid_search_metrics": {
            "average_content_length": 0,
            "information_density_score": 0.0,
            "multi_perspective_rate": 0.0,
            "vector_graph_synergy_score": 0.0,
            "dual_engine_performance": "N/A"
        }
    } 