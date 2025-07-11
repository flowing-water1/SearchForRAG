# 🤖 智能问答系统

基于 **HKUDS/LightRAG + LangGraph** 的下一代智能问答系统，集成了先进的 Agentic RAG 技术，支持多模式检索和智能决策。

## ✨ 核心特性

### 🧠 智能工作流
- **查询分析**: 自动识别查询类型（事实性、关系性、分析性）
- **多模式检索**: 支持 naive、local、global、hybrid、mix 五种 LightRAG 检索模式
- **质量评估**: 智能评估检索结果质量，决定是否需要网络搜索
- **网络搜索**: 集成 Tavily API 进行实时网络信息补充
- **答案生成**: 整合多源信息，生成高质量答案

### 🔧 技术栈说明
- **LightRAG (HKUDS)**: 正确的 LightRAG 框架，支持 naive、local、global、hybrid、mix 等检索模式
- **模式说明**：
  - **naive**: 基础检索模式
  - **local**: 向量相似度检索，适合事实性查询
  - **global**: 图谱关系检索，适合关系性查询
  - **hybrid**: 混合检索，结合向量和图谱，适合复杂分析
  - **mix**: 综合模式
- **LangGraph**: 智能工作流编排，支持条件路由和状态管理
- **PostgreSQL**: 向量数据库存储（pgvector）
- **Neo4j**: 图数据库存储
- **Streamlit**: 现代化 Web 界面
- **OpenAI API**: 大语言模型服务
- **Tavily API**: 网络搜索服务
- **错误处理**: 全面的错误恢复和重试机制
- **性能监控**: 实时性能指标和审计日志

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- PostgreSQL 12+ (with pgvector extension)
- Neo4j 5.0+
- OpenAI API 密钥
- Tavily API 密钥

### 2. 一键部署

```bash
# 克隆项目
git clone <repository-url>
cd intelligent-qa-system

# 运行一键部署脚本
./setup.sh

# 编辑环境配置
nano .env

# 测试系统
python3 test_system.py

# 启动应用
./start.sh
```

### 3. 手动安装

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖 (使用正确的 HKUDS/LightRAG)
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env

# 启动应用
streamlit run main_app.py
```

## 📋 安装说明

### 重要依赖安装

本项目使用正确的 **HKUDS/LightRAG** 框架。请注意：

1. **正确的 LightRAG 框架**: 本项目使用 `git+https://github.com/HKUDS/LightRAG.git`
2. **PyPI 包限制**: PyPI 上的 `lightrag-hku` 包存在依赖问题，推荐从 GitHub 安装
3. **自动安装**: `requirements.txt` 已配置正确的 GitHub 安装链接

```bash
# 安装正确的 LightRAG 框架
pip install git+https://github.com/HKUDS/LightRAG.git

# 或使用 requirements.txt (推荐)
pip install -r requirements.txt
```

## 🎯 使用示例

### 事实性查询
```
输入: "什么是机器学习？"
模式: local (向量检索)
输出: 详细的机器学习定义和概念解释
```

### 关系性查询
```
输入: "机器学习与深度学习的关系是什么？"
模式: global (图谱检索)
输出: 两者关系的详细分析和对比
```

### 分析性查询
```
输入: "分析当前AI技术的发展趋势"
模式: hybrid (混合检索)
输出: 综合分析报告，包含多维度信息
```

### 混合模式查询
```
输入: "比较不同机器学习算法的优缺点"
模式: mix (综合模式)
输出: 全面的算法对比和分析
```

## 🔄 工作流程

1. **查询分析** → 识别查询类型和意图
2. **LightRAG 检索** → 多模式智能检索
3. **质量评估** → 评估结果质量
4. **网络搜索** → 条件性补充信息
5. **答案生成** → 整合多源信息

## 🛠️ 开发指南

### 项目结构
```
intelligent-qa-system/
├── src/                         # 源代码
│   ├── core/                   # 核心组件
│   │   ├── config.py           # 配置管理
│   │   ├── state.py            # LangGraph状态定义
│   │   └── enhanced_workflow.py # 增强工作流（集成错误处理和监控）
│   ├── agents/                 # 智能节点
│   │   ├── query_analysis.py  # 查询分析节点
│   │   ├── lightrag_retrieval.py # LightRAG检索节点
│   │   ├── quality_assessment.py # 质量评估节点
│   │   ├── web_search.py      # 网络搜索节点
│   │   └── answer_generation.py # 答案生成节点
│   └── utils/                  # 工具模块
│       ├── lightrag_client.py # LightRAG客户端
│       ├── advanced_logging.py # 高级日志系统
│       ├── error_handling.py  # 错误处理
│       ├── system_monitoring.py # 系统监控
│       └── helpers.py         # 辅助函数
├── tests/                      # 测试套件
│   ├── test_comprehensive.py  # 综合测试
│   ├── test_workflow.py       # 工作流测试
│   └── test_performance.py    # 性能测试
├── logs/                       # 日志文件
├── data/                       # 数据目录
├── main_app.py                # 主应用
├── requirements.txt           # 依赖列表
├── test_error_handling.py     # 集成测试
└── README.md                  # 项目文档
```

### 核心 API
```python
from src.core import get_workflow, query, query_async, query_stream

# 方式1: 使用工作流实例
workflow = get_workflow()
result = workflow.run("你的问题")

# 方式2: 使用便捷函数
result = query("你的问题")                    # 同步查询
result = await query_async("你的问题")         # 异步查询

# 流式查询
for step in query_stream("你的问题"):
    print(step)

# 获取性能统计
stats = workflow.get_performance_stats()
print(f"总查询数: {stats['total_queries']}")
```

## 📊 系统特点

- ✅ **智能化**: 自动查询分析和模式选择
- ✅ **多模式**: 支持向量、图谱、混合检索
- ✅ **实时性**: 网络搜索补充最新信息
- ✅ **可视化**: 现代化 Streamlit 界面
- ✅ **可扩展**: 模块化设计，易于扩展
- ✅ **高性能**: 异步处理，流式输出
- ✅ **容错性**: 全面错误处理和重试机制
- ✅ **可观测**: 性能监控和审计日志
- ✅ **可靠性**: 系统健康检查和指标收集

## 🔧 配置示例

```bash
# .env 文件配置
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key

# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database_name
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password

# Neo4j配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# 系统配置
CONFIDENCE_THRESHOLD=0.6
DEBUG_MODE=false
LOG_LEVEL=INFO
```

## ⚙️ 详细环境设置 (Detailed Environment Setup)

如果您在遵循“快速开始”部署时遇到问题，本章节提供了更详细的步骤来手动配置您的环境。

### 1. 数据库配置

#### PostgreSQL & pgvector

项目使用 PostgreSQL 配合 `pgvector` 扩展来存储和查询向量数据。

1.  **安装 PostgreSQL**:
    请确保您的服务器上已安装 PostgreSQL (版本 12 或更高)。您可以直接通过宝塔面板的软件商店进行安装。

2.  **安装 pgvector 扩展**:
    `pgvector` 通常需要手动安装。请通过 SSH 登录您的服务器并执行以下步骤：
    
    a. **确定您的 PostgreSQL 版本**:
    ```bash
    psql --version 
    ```
    记下版本号，例如 `14`。

    b. **安装扩展包** (将 `XX` 替换为您的版本号):
    ```bash
    # 对于 Ubuntu/Debian 系统
    sudo apt-get update
    sudo apt-get install -y postgresql-XX-pgvector

    # 对于 CentOS/RHEL 系统
    sudo yum install -y pgvector_XX
    ```
    *如果找不到包，您可能需要从源码编译安装，请参考 [pgvector 官方文档](https://github.com/pgvector/pgvector)*。

    c. **在数据库中启用扩展**:
    登录到您的项目数据库 (例如，用户和数据库名均为 `searchforrag`):
    ```bash
    psql -U searchforrag -d searchforrag
    ```
    在 psql 命令行中，执行:
    ```sql
    CREATE EXTENSION vector;
    ```
    使用 `\dx vector` 确认扩展已安装成功。

#### Neo4j

项目使用 Neo4j 进行图数据存储和关系查询。

1.  **安装并运行 Neo4j**:
    推荐通过宝塔面板的 Docker 管理器一键部署 `neo4j` 镜像。请确保在部署时映射了 `7687` (数据库连接) 和 `7474` (网页管理) 两个端口。

2.  **检查服务状态**:
    如果 Neo4j 是直接安装在服务器上的，请使用 `sudo systemctl status neo4j` 检查其是否正在运行。

### 2. Python 环境与依赖

1.  **确认 Python 版本**:
    本项目要求 Python 3.9 或更高版本。请使用 `python3 --version` 检查。

2.  **安装依赖**:
    项目依赖已在 `requirements.txt` 中列出。特别注意，`lightrag` 包需要指定一个确切的预发布版本。我们已经为您在文件中修复了此问题。
    ```bash
    pip install -r requirements.txt
    ```

### 3. 环境变量配置

这是最关键的一步，确保您的应用可以连接到所有服务。

1.  **创建 `.env` 文件**:
    ```bash
    cp .env.example .env
    ```

2.  **编辑 `.env` 文件**:
    使用 `nano .env` 或宝塔面板的文件管理器，填入您自己的配置信息，包括：
    - `OPENAI_API_KEY` 和 `TAVILY_API_KEY`。
    - 您在上面步骤中配置好的 PostgreSQL 和 Neo4j 的地址、端口、用户名和密码。

完成以上所有步骤后，您的开发环境应该已经准备就绪。您可以运行测试脚本来验证配置是否全部正确。

## 🐛 故障排除

### 常见问题
1. **导入错误**: 检查依赖安装 `pip install -r requirements.txt`
2. **数据库连接**: 验证数据库配置和连接
3. **API 密钥**: 确保 .env 文件中的密钥正确
4. **内存不足**: 调整 chunk_size 和 max_results 参数

### 系统测试
```bash
# 运行综合测试套件
python tests/test_comprehensive.py

# 运行工作流测试
python tests/test_workflow.py

# 运行性能测试
python tests/test_performance.py

# 运行集成测试
python test_error_handling.py
```

## 📈 性能优化

- **检索优化**: 向量索引和图谱查询优化
- **并发处理**: 异步处理和多线程支持
- **内存管理**: 智能缓存和资源管理
- **响应速度**: 流式输出和实时更新
- **错误恢复**: 自动重试和降级策略
- **监控告警**: 实时性能指标和异常检测

## 🔍 监控和调试

### 性能监控
```python
# 获取系统性能统计
workflow = get_workflow()
stats = workflow.get_performance_stats()

print(f"总查询数: {stats['total_queries']}")
print(f"成功率: {stats['successful_queries'] / stats['total_queries']:.2%}")
print(f"平均响应时间: {stats['average_response_time']:.2f}s")

# 查看节点性能
for node, perf in stats['node_performance'].items():
    print(f"{node}: {perf['average_time']:.2f}s")
```

### 日志监控
```bash
# 查看系统日志
tail -f logs/system.log

# 查看性能日志
tail -f logs/performance.log

# 查看审计日志
tail -f logs/audit.log
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

感谢以下开源项目：
- [LightRAG](https://github.com/lightrag/lightrag)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [LangChain](https://github.com/langchain-ai/langchain)
- [Streamlit](https://github.com/streamlit/streamlit)

## 🔧 高级配置

### 错误处理配置
```python
# 自定义重试策略
config_override = {
    "max_retries": 3,
    "backoff_factor": 2.0,
    "timeout": 30
}

result = query("你的问题", config_override=config_override)
```

### 性能调优
```python
# 调整检索参数
config_override = {
    "lightrag_config": {
        "max_results": 20,
        "confidence_threshold": 0.7
    },
    "web_search_config": {
        "max_results": 10,
        "timeout": 15
    }
}
```

---

**享受智能问答的乐趣！** 🚀
