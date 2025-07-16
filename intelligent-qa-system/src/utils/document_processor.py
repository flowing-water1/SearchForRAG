"""
文档处理模块
处理各种格式的文档并将它们转换为 LightRAG 可以处理的格式
"""

import asyncio
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from ..core.config import config
from ..utils.simple_logger import get_simple_logger
from ..utils.lightrag_client import lightrag_client, initialize_lightrag_once

# 简单的辅助函数，避免循环导入
def get_file_hash(file_path: Path) -> str:
    """获取文件哈希值"""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def ensure_directory(directory: Path) -> None:
    """确保目录存在"""
    directory.mkdir(parents=True, exist_ok=True)

logger = get_simple_logger(__name__)

@dataclass
class DocumentInfo:
    """文档信息数据类"""
    path: Path
    title: str
    content: str
    file_type: str
    size: int
    hash: str
    processed_at: datetime

class DocumentProcessor:
    """文档处理器类"""
    
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text',
        '.md': 'markdown', 
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'doc'
    }
    
    def __init__(self):
        self.processed_files: Dict[str, DocumentInfo] = {}
        
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return list(self.SUPPORTED_EXTENSIONS.keys())
    
    async def process_file(self, file_path: Union[str, Path]) -> Optional[DocumentInfo]:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            处理后的文档信息，失败时返回 None
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return None
            
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"不支持的文件格式: {file_path.suffix}")
            return None
            
        try:
            logger.info(f"正在处理文件: {file_path.name}")
            
            # 获取文件信息
            file_hash = get_file_hash(file_path)
            file_size = file_path.stat().st_size
            file_type = self.SUPPORTED_EXTENSIONS[file_path.suffix.lower()]
            
            # 检查是否已处理过
            if file_hash in self.processed_files:
                logger.info(f"文件已处理过: {file_path.name}")
                return self.processed_files[file_hash]
            
            # 读取文件内容
            content = await self._read_file_content(file_path, file_type)
            
            if not content:
                logger.error(f"无法读取文件内容: {file_path}")
                return None
                
            # 创建文档信息
            doc_info = DocumentInfo(
                path=file_path,
                title=file_path.stem,
                content=content,
                file_type=file_type,
                size=file_size,
                hash=file_hash,
                processed_at=datetime.now()
            )
            
            # 缓存处理结果
            self.processed_files[file_hash] = doc_info
            
            logger.info(f"✅ 文件处理完成: {file_path.name} ({len(content)} 字符)")
            return doc_info
            
        except Exception as e:
            logger.error(f"❌ 文件处理失败 {file_path}: {e}")
            return None
    
    async def _read_file_content(self, file_path: Path, file_type: str) -> Optional[str]:
        """
        根据文件类型读取内容
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            文件内容字符串
        """
        try:
            if file_type in ['text', 'markdown']:
                return self._read_text_file(file_path)
            elif file_type == 'pdf':
                return self._read_pdf_file(file_path)
            elif file_type in ['docx', 'doc']:
                return self._read_word_file(file_path)
            else:
                logger.error(f"不支持的文件类型: {file_type}")
                return None
                
        except Exception as e:
            logger.error(f"读取文件内容失败: {e}")
            return None
    
    def _read_text_file(self, file_path: Path) -> str:
        """读取文本文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    logger.debug(f"使用 {encoding} 编码读取文件: {file_path.name}")
                    return content
            except UnicodeDecodeError:
                continue
                
        raise ValueError(f"无法解码文件: {file_path}")
    
    def _read_pdf_file(self, file_path: Path) -> str:
        """读取PDF文件"""
        try:
            import pypdf
            content = ""
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        content += text + "\n"
                    except Exception as e:
                        logger.warning(f"PDF页面 {page_num} 解析失败: {e}")
                        continue
            return content.strip()
        except ImportError:
            logger.error("缺少 pypdf 库，无法处理 PDF 文件")
            return ""
        except Exception as e:
            logger.error(f"PDF文件处理失败: {e}")
            return ""
    
    def _read_word_file(self, file_path: Path) -> str:
        """读取Word文件"""
        try:
            from docx import Document
            doc = Document(file_path)
            content = ""
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
            return content.strip()
        except ImportError:
            logger.error("缺少 python-docx 库，无法处理 Word 文件")
            return ""
        except Exception as e:
            logger.error(f"Word文件处理失败: {e}")
            return ""
    
    async def process_directory(
        self, 
        directory: Union[str, Path], 
        recursive: bool = True
    ) -> List[DocumentInfo]:
        """
        处理目录中的所有文档
        
        Args:
            directory: 目录路径
            recursive: 是否递归处理子目录
            
        Returns:
            处理成功的文档信息列表
        """
        directory = Path(directory)
        
        if not directory.exists() or not directory.is_dir():
            logger.error(f"目录不存在或不是目录: {directory}")
            return []
            
        logger.info(f"开始处理目录: {directory}")
        
        # 收集所有支持的文件
        files = []
        for ext in self.SUPPORTED_EXTENSIONS.keys():
            if recursive:
                files.extend(directory.rglob(f'*{ext}'))
            else:
                files.extend(directory.glob(f'*{ext}'))
        
        logger.info(f"找到 {len(files)} 个支持的文件")
        
        # 并行处理文件
        tasks = [self.process_file(file_path) for file_path in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤成功的结果
        processed_docs = []
        for result in results:
            if isinstance(result, DocumentInfo):
                processed_docs.append(result)
            elif isinstance(result, Exception):
                logger.error(f"文件处理异常: {result}")
        
        logger.info(f"✅ 目录处理完成: {len(processed_docs)}/{len(files)} 个文件成功处理")
        return processed_docs
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        if not self.processed_files:
            return {"total_files": 0, "file_types": {}, "total_size": 0}
            
        file_types = {}
        total_size = 0
        
        for doc_info in self.processed_files.values():
            file_type = doc_info.file_type
            file_types[file_type] = file_types.get(file_type, 0) + 1
            total_size += doc_info.size
            
        return {
            "total_files": len(self.processed_files),
            "file_types": file_types,
            "total_size": total_size,
            "processed_at": datetime.now()
        }

# 全局文档处理器实例
document_processor = DocumentProcessor()

async def process_documents(
    source: Union[str, Path], 
    recursive: bool = True
) -> List[DocumentInfo]:
    """
    处理文档（便捷函数）
    
    Args:
        source: 文件或目录路径
        recursive: 如果是目录，是否递归处理
        
    Returns:
        处理成功的文档信息列表
    """
    source = Path(source)
    
    if source.is_file():
        result = await document_processor.process_file(source)
        return [result] if result else []
    elif source.is_dir():
        return await document_processor.process_directory(source, recursive)
    else:
        logger.error(f"源路径不存在: {source}")
        return []

async def ingest_documents(
    source: Union[str, Path],
    recursive: bool = True
) -> bool:
    """
    处理文档并导入到 LightRAG
    
    Args:
        source: 文件或目录路径
        recursive: 如果是目录，是否递归处理
        
    Returns:
        导入是否成功
    """
    logger.info(f"开始文档导入流程: {source}")
    
    # 处理文档
    docs = await process_documents(source, recursive)
    
    if not docs:
        logger.warning("没有找到可处理的文档")
        return False
        
    # 提取文档内容
    contents = []
    for doc in docs:
        # 为每个文档添加标题和元数据
        formatted_content = f"# {doc.title}\n\n{doc.content}"
        contents.append(formatted_content)
        
    # 确保 LightRAG 已初始化并导入文档
    try:
        # 获取已初始化的 LightRAG 实例
        rag_instance = await initialize_lightrag_once()
        
        # 直接使用 LightRAG 实例进行文档插入
        await rag_instance.ainsert(contents)
        logger.info("✅ 文档已成功插入到 LightRAG")
        success = True
    except Exception as e:
        logger.error(f"❌ 文档插入失败: {e}")
        success = False
    
    if success:
        logger.info(f"✅ 文档导入完成: {len(docs)} 个文档")
        # 记录统计信息
        stats = document_processor.get_processing_stats()
        logger.info(f"处理统计: {stats}")
    else:
        logger.error("❌ 文档导入失败")
        
    return success