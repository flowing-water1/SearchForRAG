"""
统一配置管理模块
管理所有应用配置，包括数据库连接、API密钥等
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# -- 明确指定 .env 文件的路径 --
# 这可以确保无论从哪里运行脚本，都能正确加载配置
# config.py -> src -> intelligent-qa-system -> .env
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """统一配置管理类"""
    
    # 系统基本配置
    SYSTEM_NAME = "智能问答系统"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"  # 添加DEBUG_MODE
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # LLM API配置（用于对话和推理）
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
    
    # 知识图谱专用LLM配置（用于实体关系提取）
    KG_LLM_API_KEY = os.getenv("KG_LLM_API_KEY") or os.getenv("LLM_API_KEY")
    KG_LLM_BASE_URL = os.getenv("KG_LLM_BASE_URL") or os.getenv("LLM_BASE_URL")
    KG_LLM_MODEL = os.getenv("KG_LLM_MODEL", "gpt-4o")  # 默认使用更强的模型
    KG_LLM_TEMPERATURE = float(os.getenv("KG_LLM_TEMPERATURE", "0.1"))
    KG_LLM_MAX_TOKENS = int(os.getenv("KG_LLM_MAX_TOKENS", "4000"))
    
    # 向量提取专用LLM配置（用于文档分块和语义理解）
    VECTOR_LLM_API_KEY = os.getenv("VECTOR_LLM_API_KEY") or os.getenv("LLM_API_KEY")
    VECTOR_LLM_BASE_URL = os.getenv("VECTOR_LLM_BASE_URL") or os.getenv("LLM_BASE_URL")
    VECTOR_LLM_MODEL = os.getenv("VECTOR_LLM_MODEL", "gpt-4o-mini")  # 使用效率更高的模型
    VECTOR_LLM_TEMPERATURE = float(os.getenv("VECTOR_LLM_TEMPERATURE", "0.0"))
    VECTOR_LLM_MAX_TOKENS = int(os.getenv("VECTOR_LLM_MAX_TOKENS", "2000"))
    
    # Embedding API配置（用于向量化）
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v1")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
    
    # Tavily搜索API配置
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    # 兼容性配置（支持旧的OPENAI_API_KEY配置）
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4")
    
    # LLM配置
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    
    # PostgreSQL数据库配置（从.env读取连接信息）
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "117.72.54.192")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DATABASE", "searchforrag")  # 修复环境变量名
    POSTGRES_USER = os.getenv("POSTGRES_USER", "searchforrag")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "searchforrag")
    POSTGRES_SSL_MODE = os.getenv("POSTGRES_SSL_MODE", "prefer")
    
    # Neo4j配置
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
    
    # LightRAG配置 (HKUDS/LightRAG)
    RAG_STORAGE_DIR = Path(os.getenv("RAG_WORKING_DIR", "./rag_storage"))
    DOCS_DIR = Path(os.getenv("DOCS_DIR", "./docs"))
    
    # LightRAG基础分块配置
    CHUNK_TOKEN_SIZE = int(os.getenv("RAG_CHUNK_TOKEN_SIZE", "1200"))
    CHUNK_OVERLAP_TOKEN_SIZE = int(os.getenv("RAG_CHUNK_OVERLAP_TOKEN_SIZE", "100"))
    
    # LightRAG性能配置
    MAX_PARALLEL_INSERTIONS = int(os.getenv("RAG_MAX_PARALLEL_INSERTIONS", "3"))
    LLM_MODEL_MAX_ASYNC = int(os.getenv("RAG_LLM_MODEL_MAX_ASYNC", "12"))
    
    # 检索配置
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    MAX_LOCAL_RESULTS = 10
    MAX_WEB_RESULTS = 5
    VECTOR_SIMILARITY_THRESHOLD = 0.75
    
    # 网络搜索配置
    WEB_SEARCH_TIMEOUT = 30
    WEB_SEARCH_MAX_RETRIES = 3
    
    # Streamlit配置
    STREAMLIT_HOST = os.getenv("STREAMLIT_HOST", "localhost")
    STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
    STREAMLIT_THEME = "light"
    SHOW_DETAILS = True
    
    @property
    def postgres_url(self) -> str:
        """构建PostgreSQL连接URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode={self.POSTGRES_SSL_MODE}"
    
    @property  
    def neo4j_config(self) -> dict:
        """获取Neo4j连接配置"""
        return {
            "uri": self.NEO4J_URI,
            "auth": (self.NEO4J_USERNAME, self.NEO4J_PASSWORD),
            "database": self.NEO4J_DATABASE
        }
    
    @property
    def kg_llm_config(self) -> dict:
        """获取知识图谱LLM配置"""
        return {
            "api_key": self.KG_LLM_API_KEY,
            "base_url": self.KG_LLM_BASE_URL,
            "model": self.KG_LLM_MODEL,
            "temperature": self.KG_LLM_TEMPERATURE,
            "max_tokens": self.KG_LLM_MAX_TOKENS
        }
    
    @property
    def vector_llm_config(self) -> dict:
        """获取向量提取LLM配置"""
        return {
            "api_key": self.VECTOR_LLM_API_KEY,
            "base_url": self.VECTOR_LLM_BASE_URL,
            "model": self.VECTOR_LLM_MODEL,
            "temperature": self.VECTOR_LLM_TEMPERATURE,
            "max_tokens": self.VECTOR_LLM_MAX_TOKENS
        }
    
    @property
    def lightrag_config(self) -> dict:
        """获取LightRAG基础配置"""
        return {
            "working_dir": str(self.RAG_STORAGE_DIR),
            "chunk_token_size": self.CHUNK_TOKEN_SIZE,
            "chunk_overlap_token_size": self.CHUNK_OVERLAP_TOKEN_SIZE,
            "max_parallel_insertions": self.MAX_PARALLEL_INSERTIONS,
            "llm_model_max_async": self.LLM_MODEL_MAX_ASYNC
        }
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """验证配置是否完整"""
        errors = []
        
        # 检查基础LLM配置
        if not self.LLM_API_KEY:
            errors.append("LLM_API_KEY is required")
        if not self.LLM_BASE_URL:
            errors.append("LLM_BASE_URL is required")
            
        # 检查知识图谱LLM配置
        if not self.KG_LLM_API_KEY:
            errors.append("KG_LLM_API_KEY (or LLM_API_KEY) is required")
        if not self.KG_LLM_BASE_URL:
            errors.append("KG_LLM_BASE_URL (or LLM_BASE_URL) is required")
            
        # 检查向量LLM配置
        if not self.VECTOR_LLM_API_KEY:
            errors.append("VECTOR_LLM_API_KEY (or LLM_API_KEY) is required")
        if not self.VECTOR_LLM_BASE_URL:
            errors.append("VECTOR_LLM_BASE_URL (or LLM_BASE_URL) is required")
            
        # 检查Embedding配置
        if not self.EMBEDDING_API_KEY:
            errors.append("EMBEDDING_API_KEY is required")
        if not self.EMBEDDING_BASE_URL:
            errors.append("EMBEDDING_BASE_URL is required")
            
        # 检查搜索配置
        if not self.TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY is required") 
            
        # 检查数据库配置
        if not self.POSTGRES_PASSWORD:
            errors.append("POSTGRES_PASSWORD is required")
            
        if not self.NEO4J_PASSWORD:
            errors.append("NEO4J_PASSWORD is required")
            
        # 检查LightRAG分块配置合理性
        if self.CHUNK_OVERLAP_TOKEN_SIZE >= self.CHUNK_TOKEN_SIZE:
            errors.append("CHUNK_OVERLAP_TOKEN_SIZE must be less than CHUNK_TOKEN_SIZE")
            
        return len(errors) == 0, errors

# 全局配置实例
config = Config()