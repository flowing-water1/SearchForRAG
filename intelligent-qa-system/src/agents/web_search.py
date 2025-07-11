"""
网络搜索节点
当本地信息不足时，从网络获取补充信息
"""

import time
from typing import Dict, Any, List, Optional

from tavily import TavilyClient

from ..core.config import config
from ..core.state import AgentState, WebSearchResult
from ..utils.simple_logger import get_simple_logger

logger = get_simple_logger(__name__)

def web_search_node(state: AgentState) -> Dict[str, Any]:
    """
    网络搜索节点
    
    当质量评估节点判定本地信息不足时，使用 Tavily API 进行网络搜索补充：
    - 根据查询类型选择最佳搜索策略
    - 获取多个来源的补充信息
    - 处理和格式化搜索结果
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典
    """
    # 检查是否需要网络搜索
    need_web_search = state.get("need_web_search", False)
    if not need_web_search:
        logger.info("无需网络搜索，跳过此节点")
        return {"web_results": []}
    
    logger.info("开始网络搜索补充信息...")
    
    # 检查 Tavily API 密钥
    if not config.TAVILY_API_KEY:
        logger.error("Tavily API密钥未配置，无法进行网络搜索")
        return {
            "web_results": [],
            "web_search_summary": "API密钥未配置，网络搜索失败"
        }
    
    start_time = time.time()
    
    try:
        # 执行网络搜索
        search_results = _execute_web_search(state)
        
        search_time = time.time() - start_time
        
        if search_results:
            logger.info(f"✅ 网络搜索完成 ({search_time:.2f}s)")
            logger.info(f"获取到 {len(search_results)} 个搜索结果")
            
            # 处理搜索结果
            processed_results = _process_search_results(search_results)
            
            return {
                "web_results": processed_results,
                "web_search_summary": f"从网络获取 {len(processed_results)} 个补充信息源"
            }
        else:
            logger.warning("网络搜索未找到相关结果")
            return {
                "web_results": [],
                "web_search_summary": "网络搜索未找到相关结果"
            }
            
    except Exception as e:
        search_time = time.time() - start_time
        logger.error(f"❌ 网络搜索失败: {e}")
        
        return {
            "web_results": [],
            "web_search_summary": f"网络搜索失败: {str(e)}"
        }

def _execute_web_search(state: AgentState) -> List[Dict[str, Any]]:
    """
    执行网络搜索
    
    Args:
        state: 当前工作流状态
        
    Returns:
        搜索结果列表
    """
    # 获取搜索查询
    search_query = _build_search_query(state)
    
    # 根据查询类型选择搜索策略
    search_params = _get_search_parameters(state)
    
    logger.info(f"搜索查询: {search_query}")
    logger.info(f"搜索参数: {search_params}")
    
    # 初始化 Tavily 搜索
    tavily_client = TavilyClient(
        api_key=config.TAVILY_API_KEY
    )
    
    # 执行搜索
    try:
        response = tavily_client.search(
            query=search_query,
            search_depth=search_params["search_depth"],
            max_results=search_params["max_results"],
            include_answer=search_params["include_answer"],
            include_raw_content=search_params["include_raw_content"],
            include_domains=search_params.get("include_domains"),
            exclude_domains=search_params.get("exclude_domains")
        )
        
        # 从返回的字典中提取 "results" 键
        search_results = response.get("results", [])
        
        return search_results if isinstance(search_results, list) else []
        
    except Exception as e:
        logger.error(f"Tavily搜索API调用失败: {e}")
        return []

def _build_search_query(state: AgentState) -> str:
    """
    构建搜索查询
    
    Args:
        state: 当前工作流状态
        
    Returns:
        优化的搜索查询字符串
    """
    user_query = state.get("user_query", "")
    processed_query = state.get("processed_query", "")
    key_entities = state.get("key_entities", [])
    query_type = state.get("query_type", "ANALYTICAL")
    
    # 使用处理后的查询作为基础
    base_query = processed_query if processed_query else user_query
    
    # 根据查询类型优化搜索查询
    if query_type == "FACTUAL":
        # 事实性查询：添加定义和解释相关词汇
        search_query = f"{base_query} 定义 解释 什么是"
    elif query_type == "RELATIONAL":
        # 关系性查询：添加关系和连接相关词汇
        search_query = f"{base_query} 关系 联系 影响"
    else:  # ANALYTICAL
        # 分析性查询：添加分析和趋势相关词汇
        search_query = f"{base_query} 分析 趋势 现状 未来"
    
    # 添加关键实体以增强搜索精度
    if key_entities:
        entity_str = " ".join(key_entities[:3])  # 只取前3个实体
        search_query = f"{search_query} {entity_str}"
    
    # 限制查询长度
    if len(search_query) > 200:
        search_query = search_query[:200] + "..."
    
    return search_query

def _get_search_parameters(state: AgentState) -> Dict[str, Any]:
    """
    根据查询类型获取搜索参数
    
    Args:
        state: 当前工作流状态
        
    Returns:
        搜索参数字典
    """
    query_type = state.get("query_type", "ANALYTICAL")
    
    # 基础参数
    base_params = {
        "include_answer": True,
        "include_raw_content": False,
        "include_domains": None,
        "exclude_domains": ["ads.google.com", "googleadservices.com"]
    }
    
    # 根据查询类型调整参数
    if query_type == "FACTUAL":
        return {
            **base_params,
            "search_depth": "basic",
            "max_results": 3
        }
    elif query_type == "RELATIONAL":
        return {
            **base_params,
            "search_depth": "advanced",
            "max_results": 4
        }
    else:  # ANALYTICAL
        return {
            **base_params,
            "search_depth": "advanced",
            "max_results": 5
        }

def _process_search_results(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    处理和格式化搜索结果
    
    Args:
        search_results: 原始搜索结果
        
    Returns:
        处理后的搜索结果列表
    """
    processed_results = []
    
    for result in search_results:
        try:
            # 提取关键信息
            processed_result = {
                "title": result.get("title", "未知标题"),
                "content": _clean_content(result.get("content", "")),
                "url": result.get("url", ""),
                "score": result.get("score", 0.0),
                "source_type": "web_search",
                "snippet": _extract_snippet(result.get("content", "")),
                "domain": _extract_domain(result.get("url", ""))
            }
            
            # 过滤无效结果
            if processed_result["content"] and len(processed_result["content"]) > 50:
                processed_results.append(processed_result)
                
        except Exception as e:
            logger.warning(f"处理搜索结果失败: {e}")
            continue
    
    # 按相关性分数排序
    processed_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 限制结果数量
    return processed_results[:config.MAX_WEB_RESULTS]

def _clean_content(content: str) -> str:
    """
    清理搜索内容
    
    Args:
        content: 原始内容
        
    Returns:
        清理后的内容
    """
    if not content:
        return ""
    
    # 移除多余的空白字符
    content = " ".join(content.split())
    
    # 截断过长的内容
    if len(content) > 1000:
        content = content[:1000] + "..."
    
    return content

def _extract_snippet(content: str, max_length: int = 200) -> str:
    """
    提取内容摘要
    
    Args:
        content: 原始内容
        max_length: 最大长度
        
    Returns:
        内容摘要
    """
    if not content:
        return ""
    
    # 取前几句话作为摘要
    sentences = content.split("。")
    snippet = ""
    
    for sentence in sentences:
        if len(snippet + sentence) < max_length:
            snippet += sentence + "。"
        else:
            break
    
    return snippet.strip()

def _extract_domain(url: str) -> str:
    """
    提取域名
    
    Args:
        url: 网址
        
    Returns:
        域名
    """
    if not url:
        return ""
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ""

def get_search_statistics() -> Dict[str, Any]:
    """
    获取搜索统计信息（未来可扩展）
    
    Returns:
        搜索统计信息
    """
    return {
        "total_searches": 0,
        "successful_searches": 0,
        "average_results_per_search": 0.0,
        "average_search_time": 0.0,
        "query_type_distribution": {
            "FACTUAL": 0,
            "RELATIONAL": 0,
            "ANALYTICAL": 0
        }
    }

def get_search_guidelines() -> Dict[str, Any]:
    """
    获取搜索指南
    
    Returns:
        搜索指南信息
    """
    return {
        "search_strategies": {
            "FACTUAL": {
                "depth": "basic",
                "max_results": 3,
                "keywords": ["定义", "解释", "什么是"]
            },
            "RELATIONAL": {
                "depth": "advanced",
                "max_results": 4,
                "keywords": ["关系", "联系", "影响"]
            },
            "ANALYTICAL": {
                "depth": "advanced",
                "max_results": 5,
                "keywords": ["分析", "趋势", "现状", "未来"]
            }
        },
        "quality_filters": {
            "min_content_length": 50,
            "max_results": config.MAX_WEB_RESULTS,
            "excluded_domains": ["ads.google.com", "googleadservices.com"]
        },
        "processing_steps": [
            "清理内容格式",
            "提取关键信息",
            "按相关性排序",
            "限制结果数量"
        ]
    }