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

# 事件循环安全执行函数
def safe_run_async(coro):
    """
    安全地运行异步协程，使用nest_asyncio支持嵌套事件循环。
    
    Args:
        coro: 要执行的协程
        
    Returns:
        协程的执行结果
        
    Raises:
        Exception: 如果协程执行过程中出现错误
    """
    try:
        # 尝试导入并应用nest_asyncio来支持嵌套事件循环
        import nest_asyncio
        nest_asyncio.apply()
        logger.info("✅ 已应用nest_asyncio支持嵌套事件循环")
    except ImportError:
        logger.warning("⚠️ nest_asyncio未安装，回退到线程池方法")
        
        # 回退方案：使用线程池
        try:
            # 检查是否已经在事件循环中运行
            loop = asyncio.get_running_loop()
            logger.warning("⚠️ 检测到已运行的事件循环，使用线程池执行")
            
            import concurrent.futures
            
            def run_in_thread():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(coro)
                        logger.info("✅ 线程池中的异步任务执行成功")
                        return result
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
                except Exception as e:
                    logger.error(f"❌ 线程池中的异步任务执行失败: {e}")
                    raise
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=300)
                
        except RuntimeError:
            # 没有运行中的事件循环，可以安全使用asyncio.run
            logger.info("✅ 创建新的事件循环执行异步任务")
            return asyncio.run(coro)
    
    # 如果成功导入nest_asyncio，直接使用asyncio.run
    try:
        logger.info("✅ 使用nest_asyncio支持的asyncio.run执行")
        return asyncio.run(coro)
    except Exception as e:
        logger.error(f"❌ nest_asyncio执行失败: {e}")
        raise

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

    def _analyze_node_data(self, node_name: str, node_data: dict, step_info: dict):
        """
        分析不同节点的关键信息并打印调试输出。
        
        Args:
            node_name (str): 节点名称
            node_data (dict): 节点数据
            step_info (dict): 步骤信息字典
        """
        try:
            # 分析不同节点的关键信息
            if node_name == "query_analysis":
                query_type = node_data.get("query_type", "未知")
                lightrag_mode = node_data.get("lightrag_mode", "未知")
                print(f"🔍 查询分析结果:")
                print(f"   查询类型: {query_type}")
                print(f"   LightRAG模式: {lightrag_mode}")
                step_info["key_metrics"] = {"query_type": query_type, "lightrag_mode": lightrag_mode}
                
            elif node_name == "strategy_route":
                route_decision = node_data.get("lightrag_mode", "未知")
                print(f"🚦 策略路由决策:")
                print(f"   选择路径: {route_decision}")
                step_info["key_metrics"] = {"route_decision": route_decision}
                
            elif "search" in node_name:
                search_results = node_data.get("search_results", [])
                lightrag_results = node_data.get("lightrag_results", {})
                context_quality = node_data.get("context_quality", "未知")
                retrieval_success = node_data.get("retrieval_success", False)
                
                print(f"📚 {node_name} 检索结果:")
                print(f"   检索成功: {'是' if retrieval_success else '否'}")
                print(f"   检索条目数: {len(search_results) if search_results else 0}")
                print(f"   上下文质量: {context_quality}")
                
                if lightrag_results and lightrag_results.get("error"):
                    print(f"   ❌ LightRAG错误: {lightrag_results.get('error')}")
                    
                if search_results:
                    print(f"   结果预览: {str(search_results)[:200]}...")
                    
                step_info["key_metrics"] = {
                    "result_count": len(search_results) if search_results else 0,
                    "context_quality": context_quality,
                    "retrieval_success": retrieval_success
                }
                
            elif node_name == "quality_assessment":
                confidence_score = node_data.get("confidence_score", 0)
                quality_score = node_data.get("quality_score", 0)
                need_web_search = node_data.get("need_web_search", False)
                assessment_reason = node_data.get("assessment_reason", "无原因")
                
                print(f"⭐ 质量评估结果:")
                print(f"   置信度分数: {confidence_score}")
                print(f"   质量分数: {quality_score}")
                print(f"   需要网络搜索: {'是' if need_web_search else '否'}")
                print(f"   评估原因: {assessment_reason}")
                
                # 质量分析
                if confidence_score < 0.7:
                    print("   ⚠️ 置信度较低，可能需要改进检索策略")
                if need_web_search:
                    print("   🌐 将启用网络搜索补充信息")
                    
                step_info["key_metrics"] = {
                    "confidence_score": confidence_score,
                    "quality_score": quality_score,
                    "need_web_search": need_web_search,
                    "assessment_reason": assessment_reason
                }
                
            elif node_name == "web_search":
                web_results = node_data.get("web_results", [])
                enhanced_context = node_data.get("enhanced_context", "")
                web_search_summary = node_data.get("web_search_summary", "")
                
                print(f"🌐 网络搜索结果:")
                print(f"   网络结果数: {len(web_results) if web_results else 0}")
                print(f"   增强上下文长度: {len(enhanced_context) if enhanced_context else 0}")
                print(f"   搜索摘要: {web_search_summary}")
                
                step_info["key_metrics"] = {
                    "web_result_count": len(web_results) if web_results else 0,
                    "enhanced_context_length": len(enhanced_context) if enhanced_context else 0
                }
                
            elif node_name == "answer_generation":
                final_answer = node_data.get("final_answer", "")
                answer_confidence = node_data.get("answer_confidence", 0)
                sources = node_data.get("sources", [])
                context_used = node_data.get("context_used", "未知")
                
                print(f"✨ 答案生成结果:")
                print(f"   答案长度: {len(final_answer) if final_answer else 0}")
                print(f"   答案置信度: {answer_confidence}")
                print(f"   信息源数量: {len(sources) if sources else 0}")
                print(f"   使用的上下文: {context_used}")
                print(f"   答案预览: {final_answer[:200] if final_answer else '无'}...")
                
                step_info["key_metrics"] = {
                    "answer_length": len(final_answer) if final_answer else 0,
                    "answer_confidence": answer_confidence,
                    "source_count": len(sources) if sources else 0
                }
            else:
                # 通用节点处理
                print(f"🔧 {node_name} 节点:")
                print(f"   数据键: {list(node_data.keys()) if isinstance(node_data, dict) else '非字典'}")
                step_info["key_metrics"] = {"data_keys": list(node_data.keys()) if isinstance(node_data, dict) else []}
                
        except Exception as e:
            print(f"   ❌ 分析节点 {node_name} 时出错: {e}")
            step_info["key_metrics"] = {"error": str(e)}

    def query(self, query_text: str, config: Optional[Dict] = None, debug: bool = False) -> Dict[str, Any]:
        """
        同步执行查询。
        
        Args:
            query_text (str): 用户查询文本
            config (Optional[Dict]): 可选的配置参数
            debug (bool): 是否启用调试模式，显示详细的执行信息
        
        Returns:
            Dict[str, Any]: 查询结果，如果debug=True则返回详细调试信息
        """
        if debug:
            return self.debug_query(query_text, config)
        else:
            return safe_run_async(self.query_async(query_text, config))

    async def query_async(self, query_text: str, config: Optional[Dict] = None, debug: bool = False) -> Dict[str, Any]:
        """
        异步执行查询。
        
        Args:
            query_text (str): 用户查询文本
            config (Optional[Dict]): 可选的配置参数
            debug (bool): 是否启用调试模式，显示详细的执行信息
        
        Returns:
            Dict[str, Any]: 查询结果，如果debug=True则返回详细调试信息
        """
        if debug:
            return await self.debug_query_async(query_text, config)
            
        # 标准查询执行
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

    async def debug_query_async(self, query_text: str, config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        异步执行查询并提供详细的调试信息。
        使用stream_mode="debug"来获取每个节点的详细执行状态。
        
        Args:
            query_text (str): 用户查询文本
            config (Optional[Dict]): 可选的配置参数
        
        Returns:
            Dict[str, Any]: 包含详细调试信息的结果
        """
        start_time = time.time()
        query_id = f"debug-query-{uuid.uuid4()}"
        thread_id = (config or {}).get("configurable", {}).get("thread_id", f"thread-{uuid.uuid4()}")

        initial_state = {
            "user_query": query_text,
            "session_id": thread_id,
            "query_id": query_id
        }

        run_config = {"configurable": {"thread_id": thread_id}}
        
        print("🔍 开始详细调试执行...")
        print(f"📝 查询: {query_text}")
        print(f"🆔 查询ID: {query_id}")
        print("=" * 80)

        # 收集调试信息
        debug_info = {
            "query_text": query_text,
            "query_id": query_id,
            "execution_steps": [],
            "final_result": None,
            "execution_time": 0
        }

        step_count = 0
        
        # 使用debug流模式获取详细信息
        async for chunk in self.compiled_graph.astream(initial_state, config=run_config, stream_mode="debug"):
            step_count += 1
            
            # 打印原始chunk用于调试
            print(f"\n🚀 步骤 {step_count}: 收到调试信息")
            print(f"Chunk类型: {type(chunk)}")
            print(f"Chunk内容: {chunk}")
            print("-" * 60)
            
            # 安全解析调试chunk
            try:
                if isinstance(chunk, dict):
                    # 处理字典类型的chunk
                    for node_name, node_data in chunk.items():
                        if node_name not in ["__start__", "__end__", "step"]:
                            print(f"🎯 处理节点: '{node_name}'")
                            
                            # 提取关键状态信息
                            step_info = {
                                "step": step_count,
                                "node": node_name,
                                "input_state": {},
                                "output_state": {},
                                "key_metrics": {}
                            }

                            # 安全获取节点数据
                            if isinstance(node_data, dict):
                                self._analyze_node_data(node_name, node_data, step_info)
                                
                                # 记录状态变化
                                step_info["input_state"] = dict(node_data)
                                step_info["output_state"] = dict(node_data)
                                
                                debug_info["execution_steps"].append(step_info)
                            else:
                                print(f"   ⚠️ 节点数据格式异常: {type(node_data)}")
                                
                elif hasattr(chunk, '__iter__') and not isinstance(chunk, (str, bytes)):
                    # 处理其他可迭代类型
                    print(f"   处理可迭代chunk: {chunk}")
                else:
                    # 处理其他类型的chunk
                    print(f"   跳过非字典类型chunk: {chunk}")
                    
            except Exception as e:
                print(f"   ❌ 解析chunk时出错: {e}")
                print(f"   Chunk详情: {chunk}")
                continue
                    
        execution_time = time.time() - start_time
        debug_info["execution_time"] = execution_time
        
        # 获取最终状态
        final_state = await self.compiled_graph.ainvoke(initial_state, config=run_config)
        debug_info["final_result"] = {
            "answer": final_state.get("final_answer"),
            "sources": final_state.get("sources"),
            "quality_score": final_state.get("confidence_score"),
            "answer_confidence": final_state.get("answer_confidence")
        }

        print("\n" + "=" * 80)
        print("📊 执行摘要:")
        print(f"⏱️  总执行时间: {execution_time:.2f}s")
        print(f"🔢 执行步骤数: {len(debug_info['execution_steps'])}")
        
        # 分析执行路径
        node_sequence = [step["node"] for step in debug_info["execution_steps"]]
        print(f"🛤️  执行路径: {' → '.join(node_sequence)}")
        
        # 质量分析摘要
        quality_issues = []
        for step in debug_info["execution_steps"]:
            if step["node"] == "quality_assessment":
                confidence = step["key_metrics"].get("confidence_score", 0)
                if confidence < 0.7:
                    quality_issues.append(f"质量评估置信度较低 ({confidence})")
                if step["key_metrics"].get("need_web_search"):
                    quality_issues.append("本地信息不足，需要网络搜索补充")
                    
        if quality_issues:
            print("⚠️ 发现的问题:")
            for issue in quality_issues:
                print(f"   - {issue}")
        else:
            print("✅ 执行过程无明显问题")
            
        return debug_info

    def debug_query(self, query_text: str, config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        同步执行查询并提供详细的调试信息。
        
        Args:
            query_text (str): 用户查询文本
            config (Optional[Dict]): 可选的配置参数
        
        Returns:
            Dict[str, Any]: 包含详细调试信息的结果
        """
        return safe_run_async(self.debug_query_async(query_text, config))

    def query_stream(self, query_text: str, config: Optional[Dict] = None):
        """
        流式执行查询。
        """
        return safe_run_async(self.query_stream_async(query_text, config))

    async def query_stream_async(self, query_text: str, config: Optional[Dict] = None):
        """
        异步流式执行查询。
        """
        thread_id = (config or {}).get("configurable", {}).get("thread_id", f"thread-{uuid.uuid4()}")
        run_config = {"configurable": {"thread_id": thread_id}}
        initial_state = {"user_query": query_text, "session_id": thread_id}
        
        async for chunk in self.compiled_graph.astream(initial_state, run_config):
            yield chunk

    async def enhanced_debug_query_async(self, query_text: str, config: Optional[Dict] = None, 
                                         stream_modes: List[str] = None) -> Dict[str, Any]:
        """
        增强版异步调试查询，支持多种LangGraph stream_mode的组合监控。
        
        Args:
            query_text (str): 用户查询文本
            config (Optional[Dict]): 可选的配置参数
            stream_modes (List[str]): 监控模式列表，支持 ['debug', 'updates', 'values', 'messages', 'custom']
        
        Returns:
            Dict[str, Any]: 包含详细调试信息的结果
        """
        if stream_modes is None:
            stream_modes = ["debug", "updates"]  # 默认组合模式
            
        start_time = time.time()
        query_id = f"enhanced-debug-{uuid.uuid4()}"
        thread_id = (config or {}).get("configurable", {}).get("thread_id", f"thread-{uuid.uuid4()}")

        initial_state = {
            "user_query": query_text,
            "session_id": thread_id,
            "query_id": query_id
        }

        run_config = {"configurable": {"thread_id": thread_id}}
        
        print("🔍 开始增强版调试执行...")
        print(f"📝 查询: {query_text}")
        print(f"🆔 查询ID: {query_id}")
        print(f"📊 监控模式: {stream_modes}")
        print("=" * 80)

        # 收集增强调试信息
        enhanced_debug_info = {
            "query_text": query_text,
            "query_id": query_id,
            "stream_modes": stream_modes,
            "execution_steps": [],
            "state_history": [],
            "node_updates": [],
            "llm_messages": [],
            "custom_events": [],
            "final_result": None,
            "execution_time": 0,
            "data_verification": {}
        }

        step_count = 0
        
        # 使用多种流模式获取综合信息
        try:
            async for stream_mode, chunk in self.compiled_graph.astream(
                initial_state, 
                config=run_config, 
                stream_mode=stream_modes
            ):
                step_count += 1
                
                print(f"\n🚀 步骤 {step_count}: [{stream_mode}] 模式数据")
                print(f"Chunk类型: {type(chunk)}")
                print(f"Chunk内容: {chunk}")
                print("-" * 60)
                
                # 根据流模式分类处理
                if stream_mode == "debug":
                    self._process_debug_chunk(chunk, enhanced_debug_info, step_count)
                elif stream_mode == "updates":
                    self._process_updates_chunk(chunk, enhanced_debug_info, step_count)
                elif stream_mode == "values":
                    self._process_values_chunk(chunk, enhanced_debug_info, step_count)
                elif stream_mode == "messages":
                    self._process_messages_chunk(chunk, enhanced_debug_info, step_count)
                elif stream_mode == "custom":
                    self._process_custom_chunk(chunk, enhanced_debug_info, step_count)
                    
        except Exception as e:
            print(f"❌ 增强调试执行出错: {e}")
            enhanced_debug_info["execution_error"] = str(e)
            
        execution_time = time.time() - start_time
        enhanced_debug_info["execution_time"] = execution_time
        
        # 执行数据验证检查
        enhanced_debug_info["data_verification"] = await self._verify_lightrag_data()
        
        # 获取最终状态
        try:
            final_state = await self.compiled_graph.ainvoke(initial_state, config=run_config)
            enhanced_debug_info["final_result"] = {
                "answer": final_state.get("final_answer"),
                "sources": final_state.get("sources"),
                "quality_score": final_state.get("confidence_score"),
                "answer_confidence": final_state.get("answer_confidence"),
                "full_state": final_state
            }
        except Exception as e:
            enhanced_debug_info["final_result"] = {"error": str(e)}

        # 生成综合分析报告
        analysis_report = self._generate_analysis_report(enhanced_debug_info)
        enhanced_debug_info["analysis_report"] = analysis_report

        print("\n" + "=" * 80)
        print("📊 增强调试摘要:")
        print(f"⏱️  总执行时间: {execution_time:.2f}s")
        print(f"🔢 监控事件数: {step_count}")
        print(f"🛤️  监控模式: {stream_modes}")
        
        # 打印关键发现
        if analysis_report.get("critical_issues"):
            print("⚠️ 发现关键问题:")
            for issue in analysis_report["critical_issues"]:
                print(f"   - {issue}")
        else:
            print("✅ 未发现明显问题")
            
        return enhanced_debug_info

    def _process_debug_chunk(self, chunk: Any, debug_info: Dict, step_count: int):
        """处理debug模式的chunk数据"""
        try:
            if isinstance(chunk, dict):
                for node_name, node_data in chunk.items():
                    if node_name not in ["__start__", "__end__", "step"]:
                        step_info = {
                            "step": step_count,
                            "node": node_name,
                            "mode": "debug",
                            "data": node_data,
                            "timestamp": time.time()
                        }
                        
                        # 分析节点数据
                        if isinstance(node_data, dict):
                            self._analyze_node_data(node_name, node_data, step_info)
                            
                        debug_info["execution_steps"].append(step_info)
        except Exception as e:
            print(f"   ❌ 处理debug chunk失败: {e}")

    def _process_updates_chunk(self, chunk: Any, debug_info: Dict, step_count: int):
        """处理updates模式的chunk数据"""
        try:
            if isinstance(chunk, dict):
                for node_name, update_data in chunk.items():
                    update_info = {
                        "step": step_count,
                        "node": node_name,
                        "mode": "updates",
                        "update": update_data,
                        "timestamp": time.time()
                    }
                    debug_info["node_updates"].append(update_info)
                    print(f"   📝 节点更新: {node_name} -> {list(update_data.keys()) if isinstance(update_data, dict) else type(update_data)}")
        except Exception as e:
            print(f"   ❌ 处理updates chunk失败: {e}")

    def _process_values_chunk(self, chunk: Any, debug_info: Dict, step_count: int):
        """处理values模式的chunk数据"""
        try:
            state_info = {
                "step": step_count,
                "mode": "values",
                "state": chunk,
                "timestamp": time.time()
            }
            debug_info["state_history"].append(state_info)
            print(f"   🏛️ 完整状态: {list(chunk.keys()) if isinstance(chunk, dict) else type(chunk)}")
        except Exception as e:
            print(f"   ❌ 处理values chunk失败: {e}")

    def _process_messages_chunk(self, chunk: Any, debug_info: Dict, step_count: int):
        """处理messages模式的chunk数据"""
        try:
            if isinstance(chunk, tuple) and len(chunk) == 2:
                message, metadata = chunk
                message_info = {
                    "step": step_count,
                    "mode": "messages",
                    "message": message,
                    "metadata": metadata,
                    "timestamp": time.time()
                }
                debug_info["llm_messages"].append(message_info)
                print(f"   💬 LLM消息: {message.content[:50] if hasattr(message, 'content') and message.content else 'N/A'}...")
        except Exception as e:
            print(f"   ❌ 处理messages chunk失败: {e}")

    def _process_custom_chunk(self, chunk: Any, debug_info: Dict, step_count: int):
        """处理custom模式的chunk数据"""
        try:
            custom_info = {
                "step": step_count,
                "mode": "custom",
                "data": chunk,
                "timestamp": time.time()
            }
            debug_info["custom_events"].append(custom_info)
            print(f"   🎯 自定义事件: {chunk}")
        except Exception as e:
            print(f"   ❌ 处理custom chunk失败: {e}")

    async def _verify_lightrag_data(self) -> Dict[str, Any]:
        """验证LightRAG数据状态"""
        verification_result = {
            "lightrag_initialized": False,
            "data_loaded": False,
            "postgres_connected": False,
            "neo4j_connected": False,
            "vector_index_ready": False,
            "knowledge_graph_ready": False,
            "data_stats": {},
            "database_info": {
                "postgres_host": config.POSTGRES_HOST,
                "postgres_db": config.POSTGRES_DB,
                "neo4j_uri": config.NEO4J_URI
            }
        }
        
        try:
            # 1. 检查LightRAG实例
            from ..utils.lightrag_client import get_lightrag_instance
            
            lightrag_client = get_lightrag_instance()
            if lightrag_client and lightrag_client.rag_instance:
                verification_result["lightrag_initialized"] = True
                
                # 2. 测试PostgreSQL连接
                try:
                    import psycopg2
                    pg_conn = psycopg2.connect(
                        host=config.POSTGRES_HOST,
                        port=config.POSTGRES_PORT,
                        database=config.POSTGRES_DB,
                        user=config.POSTGRES_USER,
                        password=config.POSTGRES_PASSWORD
                    )
                    with pg_conn.cursor() as cur:
                        cur.execute("SELECT version();")
                        pg_version = cur.fetchone()[0]
                        verification_result["postgres_connected"] = True
                        verification_result["data_stats"]["postgres_version"] = pg_version
                    pg_conn.close()
                except Exception as e:
                    verification_result["data_stats"]["postgres_error"] = str(e)
                
                # 3. 测试Neo4j连接
                try:
                    from neo4j import GraphDatabase
                    neo4j_driver = GraphDatabase.driver(
                        config.NEO4J_URI,
                        auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
                    )
                    with neo4j_driver.session() as session:
                        result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
                        neo4j_info = result.single()
                        verification_result["neo4j_connected"] = True
                        verification_result["data_stats"]["neo4j_info"] = dict(neo4j_info)
                    neo4j_driver.close()
                except Exception as e:
                    verification_result["data_stats"]["neo4j_error"] = str(e)
                
                # 4. 检查数据是否加载
                if verification_result["postgres_connected"]:
                    try:
                        pg_conn = psycopg2.connect(
                            host=config.POSTGRES_HOST,
                            port=config.POSTGRES_PORT,
                            database=config.POSTGRES_DB,
                            user=config.POSTGRES_USER,
                            password=config.POSTGRES_PASSWORD
                        )
                        with pg_conn.cursor() as cur:
                            # 检查文档表
                            cur.execute("SELECT COUNT(*) FROM full_docs;")
                            doc_count = cur.fetchone()[0]
                            verification_result["data_stats"]["document_count"] = doc_count
                            
                            # 检查向量表
                            cur.execute("SELECT COUNT(*) FROM vdb_entities;")
                            entity_count = cur.fetchone()[0]
                            verification_result["data_stats"]["entity_count"] = entity_count
                            
                            if doc_count > 0:
                                verification_result["data_loaded"] = True
                            if entity_count > 0:
                                verification_result["vector_index_ready"] = True
                                
                        pg_conn.close()
                    except Exception as e:
                        verification_result["data_stats"]["pg_query_error"] = str(e)
                
                # 5. 检查Neo4j知识图谱
                if verification_result["neo4j_connected"]:
                    try:
                        neo4j_driver = GraphDatabase.driver(
                            config.NEO4J_URI,
                            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
                        )
                        with neo4j_driver.session() as session:
                            # 检查节点数量
                            result = session.run("MATCH (n) RETURN COUNT(n) as node_count")
                            node_count = result.single()["node_count"]
                            verification_result["data_stats"]["neo4j_node_count"] = node_count
                            
                            # 检查关系数量
                            result = session.run("MATCH ()-[r]->() RETURN COUNT(r) as rel_count")
                            rel_count = result.single()["rel_count"]
                            verification_result["data_stats"]["neo4j_relationship_count"] = rel_count
                            
                            if node_count > 0:
                                verification_result["knowledge_graph_ready"] = True
                                
                        neo4j_driver.close()
                    except Exception as e:
                        verification_result["data_stats"]["neo4j_query_error"] = str(e)
                        
            print(f"🔍 数据源验证结果: {verification_result}")
            
        except Exception as e:
            verification_result["error"] = str(e)
            print(f"❌ 数据源验证失败: {e}")
            
        return verification_result

    def _generate_analysis_report(self, debug_info: Dict) -> Dict[str, Any]:
        """生成综合分析报告"""
        report = {
            "critical_issues": [],
            "warnings": [],
            "performance_metrics": {},
            "recommendations": [],
            "database_status": {}
        }
        
        try:
            # 分析数据验证结果
            data_verification = debug_info.get("data_verification", {})
            
            # 数据库连接问题检查
            if not data_verification.get("lightrag_initialized"):
                report["critical_issues"].append("LightRAG未正确初始化")
            if not data_verification.get("postgres_connected"):
                report["critical_issues"].append(f"PostgreSQL连接失败 ({data_verification.get('database_info', {}).get('postgres_host', 'unknown')})")
            if not data_verification.get("neo4j_connected"):
                report["critical_issues"].append(f"Neo4j连接失败 ({data_verification.get('database_info', {}).get('neo4j_uri', 'unknown')})")
            
            # 数据准备状态检查
            if not data_verification.get("data_loaded"):
                report["warnings"].append("数据库中无文档数据")
            if not data_verification.get("vector_index_ready"):
                report["warnings"].append("向量索引未准备就绪")
            if not data_verification.get("knowledge_graph_ready"):
                report["warnings"].append("知识图谱未准备就绪")
                
            # 数据库状态摘要
            report["database_status"] = {
                "postgres_connected": data_verification.get("postgres_connected", False),
                "neo4j_connected": data_verification.get("neo4j_connected", False),
                "document_count": data_verification.get("data_stats", {}).get("document_count", 0),
                "entity_count": data_verification.get("data_stats", {}).get("entity_count", 0),
                "neo4j_node_count": data_verification.get("data_stats", {}).get("neo4j_node_count", 0),
                "neo4j_relationship_count": data_verification.get("data_stats", {}).get("neo4j_relationship_count", 0)
            }
                
            # 分析执行步骤
            execution_steps = debug_info.get("execution_steps", [])
            search_steps = [step for step in execution_steps if "search" in step.get("node", "")]
            
            if search_steps:
                # 检查检索质量
                low_quality_searches = []
                for step in search_steps:
                    key_metrics = step.get("key_metrics", {})
                    if key_metrics.get("context_quality") and "低" in str(key_metrics["context_quality"]):
                        low_quality_searches.append(step["node"])
                        
                if low_quality_searches:
                    report["warnings"].append(f"检索质量较低的节点: {low_quality_searches}")
                    
            # 性能指标
            report["performance_metrics"] = {
                "execution_time": debug_info.get("execution_time", 0),
                "total_steps": len(execution_steps),
                "search_steps": len(search_steps)
            }
            
            # 建议生成
            if report["critical_issues"]:
                if "PostgreSQL连接失败" in str(report["critical_issues"]):
                    report["recommendations"].append("检查PostgreSQL数据库连接配置和网络连通性")
                if "Neo4j连接失败" in str(report["critical_issues"]):
                    report["recommendations"].append("检查Neo4j数据库连接配置和认证信息")
                if "LightRAG未正确初始化" in str(report["critical_issues"]):
                    report["recommendations"].append("检查LightRAG配置和依赖项")
            
            if report["warnings"]:
                if "数据库中无文档数据" in str(report["warnings"]):
                    report["recommendations"].append("需要先导入文档数据到数据库")
                if "向量索引未准备就绪" in str(report["warnings"]):
                    report["recommendations"].append("需要构建向量索引")
                if "知识图谱未准备就绪" in str(report["warnings"]):
                    report["recommendations"].append("需要构建知识图谱")
                if "检索质量较低" in str(report["warnings"]):
                    report["recommendations"].append("考虑调整质量评估阈值或优化检索策略")
                
        except Exception as e:
            report["analysis_error"] = str(e)
            
        return report

    def enhanced_debug_query(self, query_text: str, config: Optional[Dict] = None,
                           stream_modes: List[str] = None) -> Dict[str, Any]:
        """增强版调试查询的同步封装"""
        return safe_run_async(self.enhanced_debug_query_async(query_text, config, stream_modes))

# --- 全局实例和便捷函数 ---

_workflow_instance: Optional[IntelligentQAWorkflow] = None

def get_workflow() -> IntelligentQAWorkflow:
    """获取全局工作流实例 (单例模式)。"""
    global _workflow_instance
    if _workflow_instance is None:
        logger.info("创建新的全局工作流实例...")
        _workflow_instance = IntelligentQAWorkflow()
    return _workflow_instance

def query(query_text: str, config: Optional[Dict] = None, debug: bool = False) -> Dict[str, Any]:
    """便捷的同步查询函数。"""
    workflow = get_workflow()
    return workflow.query(query_text, config, debug)

async def query_async(query_text: str, config: Optional[Dict] = None, debug: bool = False) -> Dict[str, Any]:
    """便捷的异步查询函数。"""
    workflow = get_workflow()
    return await workflow.query_async(query_text, config, debug)

def debug_query(query_text: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """便捷的同步调试查询函数。"""
    workflow = get_workflow()
    return workflow.debug_query(query_text, config)

async def debug_query_async(query_text: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """便捷的异步调试查询函数。"""
    workflow = get_workflow()
    return await workflow.debug_query_async(query_text, config)

def enhanced_debug_query(query_text: str, config: Optional[Dict] = None, 
                       stream_modes: List[str] = None) -> Dict[str, Any]:
    """便捷的增强版同步调试查询函数。"""
    workflow = get_workflow()
    return workflow.enhanced_debug_query(query_text, config, stream_modes)

async def enhanced_debug_query_async(query_text: str, config: Optional[Dict] = None,
                                   stream_modes: List[str] = None) -> Dict[str, Any]:
    """便捷的增强版异步调试查询函数。"""
    workflow = get_workflow()
    return await workflow.enhanced_debug_query_async(query_text, config, stream_modes)

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

    # 合并所有测试到一个异步函数中
    async def run_all_tests():
        print("\n=== 原有测试保持不变 ===")
        original_test_query = "LangGraph是什么？它和LangChain有什么关系？"
        
        # 同步查询测试
        print("\n--- 同步查询测试 ---")
        sync_result = query(original_test_query)
        print(f"答案: {sync_result['answer']}")
        print(f"来源: {sync_result['sources']}")
        print(f"路由: {sync_result['route_taken']}")

        # 异步查询测试
        print("\n--- 异步查询测试 ---")
        async_result = await query_async(original_test_query)
        print(f"答案: {async_result['answer']}")

        # 流式查询测试
        print("\n--- 流式查询测试 ---")
        workflow = get_workflow()
        async for step in workflow.query_stream_async(original_test_query):
            print(step)
            print("-" * 20)
    
    # 只执行一次asyncio.run()
    safe_run_async(run_all_tests())
    
    print("\n" + "=" * 100)
    print("🔍 调试模式测试")
    print("=" * 100)
    print("使用debug模式查看详细的执行过程，诊断检索质量问题...")
    
    # 选择一个典型的低置信度查询进行详细分析
    debug_test_query = "OpenAI在2024年筹集了多少资金？"
    print(f"\n📋 调试查询: {debug_test_query}")
    print("这个查询之前显示置信度较低，让我们看看详细的执行过程...")
    
    try:
        print("\n🚀 开始Debug模式执行...")
        debug_result = debug_query(debug_test_query)
        
        print("\n📈 调试分析完成!")
        print("如果您看到任何质量问题，可以：")
        print("1. 检查LightRAG数据是否充分")
        print("2. 调整quality_assessment的评分阈值")
        print("3. 改进检索策略或提示词")
        
    except Exception as e:
        print(f"❌ 调试执行失败: {e}")
        print("这可能是因为LightRAG未正确初始化或数据有问题")
    
    print("\n💡 提示：在日常使用中，您可以通过以下方式启用调试:")
    print("- query('你的问题', debug=True)")  
    print("- debug_query('你的问题')")
    print("- workflow.debug_query('你的问题')")
    print("\n调试模式会显示每个节点的详细执行信息，帮助您诊断和改进系统性能。")