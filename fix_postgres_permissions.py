#!/usr/bin/env python3
"""
PostgreSQL 权限修复脚本
为 searchforrag 用户授予必要的权限
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path("intelligent-qa-system/.env")
load_dotenv(dotenv_path=env_path)

async def fix_postgres_permissions():
    """修复 PostgreSQL 权限"""
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
    
    print("PostgreSQL 权限修复")
    print(f"目标用户: {user}")
    print(f"数据库: {database}")
    print()
    
    if not password:
        print("❌ POSTGRES_PASSWORD 环境变量未设置")
        return False
    
    try:
        print("正在连接数据库...")
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        print("✅ 数据库连接成功")
        
        # 检查当前用户
        current_user = await conn.fetchval("SELECT current_user")
        print(f"当前用户: {current_user}")
        
        # 检查权限
        print("\n检查权限...")
        
        create_perm = await conn.fetchval(
            "SELECT has_schema_privilege($1, 'public', 'CREATE')", user
        )
        usage_perm = await conn.fetchval(
            "SELECT has_schema_privilege($1, 'public', 'USAGE')", user
        )
        
        print(f"CREATE 权限: {create_perm}")
        print(f"USAGE 权限: {usage_perm}")
        
        if not create_perm or not usage_perm:
            print("\n❌ 权限不足，尝试授予权限...")
            
            try:
                # 授予权限
                await conn.execute("GRANT CREATE, USAGE ON SCHEMA public TO $1", user)
                print("✅ 已授予 CREATE 和 USAGE 权限")
                
                # 确保用户可以创建表
                await conn.execute("GRANT CREATE ON SCHEMA public TO $1", user)
                print("✅ 已确认 CREATE 权限")
                
            except Exception as e:
                print(f"⚠️  授予权限失败: {e}")
                print("请使用管理员账户运行以下 SQL 命令:")
                print(f"GRANT CREATE, USAGE ON SCHEMA public TO {user};")
                return False
        else:
            print("✅ 权限检查通过")
        
        # 再次检查权限
        print("\n重新验证权限...")
        create_perm = await conn.fetchval(
            "SELECT has_schema_privilege($1, 'public', 'CREATE')", user
        )
        usage_perm = await conn.fetchval(
            "SELECT has_schema_privilege($1, 'public', 'USAGE')", user
        )
        
        print(f"CREATE 权限: {create_perm}")
        print(f"USAGE 权限: {usage_perm}")
        
        if create_perm and usage_perm:
            print("✅ 权限修复成功")
            success = True
        else:
            print("❌ 权限仍然不足")
            success = False
        
        await conn.close()
        return success
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return False

async def main():
    """主函数"""
    print("=" * 50)
    print("PostgreSQL 权限修复脚本")
    print("=" * 50)
    
    success = await fix_postgres_permissions()
    
    print("=" * 50)
    if success:
        print("✅ 权限修复完成")
        print("现在可以重新运行文档导入脚本")
        sys.exit(0)
    else:
        print("❌ 权限修复失败")
        print("请联系数据库管理员手动授予权限")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 