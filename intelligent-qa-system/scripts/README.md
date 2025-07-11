# 脚本工具技术文档

> 返回 [项目概览文档](../../TECHNICAL_REFERENCE.md)

## 📍 相关文档导航
- **[核心模块文档](../src/core/README.md)** - 查看脚本使用的配置和工作流
- **[工具模块文档](../src/utils/README.md)** - 查看脚本依赖的客户端和工具
- **[测试模块文档](../tests/README.md)** - 查看脚本的测试和验证
- **[项目根目录](../../TECHNICAL_REFERENCE.md)** - 返回项目完整概览

## 🔗 脚本与系统集成
- [配置管理](../src/core/README.md#1-配置管理系统-configpy) - 脚本使用的配置系统
- [LightRAG客户端](../src/utils/README.md#5-lightrag客户端-lightrag_clientpy) - 文档摄取的核心依赖
- [系统监控](../src/utils/README.md#4-系统监控-system_monitoringpy) - 环境检查和健康验证
- [错误处理](../src/utils/README.md#3-错误处理框架-error_handlingpy) - 脚本的异常处理机制

---

## 模块概述

脚本工具模块 (scripts/) 提供了智能问答系统的部署、管理和维护脚本。这些脚本自动化了环境设置、数据摄取、连接测试等关键操作，简化了系统的部署和运维流程。

### 模块结构
```
scripts/
├── setup_environment.py     # 环境初始化脚本
├── ingest_documents.py      # 文档摄取脚本
└── test_connections.py      # 连接测试脚本
```

### 脚本分类
- **环境管理**: 初始化和配置系统环境
- **数据管理**: 文档摄取和知识库构建
- **运维工具**: 连接测试和健康检查

---

## 脚本详解

### 1. 环境初始化脚本 (setup_environment.py)

**主要功能**: 设置数据库、创建必要的表和索引，初始化系统运行环境。

#### 脚本结构

```python
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
```

#### 目录创建功能

```python
async def setup_directories():
    """创建必要的目录
    
    创建目录:
    - RAG存储目录
    - 向量存储目录
    - 图存储目录
    - 文档目录
    """
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
```

#### PostgreSQL设置

```python
async def setup_postgresql():
    """设置PostgreSQL数据库
    
    功能:
    - 检查数据库连接
    - 安装pgvector扩展
    - 创建必要的表和索引
    - 配置向量存储
    """
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
            logger.info("✅ pgvector扩展已安装")
        except psycopg2.Error as e:
            logger.warning(f"⚠️  pgvector扩展安装失败: {e}")
            logger.info("请手动安装pgvector扩展")
        
        # 创建向量表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_vectors (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR(1536),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_vectors_embedding 
            ON document_vectors USING ivfflat (embedding vector_cosine_ops);
        """)
        
        # 创建文档元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id VARCHAR(255) PRIMARY KEY,
                title VARCHAR(255),
                content TEXT,
                source VARCHAR(255),
                metadata JSONB,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.close()
        conn.close()
        
        logger.info("✅ PostgreSQL数据库设置完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL设置失败: {e}")
        return False
```

#### Neo4j设置

```python
async def setup_neo4j():
    """设置Neo4j图数据库
    
    功能:
    - 检查Neo4j连接
    - 创建约束和索引
    - 配置图存储参数
    """
    logger.info("设置Neo4j数据库...")
    
    try:
        from neo4j import GraphDatabase
        
        # 连接Neo4j
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
        )
        
        with driver.session() as session:
            # 创建唯一约束
            constraints = [
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"✅ 约束已创建: {constraint.split()[2]}")
                except Exception as e:
                    logger.warning(f"约束创建可能已存在: {e}")
            
            # 创建索引
            indexes = [
                "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX document_title IF NOT EXISTS FOR (d:Document) ON (d.title)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"✅ 索引已创建: {index.split()[2]}")
                except Exception as e:
                    logger.warning(f"索引创建可能已存在: {e}")
        
        driver.close()
        logger.info("✅ Neo4j数据库设置完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ Neo4j设置失败: {e}")
        logger.info("请检查Neo4j服务是否正在运行")
        return False
```

#### LightRAG初始化

```python
async def setup_lightrag():
    """初始化LightRAG系统
    
    功能:
    - 初始化LightRAG客户端
    - 配置存储后端
    - 验证系统功能
    """
    logger.info("初始化LightRAG系统...")
    
    try:
        from utils.lightrag_client import lightrag_client
        
        # 初始化LightRAG客户端
        success = await lightrag_client.initialize()
        
        if success:
            logger.info("✅ LightRAG系统初始化成功")
            
            # 获取系统状态
            status = await lightrag_client.get_health_status()
            logger.info(f"LightRAG状态: {status}")
            
            return True
        else:
            logger.error("❌ LightRAG系统初始化失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ LightRAG初始化异常: {e}")
        return False
```

#### 完整环境设置

```python
async def setup_complete_environment():
    """设置完整环境
    
    执行步骤:
    1. 创建必要目录
    2. 设置PostgreSQL
    3. 设置Neo4j
    4. 初始化LightRAG
    5. 验证环境配置
    """
    logger.info("🚀 开始环境初始化...")
    
    success_count = 0
    total_steps = 4
    
    # 1. 创建目录
    try:
        await setup_directories()
        success_count += 1
        logger.info("✅ 步骤 1/4: 目录创建完成")
    except Exception as e:
        logger.error(f"❌ 步骤 1/4: 目录创建失败 - {e}")
    
    # 2. 设置PostgreSQL
    try:
        postgres_success = await setup_postgresql()
        if postgres_success:
            success_count += 1
            logger.info("✅ 步骤 2/4: PostgreSQL设置完成")
        else:
            logger.error("❌ 步骤 2/4: PostgreSQL设置失败")
    except Exception as e:
        logger.error(f"❌ 步骤 2/4: PostgreSQL设置异常 - {e}")
    
    # 3. 设置Neo4j
    try:
        neo4j_success = await setup_neo4j()
        if neo4j_success:
            success_count += 1
            logger.info("✅ 步骤 3/4: Neo4j设置完成")
        else:
            logger.error("❌ 步骤 3/4: Neo4j设置失败")
    except Exception as e:
        logger.error(f"❌ 步骤 3/4: Neo4j设置异常 - {e}")
    
    # 4. 初始化LightRAG
    try:
        lightrag_success = await setup_lightrag()
        if lightrag_success:
            success_count += 1
            logger.info("✅ 步骤 4/4: LightRAG初始化完成")
        else:
            logger.error("❌ 步骤 4/4: LightRAG初始化失败")
    except Exception as e:
        logger.error(f"❌ 步骤 4/4: LightRAG初始化异常 - {e}")
    
    # 总结
    logger.info(f"\n🎯 环境初始化完成: {success_count}/{total_steps} 步骤成功")
    
    if success_count == total_steps:
        logger.info("🎉 所有组件设置成功！系统已准备就绪。")
        return True
    else:
        logger.warning("⚠️  部分组件设置失败，请检查错误信息并手动修复。")
        return False

# 主执行函数
async def main():
    """主执行函数"""
    try:
        success = await setup_complete_environment()
        
        if success:
            print("\n" + "="*50)
            print("🎉 环境初始化成功完成！")
            print("你现在可以运行以下命令启动系统:")
            print("  streamlit run main_app.py")
            print("  streamlit run streamlit_app.py")
            print("="*50)
            sys.exit(0)
        else:
            print("\n" + "="*50)
            print("⚠️  环境初始化部分失败")
            print("请检查错误日志并手动修复问题")
            print("="*50)
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"环境初始化异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 文档摄取脚本 (ingest_documents.py)

**主要功能**: 批量处理和摄取文档到知识库，构建向量索引和知识图谱。

#### 脚本架构

```python
"""
文档摄取脚本
批量处理文档并摄取到LightRAG知识库
"""

import asyncio
import sys
from pathlib import Path
import argparse
from typing import List, Dict, Any
import json

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import config
from utils.lightrag_client import lightrag_client
from utils.document_processor import DocumentProcessor
from utils.helpers import setup_logger, validate_file_type
from utils.advanced_logging import get_performance_logger

logger = setup_logger(__name__)
perf_logger = get_performance_logger(__name__)
```

#### 文档处理器

```python
class DocumentIngestor:
    """文档摄取器
    
    功能:
    - 支持多种文档格式
    - 批量处理和进度跟踪
    - 错误处理和重试机制
    - 性能监控和优化
    """
    
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.processor = DocumentProcessor()
        self.processed_count = 0
        self.failed_count = 0
        self.total_count = 0
    
    async def ingest_directory(self, directory: Path, recursive: bool = True) -> Dict[str, Any]:
        """摄取目录中的所有文档
        
        Args:
            directory: 文档目录路径
            recursive: 是否递归处理子目录
            
        Returns:
            摄取结果统计
        """
        logger.info(f"开始摄取目录: {directory}")
        perf_logger.start_operation("directory_ingestion", directory=str(directory))
        
        try:
            # 获取所有文档文件
            files = self._get_document_files(directory, recursive)
            self.total_count = len(files)
            
            logger.info(f"发现 {self.total_count} 个文档文件")
            
            if self.total_count == 0:
                logger.warning("未发现可处理的文档文件")
                return self._get_summary()
            
            # 分批处理文档
            for i in range(0, len(files), self.batch_size):
                batch_files = files[i:i + self.batch_size]
                batch_number = i // self.batch_size + 1
                total_batches = (len(files) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"处理批次 {batch_number}/{total_batches} ({len(batch_files)} 文件)")
                
                await self._process_batch(batch_files)
                
                # 显示进度
                progress = (i + len(batch_files)) / len(files) * 100
                logger.info(f"进度: {progress:.1f}% ({self.processed_count}/{self.total_count})")
            
            # 完成摄取
            perf_logger.end_operation(
                success=True,
                processed_files=self.processed_count,
                failed_files=self.failed_count
            )
            
            summary = self._get_summary()
            logger.info("摄取完成:")
            logger.info(f"  成功: {summary['processed_count']} 文件")
            logger.info(f"  失败: {summary['failed_count']} 文件")
            logger.info(f"  总计: {summary['total_count']} 文件")
            
            return summary
            
        except Exception as e:
            perf_logger.end_operation(success=False, error=str(e))
            logger.error(f"目录摄取失败: {e}")
            raise
    
    def _get_document_files(self, directory: Path, recursive: bool) -> List[Path]:
        """获取目录中的文档文件"""
        supported_extensions = {'.txt', '.md', '.pdf', '.docx', '.html', '.json'}
        files = []
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                files.append(file_path)
        
        return sorted(files)
    
    async def _process_batch(self, files: List[Path]):
        """处理文件批次"""
        tasks = [self._process_single_file(file_path) for file_path in files]
        
        # 并发处理文件
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for file_path, result in zip(files, results):
            if isinstance(result, Exception):
                logger.error(f"处理文件失败 {file_path}: {result}")
                self.failed_count += 1
            elif result:
                logger.info(f"✅ 成功处理: {file_path.name}")
                self.processed_count += 1
            else:
                logger.warning(f"⚠️  跳过文件: {file_path.name}")
                self.failed_count += 1
    
    async def _process_single_file(self, file_path: Path) -> bool:
        """处理单个文件"""
        try:
            # 读取文档内容
            content = await self.processor.read_document(file_path)
            
            if not content or len(content.strip()) < 100:
                logger.warning(f"文档内容过短，跳过: {file_path}")
                return False
            
            # 准备文档元数据
            metadata = {
                "source": str(file_path),
                "filename": file_path.name,
                "extension": file_path.suffix,
                "size": file_path.stat().st_size,
                "processed_at": datetime.now().isoformat()
            }
            
            # 摄取到LightRAG
            success = await lightrag_client.insert_document(content, metadata)
            
            return success
            
        except Exception as e:
            logger.error(f"处理文件异常 {file_path}: {e}")
            return False
    
    def _get_summary(self) -> Dict[str, Any]:
        """获取摄取结果摘要"""
        return {
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "success_rate": self.processed_count / self.total_count if self.total_count > 0 else 0
        }
```

#### 命令行接口

```python
def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="智能问答系统文档摄取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python ingest_documents.py docs/                    # 摄取docs目录
  python ingest_documents.py docs/ --recursive        # 递归摄取子目录
  python ingest_documents.py docs/ --batch-size 20    # 设置批次大小
  python ingest_documents.py single_file.pdf          # 摄取单个文件
        """
    )
    
    parser.add_argument(
        "path",
        type=str,
        help="要摄取的文档路径(文件或目录)"
    )
    
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="递归处理子目录"
    )
    
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=10,
        help="批次处理大小 (默认: 10)"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制重新处理已存在的文档"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，不实际摄取文档"
    )
    
    return parser

async def main():
    """主执行函数"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 验证路径
    input_path = Path(args.path)
    if not input_path.exists():
        logger.error(f"路径不存在: {input_path}")
        sys.exit(1)
    
    try:
        # 初始化LightRAG客户端
        logger.info("初始化LightRAG客户端...")
        await lightrag_client.initialize()
        
        # 创建文档摄取器
        ingestor = DocumentIngestor(batch_size=args.batch_size)
        
        # 执行摄取
        if input_path.is_file():
            # 单文件摄取
            logger.info(f"摄取单个文件: {input_path}")
            success = await ingestor._process_single_file(input_path)
            
            if success:
                logger.info("✅ 文件摄取成功")
            else:
                logger.error("❌ 文件摄取失败")
                sys.exit(1)
        
        elif input_path.is_dir():
            # 目录摄取
            if args.dry_run:
                logger.info("🔍 试运行模式 - 仅扫描文件，不执行摄取")
                files = ingestor._get_document_files(input_path, args.recursive)
                logger.info(f"发现 {len(files)} 个可处理文件:")
                for file_path in files:
                    logger.info(f"  - {file_path}")
            else:
                summary = await ingestor.ingest_directory(input_path, args.recursive)
                
                if summary["success_rate"] > 0.8:
                    logger.info("🎉 文档摄取成功完成")
                elif summary["success_rate"] > 0.5:
                    logger.warning("⚠️  文档摄取部分成功")
                else:
                    logger.error("❌ 文档摄取大部分失败")
                    sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"文档摄取异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 连接测试脚本 (test_connections.py)

**主要功能**: 测试系统各组件的连接状态和健康状况。

#### 测试架构

```python
"""
连接测试脚本
测试系统各组件的连接状态和配置
"""

import asyncio
import sys
from pathlib import Path
import json
from typing import Dict, Any, List
import time

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import config
from utils.lightrag_client import lightrag_client
from utils.system_monitoring import ApplicationHealthChecker
from utils.helpers import setup_logger

logger = setup_logger(__name__)
```

#### 连接测试器

```python
class ConnectionTester:
    """连接测试器
    
    功能:
    - 测试所有外部依赖连接
    - 生成详细的健康报告
    - 提供修复建议
    """
    
    def __init__(self):
        self.health_checker = ApplicationHealthChecker()
        self.test_results = {}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有连接测试"""
        logger.info("🔍 开始系统连接测试...")
        
        tests = [
            ("配置验证", self._test_configuration),
            ("PostgreSQL连接", self._test_postgresql),
            ("Neo4j连接", self._test_neo4j),
            ("OpenAI API", self._test_openai_api),
            ("Tavily API", self._test_tavily_api),
            ("LightRAG系统", self._test_lightrag_system),
            ("文件系统访问", self._test_file_system)
        ]
        
        total_tests = len(tests)
        passed_tests = 0
        
        for i, (test_name, test_func) in enumerate(tests, 1):
            logger.info(f"[{i}/{total_tests}] 测试 {test_name}...")
            
            try:
                result = await test_func()
                self.test_results[test_name] = result
                
                if result["status"] == "success":
                    logger.info(f"✅ {test_name}: {result['message']}")
                    passed_tests += 1
                elif result["status"] == "warning":
                    logger.warning(f"⚠️  {test_name}: {result['message']}")
                    passed_tests += 0.5
                else:
                    logger.error(f"❌ {test_name}: {result['message']}")
                
            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"测试异常: {str(e)}",
                    "details": {"exception": str(e)}
                }
                self.test_results[test_name] = error_result
                logger.error(f"❌ {test_name}: 测试异常 - {e}")
        
        # 生成总结报告
        success_rate = passed_tests / total_tests
        overall_status = self._determine_overall_status(success_rate)
        
        summary = {
            "overall_status": overall_status,
            "success_rate": success_rate,
            "total_tests": total_tests,
            "passed_tests": int(passed_tests),
            "test_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }
        
        logger.info(f"\n📊 测试完成: {int(passed_tests)}/{total_tests} 通过 ({success_rate:.1%})")
        return summary
    
    async def _test_configuration(self) -> Dict[str, Any]:
        """测试配置有效性"""
        issues = []
        warnings = []
        
        # 检查必需配置
        required_configs = [
            ("LLM_API_KEY", "LLM API密钥"),
            ("LLM_MODEL", "LLM模型"),
            ("EMBEDDING_MODEL", "嵌入模型")
        ]
        
        for config_key, description in required_configs:
            value = getattr(config, config_key, None)
            if not value:
                issues.append(f"缺少配置: {description} ({config_key})")
        
        # 检查可选配置
        optional_configs = [
            ("TAVILY_API_KEY", "Tavily搜索API密钥"),
            ("NEO4J_URI", "Neo4j数据库URI"),
            ("POSTGRES_HOST", "PostgreSQL主机")
        ]
        
        for config_key, description in optional_configs:
            value = getattr(config, config_key, None)
            if not value:
                warnings.append(f"可选配置未设置: {description} ({config_key})")
        
        # 验证API密钥格式
        if hasattr(config, 'LLM_API_KEY') and config.LLM_API_KEY:
            if not config.LLM_API_KEY.startswith(('sk-', 'gsk_')):
                warnings.append("LLM API密钥格式可能不正确")
        
        if issues:
            return {
                "status": "error",
                "message": f"配置验证失败: {len(issues)} 个必需配置缺失",
                "details": {"issues": issues, "warnings": warnings}
            }
        elif warnings:
            return {
                "status": "warning", 
                "message": f"配置基本正确，但有 {len(warnings)} 个警告",
                "details": {"warnings": warnings}
            }
        else:
            return {
                "status": "success",
                "message": "所有配置验证通过",
                "details": {}
            }
    
    async def _test_postgresql(self) -> Dict[str, Any]:
        """测试PostgreSQL连接"""
        try:
            health_check = self.health_checker.check_database_connection()
            
            if health_check.status.value == "healthy":
                return {
                    "status": "success",
                    "message": "PostgreSQL连接正常",
                    "details": health_check.details
                }
            else:
                return {
                    "status": "error",
                    "message": health_check.message,
                    "details": health_check.details
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"PostgreSQL连接测试失败: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def _test_neo4j(self) -> Dict[str, Any]:
        """测试Neo4j连接"""
        try:
            if not hasattr(config, 'NEO4J_URI') or not config.NEO4J_URI:
                return {
                    "status": "warning",
                    "message": "Neo4j配置未设置，将使用文件存储",
                    "details": {}
                }
            
            from neo4j import GraphDatabase
            
            driver = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
            )
            
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
            
            driver.close()
            
            if test_value == 1:
                return {
                    "status": "success",
                    "message": "Neo4j连接正常",
                    "details": {"uri": config.NEO4J_URI}
                }
            else:
                return {
                    "status": "error",
                    "message": "Neo4j测试查询返回异常值",
                    "details": {"expected": 1, "actual": test_value}
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Neo4j连接失败: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def _test_openai_api(self) -> Dict[str, Any]:
        """测试OpenAI API连接"""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=config.LLM_API_KEY,
                base_url=config.LLM_BASE_URL
            )
            
            # 测试模型列表
            models = client.models.list()
            
            if models:
                model_count = len(models.data) if hasattr(models, 'data') else 0
                return {
                    "status": "success",
                    "message": f"OpenAI API连接正常，可用模型: {model_count}",
                    "details": {
                        "base_url": config.LLM_BASE_URL,
                        "model_count": model_count
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "OpenAI API连接成功但无可用模型",
                    "details": {}
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"OpenAI API连接失败: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def _test_tavily_api(self) -> Dict[str, Any]:
        """测试Tavily API连接"""
        try:
            if not hasattr(config, 'TAVILY_API_KEY') or not config.TAVILY_API_KEY:
                return {
                    "status": "warning",
                    "message": "Tavily API密钥未配置，网络搜索功能不可用",
                    "details": {}
                }
            
            from tavily import TavilySearchAPIWrapper
            
            tavily = TavilySearchAPIWrapper(api_key=config.TAVILY_API_KEY)
            
            # 执行测试搜索
            results = tavily.search("test query", max_results=1)
            
            if results:
                return {
                    "status": "success",
                    "message": "Tavily API连接正常",
                    "details": {"test_results": len(results)}
                }
            else:
                return {
                    "status": "warning",
                    "message": "Tavily API连接成功但测试搜索无结果",
                    "details": {}
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Tavily API连接失败: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def _test_lightrag_system(self) -> Dict[str, Any]:
        """测试LightRAG系统"""
        try:
            # 初始化LightRAG客户端
            await lightrag_client.initialize()
            
            # 获取健康状态
            health_status = await lightrag_client.get_health_status()
            
            if health_status.get("initialized", False):
                return {
                    "status": "success",
                    "message": "LightRAG系统正常",
                    "details": health_status
                }
            else:
                return {
                    "status": "error",
                    "message": "LightRAG系统初始化失败",
                    "details": health_status
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"LightRAG系统测试失败: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def _test_file_system(self) -> Dict[str, Any]:
        """测试文件系统访问"""
        try:
            issues = []
            
            # 检查必要目录
            directories = [
                config.RAG_STORAGE_DIR,
                config.DOCS_DIR
            ]
            
            for directory in directories:
                if not directory.exists():
                    issues.append(f"目录不存在: {directory}")
                elif not os.access(directory, os.R_OK | os.W_OK):
                    issues.append(f"目录无读写权限: {directory}")
            
            # 检查日志目录
            log_dir = Path("logs")
            if not log_dir.exists():
                try:
                    log_dir.mkdir(exist_ok=True)
                except Exception as e:
                    issues.append(f"无法创建日志目录: {e}")
            
            if issues:
                return {
                    "status": "error",
                    "message": f"文件系统访问有 {len(issues)} 个问题",
                    "details": {"issues": issues}
                }
            else:
                return {
                    "status": "success",
                    "message": "文件系统访问正常",
                    "details": {}
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"文件系统测试失败: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    def _determine_overall_status(self, success_rate: float) -> str:
        """确定整体状态"""
        if success_rate >= 0.9:
            return "healthy"
        elif success_rate >= 0.7:
            return "warning"
        else:
            return "error"
    
    def _generate_recommendations(self) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        for test_name, result in self.test_results.items():
            if result["status"] == "error":
                if "配置" in test_name:
                    recommendations.append("检查.env文件，确保所有必需配置已设置")
                elif "PostgreSQL" in test_name:
                    recommendations.append("启动PostgreSQL服务并安装pgvector扩展")
                elif "Neo4j" in test_name:
                    recommendations.append("启动Neo4j服务或更新连接配置")
                elif "OpenAI" in test_name:
                    recommendations.append("验证OpenAI API密钥和网络连接")
                elif "Tavily" in test_name:
                    recommendations.append("配置Tavily API密钥(可选)")
                elif "LightRAG" in test_name:
                    recommendations.append("检查LightRAG依赖和存储配置")
                elif "文件系统" in test_name:
                    recommendations.append("检查目录权限和磁盘空间")
        
        return recommendations
```

#### 主执行函数

```python
async def main():
    """主执行函数"""
    try:
        tester = ConnectionTester()
        summary = await tester.run_all_tests()
        
        # 打印详细报告
        print("\n" + "="*60)
        print("🔍 系统连接测试报告")
        print("="*60)
        
        overall_status = summary["overall_status"]
        if overall_status == "healthy":
            print("🟢 整体状态: 健康")
        elif overall_status == "warning":
            print("🟡 整体状态: 警告")
        else:
            print("🔴 整体状态: 错误")
        
        print(f"📊 成功率: {summary['success_rate']:.1%}")
        print(f"📈 通过测试: {summary['passed_tests']}/{summary['total_tests']}")
        
        # 打印失败的测试
        failed_tests = [
            name for name, result in summary["test_results"].items()
            if result["status"] == "error"
        ]
        
        if failed_tests:
            print(f"\n❌ 失败的测试 ({len(failed_tests)}):")
            for test_name in failed_tests:
                result = summary["test_results"][test_name]
                print(f"  - {test_name}: {result['message']}")
        
        # 打印建议
        if summary["recommendations"]:
            print(f"\n💡 修复建议:")
            for i, rec in enumerate(summary["recommendations"], 1):
                print(f"  {i}. {rec}")
        
        print("="*60)
        
        # 保存详细报告
        report_file = Path("connection_test_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"📄 详细报告已保存到: {report_file}")
        
        # 根据结果设置退出码
        if overall_status == "healthy":
            sys.exit(0)
        elif overall_status == "warning":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"连接测试异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 脚本使用指南

### 快速开始

```bash
# 1. 初始化环境
python scripts/setup_environment.py

# 2. 测试系统连接
python scripts/test_connections.py

# 3. 摄取文档
python scripts/ingest_documents.py docs/
```

### 详细使用方法

**环境初始化**
```bash
# 完整环境设置
python scripts/setup_environment.py

# 查看设置日志
tail -f logs/setup.log
```

**文档摄取**
```bash
# 摄取单个目录
python scripts/ingest_documents.py documents/

# 递归摄取所有子目录
python scripts/ingest_documents.py documents/ --recursive

# 设置批次大小
python scripts/ingest_documents.py documents/ --batch-size 20

# 试运行（不实际摄取）
python scripts/ingest_documents.py documents/ --dry-run

# 摄取单个文件
python scripts/ingest_documents.py path/to/document.pdf
```

**连接测试**
```bash
# 运行所有测试
python scripts/test_connections.py

# 查看详细报告
cat connection_test_report.json
```

---

## 自动化和集成

### 部署脚本

```bash
#!/bin/bash
# deploy.sh - 自动化部署脚本

set -e

echo "🚀 开始系统部署..."

# 1. 环境初始化
echo "📋 步骤 1: 环境初始化"
python scripts/setup_environment.py

# 2. 连接测试
echo "🔍 步骤 2: 连接测试"
python scripts/test_connections.py

# 3. 摄取示例文档
echo "📚 步骤 3: 摄取示例文档"
if [ -d "docs/" ]; then
    python scripts/ingest_documents.py docs/ --recursive
fi

echo "✅ 部署完成！"
echo "现在可以运行: streamlit run main_app.py"
```

### 定时任务

```bash
# crontab -e
# 每日健康检查
0 9 * * * cd /path/to/project && python scripts/test_connections.py >> logs/daily_health.log 2>&1

# 每周文档摄取
0 2 * * 0 cd /path/to/project && python scripts/ingest_documents.py new_docs/ --recursive >> logs/weekly_ingest.log 2>&1
```

### Docker集成

```dockerfile
# Dockerfile中的脚本使用
FROM python:3.10

COPY scripts/ /app/scripts/
COPY src/ /app/src/

WORKDIR /app

# 安装依赖
RUN pip install -r requirements.txt

# 初始化环境
RUN python scripts/setup_environment.py

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/test_connections.py || exit 1

CMD ["streamlit", "run", "main_app.py"]
```

---

## 故障排除

### 常见问题

**环境初始化失败**
```bash
# 检查依赖
pip list | grep -E "(psycopg2|neo4j|lightrag)"

# 检查数据库服务
systemctl status postgresql
systemctl status neo4j

# 手动测试连接
python -c "import psycopg2; print('PostgreSQL可用')"
python -c "from neo4j import GraphDatabase; print('Neo4j可用')"
```

**文档摄取失败**
```bash
# 检查文件权限
ls -la docs/

# 测试单个文件
python scripts/ingest_documents.py single_file.txt --dry-run

# 查看详细错误
python scripts/ingest_documents.py docs/ --batch-size 1
```

**连接测试异常**
```bash
# 逐步测试
python -c "from src.core.config import config; print(config.LLM_API_KEY[:10])"
curl -H "Authorization: Bearer $LLM_API_KEY" https://api.openai.com/v1/models
```

### 调试技巧

**详细日志**
```python
# 在脚本中启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

**性能监控**
```python
# 添加性能监控
from utils.advanced_logging import get_performance_logger
perf_logger = get_performance_logger(__name__)

perf_logger.start_operation("script_execution")
# 脚本逻辑
perf_logger.end_operation(success=True)
```

---

**📝 说明**: 本文档详细介绍了智能问答系统的所有脚本工具。这些脚本自动化了环境设置、文档摄取和系统监控等关键操作，是系统部署和维护的重要工具。