#!/usr/bin/env python3
"""
API 配置测试脚本
测试 LLM 和 Embedding API 的连接是否正常
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv()

def test_llm_api():
    """测试 LLM API 连接"""
    print("🔍 测试 LLM API 连接...")
    
    try:
        import openai
        
        # 获取配置
        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL")
        model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
        if not api_key:
            print("❌ LLM_API_KEY 未配置")
            return False
            
        if not base_url:
            print("❌ LLM_BASE_URL 未配置")
            return False
        
        # 创建客户端
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 测试调用
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        print(f"✅ LLM API 连接成功")
        print(f"   模型: {model}")
        print(f"   Base URL: {base_url}")
        print(f"   响应: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM API 连接失败: {e}")
        return False

def test_embedding_api():
    """测试 Embedding API 连接"""
    print("\n🔍 测试 Embedding API 连接...")
    
    try:
        import openai
        
        # 获取配置
        api_key = os.getenv("EMBEDDING_API_KEY")
        base_url = os.getenv("EMBEDDING_BASE_URL")
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-v1")
        embedding_dim = int(os.getenv("EMBEDDING_DIM", "1536"))
        
        if not api_key:
            print("❌ EMBEDDING_API_KEY 未配置")
            return False
            
        if not base_url:
            print("❌ EMBEDDING_BASE_URL 未配置")
            return False
        
        # 创建客户端
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 测试调用
        response = client.embeddings.create(
            input=["测试文本"],
            model=model,
            dimensions=embedding_dim  # 添加维度参数
        )
        
        embedding = response.data[0].embedding
        actual_dim = len(embedding)
        
        print(f"✅ Embedding API 连接成功")
        print(f"   模型: {model}")
        print(f"   Base URL: {base_url}")
        print(f"   配置维度: {embedding_dim}")
        print(f"   实际维度: {actual_dim}")
        
        if actual_dim != embedding_dim:
            print(f"⚠️  警告: 实际维度 ({actual_dim}) 与配置维度 ({embedding_dim}) 不匹配")
            print(f"   请检查 EMBEDDING_DIM 配置")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding API 连接失败: {e}")
        return False

def test_database_connections():
    """测试数据库连接"""
    print("\n🔍 测试数据库连接...")
    
    # 测试 PostgreSQL
    try:
        import psycopg2
        
        postgres_host = os.getenv("POSTGRES_HOST", "117.72.54.192")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "searchforrag")
        postgres_user = os.getenv("POSTGRES_USER", "searchforrag")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "searchforrag")
        
        conn = psycopg2.connect(
            host=postgres_host,
            port=postgres_port,
            database=postgres_db,
            user=postgres_user,
            password=postgres_password
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        # 检查 pgvector 扩展
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        vector_ext = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        print(f"✅ PostgreSQL 连接成功")
        print(f"   主机: {postgres_host}:{postgres_port}")
        print(f"   数据库: {postgres_db}")
        print(f"   pgvector 扩展: {'已安装' if vector_ext else '未安装'}")
        
        if not vector_ext:
            print("⚠️  警告: pgvector 扩展未安装，将使用 NanoVectorDB 作为备选")
        
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败: {e}")
    
    # 测试 Neo4j
    try:
        from neo4j import GraphDatabase
        
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_username, neo4j_password)
        )
        
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
        
        driver.close()
        
        print(f"✅ Neo4j 连接成功")
        print(f"   URI: {neo4j_uri}")
        print(f"   用户: {neo4j_username}")
        
    except Exception as e:
        print(f"❌ Neo4j 连接失败: {e}")
        print("⚠️  将使用 NetworkX 作为备选图存储")

def test_lightrag_integration():
    """测试 LightRAG 集成"""
    print("\n🔍 测试 LightRAG 集成...")
    
    try:
        from src.utils.lightrag_client import LightRAGClient
        
        async def test_lightrag():
            client = LightRAGClient()
            success = await client.initialize()
            
            if success:
                print("✅ LightRAG 初始化成功")
                
                # 获取状态信息
                status = client.get_status()
                print(f"   工作目录: {status['working_dir']}")
                print(f"   pgvector 可用: {status['pgvector_available']}")
                print(f"   Neo4j 可用: {status['neo4j_available']}")
                print(f"   支持的模式: {status['supported_modes']}")
                
                return True
            else:
                print("❌ LightRAG 初始化失败")
                return False
        
        return asyncio.run(test_lightrag())
        
    except Exception as e:
        print(f"❌ LightRAG 集成测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 智能问答系统 API 配置测试")
    print("=" * 50)
    
    # 检查环境变量文件
    if not os.path.exists(".env"):
        print("❌ .env 文件不存在")
        print("请复制 .env.example 到 .env 并配置相关参数")
        return
    
    results = []
    
    # 测试 LLM API
    results.append(test_llm_api())
    
    # 测试 Embedding API
    results.append(test_embedding_api())
    
    # 测试数据库连接
    test_database_connections()
    
    # 测试 LightRAG 集成
    results.append(test_lightrag_integration())
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结:")
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print("🎉 所有测试通过！系统配置正确。")
    else:
        print(f"⚠️  {success_count}/{total_count} 个测试通过")
        print("请检查失败的配置项并重新测试")
    
    print("\n💡 提示:")
    print("- 确保 .env 文件中的 API Key 和 Base URL 正确")
    print("- 检查数据库连接参数")
    print("- 确认 embedding 模型的维度配置")

if __name__ == "__main__":
    main()