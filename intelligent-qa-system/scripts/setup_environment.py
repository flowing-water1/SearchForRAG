"""
环境初始化脚本
设置数据库、创建必要的表和索引
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import config
from utils.helpers import setup_logger, ensure_directory
from utils.lightrag_client import initialize_lightrag
from utils.document_processor import ingest_documents

logger = setup_logger(__name__)

async def setup_directories():
    """创建必要的目录"""
    logger.info("创建项目目录...")
    
    directories = [
        config.RAG_STORAGE_DIR,
        config.RAG_STORAGE_DIR / "kv_storage",
        config.RAG_STORAGE_DIR / "vector_storage",
        config.RAG_STORAGE_DIR / "graph_storage",
        config.DOCS_DIR
    ]
    
    for directory in directories:
        ensure_directory(directory)
        logger.info(f"✅ 目录已创建: {directory}")

async def setup_postgresql():
    """设置PostgreSQL数据库"""
    logger.info("设置PostgreSQL数据库...")
    
    try:
        import psycopg2
        
        # 连接数据库
        conn = psycopg2.connect(config.postgres_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 尝试创建pgvector扩展
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("✅ pgvector扩展已创建")
        except Exception as e:
            logger.warning(f"⚠️ pgvector扩展创建失败: {e}")
            logger.warning("将使用默认向量存储")
        
        # 创建LightRAG所需的表结构（如果需要）
        # 注意：LightRAG会自动创建所需的表，这里只是预留
        
        cursor.close()
        conn.close()
        
        logger.info("✅ PostgreSQL设置完成")
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL设置失败: {e}")
        raise

async def setup_neo4j():
    """设置Neo4j数据库"""
    logger.info("设置Neo4j数据库...")
    
    try:
        from neo4j import GraphDatabase
        
        # 连接Neo4j
        driver = GraphDatabase.driver(**config.neo4j_config)
        
        with driver.session() as session:
            # 创建索引和约束
            try:
                # 实体节点约束
                session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
                # 关系约束
                session.run("CREATE CONSTRAINT relationship_id IF NOT EXISTS FOR (r:Relationship) REQUIRE r.id IS UNIQUE")
                # 创建索引
                session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
                session.run("CREATE INDEX relationship_type IF NOT EXISTS FOR (r:Relationship) ON (r.type)")
                
                logger.info("✅ Neo4j约束和索引已创建")
                
            except Exception as e:
                logger.warning(f"⚠️ Neo4j约束创建失败: {e}")
        
        driver.close()
        logger.info("✅ Neo4j设置完成")
        
    except Exception as e:
        logger.error(f"❌ Neo4j设置失败: {e}")
        logger.warning("将使用默认图存储")

async def initialize_lightrag_system():
    """初始化LightRAG系统"""
    logger.info("初始化LightRAG系统...")
    
    success = await initialize_lightrag()
    
    if success:
        logger.info("✅ LightRAG系统初始化完成")
    else:
        logger.error("❌ LightRAG系统初始化失败")
        raise Exception("LightRAG初始化失败")

async def load_sample_documents():
    """加载示例文档"""
    logger.info("检查示例文档...")
    
    docs_dir = config.DOCS_DIR
    
    # 检查文档目录是否有文件
    if not any(docs_dir.iterdir()):
        logger.info("创建示例文档...")
        
        # 创建示例文档
        sample_content = """
# 人工智能基础知识

## 什么是人工智能？

人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，它试图理解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。

## 机器学习

机器学习是人工智能的一个重要分支，它使计算机能够在没有明确编程的情况下学习。

### 主要类型

1. **监督学习**：使用标记数据进行训练
2. **无监督学习**：从无标记数据中发现模式
3. **强化学习**：通过试错学习最优行为

## 深度学习

深度学习是机器学习的一个子集，它使用多层神经网络来模拟人脑的工作方式。

### 应用领域

- 图像识别
- 自然语言处理
- 语音识别
- 自动驾驶
"""
        
        sample_file = docs_dir / "ai_basics.md"
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
            
        logger.info(f"✅ 示例文档已创建: {sample_file}")
    
    # 导入文档到LightRAG
    logger.info("导入文档到LightRAG...")
    success = await ingest_documents(docs_dir)
    
    if success:
        logger.info("✅ 文档导入完成")
    else:
        logger.warning("⚠️ 文档导入失败")

async def main():
    """主函数"""
    logger.info("🚀 开始环境初始化...")
    logger.info("=" * 50)
    
    try:
        # 验证配置
        config_valid, config_errors = config.validate_config()
        if not config_valid:
            logger.error("配置验证失败:")
            for error in config_errors:
                logger.error(f"  - {error}")
            logger.error("请检查 .env 文件配置")
            return False
        
        # 创建目录
        await setup_directories()
        
        # 设置数据库
        await setup_postgresql()
        await setup_neo4j()
        
        # 初始化LightRAG
        await initialize_lightrag_system()
        
        # 加载示例文档
        await load_sample_documents()
        
        logger.info("=" * 50)
        logger.info("🎉 环境初始化完成！")
        logger.info("你可以运行以下命令启动应用:")
        logger.info("  streamlit run src/streamlit_app.py")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 环境初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)