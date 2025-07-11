#!/bin/bash

# 智能问答系统一键部署脚本
# 自动创建虚拟环境、安装依赖、配置环境

echo "🚀 智能问答系统一键部署"
echo "======================="

# 检查 Python 版本
echo "🔍 检查 Python 环境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 未找到，请安装 Python 3.8+"
    exit 1
fi

# 创建虚拟环境
echo "🔧 创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "📦 升级 pip..."
pip install --upgrade pip

# 安装依赖包
echo "📦 安装依赖包..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ 依赖包安装完成"
else
    echo "⚠️ 未找到 requirements.txt，手动安装关键依赖..."
    pip install streamlit langchain langchain-openai langgraph python-dotenv
    # 安装正确的 HKUDS/LightRAG (从 GitHub)
    pip install git+https://github.com/HKUDS/LightRAG.git
    pip install psycopg2-binary neo4j tavily-python
    pip install pydantic typing-extensions
fi

# 创建环境配置文件
echo "🔧 创建环境配置..."
if [ ! -f ".env" ]; then
    cat > .env << EOL
# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Tavily API 配置
TAVILY_API_KEY=your_tavily_api_key_here

# PostgreSQL 配置
POSTGRES_HOST=117.72.54.192
POSTGRES_PORT=5432
POSTGRES_DB=searchforrag
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password

# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# 系统配置
DEBUG_MODE=false
CONFIDENCE_THRESHOLD=0.6
MAX_WEB_RESULTS=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# 存储配置
RAG_STORAGE_DIR=./rag_storage
LOG_LEVEL=INFO
EOL
    echo "✅ 环境配置文件已创建: .env"
    echo "⚠️ 请编辑 .env 文件，填入您的 API 密钥和数据库配置"
else
    echo "✅ 环境配置文件已存在"
fi

# 创建存储目录
echo "📁 创建存储目录..."
mkdir -p rag_storage
mkdir -p logs
echo "✅ 存储目录创建完成"

# 检查项目结构
echo "📁 检查项目结构..."
required_files=("src/core/config.py" "src/core/workflow.py" "main_app.py")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo "❌ 缺少以下文件: ${missing_files[*]}"
    echo "   请确保项目文件完整"
    exit 1
fi

echo "✅ 项目结构检查通过"

# 测试导入
echo "🔍 测试模块导入..."
python3 -c "
try:
    import streamlit
    import langchain
    import langgraph
    print('✅ 核心模块导入成功')
except ImportError as e:
    print(f'❌ 模块导入失败: {e}')
    exit(1)
"

# 创建快速测试脚本
echo "🧪 创建测试脚本..."
cat > test_system.py << 'EOF'
#!/usr/bin/env python3
"""
系统快速测试脚本
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        import streamlit
        print("✅ Streamlit 导入成功")
        
        import langchain
        print("✅ LangChain 导入成功")
        
        import langgraph
        print("✅ LangGraph 导入成功")
        
        # 测试项目模块
        from src.core.config import config
        print("✅ 项目配置模块导入成功")
        
        from src.core.workflow import get_workflow
        print("✅ 工作流模块导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def test_config():
    """测试配置"""
    print("🔧 测试配置...")
    
    try:
        from src.core.config import config
        
        print(f"调试模式: {config.DEBUG_MODE}")
        print(f"工作目录: {config.RAG_STORAGE_DIR}")
        print(f"LLM 模型: {config.OPENAI_MODEL}")
        
        # 检查API密钥
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your_openai_api_key_here":
            print("✅ OpenAI API 密钥已配置")
        else:
            print("⚠️ OpenAI API 密钥未配置")
        
        if config.TAVILY_API_KEY and config.TAVILY_API_KEY != "your_tavily_api_key_here":
            print("✅ Tavily API 密钥已配置")
        else:
            print("⚠️ Tavily API 密钥未配置")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 智能问答系统测试")
    print("==================")
    
    tests = [
        test_imports,
        test_config
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"测试结果: {passed}/{len(tests)} 通过")
    
    if passed == len(tests):
        print("🎉 系统测试通过！可以启动应用")
        print("运行: ./start.sh 启动系统")
    else:
        print("⚠️ 部分测试失败，请检查配置")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

chmod +x test_system.py

echo ""
echo "🎉 部署完成！"
echo "============="
echo ""
echo "下一步操作："
echo "1. 编辑 .env 文件，配置 API 密钥和数据库连接"
echo "2. 运行测试: python3 test_system.py"
echo "3. 启动系统: ./start.sh"
echo ""
echo "系统端口: http://localhost:8501"
echo ""
echo "如有问题，请检查："
echo "- API 密钥是否正确配置"
echo "- 数据库连接是否正常"
echo "- 所有依赖包是否安装完成"
echo ""
echo "祝您使用愉快！🚀"