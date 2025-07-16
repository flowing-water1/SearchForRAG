"""
文档导入脚本
用于将文档导入到LightRAG系统中
"""
## /home/low_ater/SearchForRAG/intelligent-qa-system/docs
import sys
import os
import asyncio
import argparse
from pathlib import Path

# 添加项目根目录到Python路径，让相对导入正常工作
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 使用绝对导入从src目录导入模块
from src.core.config import config
from src.utils.helpers import setup_logger
from src.utils.lightrag_client import initialize_lightrag_once
from src.utils.document_processor import ingest_documents, document_processor

logger = setup_logger(__name__)

def get_interactive_input():
    """交互式收集用户输入参数"""
    print("=" * 50)
    print("🚀 欢迎使用文档导入系统")
    print("=" * 50)
    
    # 获取文档路径
    while True:
        path = input("请输入文档路径（文件或目录）: ").strip()
        if not path:
            print("路径不能为空，请重新输入")
            continue
        
        source_path = Path(path)
        if not source_path.exists():
            print(f"路径不存在: {source_path}，请重新输入")
            continue
        break
    
    # 是否递归处理
    recursive = False
    if source_path.is_dir():
        while True:
            recursive_input = input("是否递归处理子目录？(y/n) [默认: n]: ").strip().lower()
            if recursive_input in ['', 'n', 'no']:
                recursive = False
                break
            elif recursive_input in ['y', 'yes']:
                recursive = True
                break
            else:
                print("请输入 y/yes 或 n/no")
    
    # 是否初始化LightRAG
    init_lightrag = False
    while True:
        init_input = input("是否初始化LightRAG系统？(y/n) [默认: n]: ").strip().lower()
        if init_input in ['', 'n', 'no']:
            init_lightrag = False
            break
        elif init_input in ['y', 'yes']:
            init_lightrag = True
            break
        else:
            print("请输入 y/yes 或 n/no")
    
    print("\n输入完成，开始处理...")
    print("=" * 50)
    
    return {
        'path': str(path),
        'recursive': recursive,
        'init_lightrag': init_lightrag
    }

def is_interactive_mode():
    """判断是否为交互模式"""
    # 如果没有任何命令行参数（除了脚本名），则进入交互模式
    return len(sys.argv) == 1

async def main():
    """主函数"""
    # 判断运行模式
    interactive = is_interactive_mode()
    
    if interactive:
        # 交互模式：直接收集用户输入
        params = get_interactive_input()
        path = params['path']
        recursive = params['recursive']
        init_lightrag = params['init_lightrag']
    else:
        # 命令行模式：解析命令行参数
        parser = argparse.ArgumentParser(description="导入文档到LightRAG系统")
        parser.add_argument(
            "--path", 
            required=True,
            help="要导入的文档路径（文件或目录）"
        )
        parser.add_argument(
            "--recursive", 
            action="store_true",
            help="递归处理子目录"
        )
        parser.add_argument(
            "--init-lightrag",
            action="store_true", 
            help="初始化LightRAG系统"
        )
        
        args = parser.parse_args()
        path = args.path
        recursive = args.recursive
        init_lightrag = args.init_lightrag
    
    logger.info("🚀 开始文档导入流程...")
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
        
        # 打印LightRAG工作目录的绝对路径以供调试
        logger.info(f"RAG Working Directory (Absolute Path): {config.RAG_STORAGE_DIR.resolve()}")

        # 初始化LightRAG（如果需要）
        if init_lightrag:
            logger.info("初始化LightRAG系统...")
            try:
                await initialize_lightrag_once()
                logger.info("✅ LightRAG初始化成功")
            except Exception as e:
                logger.error(f"LightRAG初始化失败: {e}")
                return False
        
        # 验证路径
        source_path = Path(path)
        if not source_path.exists():
            logger.error(f"路径不存在: {source_path}")
            return False
        
        # 导入文档
        logger.info(f"开始导入文档: {source_path}")
        success = await ingest_documents(source_path, recursive)
        
        if success:
            # 显示处理统计
            stats = document_processor.get_processing_stats()
            logger.info("文档导入统计:")
            logger.info(f"  - 总文件数: {stats['total_files']}")
            logger.info(f"  - 文件类型: {stats['file_types']}")
            logger.info(f"  - 总大小: {stats['total_size']:,} 字节")
            
            logger.info("=" * 50)
            logger.info("🎉 文档导入完成！")
            return True
        else:
            logger.error("❌ 文档导入失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 文档导入过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)