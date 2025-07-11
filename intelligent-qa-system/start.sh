#!/bin/bash

# 智能问答系统启动脚本
# 自动检查环境并启动 Streamlit 应用

echo "🤖 智能问答系统启动脚本"
echo "========================="

# 检查 Python 版本
echo "🔍 检查 Python 环境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 未找到，请安装 Python 3.8+"
    exit 1
fi

# 检查是否存在虚拟环境
if [ -d "venv" ]; then
    echo "🔧 激活虚拟环境..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "🔧 激活虚拟环境..."
    source .venv/bin/activate
else
    echo "⚠️ 未找到虚拟环境，建议创建虚拟环境"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
fi

# 检查依赖包
echo "📦 检查依赖包..."
if [ -f "requirements.txt" ]; then
    echo "   发现 requirements.txt，检查关键依赖..."
    
    # 检查关键包 (注意: lightrag 安装来自 GitHub，包名在Python中仍是lightrag)
    key_packages=("streamlit" "langchain" "langgraph" "lightrag")
    missing_packages=()
    
    for package in "${key_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo "❌ 缺少以下关键依赖包: ${missing_packages[*]}"
        echo "   请运行: pip install -r requirements.txt"
        echo "   注意: lightrag 需要从 GitHub 安装: pip install git+https://github.com/HKUDS/LightRAG.git"
        exit 1
    fi
    
    echo "✅ 关键依赖包检查通过"
else
    echo "⚠️ 未找到 requirements.txt 文件"
fi

# 检查环境变量配置
echo "🔧 检查环境配置..."
if [ -f ".env" ]; then
    echo "✅ 发现 .env 配置文件"
    
    # 检查关键环境变量
    if grep -q "OPENAI_API_KEY" .env; then
        echo "   ✅ OpenAI API 密钥已配置"
    else
        echo "   ⚠️ 缺少 OpenAI API 密钥配置"
    fi
    
    if grep -q "TAVILY_API_KEY" .env; then
        echo "   ✅ Tavily API 密钥已配置"
    else
        echo "   ⚠️ 缺少 Tavily API 密钥配置"
    fi
    
else
    echo "⚠️ 未找到 .env 配置文件"
    echo "   请参考 .env.example 创建 .env 文件"
fi

# 检查数据库配置
echo "🗄️ 检查数据库配置..."
if [ -f ".env" ]; then
    if grep -q "POSTGRES_HOST" .env; then
        echo "   ✅ PostgreSQL 配置已找到"
    else
        echo "   ⚠️ 缺少 PostgreSQL 配置"
    fi
    
    if grep -q "NEO4J_URI" .env; then
        echo "   ✅ Neo4j 配置已找到"
    else
        echo "   ⚠️ 缺少 Neo4j 配置"
    fi
fi

# 检查项目结构
echo "📁 检查项目结构..."
required_dirs=("src" "src/core" "src/agents" "src/utils")
missing_dirs=()

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        missing_dirs+=("$dir")
    fi
done

if [ ${#missing_dirs[@]} -gt 0 ]; then
    echo "❌ 缺少以下目录: ${missing_dirs[*]}"
    echo "   请确保项目结构完整"
    exit 1
fi

echo "✅ 项目结构检查通过"

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 启动 Streamlit
echo ""
echo "🚀 启动 Streamlit 应用..."
echo "========================="
echo ""

# 检查端口
PORT=${1:-8501}
echo "📡 使用端口: $PORT"

# 启动应用
if [ -f "main_app.py" ]; then
    echo "🔄 启动主应用..."
    streamlit run main_app.py --server.port=$PORT --server.headless=true
elif [ -f "streamlit_app.py" ]; then
    echo "🔄 启动基础应用..."
    streamlit run streamlit_app.py --server.port=$PORT --server.headless=true
else
    echo "❌ 未找到应用文件 (main_app.py 或 streamlit_app.py)"
    exit 1
fi