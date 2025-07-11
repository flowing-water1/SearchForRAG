#!/usr/bin/env python3
"""
配置迁移脚本
将旧的 OPENAI_* 配置迁移到新的 LLM_* 和 EMBEDDING_* 配置
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def backup_env_file():
    """备份现有的 .env 文件"""
    env_path = Path(".env")
    if env_path.exists():
        backup_path = Path(f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(env_path, backup_path)
        print(f"✅ 已备份现有配置到: {backup_path}")
        return True
    return False

def read_env_file():
    """读取现有的 .env 文件"""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env 文件不存在")
        return {}
    
    env_vars = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def migrate_config(env_vars):
    """迁移配置"""
    print("\n🔄 开始配置迁移...")
    
    # 新的配置映射
    new_config = {}
    
    # 迁移 LLM 配置
    if 'OPENAI_API_KEY' in env_vars:
        new_config['LLM_API_KEY'] = env_vars['OPENAI_API_KEY']
        print(f"✅ 迁移 LLM_API_KEY: {env_vars['OPENAI_API_KEY'][:20]}...")
    
    if 'OPENAI_BASE_URL' in env_vars:
        new_config['LLM_BASE_URL'] = env_vars['OPENAI_BASE_URL']
        print(f"✅ 迁移 LLM_BASE_URL: {env_vars['OPENAI_BASE_URL']}")
    
    if 'OPENAI_MODEL' in env_vars:
        new_config['LLM_MODEL'] = env_vars['OPENAI_MODEL']
        print(f"✅ 迁移 LLM_MODEL: {env_vars['OPENAI_MODEL']}")
    
    # 设置 Embedding 配置（用户需要手动配置）
    print("\n⚠️  Embedding 配置需要手动设置:")
    print("   请根据您的需求配置以下项目:")
    print("   - EMBEDDING_API_KEY")
    print("   - EMBEDDING_BASE_URL")
    print("   - EMBEDDING_MODEL")
    print("   - EMBEDDING_DIM")
    
    # 如果没有现有的 embedding 配置，设置默认值
    if 'EMBEDDING_API_KEY' not in env_vars:
        new_config['EMBEDDING_API_KEY'] = 'your_embedding_api_key_here'
    if 'EMBEDDING_BASE_URL' not in env_vars:
        new_config['EMBEDDING_BASE_URL'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    if 'EMBEDDING_MODEL' not in env_vars:
        new_config['EMBEDDING_MODEL'] = 'text-embedding-v1'
    if 'EMBEDDING_DIM' not in env_vars:
        new_config['EMBEDDING_DIM'] = '1536'
    
    # 保留其他配置
    preserve_keys = [
        'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD',
        'NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD',
        'TAVILY_API_KEY',
        'RAG_WORKING_DIR', 'RAG_CHUNK_SIZE', 'RAG_CHUNK_OVERLAP',
        'CONFIDENCE_THRESHOLD', 'MAX_RESULTS', 'REQUEST_TIMEOUT',
        'LOG_LEVEL', 'LOG_FORMAT',
        'MAX_CONCURRENT_REQUESTS', 'CACHE_TTL', 'RETRY_MAX_ATTEMPTS', 'RETRY_BACKOFF_FACTOR'
    ]
    
    for key in preserve_keys:
        if key in env_vars:
            new_config[key] = env_vars[key]
    
    return new_config

def write_new_env_file(config):
    """写入新的 .env 文件"""
    env_content = []
    
    # 数据库配置
    env_content.append("# 数据库配置")
    db_keys = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    for key in db_keys:
        if key in config:
            env_content.append(f"{key}={config[key]}")
    env_content.append("")
    
    # Neo4j 配置
    env_content.append("# Neo4j 配置")
    neo4j_keys = ['NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD']
    for key in neo4j_keys:
        if key in config:
            env_content.append(f"{key}={config[key]}")
    env_content.append("")
    
    # LLM API 配置
    env_content.append("# LLM API 配置（用于对话和推理）")
    llm_keys = ['LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL']
    for key in llm_keys:
        if key in config:
            env_content.append(f"{key}={config[key]}")
    env_content.append("")
    
    # Embedding API 配置
    env_content.append("# Embedding API 配置（用于向量化）")
    embedding_keys = ['EMBEDDING_API_KEY', 'EMBEDDING_BASE_URL', 'EMBEDDING_MODEL', 'EMBEDDING_DIM']
    for key in embedding_keys:
        if key in config:
            env_content.append(f"{key}={config[key]}")
    env_content.append("")
    
    # Tavily 配置
    env_content.append("# Tavily 搜索 API 配置")
    if 'TAVILY_API_KEY' in config:
        env_content.append(f"TAVILY_API_KEY={config['TAVILY_API_KEY']}")
    env_content.append("")
    
    # LightRAG 配置
    env_content.append("# LightRAG 配置")
    rag_keys = ['RAG_WORKING_DIR', 'RAG_CHUNK_SIZE', 'RAG_CHUNK_OVERLAP']
    for key in rag_keys:
        if key in config:
            env_content.append(f"{key}={config[key]}")
    env_content.append("")
    
    # 系统配置
    env_content.append("# 系统配置")
    system_keys = ['CONFIDENCE_THRESHOLD', 'MAX_RESULTS', 'REQUEST_TIMEOUT', 'LOG_LEVEL', 'LOG_FORMAT']
    for key in system_keys:
        if key in config:
            env_content.append(f"{key}={config[key]}")
    env_content.append("")
    
    # 性能配置
    env_content.append("# 性能配置")
    perf_keys = ['MAX_CONCURRENT_REQUESTS', 'CACHE_TTL', 'RETRY_MAX_ATTEMPTS', 'RETRY_BACKOFF_FACTOR']
    for key in perf_keys:
        if key in config:
            env_content.append(f"{key}={config[key]}")
    
    # 写入文件
    with open('.env', 'w', encoding='utf-8') as f:
        f.write('\n'.join(env_content))
    
    print(f"✅ 新的 .env 文件已生成")

def main():
    """主函数"""
    print("🔄 智能问答系统配置迁移工具")
    print("=" * 50)
    
    # 检查是否存在 .env 文件
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env 文件不存在")
        print("请先复制 .env.example 到 .env")
        return
    
    # 备份现有配置
    backup_env_file()
    
    # 读取现有配置
    env_vars = read_env_file()
    if not env_vars:
        print("❌ 无法读取现有配置")
        return
    
    print(f"✅ 读取到 {len(env_vars)} 个配置项")
    
    # 迁移配置
    new_config = migrate_config(env_vars)
    
    # 写入新配置
    write_new_env_file(new_config)
    
    print("\n" + "=" * 50)
    print("✅ 配置迁移完成!")
    print("\n📝 后续步骤:")
    print("1. 编辑 .env 文件，配置正确的 EMBEDDING_API_KEY 和相关参数")
    print("2. 运行 'python test_api_config.py' 测试配置")
    print("3. 启动应用: 'streamlit run main_app.py'")
    print("\n📖 详细配置指南请查看: API_CONFIG_GUIDE.md")

if __name__ == "__main__":
    main()