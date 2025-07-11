#!/usr/bin/env python3
"""
PostgreSQL 连接测试脚本
用于验证数据库连接和 pgvector 扩展
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path("intelligent-qa-system/.env")
load_dotenv(dotenv_path=env_path)

async def test_postgres_connection():
    """测试 PostgreSQL 连接"""
    try:
        import asyncpg
    except ImportError:
        print("❌ asyncpg 库未安装，请先安装：pip install asyncpg")
        return False
    
    # 从环境变量获取连接参数
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DATABASE", "postgres")
    workspace = os.getenv("POSTGRES_WORKSPACE", "default")
    
    print("PostgreSQL 连接参数:")
    print(f"  主机: {host}:{port}")
    print(f"  用户: {user}")
    print(f"  数据库: {database}")
    print(f"  工作空间: {workspace}")
    print()
    
    if not password:
        print("❌ POSTGRES_PASSWORD 环境变量未设置")
        return False
    
    try:
        print("正在尝试连接 PostgreSQL...")
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        print("✅ PostgreSQL 连接成功")
        
        # 检查 pgvector 扩展
        print("检查 pgvector 扩展...")
        try:
            result = await conn.fetchval("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            if result:
                print("✅ pgvector 扩展已安装")
            else:
                print("⚠️  pgvector 扩展未安装")
                print("请运行以下命令安装 pgvector:")
                print("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            print(f"⚠️  检查 pgvector 扩展时出错: {e}")
        
        # 测试基本查询
        print("测试基本查询...")
        version = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL 版本: {version}")
        
        await conn.close()
        print("✅ 数据库连接测试完成")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败: {e}")
        print("\n请检查以下项目:")
        print("1. PostgreSQL 服务是否运行")
        print("2. 主机地址和端口是否正确")
        print("3. 用户名和密码是否正确")
        print("4. 数据库是否存在")
        print("5. 网络连接是否正常")
        return False

async def main():
    """主函数"""
    print("=" * 50)
    print("PostgreSQL 连接测试")
    print("=" * 50)
    
    success = await test_postgres_connection()
    
    print("=" * 50)
    if success:
        print("✅ 所有测试通过")
        sys.exit(0)
    else:
        print("❌ 测试失败")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 