"""
答案生成节点
整合 LightRAG 检索结果和网络搜索补充信息，生成最终答案
"""

import time
import logging
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI

from ..core.config import config
from ..core.state import AgentState, SourceInfo

# 简单的日志配置，避免循环导入
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def answer_generation_node(state: AgentState) -> Dict[str, Any]:
    """
    答案生成节点
    
    整合本地知识库检索结果和网络搜索补充信息，生成最终答案：
    - 优先使用本地知识库信息作为主要依据
    - 用网络搜索结果补充最新信息或填补知识空白
    - 清楚标注信息来源和置信度
    - 根据检索模式调整答案风格
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典
    """
    logger.info("开始生成最终答案...")
    
    start_time = time.time()
    
    try:
        # 收集所有上下文信息
        context_info = _collect_context_information(state)
        
        # 构建答案生成提示词
        answer_prompt = _build_answer_prompt(state, context_info)
        
        # 生成答案
        final_answer = _generate_answer_with_llm(answer_prompt)
        
        # 计算答案置信度
        answer_confidence = _calculate_answer_confidence(state, context_info)
        
        # 整理信息来源
        sources = _organize_sources(context_info)
        
        generation_time = time.time() - start_time
        
        logger.info(f"✅ 答案生成完成 ({generation_time:.2f}s)")
        logger.info(f"答案长度: {len(final_answer)} 字符")
        logger.info(f"答案置信度: {answer_confidence:.2f}")
        logger.info(f"信息来源数量: {len(sources)}")
        
        return {
            "final_answer": final_answer,
            "sources": sources,
            "context_used": len(context_info["context_parts"]),
            "lightrag_mode_used": state.get("lightrag_mode", "unknown"),
            "answer_confidence": answer_confidence,
            "generation_time": generation_time
        }
        
    except Exception as e:
        generation_time = time.time() - start_time
        logger.error(f"❌ 答案生成失败: {e}")
        
        # 返回错误信息
        return {
            "final_answer": f"抱歉，答案生成过程中发生错误: {str(e)}",
            "sources": [],
            "context_used": 0,
            "lightrag_mode_used": state.get("lightrag_mode", "unknown"),
            "answer_confidence": 0.0,
            "generation_time": generation_time
        }

def _collect_context_information(state: AgentState) -> Dict[str, Any]:
    """
    收集所有上下文信息
    
    Args:
        state: 当前工作流状态
        
    Returns:
        上下文信息字典
    """
    context_info = {
        "context_parts": [],
        "lightrag_info": None,
        "web_info": None,
        "total_sources": 0
    }
    
    # 收集 LightRAG 检索结果
    lightrag_results = state.get("lightrag_results", {})
    if lightrag_results.get("content"):
        lightrag_mode = lightrag_results.get("mode", "unknown")
        context_info["context_parts"].append(
            f"**本地知识库检索结果** (使用 {lightrag_mode} 模式)：\n{lightrag_results['content']}"
        )
        context_info["lightrag_info"] = lightrag_results
        context_info["total_sources"] += 1
    
    # 收集网络搜索结果
    web_results = state.get("web_results", [])
    if web_results:
        web_content = _format_web_results(web_results)
        context_info["context_parts"].append(
            f"**网络搜索补充信息**：\n{web_content}"
        )
        context_info["web_info"] = web_results
        context_info["total_sources"] += len(web_results)
    
    return context_info

def _format_web_results(web_results: List[Dict[str, Any]]) -> str:
    """
    格式化网络搜索结果
    
    Args:
        web_results: 网络搜索结果列表
        
    Returns:
        格式化后的网络搜索内容
    """
    if not web_results or not isinstance(web_results, list):
        return "无有效的网络搜索结果"
    
    formatted_results = []
    
    for i, result in enumerate(web_results[:3], 1):  # 只使用前3个结果
        if not result or not isinstance(result, dict):
            continue
            
        title = result.get("title", "未知标题")
        content = result.get("content", "")
        url = result.get("url", "")
        domain = result.get("domain", "")
        
        # 截断过长内容
        if len(content) > 300:
            content = content[:300] + "..."
        
        formatted_results.append(f"{i}. **{title}** ({domain})")
        if content:
            formatted_results.append(f"   {content}")
        if url:
            formatted_results.append(f"   来源: {url}")
        formatted_results.append("")  # 空行分隔
    
    return "\n".join(formatted_results) if formatted_results else "无有效的网络搜索结果"

def _build_answer_prompt(state: AgentState, context_info: Dict[str, Any]) -> str:
    """
    构建答案生成提示词
    
    Args:
        state: 当前工作流状态
        context_info: 上下文信息
        
    Returns:
        答案生成提示词
    """
    user_query = state.get("user_query", "")
    query_type = state.get("query_type", "ANALYTICAL")
    lightrag_mode = state.get("lightrag_mode", "hybrid")
    confidence_score = state.get("confidence_score", 0.0)
    
    # 整合所有上下文
    full_context = "\n\n".join(context_info["context_parts"])
    
    # 根据查询类型调整答案风格指导
    style_guidance = _get_style_guidance(query_type, lightrag_mode)
    
    prompt = f"""
基于以下信息回答用户问题，请提供准确、全面且有条理的答案。

**用户问题**: {user_query}

**查询类型**: {query_type}
**检索模式**: {lightrag_mode}
**信息置信度**: {confidence_score:.2f}

**可用信息**:
{full_context}

**答案要求**:
1. **信息优先级**: 优先使用本地知识库的信息作为主要答案依据，网络搜索结果作为补充
2. **来源标注**: 在答案中适当标注信息来源（本地知识库 vs 网络搜索）
3. **信息整合**: 如果本地和网络信息存在差异，请说明并提供平衡的观点
4. **完整性**: 如果信息不足或存在空白，请诚实说明
5. **结构化**: 使用清晰的段落和逻辑结构组织答案

{style_guidance}

**格式要求**:
- 使用 Markdown 格式
- 包含适当的标题和列表
- 在答案末尾简要说明信息来源
- 如果信息不确定，请明确标注

请生成一个专业、准确且易于理解的答案。
"""
    
    return prompt

def _get_style_guidance(query_type: str, lightrag_mode: str) -> str:
    """
    根据查询类型和检索模式获取风格指导
    
    Args:
        query_type: 查询类型
        lightrag_mode: 检索模式
        
    Returns:
        风格指导文本
    """
    style_mappings = {
        "FACTUAL": {
            "local": "提供准确的事实性答案，重点关注定义、概念和具体信息",
            "global": "在事实基础上，额外说明相关的实体关系和联系",
            "hybrid": "结合事实信息和关系分析，提供全面的解释"
        },
        "RELATIONAL": {
            "local": "基于检索到的信息，重点说明实体间的关系和联系",
            "global": "深入分析实体关系，利用图谱信息提供关系链和影响分析",
            "hybrid": "综合分析实体关系，结合具体事实和关系网络"
        },
        "ANALYTICAL": {
            "local": "基于检索信息进行分析，提供有条理的分析结果",
            "global": "利用关系信息进行深度分析，探讨影响和趋势",
            "hybrid": "进行全面的综合分析，结合多个维度和角度"
        }
    }
    
    guidance = style_mappings.get(query_type, {}).get(lightrag_mode, "")
    
    if guidance:
        return f"**答案风格**: {guidance}"
    else:
        return "**答案风格**: 提供清晰、准确且全面的回答"

def _generate_answer_with_llm(prompt: str) -> str:
    """
    使用 LLM 生成答案
    
    Args:
        prompt: 生成提示词
        
    Returns:
        生成的答案
    """
    try:
        # 初始化 LLM
        llm = ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL
        )
        
        # 生成答案
        response = llm.invoke(prompt)
        
        return response.content.strip()
        
    except Exception as e:
        logger.error(f"LLM 答案生成失败: {e}")
        return f"抱歉，答案生成过程中发生错误: {str(e)}"

def _calculate_answer_confidence(state: AgentState, context_info: Dict[str, Any]) -> float:
    """
    计算答案置信度
    
    Args:
        state: 当前工作流状态
        context_info: 上下文信息
        
    Returns:
        答案置信度分数
    """
    # 基础置信度（来自质量评估）
    base_confidence = state.get("confidence_score", 0.5)
    
    # 信息来源奖励
    source_bonus = 0.0
    
    # LightRAG 结果奖励
    if context_info.get("lightrag_info"):
        lightrag_mode = context_info["lightrag_info"].get("mode", "")
        mode_bonus = {
            "local": 0.1,
            "global": 0.15,
            "hybrid": 0.2
        }.get(lightrag_mode, 0.1)
        source_bonus += mode_bonus
    
    # 网络搜索结果奖励
    web_results = context_info.get("web_info", [])
    if web_results:
        # 基于搜索结果数量和质量的奖励
        web_bonus = min(len(web_results) * 0.05, 0.15)
        source_bonus += web_bonus
    
    # 信息丰富度奖励
    total_sources = context_info.get("total_sources", 0)
    if total_sources > 1:
        source_bonus += 0.1
    
    # 检索成功奖励
    if state.get("retrieval_success", False):
        source_bonus += 0.05
    
    # 计算最终置信度
    final_confidence = min(base_confidence + source_bonus, 1.0)
    
    return final_confidence

def _organize_sources(context_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    整理信息来源
    
    Args:
        context_info: 上下文信息
        
    Returns:
        整理后的信息来源列表
    """
    sources = []
    
    # 添加 LightRAG 来源
    lightrag_info = context_info.get("lightrag_info")
    if lightrag_info:
        sources.append({
            "type": "lightrag_knowledge",
            "mode": lightrag_info.get("mode", "unknown"),
            "content": lightrag_info.get("content", "")[:200] + "...",
            "confidence": lightrag_info.get("confidence", 0.0),
            "query": lightrag_info.get("query", "")
        })
    
    # 添加网络搜索来源 - 确保web_info不为None
    web_info = context_info.get("web_info", [])
    if web_info is not None and isinstance(web_info, list):
        for result in web_info:
            if result and isinstance(result, dict):  # 确保result不为None且是字典
                sources.append({
                    "type": "web_search",
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "domain": result.get("domain", ""),
                    "score": result.get("score", 0.0),
                    "snippet": result.get("snippet", "")
                })
    
    return sources

def get_generation_guidelines() -> Dict[str, Any]:
    """
    获取答案生成指南
    
    Returns:
        答案生成指南
    """
    return {
        "information_priority": {
            "primary": "本地知识库 (LightRAG) 信息",
            "secondary": "网络搜索补充信息",
            "handling": "优先使用本地信息，网络信息作为补充或更新"
        },
        "style_adaptation": {
            "FACTUAL": "提供准确的事实性答案，重点关注定义和概念",
            "RELATIONAL": "强调实体关系和联系，利用图谱信息",
            "ANALYTICAL": "进行全面的综合分析，结合多个维度"
        },
        "quality_requirements": {
            "accuracy": "确保信息准确性",
            "completeness": "提供完整的答案",
            "clarity": "使用清晰的结构和语言",
            "source_attribution": "标注信息来源"
        },
        "confidence_factors": {
            "base_confidence": "质量评估的基础置信度",
            "source_bonus": "信息来源质量和数量奖励",
            "mode_effectiveness": "检索模式有效性奖励"
        }
    }