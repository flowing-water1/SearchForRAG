"""
增强版工作流编排 - 集成综合错误处理和日志记录
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Union
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .config import config
from ..agents.query_analysis import query_analysis_node
from ..agents.lightrag_retrieval import lightrag_retrieval_node
from ..agents.quality_assessment import quality_assessment_node
from ..agents.web_search import web_search_node
from ..agents.answer_generation import answer_generation_node
from ..utils.advanced_logging import (
    setup_logger, get_performance_logger, audit_log, 
    performance_context, record_metric
)
from ..utils.error_handling import (
    handle_errors, retry_on_failure, ErrorContext,
    SystemError, ConfigurationError, ErrorSeverity, ErrorCategory
)

logger = setup_logger(__name__)
perf_logger = get_performance_logger(__name__)


class EnhancedIntelligentQAWorkflow:
    """
    增强版智能问答工作流管理器
    
    集成了全面的错误处理、性能监控和日志记录功能
    """
    
    def __init__(self):
        self.graph = None
        self.compiled_graph = None
        self.is_initialized = False
        self.workflow_id = str(uuid.uuid4())
        self.performance_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "node_performance": {}
        }
        
        # 审计日志
        audit_log("workflow_creation", details={"workflow_id": self.workflow_id})
        
        # 初始化工作流
        self._initialize_workflow()
    
    @handle_errors(reraise=True)
    def _initialize_workflow(self):
        """初始化工作流图"""
        with performance_context("workflow_initialization", __name__):
            logger.info(f"初始化智能问答工作流 {self.workflow_id}...")
            
            try:
                # 创建状态图
                self.graph = StateGraph(AgentState)
                
                # 添加节点
                self._add_nodes()
                
                # 添加边和条件路由
                self._add_edges()
                
                # 编译工作流
                self._compile_workflow()
                
                self.is_initialized = True
                logger.info(f"✅ 智能问答工作流初始化成功 {self.workflow_id}")
                
                # 记录指标
                record_metric("workflow_initialized", 1, workflow_id=self.workflow_id)
                
            except Exception as e:
                logger.error(f"❌ 工作流初始化失败: {e}")
                raise ConfigurationError(
                    f"工作流初始化失败: {str(e)}",
                    error_code="WORKFLOW_INIT_FAILED",
                    severity=ErrorSeverity.CRITICAL,
                    recovery_suggestions=[
                        "检查所有依赖模块是否正确安装",
                        "验证配置文件设置",
                        "查看详细错误日志"
                    ]
                )
    
    def _add_nodes(self):
        """添加工作流节点"""
        logger.info("添加工作流节点...")
        
        # 使用装饰器包装节点以增加错误处理
        wrapped_nodes = {
            "query_analysis": self._wrap_node(query_analysis_node, "query_analysis"),
            "lightrag_retrieval": self._wrap_node(lightrag_retrieval_node, "lightrag_retrieval"),
            "quality_assessment": self._wrap_node(quality_assessment_node, "quality_assessment"),
            "web_search": self._wrap_node(web_search_node, "web_search"),
            "answer_generation": self._wrap_node(answer_generation_node, "answer_generation")
        }
        
        # 添加节点到图
        for node_name, node_func in wrapped_nodes.items():
            self.graph.add_node(node_name, node_func)
            logger.debug(f"添加节点: {node_name}")
        
        logger.info("所有节点已添加完成")
    
    def _wrap_node(self, node_func, node_name: str):
        """包装节点函数以增加错误处理和性能监控"""
        
        def wrapped_node(state: AgentState) -> Dict[str, Any]:
            node_start_time = time.time()
            
            try:
                with performance_context(f"node_{node_name}", f"workflow.{node_name}"):
                    logger.info(f"🔄 执行节点: {node_name}")
                    
                    # 记录节点开始
                    audit_log(
                        "node_execution_start",
                        details={
                            "node_name": node_name,
                            "workflow_id": self.workflow_id,
                            "state_keys": list(state.keys())
                        }
                    )
                    
                    # 执行节点
                    result = node_func(state)
                    
                    # 记录执行时间
                    execution_time = time.time() - node_start_time
                    self._update_node_performance(node_name, execution_time, True)
                    
                    logger.info(f"✅ 节点执行成功: {node_name} ({execution_time:.2f}s)")
                    
                    # 记录节点完成
                    audit_log(
                        "node_execution_success",
                        details={
                            "node_name": node_name,
                            "workflow_id": self.workflow_id,
                            "execution_time": execution_time,
                            "result_keys": list(result.keys()) if result else []
                        }
                    )
                    
                    return result
                    
            except Exception as e:
                execution_time = time.time() - node_start_time
                self._update_node_performance(node_name, execution_time, False)
                
                logger.error(f"❌ 节点执行失败: {node_name} ({execution_time:.2f}s) - {str(e)}")
                
                # 记录错误
                audit_log(
                    "node_execution_error",
                    details={
                        "node_name": node_name,
                        "workflow_id": self.workflow_id,
                        "execution_time": execution_time,
                        "error": str(e)
                    }
                )
                
                # 根据节点类型决定错误处理策略
                if node_name in ["query_analysis", "lightrag_retrieval"]:
                    # 关键节点错误，直接抛出
                    raise SystemError(
                        f"{node_name} 节点执行失败: {str(e)}",
                        error_code=f"NODE_{node_name.upper()}_FAILED",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH
                    )
                else:
                    # 非关键节点错误，返回错误状态
                    return {
                        "error": str(e),
                        "node_name": node_name,
                        "execution_time": execution_time,
                        "success": False
                    }
        
        return wrapped_node
    
    def _update_node_performance(self, node_name: str, execution_time: float, success: bool):
        """更新节点性能统计"""
        if node_name not in self.performance_stats["node_performance"]:
            self.performance_stats["node_performance"][node_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_time": 0.0,
                "average_time": 0.0
            }
        
        stats = self.performance_stats["node_performance"][node_name]
        stats["total_executions"] += 1
        stats["total_time"] += execution_time
        stats["average_time"] = stats["total_time"] / stats["total_executions"]
        
        if success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
        
        # 记录指标
        record_metric(
            f"node_{node_name}_execution_time",
            execution_time,
            node_name=node_name,
            success=success
        )
    
    def _add_edges(self):
        """添加边和条件路由"""
        logger.info("配置工作流路由...")
        
        # 设置入口点
        self.graph.set_entry_point("query_analysis")
        
        # 查询分析 → LightRAG 检索
        self.graph.add_edge("query_analysis", "lightrag_retrieval")
        
        # LightRAG 检索 → 质量评估
        self.graph.add_edge("lightrag_retrieval", "quality_assessment")
        
        # 质量评估 → 条件路由 (网络搜索 或 答案生成)
        self.graph.add_conditional_edges(
            "quality_assessment",
            self._should_use_web_search,
            {
                "web_search": "web_search",
                "answer_generation": "answer_generation"
            }
        )
        
        # 网络搜索 → 答案生成
        self.graph.add_edge("web_search", "answer_generation")
        
        # 答案生成 → 结束
        self.graph.add_edge("answer_generation", END)
        
        logger.info("工作流路由配置完成")
    
    def _should_use_web_search(self, state: AgentState) -> str:
        """
        决定是否需要网络搜索
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        try:
            need_web_search = state.get("need_web_search", False)
            confidence_score = state.get("confidence_score", 0.0)
            
            logger.debug(f"质量评估决策: need_web_search={need_web_search}, confidence={confidence_score:.2f}")
            
            if need_web_search:
                logger.info("🔍 质量评估判定需要网络搜索补充")
                record_metric("web_search_triggered", 1, confidence_score=confidence_score)
                return "web_search"
            else:
                logger.info("✅ 质量评估判定可直接生成答案")
                record_metric("direct_answer_generation", 1, confidence_score=confidence_score)
                return "answer_generation"
                
        except Exception as e:
            logger.error(f"路由决策失败: {e}")
            # 默认到答案生成
            return "answer_generation"
    
    @handle_errors(reraise=True)
    def _compile_workflow(self):
        """编译工作流"""
        logger.info("编译工作流...")
        
        try:
            # 创建内存检查点
            memory = MemorySaver()
            
            # 编译图
            self.compiled_graph = self.graph.compile(
                checkpointer=memory,
                debug=config.DEBUG_MODE
            )
            
            logger.info("✅ 工作流编译成功")
            
        except Exception as e:
            logger.error(f"❌ 工作流编译失败: {e}")
            raise ConfigurationError(
                f"工作流编译失败: {str(e)}",
                error_code="WORKFLOW_COMPILE_FAILED",
                severity=ErrorSeverity.CRITICAL
            )
    
    @handle_errors(reraise=True)
    @retry_on_failure(max_retries=2, backoff_factor=1.0)
    async def arun(self, 
                   user_query: str, 
                   config_override: Optional[Dict[str, Any]] = None,
                   thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        异步运行工作流
        
        Args:
            user_query: 用户查询
            config_override: 配置覆盖
            thread_id: 线程ID (用于会话管理)
            
        Returns:
            工作流执行结果
        """
        if not self.is_initialized:
            raise SystemError(
                "工作流未初始化",
                error_code="WORKFLOW_NOT_INITIALIZED",
                severity=ErrorSeverity.HIGH
            )
        
        query_id = str(uuid.uuid4())
        start_time = time.time()
        
        with performance_context(f"workflow_execution_{query_id}", __name__):
            logger.info(f"开始处理查询 {query_id}: {user_query[:100]}...")
            
            # 记录查询开始
            audit_log(
                "query_start",
                details={
                    "query_id": query_id,
                    "user_query": user_query[:500],  # 限制长度
                    "thread_id": thread_id,
                    "workflow_id": self.workflow_id
                }
            )
            
            # 初始化状态
            initial_state = {
                "user_query": user_query,
                "query_id": query_id,
                "thread_id": thread_id or "default",
                "workflow_id": self.workflow_id,
                "start_time": start_time,
                "query_type": "",
                "lightrag_mode": "",
                "key_entities": [],
                "processed_query": "",
                "lightrag_results": {},
                "retrieval_score": 0.0,
                "retrieval_success": False,
                "confidence_score": 0.0,
                "need_web_search": False,
                "web_results": [],
                "final_answer": "",
                "sources": [],
                "context_used": 0,
                "answer_confidence": 0.0
            }
            
            # 配置
            run_config = {
                "configurable": {
                    "thread_id": thread_id or "default"
                }
            }
            
            if config_override:
                run_config.update(config_override)
            
            try:
                # 执行工作流
                result = await self.compiled_graph.ainvoke(
                    initial_state,
                    config=run_config
                )
                
                # 计算执行时间
                execution_time = time.time() - start_time
                
                # 更新统计
                self._update_query_stats(True, execution_time)
                
                # 记录成功
                logger.info(f"✅ 工作流执行完成 {query_id} ({execution_time:.2f}s)")
                
                audit_log(
                    "query_success",
                    details={
                        "query_id": query_id,
                        "execution_time": execution_time,
                        "final_answer_length": len(result.get("final_answer", "")),
                        "sources_count": len(result.get("sources", [])),
                        "confidence_score": result.get("answer_confidence", 0.0)
                    }
                )
                
                # 添加执行信息
                result.update({
                    "query_id": query_id,
                    "execution_time": execution_time,
                    "workflow_id": self.workflow_id,
                    "success": True
                })
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                self._update_query_stats(False, execution_time)
                
                logger.error(f"❌ 工作流执行失败 {query_id} ({execution_time:.2f}s): {e}")
                
                audit_log(
                    "query_failure",
                    details={
                        "query_id": query_id,
                        "execution_time": execution_time,
                        "error": str(e)
                    }
                )
                
                raise
    
    def _update_query_stats(self, success: bool, execution_time: float):
        """更新查询统计"""
        self.performance_stats["total_queries"] += 1
        
        if success:
            self.performance_stats["successful_queries"] += 1
        else:
            self.performance_stats["failed_queries"] += 1
        
        # 更新平均响应时间
        total_time = (self.performance_stats["average_response_time"] * 
                     (self.performance_stats["total_queries"] - 1) + execution_time)
        self.performance_stats["average_response_time"] = total_time / self.performance_stats["total_queries"]
        
        # 记录指标
        record_metric("query_execution_time", execution_time, success=success)
        record_metric("total_queries", self.performance_stats["total_queries"])
        record_metric("success_rate", 
                     self.performance_stats["successful_queries"] / self.performance_stats["total_queries"])
    
    def run(self, 
            user_query: str, 
            config_override: Optional[Dict[str, Any]] = None,
            thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        同步运行工作流
        
        Args:
            user_query: 用户查询
            config_override: 配置覆盖
            thread_id: 线程ID
            
        Returns:
            工作流执行结果
        """
        return asyncio.run(self.arun(user_query, config_override, thread_id))
    
    def stream(self, 
               user_query: str, 
               config_override: Optional[Dict[str, Any]] = None,
               thread_id: Optional[str] = None):
        """
        流式执行工作流
        
        Args:
            user_query: 用户查询
            config_override: 配置覆盖
            thread_id: 线程ID
            
        Yields:
            工作流执行步骤
        """
        if not self.is_initialized:
            raise SystemError(
                "工作流未初始化",
                error_code="WORKFLOW_NOT_INITIALIZED",
                severity=ErrorSeverity.HIGH
            )
        
        query_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"开始流式处理查询 {query_id}: {user_query[:100]}...")
        
        # 初始化状态
        initial_state = {
            "user_query": user_query,
            "query_id": query_id,
            "thread_id": thread_id or "default",
            "workflow_id": self.workflow_id,
            "start_time": start_time,
            "query_type": "",
            "lightrag_mode": "",
            "key_entities": [],
            "processed_query": "",
            "lightrag_results": {},
            "retrieval_score": 0.0,
            "retrieval_success": False,
            "confidence_score": 0.0,
            "need_web_search": False,
            "web_results": [],
            "final_answer": "",
            "sources": [],
            "context_used": 0,
            "answer_confidence": 0.0
        }
        
        # 配置
        run_config = {
            "configurable": {
                "thread_id": thread_id or "default"
            }
        }
        
        if config_override:
            run_config.update(config_override)
        
        try:
            # 流式执行
            for step in self.compiled_graph.stream(initial_state, config=run_config):
                # 添加时间戳和查询ID
                if step:
                    step_data = list(step.values())[0] if step else {}
                    step_data.update({
                        "query_id": query_id,
                        "timestamp": time.time(),
                        "workflow_id": self.workflow_id
                    })
                    
                yield step
                
            # 记录成功
            execution_time = time.time() - start_time
            self._update_query_stats(True, execution_time)
            
            logger.info(f"✅ 流式工作流执行完成 {query_id} ({execution_time:.2f}s)")
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_query_stats(False, execution_time)
            
            logger.error(f"❌ 流式工作流执行失败 {query_id} ({execution_time:.2f}s): {e}")
            raise
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """获取工作流信息"""
        return {
            "workflow_id": self.workflow_id,
            "name": "增强版智能问答工作流",
            "version": "2.0.0",
            "initialized": self.is_initialized,
            "nodes": [
                {
                    "name": "query_analysis",
                    "description": "查询分析节点",
                    "function": "分析用户查询，确定查询类型并选择最佳LightRAG模式"
                },
                {
                    "name": "lightrag_retrieval", 
                    "description": "LightRAG检索节点 (HKUDS/LightRAG)",
                    "function": "使用HKUDS/LightRAG执行智能检索，支持naive/local/global/hybrid/mix模式"
                },
                {
                    "name": "quality_assessment",
                    "description": "质量评估节点",
                    "function": "评估检索结果质量，决定是否需要网络搜索补充"
                },
                {
                    "name": "web_search",
                    "description": "网络搜索节点",
                    "function": "当本地信息不足时，从网络获取补充信息"
                },
                {
                    "name": "answer_generation",
                    "description": "答案生成节点",
                    "function": "整合本地和网络信息，生成最终答案"
                }
            ],
            "workflow_pattern": "查询分析 → HKUDS/LightRAG检索 → 质量评估 → [网络搜索] → 答案生成",
            "features": [
                "智能查询分析和路由",
                "多模式HKUDS/LightRAG检索",
                "质量评估和决策",
                "网络搜索补充",
                "答案生成和整合",
                "流式处理支持",
                "会话记忆管理",
                "综合错误处理",
                "性能监控",
                "审计日志记录"
            ],
            "performance_stats": self.performance_stats
        }
    
    def get_workflow_graph(self) -> Optional[str]:
        """获取工作流图的可视化表示"""
        try:
            if self.compiled_graph:
                return self.compiled_graph.get_graph().draw_mermaid()
            return None
        except Exception as e:
            logger.warning(f"无法生成工作流图: {e}")
            return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return dict(self.performance_stats)
    
    def reset_performance_stats(self):
        """重置性能统计"""
        self.performance_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "node_performance": {}
        }
        
        logger.info("性能统计已重置")
        audit_log("performance_stats_reset", details={"workflow_id": self.workflow_id})


# 使用增强版工作流替换原有的工作流
IntelligentQAWorkflow = EnhancedIntelligentQAWorkflow

# 全局工作流实例
_workflow_instance = None


def get_workflow() -> IntelligentQAWorkflow:
    """获取全局工作流实例"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = IntelligentQAWorkflow()
    return _workflow_instance


def reset_workflow():
    """重置全局工作流实例"""
    global _workflow_instance
    if _workflow_instance:
        audit_log("workflow_reset", details={"workflow_id": _workflow_instance.workflow_id})
    _workflow_instance = None


# 便捷函数 - 现在包含错误处理
async def query_async(user_query: str, 
                     config_override: Optional[Dict[str, Any]] = None,
                     thread_id: Optional[str] = None) -> Dict[str, Any]:
    """异步查询便捷函数"""
    workflow = get_workflow()
    return await workflow.arun(user_query, config_override, thread_id)


def query(user_query: str, 
          config_override: Optional[Dict[str, Any]] = None,
          thread_id: Optional[str] = None) -> Dict[str, Any]:
    """同步查询便捷函数"""
    workflow = get_workflow()
    return workflow.run(user_query, config_override, thread_id)


def query_stream(user_query: str, 
                 config_override: Optional[Dict[str, Any]] = None,
                 thread_id: Optional[str] = None):
    """流式查询便捷函数"""
    workflow = get_workflow()
    yield from workflow.stream(user_query, config_override, thread_id)


def get_workflow_info() -> Dict[str, Any]:
    """获取工作流信息"""
    workflow = get_workflow()
    return workflow.get_workflow_info()


def get_workflow_graph() -> Optional[str]:
    """获取工作流图"""
    workflow = get_workflow()
    return workflow.get_workflow_graph()


def get_performance_stats() -> Dict[str, Any]:
    """获取性能统计"""
    workflow = get_workflow()
    return workflow.get_performance_stats()


def reset_performance_stats():
    """重置性能统计"""
    workflow = get_workflow()
    workflow.reset_performance_stats()