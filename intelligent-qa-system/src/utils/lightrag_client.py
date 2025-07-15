"""
LightRAG 核心集成模块 (HKUDS/LightRAG)
配置并初始化 LightRAG 实例，支持文档检索和问答
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, gpt_4o_complete, openai_embed
from lightrag.utils import setup_logger
from lightrag.kg.shared_storage import initialize_pipeline_status

from ..core.config import config
from .simple_logger import get_simple_logger

# 使用简单日志模块，避免循环导入
logger = get_simple_logger(__name__)

async def custom_llm_func(prompt: str, **kwargs) -> str:
    """
    自定义LLM函数，支持不同的base_url和API key
    """
    try:
        import openai
        
        # LightRAG会注入一个hashing_kv参数用于其内部缓存，
        # 我们需要在这里接收它，但不能将它传递给OpenAI的API
        kwargs.pop("hashing_kv", None)
        kwargs.pop("history_messages", None)
        
        # 创建OpenAI客户端，使用LLM专用配置
        client = openai.AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL
        )
        
        # 调用LLM API
        response = await client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            **kwargs
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"LLM API 调用失败: {e}")
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

class LightRAGClient:
    """
    LightRAG 客户端封装类 (HKUDS/LightRAG)
    提供统一的 LightRAG 接口和配置管理
    """
    
    def __init__(self):
        self.rag_instance: Optional[LightRAG] = None
        self._initialized = False
        self._working_dir = str(config.RAG_STORAGE_DIR)
        
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
            
            # 设置Neo4j环境变量（LightRAG会从环境变量读取）
            os.environ["NEO4J_URI"] = config.NEO4J_URI
            os.environ["NEO4J_USERNAME"] = config.NEO4J_USERNAME
            os.environ["NEO4J_PASSWORD"] = config.NEO4J_PASSWORD
            
            # 创建 LightRAG 实例
            self.rag_instance = LightRAG(
                working_dir=self._working_dir,
                llm_model_func=custom_llm_func,
                embedding_func=custom_embedding_func,
                # -- 混合存储方案：Neo4j图存储 + PostgreSQL其他存储 --
                kv_storage="PGKVStorage",
                vector_storage="PGVectorStorage", 
                graph_storage="Neo4JStorage",  # 使用Neo4j作为图存储（注意大小写）
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
        logger.info(f"  - LLM模型: {config.LLM_MODEL}")
        logger.info(f"  - LLM Base URL: {config.LLM_BASE_URL}")
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
            
            # 添加调试信息
            logger.info("调试: 检查 rag_instance 状态...")
            logger.info(f"调试: rag_instance 类型: {type(self.rag_instance)}")
            
            # 直接调用 ainsert 方法，这是推荐的方式
            logger.info("调试: 开始调用 ainsert...")
            await self.rag_instance.ainsert(documents)
            logger.info("调试: ainsert 调用完成")
                
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
            
        try:
            logger.info(f"执行查询: {query[:50]}... (模式: {mode})")
            
            # 执行查询 - HKUDS/LightRAG 使用 query 方法
            result = await asyncio.to_thread(
                self.rag_instance.query,
                query,
                param=QueryParam(mode=mode, **kwargs)
            )
            
            return {
                "success": True,
                "content": result,
                "mode": mode,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": mode,
                "query": query
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

# 便捷函数
async def initialize_lightrag() -> bool:
    """初始化 LightRAG 客户端"""
    return await lightrag_client.initialize()

async def query_lightrag(query: str, mode: str = "hybrid") -> Dict[str, Any]:
    """查询 LightRAG"""
    return await lightrag_client.query(query, mode)

def query_lightrag_sync(query: str, mode: str = "hybrid") -> Dict[str, Any]:
    """同步查询 LightRAG"""
    return asyncio.run(lightrag_client.query(query, mode))

async def insert_documents_to_lightrag(documents: List[str]) -> bool:
    """向 LightRAG 插入文档"""
    return await lightrag_client.insert_documents(documents)