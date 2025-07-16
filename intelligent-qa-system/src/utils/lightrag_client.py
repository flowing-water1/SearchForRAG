"""
LightRAG 核心集成模块 (HKUDS/LightRAG)
配置并初始化 LightRAG 实例，支持文档检索和问答
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status

from ..core.config import config
from .simple_logger import get_simple_logger

# 使用简单日志模块，避免循环导入
logger = get_simple_logger(__name__)

async def custom_llm_func(prompt: str, **kwargs) -> str:
    """
    自定义LLM函数，专门用于知识图谱构建，使用KG专用配置
    """
    try:
        import openai
        
        # LightRAG会注入一些内部参数，我们需要在这里接收它们，
        # 但不能将它们传递给OpenAI的API
        kwargs.pop("hashing_kv", None)
        kwargs.pop("history_messages", None)
        kwargs.pop("keyword_extraction", None)
        system_prompt = kwargs.pop("system_prompt", None)  # 移除system_prompt参数
        
        # 移除其他可能的LightRAG内部参数
        kwargs.pop("response_format", None)
        kwargs.pop("max_async", None) 
        kwargs.pop("max_retry", None)
        
        # 只保留OpenAI API支持的参数
        allowed_params = {
            "temperature", "max_tokens", "top_p", "frequency_penalty", 
            "presence_penalty", "stop", "seed", "logit_bias", "logprobs", "top_logprobs"
        }
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
        
        # 创建OpenAI客户端，使用知识图谱专用配置
        client = openai.AsyncOpenAI(
            api_key=config.KG_LLM_API_KEY,
            base_url=config.KG_LLM_BASE_URL
        )
        
        # 构建消息，如果有system_prompt则添加为系统消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 调用LLM API，使用过滤后的参数
        response = await client.chat.completions.create(
            model=config.KG_LLM_MODEL,
            messages=messages,
            temperature=config.KG_LLM_TEMPERATURE,
            max_tokens=config.KG_LLM_MAX_TOKENS,
            **filtered_kwargs
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"知识图谱LLM API 调用失败: {e}")
        raise

async def custom_embedding_func(texts: List[str]) -> List[List[float]]:
    """
    自定义嵌入函数，支持不同的base_url和API key
    """
    try:
        import openai
        
        # 创建OpenAI客户端，使用embedding专用配置
        client = openai.AsyncOpenAI(
            api_key=config.EMBEDDING_API_KEY,
            base_url=config.EMBEDDING_BASE_URL
        )
        
        # 调用embedding API
        response = await client.embeddings.create(
            input=texts,
            model=config.EMBEDDING_MODEL,
            dimensions=config.EMBEDDING_DIM if hasattr(config, 'EMBEDDING_DIM') else None
        )
        
        # 提取embedding向量
        embeddings = [item.embedding for item in response.data]
        return embeddings
        
    except Exception as e:
        logger.error(f"Embedding API 调用失败: {e}")
        raise

# 为自定义嵌入函数动态添加 embedding_dim 属性
# LightRAG 初始化时需要此属性来配置向量存储
if hasattr(config, 'EMBEDDING_DIM') and config.EMBEDDING_DIM:
    setattr(custom_embedding_func, 'embedding_dim', config.EMBEDDING_DIM)

def get_mode_description(mode: str) -> Dict[str, str]:
    """
    获取检索模式的特性描述
    
    Args:
        mode: 检索模式 ("local", "global", "hybrid")
        
    Returns:
        模式特性描述字典
    """
    mode_descriptions = {
        "local": {
            "algorithm": "向量相似度检索",
            "focus": "局部上下文相关信息",
            "storage_usage": "主要使用向量存储",
            "complexity": "低复杂度，快速检索",
            "best_for": "事实性查询、具体概念定义"
        },
        "global": {
            "algorithm": "知识图谱关系遍历",
            "focus": "全局知识关系网络",
            "storage_usage": "主要使用图数据库",
            "complexity": "高复杂度，深度推理",
            "best_for": "关系性查询、复杂推理"
        },
        "hybrid": {
            "algorithm": "向量检索 + 图谱遍历组合",
            "focus": "综合局部相似性和全局关系",
            "storage_usage": "同时使用向量存储和图数据库",
            "complexity": "最高复杂度，最全面覆盖",
            "best_for": "复杂分析查询、综合理解"
        }
    }
    
    return mode_descriptions.get(mode, {
        "algorithm": "未知算法",
        "focus": "未知",
        "storage_usage": "未知",
        "complexity": "未知",
        "best_for": "未知"
    })

class LightRAGClient:
    """
    LightRAG 客户端封装类 (HKUDS/LightRAG)
    提供统一的 LightRAG 接口和配置管理
    """
    
    def __init__(self):
        self.rag_instance: Optional[LightRAG] = None
        self._initialized = False
        self._working_dir = str(config.RAG_STORAGE_DIR)
        
        # 检索效果监控指标
        self._query_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "modes_used": {"local": 0, "global": 0, "hybrid": 0, "naive": 0, "mix": 0},
            "average_response_time": 0.0
        }
    
    async def initialize(self) -> bool:
        """
        初始化 LightRAG 实例
        
        Returns:
            初始化是否成功
        """
        try:
            logger.info("正在初始化 LightRAG (HKUDS)...")
            
            # 确保存储目录存在
            config.RAG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            
            # 设置PostgreSQL环境变量（LightRAG会从环境变量读取）
            os.environ["POSTGRES_HOST"] = config.POSTGRES_HOST
            os.environ["POSTGRES_PORT"] = str(config.POSTGRES_PORT)
            os.environ["POSTGRES_DATABASE"] = config.POSTGRES_DB
            os.environ["POSTGRES_USER"] = config.POSTGRES_USER
            os.environ["POSTGRES_PASSWORD"] = config.POSTGRES_PASSWORD
            
            # 设置Neo4j环境变量（LightRAG会从环境变量读取）
            os.environ["NEO4J_URI"] = config.NEO4J_URI
            os.environ["NEO4J_USERNAME"] = config.NEO4J_USERNAME
            os.environ["NEO4J_PASSWORD"] = config.NEO4J_PASSWORD
            
            # 创建 LightRAG 实例 - 使用统一存储配置
            self.rag_instance = LightRAG(
                working_dir=self._working_dir,
                llm_model_func=custom_llm_func,
                embedding_func=custom_embedding_func,
                # 统一存储方案：PostgreSQL + Neo4j
                kv_storage="PGKVStorage",
                vector_storage="PGVectorStorage", 
                graph_storage="Neo4JStorage",
                doc_status_storage="PGDocStatusStorage"
            )
            
            # 确保所有存储实例被正确初始化
            logger.info("正在初始化存储实例...")
            await self.rag_instance.initialize_storages()
            
            # 初始化pipeline状态（必须在存储初始化后）
            logger.info("正在初始化Pipeline状态...")
            await initialize_pipeline_status()
            
            self._initialized = True
            logger.info("✅ LightRAG 初始化完成")
            
            # 记录当前配置
            self._log_configuration()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ LightRAG 初始化失败: {e}")
            return False
    
    def _log_configuration(self):
        """记录当前配置信息"""
        logger.info("LightRAG 配置信息:")
        logger.info(f"  - 工作目录: {self._working_dir}")
        logger.info(f"  - 存储方案: PostgreSQL (向量/KV/文档状态) + Neo4j (图数据)")
        logger.info(f"  - 知识图谱LLM模型: {config.KG_LLM_MODEL}")
        logger.info(f"  - 知识图谱LLM Base URL: {config.KG_LLM_BASE_URL}")
        logger.info(f"  - 嵌入模型: {config.EMBEDDING_MODEL}")
        logger.info(f"  - 嵌入 Base URL: {config.EMBEDDING_BASE_URL}")
    
    async def insert_documents(self, documents: List[str]) -> bool:
        """
        插入文档到 LightRAG
        
        Args:
            documents: 文档内容列表
            
        Returns:
            插入是否成功
        """
        if not self._initialized:
            logger.error("LightRAG 未初始化，请先调用 initialize()")
            return False
            
        try:
            logger.info(f"正在插入 {len(documents)} 个文档...")
            
            # 调用 ainsert 方法
            await self.rag_instance.ainsert(documents)
                
            logger.info("✅ 文档插入完成")
            return True
            
        except Exception as e:
            import traceback
            logger.error(f"❌ 文档插入失败: {e}")
            logger.error(f"详细错误信息:\n{traceback.format_exc()}")
            return False
    
    async def query(
        self, 
        query: str, 
        mode: str = "hybrid",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行查询
        
        Args:
            query: 查询文本
            mode: 查询模式 ("naive", "local", "global", "hybrid")
            **kwargs: 额外参数
            
        Returns:
            查询结果字典
        """
        if not self._initialized:
            logger.error("LightRAG 未初始化，请先调用 initialize()")
            return {"success": False, "error": "LightRAG not initialized"}
            
        # 记录查询开始时间
        import time
        start_time = time.time()
            
        try:
            logger.info(f"执行查询: {query[:50]}... (模式: {mode})")
            
            # 更新统计
            self._query_stats["total_queries"] += 1
            self._query_stats["modes_used"][mode] = self._query_stats["modes_used"].get(mode, 0) + 1
            
            # 使用标准的LightRAG查询方式
            result = await self.rag_instance.aquery(
                query,
                param=QueryParam(mode=mode, **kwargs)
            )
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 更新成功统计
            self._query_stats["successful_queries"] += 1
            
            # 更新平均响应时间
            total_time = self._query_stats["average_response_time"] * (self._query_stats["successful_queries"] - 1) + response_time
            self._query_stats["average_response_time"] = total_time / self._query_stats["successful_queries"]
            
            # 获取模式特性描述
            mode_desc = get_mode_description(mode)
            
            return {
                "success": True,
                "content": result,
                "mode": mode,
                "query": query,
                "response_time": response_time,
                "storage_backend": {
                    "kv_storage": "PGKVStorage (PostgreSQL)",
                    "vector_storage": "PGVectorStorage (PostgreSQL)", 
                    "graph_storage": "Neo4JStorage (Neo4j)",
                    "doc_status_storage": "PGDocStatusStorage (PostgreSQL)"
                },
                "mode_description": mode_desc,
                "query_stats": self._get_query_stats()
            }
            
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            
            # 更新失败统计
            self._query_stats["failed_queries"] += 1
            
            return {
                "success": False,
                "error": str(e),
                "mode": mode,
                "query": query,
                "response_time": time.time() - start_time,
                "query_stats": self._get_query_stats()
            }
    
    def _get_query_stats(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        total = self._query_stats["total_queries"]
        success_rate = (self._query_stats["successful_queries"] / total * 100) if total > 0 else 0
        
        return {
            "total_queries": total,
            "success_rate": f"{success_rate:.1f}%",
            "average_response_time": f"{self._query_stats['average_response_time']:.2f}s",
            "modes_distribution": self._query_stats["modes_used"]
        }
    
    def get_supported_modes(self) -> List[str]:
        """
        获取支持的查询模式
        
        Returns:
            支持的查询模式列表
        """
        return ["naive", "local", "global", "hybrid", "mix"]
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取 LightRAG 状态信息
        
        Returns:
            状态信息字典
        """
        return {
            "initialized": self._initialized,
            "working_dir": self._working_dir,
            "supported_modes": self.get_supported_modes(),
            "framework": "HKUDS/LightRAG"
        }

# 全局 LightRAG 客户端实例
lightrag_client = LightRAGClient()

# 全局LightRAG实例和初始化状态
_lightrag_instance = None
_initialization_lock = asyncio.Lock()
_is_initialized = False

async def initialize_lightrag_once():
    """
    全局单次LightRAG初始化函数
    """
    global _lightrag_instance, _is_initialized
    
    if _is_initialized and _lightrag_instance is not None:
        return _lightrag_instance
    
    async with _initialization_lock:
        # 双重检查锁定
        if _is_initialized and _lightrag_instance is not None:
            return _lightrag_instance
            
        try:
            logger.info("开始LightRAG全局初始化...")
            
            # 设置环境变量
            os.environ["POSTGRES_HOST"] = config.POSTGRES_HOST
            os.environ["POSTGRES_PORT"] = str(config.POSTGRES_PORT)
            os.environ["POSTGRES_DATABASE"] = config.POSTGRES_DB
            os.environ["POSTGRES_USER"] = config.POSTGRES_USER
            os.environ["POSTGRES_PASSWORD"] = config.POSTGRES_PASSWORD
            os.environ["NEO4J_URI"] = config.NEO4J_URI
            os.environ["NEO4J_USERNAME"] = config.NEO4J_USERNAME
            os.environ["NEO4J_PASSWORD"] = config.NEO4J_PASSWORD
            
            # 创建LightRAG实例
            rag = LightRAG(
                working_dir=lightrag_client._working_dir,
                llm_model_func=custom_llm_func,
                embedding_func=custom_embedding_func,
                # 统一存储方案：PostgreSQL + Neo4j
                kv_storage="PGKVStorage",
                vector_storage="PGVectorStorage", 
                graph_storage="Neo4JStorage",
                doc_status_storage="PGDocStatusStorage"
            )
            
            # 执行必要的异步初始化
            await rag.initialize_storages()
            await initialize_pipeline_status()
            
            _lightrag_instance = rag
            _is_initialized = True
            
            logger.info("✅ LightRAG全局初始化成功")
            return rag
            
        except Exception as e:
            logger.error(f"❌ LightRAG初始化失败: {e}")
            raise

async def query_lightrag(query: str, mode: str = "hybrid") -> Dict[str, Any]:
    """
    异步查询LightRAG - 使用标准LightRAG配置
    """
    try:
        # 获取全局初始化的实例
        rag = await initialize_lightrag_once()
        
        logger.info(f"执行查询: {query[:100]}... (模式: {mode})")
        
        # 获取存储后端信息
        storage_info = {
            "kv_storage": "PGKVStorage (PostgreSQL)",
            "vector_storage": "PGVectorStorage (PostgreSQL)", 
            "graph_storage": "Neo4JStorage (Neo4j)",
            "doc_status_storage": "PGDocStatusStorage (PostgreSQL)"
        }
        
        # 使用标准LightRAG查询参数
        result = await rag.aquery(query, param=QueryParam(mode=mode))
        
        logger.info("✅ LightRAG查询成功")
        logger.info(f"📊 存储后端: {storage_info}")
        
        # 获取模式特性描述
        mode_desc = get_mode_description(mode)
        
        return {
            "success": True,
            "content": result,
            "mode": mode,
            "query": query,
            "storage_backend": storage_info,
            "data_source": "database",
            "retrieval_path": f"{mode} mode -> {storage_info['vector_storage']} + {storage_info['graph_storage']}",
            "mode_description": mode_desc
        }
        
    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": mode,
            "query": query,
            "storage_backend": "unknown",
            "data_source": "error"
        }

def query_lightrag_sync(query: str, mode: str = "hybrid") -> Dict[str, Any]:
    """
    同步查询LightRAG - 内部使用异步实现
    """
    try:
        return asyncio.run(query_lightrag(query, mode))
    except Exception as e:
        logger.error(f"❌ 同步查询失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "mode": mode,
            "query": query
        }

# 全局实例管理
_global_lightrag_instance: Optional[LightRAGClient] = None

def get_lightrag_instance() -> Optional[LightRAGClient]:
    """获取全局LightRAG实例"""
    global _global_lightrag_instance
    return _global_lightrag_instance

def initialize_lightrag():
    """
    同步初始化全局LightRAG实例的包装函数
    注意: 推荐在异步环境中直接使用 initialize_lightrag_once()
    """
    global _global_lightrag_instance
    try:
        if _global_lightrag_instance is None:
            _global_lightrag_instance = LightRAGClient()
            logger.info("开始LightRAG全局初始化...")
            # 使用简单的 asyncio.run 来运行异步函数
            success = asyncio.run(_global_lightrag_instance.initialize())
            if success:
                logger.info("✅ LightRAG全局初始化成功")
            else:
                logger.error("❌ LightRAG全局初始化失败")
                _global_lightrag_instance = None
        return _global_lightrag_instance
    except Exception as e:
        logger.error(f"❌ LightRAG全局初始化异常: {e}")
        return None

async def insert_documents_to_lightrag(documents: List[str]) -> bool:
    """向 LightRAG 插入文档"""
    return await lightrag_client.insert_documents(documents)