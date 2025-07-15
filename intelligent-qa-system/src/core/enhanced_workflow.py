"""
增强版工作流编排 - 集成综合错误处理和日志记录
"""

import asyncio
import time
import uuid
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- 相对导入处理 ---
# 使得脚本可以直接运行进行测试
try:
    from .state import AgentState
    from .config import config
    from ..agents.query_analysis import query_analysis_node
    from ..agents.strategy_route import strategy_route_node
    from ..agents.local_search import local_search_node
    from ..agents.global_search import global_search_node
    from ..agents.hybrid_search import hybrid_search_node
    from ..agents.quality_assessment import quality_assessment_node
    from ..agents.web_search import web_search_node
    from ..agents.answer_generation import answer_generation_node
    from ..utils.simple_logger import get_simple_logger
    from ..utils.lightrag_client import initialize_lightrag
except ImportError:
    # 添加项目根目录到Python路径
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from src.core.state import AgentState
    from src.core.config import config
    from src.agents.query_analysis import query_analysis_node
    from src.agents.strategy_route import strategy_route_node
    from src.agents.local_search import local_search_node
    from src.agents.global_search import global_search_node
    from src.agents.hybrid_search import hybrid_search_node
    from src.agents.quality_assessment import quality_assessment_node
    from src.agents.web_search import web_search_node
    from src.agents.answer_generation import answer_generation_node
    # Use direct import to avoid circular dependency
    import logging
    import sys
    
    def get_simple_logger(name: str, level: str = "INFO") -> logging.Logger:
        """Simple logger function to avoid circular imports"""
        logger = logging.getLogger(name)
        if logger.handlers:
            return logger
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
        
        return logger
    
    # Import lightrag initialization function
    try:
        from src.utils.lightrag_client import initialize_lightrag
    except ImportError:
        # Fallback if lightrag_client has issues
        def initialize_lightrag():
            print("Warning: LightRAG initialization skipped due to import issues")
            pass

# 日志记录
logger = get_simple_logger(__name__)

# 定义支持的节点及其描述
SUPPORTED_NODES = [
    {"name": "query_analysis", "description": "查询分析节点", "function": "分析用户查询，确定查询类型并选择最佳LightRAG模式"},
    {"name": "strategy_route", "description": "策略路由节点", "function": "根据查询分析结果决定检索路径"},
    {"name": "local_search", "description": "本地检索节点", "function": "专门处理事实性查询的向量检索"},
    {"name": "global_search", "description": "全局检索节点", "function": "专门处理关系性查询的图检索"},
    {"name": "hybrid_search", "description": "混合检索节点", "function": "专门处理复杂查询的混合检索"},
    {"name": "quality_assessment", "description": "质量评估节点", "function": "评估检索结果质量，决定是否需要网络搜索补充"},
    {"name": "web_search", "description": "网络搜索节点", "function": "当本地信息不足时，从网络获取补充信息"},
    {"name": "answer_generation", "description": "答案生成节点", "function": "整合本地和网络信息，生成最终答案"}
]

class IntelligentQAWorkflow:
    """
    一个用于智能问答（Intelligent QA）的编排工作流，
    该工作流结合了 LightRAG 和 LangGraph 的功能，
    实现了从查询分析到答案生成的完整流程。
    """
    def __init__(self, workflow_id: Optional[str] = None):
        """
        初始化智能问答工作流。
        
        Args:
            workflow_id (Optional[str]): 工作流的唯一标识符。如果未提供，则会自动生成。
        """
        self.workflow_id = workflow_id or f"intelligent-qa-{uuid.uuid4()}"
        self.version = "2.0.0"
        self._graph = self._build_graph()
        self.compiled_graph = self._compile_graph()
        logger.info(f"✅ 智能问答工作流初始化成功 {self.workflow_id}")
        logger.info("注意：LightRAG将在第一次查询时延迟初始化")

    def _build_graph(self) -> StateGraph:
        """
        构建工作流的图结构，包括添加节点和边。
        
        Returns:
            StateGraph: 构建完成的工作流图。
        """
        graph = StateGraph(AgentState)
        self._add_nodes(graph)
        self._add_edges(graph)
        return graph

    def _add_nodes(self, graph: StateGraph):
        """
        向图中添加所有处理节点。
        """
        logger.info("添加工作流节点...")
        graph.add_node("query_analysis", query_analysis_node)
        graph.add_node("strategy_route", strategy_route_node)
        graph.add_node("local_search", local_search_node)
        graph.add_node("global_search", global_search_node)
        graph.add_node("hybrid_search", hybrid_search_node)
        graph.add_node("quality_assessment", quality_assessment_node)
        graph.add_node("web_search", web_search_node)
        graph.add_node("answer_generation", answer_generation_node)
        logger.info("所有节点已添加完成")

    def _add_edges(self, graph: StateGraph):
        """
        定义节点之间的连接和条件路由。
        """
        logger.info("配置智能检索工作流路由...")
        graph.set_entry_point("query_analysis")
        graph.add_edge("query_analysis", "strategy_route")

        graph.add_conditional_edges(
            "strategy_route",
            self._route_to_search_node,
            {
                "local_search": "local_search",
                "global_search": "global_search",
                "hybrid_search": "hybrid_search"
            }
        )

        graph.add_edge("local_search", "quality_assessment")
        graph.add_edge("global_search", "quality_assessment")
        graph.add_edge("hybrid_search", "quality_assessment")

        graph.add_conditional_edges(
            "quality_assessment",
            self._should_use_web_search,
            {
                "web_search": "web_search",
                "answer_generation": "answer_generation"
            }
        )

        graph.add_edge("web_search", "answer_generation")
        graph.add_edge("answer_generation", END)
        logger.info("智能检索工作流路由配置完成")

    def _route_to_search_node(self, state: AgentState) -> str:
        """根据策略路由节点的决策选择下一个检索节点。"""
        route_decision = state.get("lightrag_mode")
        logger.info(f"🔀 策略路由: {state.get('query_type')} → {route_decision} → {route_decision}_search")
        if route_decision == "local":
            return "local_search"
        elif route_decision == "global":
            return "global_search"
        elif route_decision == "hybrid":
            return "hybrid_search"
        else:
            logger.warning(f"未知的路由决策 '{route_decision}', 默认使用 local_search。")
            return "local_search"

    def _should_use_web_search(self, state: AgentState) -> str:
        """
        根据质量评估结果决定是否需要进行网络搜索。
        """
        if state.get("need_web_search", False):
            logger.info("🔍 质量评估判定需要网络搜索补充")
            return "web_search"
        else:
            logger.info("✅ 质量评估认为本地信息已足够")
            return "answer_generation"

    def _compile_graph(self):
        """
        编译工作流图，使其可执行。
        """
        logger.info("编译工作流...")
        try:
            # 使用内存检查点来支持流式处理和会话管理
            checkpointer = MemorySaver()
            compiled_graph = self._graph.compile(checkpointer=checkpointer)
            logger.info("✅ 工作流编译成功")
            # 可选：生成可视化图片以供调试
            try:
                image_bytes = compiled_graph.get_graph().draw_mermaid_png()
                with open("graph.png", "wb") as f:
                    f.write(image_bytes)
                logger.info("✅ 工作流可视化图片已保存: graph.png")
            except Exception as viz_error:
                logger.warning(f"⚠️  无法生成工作流可视化图片: {viz_error}")
            return compiled_graph
        except Exception as e:
            logger.error(f"❌ 工作流编译失败: {e}")
            raise

    def query(self, query_text: str, config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        同步执行查询。
        """
        return asyncio.run(self.query_async(query_text, config))

    async def query_async(self, query_text: str, config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        异步执行查询。
        """
        start_time = time.time()
        query_id = f"query-{uuid.uuid4()}"
        thread_id = (config or {}).get("configurable", {}).get("thread_id", f"thread-{uuid.uuid4()}")

        initial_state = {
            "user_query": query_text,
            "session_id": thread_id,
            "query_id": query_id
        }

        run_config = {"configurable": {"thread_id": thread_id}}
        
        logger.info(f"开始处理查询 {query_id}: {query_text[:100]}...")
        final_state = await self.compiled_graph.ainvoke(initial_state, config=run_config)
        
        execution_time = time.time() - start_time
        logger.info(f"✅ 工作流执行完成 {query_id} ({execution_time:.2f}s)")
        
        # 整理路由路径
        route_taken = []
        
        # 尝试多种方式提取路由信息
        logger.info(f"调试：final_state键: {list(final_state.keys())}")
        
        # 方法1：从messages中提取
        if 'messages' in final_state and final_state['messages']:
            for message in final_state['messages']:
                if hasattr(message, 'name') and message.name:
                    route_taken.append(message.name)
        
        # 方法2：从执行历史中提取（如果存在）
        if 'execution_history' in final_state:
            route_taken.extend(final_state['execution_history'])
        
        # 方法3：从其他可能的字段提取
        for key in ['node_sequence', 'path_taken', 'execution_path']:
            if key in final_state and final_state[key]:
                route_taken.extend(final_state[key])
        
        # 如果仍然为空，尝试从工作流决策中推断
        if not route_taken:
            if final_state.get('lightrag_mode') == 'local':
                route_taken = ['query_analysis', 'strategy_route', 'local_search', 'quality_assessment']
            elif final_state.get('lightrag_mode') == 'global':
                route_taken = ['query_analysis', 'strategy_route', 'global_search', 'quality_assessment']
            elif final_state.get('lightrag_mode') == 'hybrid':
                route_taken = ['query_analysis', 'strategy_route', 'hybrid_search', 'quality_assessment']
            
            # 添加最终步骤
            if final_state.get('need_web_search'):
                route_taken.append('web_search')
            route_taken.append('answer_generation')
        
        logger.info(f"调试：提取的路由: {route_taken}")

        # 简化最终输出
        return {
            "answer": final_state.get("final_answer"),
            "sources": final_state.get("sources"),
            "quality_score": final_state.get("confidence_score"),
            "answer_confidence": final_state.get("answer_confidence"),
            "execution_time": execution_time,
            "query_id": query_id,
            "route_taken": route_taken
        }

    def query_stream(self, query_text: str, config: Optional[Dict] = None):
        """
        流式执行查询。
        """
        return asyncio.run(self.query_stream_async(query_text, config))

    async def query_stream_async(self, query_text: str, config: Optional[Dict] = None):
        """
        异步流式执行查询。
        """
        thread_id = (config or {}).get("configurable", {}).get("thread_id", f"thread-{uuid.uuid4()}")
        run_config = {"configurable": {"thread_id": thread_id}}
        initial_state = {"user_query": query_text, "session_id": thread_id}
        
        async for chunk in self.compiled_graph.astream(initial_state, run_config):
            yield chunk

# --- 全局实例和便捷函数 ---

_workflow_instance: Optional[IntelligentQAWorkflow] = None

def get_workflow() -> IntelligentQAWorkflow:
    """获取全局工作流实例 (单例模式)。"""
    global _workflow_instance
    if _workflow_instance is None:
        logger.info("创建新的全局工作流实例...")
        _workflow_instance = IntelligentQAWorkflow()
    return _workflow_instance

def query(query_text: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """便捷的同步查询函数。"""
    workflow = get_workflow()
    return workflow.query(query_text, config)

async def query_async(query_text: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """便捷的异步查询函数。"""
    workflow = get_workflow()
    return await workflow.query_async(query_text, config)

def query_stream(query_text: str, config: Optional[Dict] = None):
    """便捷的流式查询函数。"""
    workflow = get_workflow()
    return workflow.query_stream(query_text, config)
    
def get_workflow_info() -> Dict[str, Any]:
    """获取工作流的元数据信息。"""
    workflow = get_workflow()
    return {
        "id": workflow.workflow_id,
        "version": workflow.version,
        "nodes": SUPPORTED_NODES,
        "graph_type": "StateGraph",
        "framework": "LangGraph"
    }

if __name__ == '__main__':
    # 用于直接运行此文件进行测试
    print("运行工作流测试...")
    print("✅ 使用已预处理的LightRAG数据进行测试")

    # 基于docs目录内容的测试查询（数据已预处理）
    test_queries = [
        {
            "query": "OpenAI在2024年筹集了多少资金？",
            "expected_strategy": "local_search",
            "description": "事实性查询测试 - OpenAI融资"
        },
        {
            "query": "Amazon对Anthropic总共投资了多少钱？",
            "expected_strategy": "local_search", 
            "description": "事实性查询测试 - Amazon投资"
        },
        {
            "query": "Amazon和Anthropic的合作关系是什么？",
            "expected_strategy": "global_search", 
            "description": "关系性查询测试 - 合作关系"
        },
        {
            "query": "Databricks的最新估值是多少？",
            "expected_strategy": "local_search",
            "description": "事实性查询测试 - Databricks估值"
        },
        {
            "query": "分析这些AI公司的融资情况和投资关系",
            "expected_strategy": "hybrid_search",
            "description": "复杂查询测试 - 融资分析"
        },
        {
            "query": "这些公司之间存在什么投资和合作关系？",
            "expected_strategy": "global_search",
            "description": "关系性查询测试 - 投资关系"
        }
    ]
    
    print("\n=== 多策略检索测试 ===")
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n--- 测试 {i}: {test_case['description']} ---")
        print(f"查询: {test_case['query']}")
        print(f"期望策略: {test_case['expected_strategy']}")
        
        try:
            result = query(test_case['query'])
            
            # 分析路由结果
            route_taken = result.get('route_taken', [])
            actual_strategy = "未知"
            
            if 'local_search' in route_taken:
                actual_strategy = "local_search"
            elif 'global_search' in route_taken:
                actual_strategy = "global_search"
            elif 'hybrid_search' in route_taken:
                actual_strategy = "hybrid_search"
            
            print(f"实际策略: {actual_strategy}")
            print(f"执行时间: {result.get('execution_time', 0):.2f}s")
            print(f"置信度: {result.get('quality_score', 'N/A')}")
            print(f"完整路由: {' -> '.join(route_taken)}")
            
            # 显示答案的前200个字符
            answer = result.get('answer', '无答案')
            print(f"答案摘要: {answer[:200]}...")
            
            # 检查是否符合期望
            if actual_strategy == test_case['expected_strategy']:
                print("✅ 路由策略符合预期")
            else:
                print("❌ 路由策略不符合预期")
            
            # 检查是否使用了本地检索（新增）
            sources = result.get('sources', [])
            web_search_used = any('web_search' in str(source).lower() for source in sources) if sources else False
            need_web_search = result.get('route_taken', [])
            web_in_route = 'web_search' in need_web_search
            
            if web_in_route:
                print("⚠️ 使用了网络搜索补充")
                # 检查是否是因为本地检索质量不足
                confidence = result.get('quality_score', 0)
                print(f"   本地检索置信度: {confidence}")
                if confidence < 0.7:
                    print("   原因: 本地内容质量不足，需要网络补充")
                else:
                    print("   原因: 其他因素触发网络搜索")
            else:
                print("✅ 完全使用本地检索，无需网络搜索")
            
            # 特别检查预期的关键信息是否存在
            answer_lower = answer.lower()
            query_lower = test_case['query'].lower()
            
            expected_keywords = {
                "openai": ["6.6", "billion", "157", "thrive"],
                "amazon": ["8", "billion", "anthropic", "4 billion"],  
                "databricks": ["62", "billion", "10 billion", "series j"],
                "合作": ["amazon", "anthropic", "aws", "partnership"],
                "投资": ["amazon", "anthropic", "thrive", "funding"]
            }
            
            found_keywords = False
            for category, keywords in expected_keywords.items():
                if category in query_lower:
                    found_count = sum(1 for kw in keywords if kw in answer_lower)
                    if found_count >= 2:  # 至少找到2个关键词
                        print(f"✅ 找到期望的关键信息 ({category}): {found_count}/{len(keywords)} 个关键词")
                        found_keywords = True
                        break
            
            if not found_keywords:
                print("⚠️ 未找到明显的期望关键信息")
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        
        print("-" * 80)

    # 保留原有的单个查询测试
    print("\n=== 原有测试保持不变 ===")
    original_test_query = "LangGraph是什么？它和LangChain有什么关系？"
    
    # 同步查询测试
    print("\n--- 同步查询测试 ---")
    sync_result = query(original_test_query)
    print(f"答案: {sync_result['answer']}")
    print(f"来源: {sync_result['sources']}")
    print(f"路由: {sync_result['route_taken']}")

    # 异步查询测试
    async def main_async():
        print("\n--- 异步查询测试 ---")
        async_result = await query_async(original_test_query)
        print(f"答案: {async_result['answer']}")

    asyncio.run(main_async())

    # 流式查询测试
    print("\n--- 流式查询测试 ---")
    async def test_stream():
        workflow = get_workflow()
        async for step in workflow.query_stream_async(original_test_query):
            print(step)
            print("-" * 20)
    
    asyncio.run(test_stream())