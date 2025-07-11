"""
数据库连接测试脚本
测试 PostgreSQL 和 Neo4j 连接状态
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import config
from utils.helpers import setup_logger

import psycopg2
from neo4j import GraphDatabase

logger = setup_logger(__name__)

def test_postgresql_connection() -> bool:
    """
    测试PostgreSQL连接
    
    Returns:
        连接是否成功
    """
    try:
        logger.info("测试PostgreSQL连接...")
        
        conn = psycopg2.connect(config.postgres_url)
        cursor = conn.cursor()
        
        # 测试基本连接
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(f"PostgreSQL版本: {version[0]}")
        
        # 检查pgvector扩展
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        vector_ext = cursor.fetchone()
        
        if vector_ext:
            logger.info("✅ pgvector扩展已安装")
        else:
            logger.warning("⚠️ pgvector扩展未安装")
            
        # 测试创建表权限
        cursor.execute("SELECT current_user, current_database();")
        user_db = cursor.fetchone()
        logger.info(f"当前用户: {user_db[0]}, 数据库: {user_db[1]}")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ PostgreSQL连接测试成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL连接失败: {e}")
        return False

def test_neo4j_connection() -> bool:
    """
    测试Neo4j连接
    
    Returns:
        连接是否成功
    """
    try:
        logger.info("测试Neo4j连接...")
        
        driver = GraphDatabase.driver(**config.neo4j_config)
        
        with driver.session() as session:
            # 测试基本连接
            result = session.run("RETURN 'Hello Neo4j' AS message")
            message = result.single()
            logger.info(f"Neo4j响应: {message['message']}")
            
            # 获取Neo4j版本信息
            result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
            components = list(result)
            
            for component in components:
                logger.info(f"Neo4j组件: {component['name']} v{component['version']}")
                
            # 测试节点创建权限
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            count = result.single()
            logger.info(f"当前节点数量: {count['node_count']}")
            
        driver.close()
        
        logger.info("✅ Neo4j连接测试成功")
        logger.info(f"Neo4j Web界面: http://localhost:7474")
        return True
        
    except Exception as e:
        logger.error(f"❌ Neo4j连接失败: {e}")
        logger.error("请确保Neo4j已启动并且密码正确")
        return False

def test_api_keys() -> bool:
    """
    测试API密钥配置
    
    Returns:
        API密钥是否配置完整
    """
    logger.info("检查API密钥配置...")
    
    success = True
    
    if not config.OPENAI_API_KEY:
        logger.error("❌ OPENAI_API_KEY 未配置")
        success = False
    else:
        logger.info("✅ OPENAI_API_KEY 已配置")
        
    if not config.TAVILY_API_KEY:
        logger.error("❌ TAVILY_API_KEY 未配置")
        success = False
    else:
        logger.info("✅ TAVILY_API_KEY 已配置")
        
    return success

def check_directories() -> bool:
    """
    检查必要目录是否存在
    
    Returns:
        目录检查是否通过
    """
    logger.info("检查项目目录...")
    
    directories = [
        config.RAG_STORAGE_DIR,
        config.DOCS_DIR,
        config.RAG_STORAGE_DIR / "kv_storage",
        config.RAG_STORAGE_DIR / "vector_storage", 
        config.RAG_STORAGE_DIR / "graph_storage"
    ]
    
    for directory in directories:
        if not directory.exists():
            logger.warning(f"⚠️ 目录不存在，正在创建: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
        else:
            logger.info(f"✅ 目录存在: {directory}")
            
    return True

def main():
    """主函数"""
    logger.info("🔍 开始系统健康检查...")
    logger.info("=" * 50)
    
    # 配置验证
    config_valid, config_errors = config.validate_config()
    if not config_valid:
        logger.error("配置验证失败:")
        for error in config_errors:
            logger.error(f"  - {error}")
        logger.error("请检查 .env 文件配置")
        return False
    
    # 目录检查
    check_directories()
    
    # 数据库连接测试
    pg_success = test_postgresql_connection()
    neo4j_success = test_neo4j_connection()
    api_success = test_api_keys()
    
    logger.info("=" * 50)
    
    if pg_success and neo4j_success and api_success:
        logger.info("🎉 所有连接测试通过！系统准备就绪。")
        return True
    else:
        logger.error("⚠️ 部分测试失败，请检查配置和服务状态")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)