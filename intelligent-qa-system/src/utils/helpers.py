"""
辅助函数模块
提供系统通用的工具函数，集成高级日志记录和错误处理
"""

import json
import logging
import hashlib
import time
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path

# 导入新的日志系统
from .advanced_logging import setup_logger as advanced_setup_logger
from .error_handling import ValidationError, handle_errors


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    设置日志记录器 - 向后兼容包装器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    return advanced_setup_logger(name)


@handle_errors(reraise=False, return_on_error="")
def format_sources(sources: List[Dict[str, Any]]) -> str:
    """
    格式化信息来源
    
    Args:
        sources: 信息来源列表
        
    Returns:
        格式化后的来源信息字符串
    """
    if not sources:
        return "无信息来源"
    
    formatted = []
    
    try:
        for i, source in enumerate(sources, 1):
            source_type = source.get("type", "unknown")
            
            if source_type == "lightrag_knowledge":
                mode = source.get("mode", "unknown")
                confidence = source.get("confidence", 0)
                formatted.append(f"{i}. 本地知识库 ({mode}模式, 置信度: {confidence:.2f})")
                
            elif source_type == "web_search":
                title = source.get("title", "未知标题")
                url = source.get("url", "")
                domain = source.get("domain", "")
                score = source.get("score", 0)
                formatted.append(f"{i}. 网络搜索: [{title}]({url}) - {domain} (评分: {score:.2f})")
                
            elif source_type == "knowledge_graph":
                entities = source.get("entities", 0)
                formatted.append(f"{i}. 知识图谱 (实体数: {entities})")
            else:
                formatted.append(f"{i}. {source_type}")
        
        return "\n".join(formatted)
        
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"格式化信息来源失败: {e}")
        return "信息来源格式化失败"


def calculate_confidence(
    retrieval_score: float,
    content_length: int, 
    entity_coverage: float,
    mode_effectiveness: float,
    additional_factors: Dict[str, float] = None
) -> float:
    """
    计算综合置信度
    
    Args:
        retrieval_score: 检索质量分数
        content_length: 内容长度
        entity_coverage: 实体覆盖度
        mode_effectiveness: 模式有效性
        additional_factors: 额外因素字典
        
    Returns:
        综合置信度分数 (0-1)
    """
    try:
        # 权重设置
        weights = {
            "retrieval": 0.35,
            "content": 0.25, 
            "entity": 0.25,
            "mode": 0.15
        }
        
        # 内容长度标准化 (基于1000字符)
        content_score = min(content_length / 1000, 1.0)
        
        # 计算基础加权平均
        confidence = (
            retrieval_score * weights["retrieval"] +
            content_score * weights["content"] +
            entity_coverage * weights["entity"] +
            mode_effectiveness * weights["mode"]
        )
        
        # 添加额外因素
        if additional_factors:
            for factor, value in additional_factors.items():
                confidence += value * 0.05  # 每个额外因素最多贡献5%
        
        return min(max(confidence, 0.0), 1.0)
        
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"计算置信度失败: {e}")
        return 0.5  # 返回中等置信度


def generate_session_id() -> str:
    """
    生成唯一的会话ID
    
    Returns:
        会话ID字符串
    """
    timestamp = datetime.now().isoformat()
    random_part = str(uuid.uuid4())[:8]
    return hashlib.md5(f"{timestamp}-{random_part}".encode()).hexdigest()[:16]


def generate_query_id() -> str:
    """
    生成唯一的查询ID
    
    Returns:
        查询ID字符串
    """
    return str(uuid.uuid4())


def validate_query(query: str, 
                  min_length: int = 3,
                  max_length: int = 1000,
                  forbidden_chars: List[str] = None) -> tuple[bool, Optional[str]]:
    """
    验证用户查询
    
    Args:
        query: 用户查询字符串
        min_length: 最小长度
        max_length: 最大长度
        forbidden_chars: 禁止字符列表
        
    Returns:
        (是否有效, 错误信息)
    """
    if not query or not query.strip():
        return False, "查询不能为空"
        
    query_trimmed = query.strip()
    
    if len(query_trimmed) < min_length:
        return False, f"查询太短，请至少输入{min_length}个字符"
        
    if len(query_trimmed) > max_length:
        return False, f"查询太长，请限制在{max_length}字符以内"
    
    # 检查禁止字符
    if forbidden_chars:
        for char in forbidden_chars:
            if char in query_trimmed:
                return False, f"查询包含禁止字符: {char}"
    
    # 检查是否包含潜在的恶意内容
    suspicious_patterns = [
        '<script>', '</script>', 
        'javascript:', 'vbscript:',
        'onload=', 'onerror=',
        'eval(', 'exec(',
        'DROP TABLE', 'DELETE FROM', 'UPDATE SET'
    ]
    
    query_lower = query_trimmed.lower()
    for pattern in suspicious_patterns:
        if pattern.lower() in query_lower:
            return False, "查询包含可疑内容，请重新输入"
    
    return True, None


def safe_json_parse(text: str, default: Dict = None) -> Dict[str, Any]:
    """
    安全的JSON解析
    
    Args:
        text: 要解析的JSON字符串
        default: 解析失败时的默认值
        
    Returns:
        解析后的字典对象
    """
    if default is None:
        default = {}
    
    if not text or not text.strip():
        return default
        
    try:
        # 尝试清理JSON字符串
        cleaned_text = text.strip()
        
        # 移除可能的代码块标记
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3]
        
        cleaned_text = cleaned_text.strip()
        
        return json.loads(cleaned_text)
        
    except (json.JSONDecodeError, TypeError) as e:
        logger = setup_logger(__name__)
        logger.warning(f"JSON解析失败: {e}, 原文本: {text[:100]}...")
        return default


def truncate_text(text: str, 
                 max_length: int = 200, 
                 suffix: str = "...",
                 preserve_words: bool = True) -> str:
    """
    截断文本
    
    Args:
        text: 原文本
        max_length: 最大长度
        suffix: 截断后缀
        preserve_words: 是否保持单词完整
        
    Returns:
        截断后的文本
    """
    if not text:
        return text
    
    if len(text) <= max_length:
        return text
    
    if preserve_words:
        # 在单词边界截断
        truncated = text[:max_length - len(suffix)]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.7:  # 如果空格位置合理
            truncated = truncated[:last_space]
    else:
        truncated = text[:max_length - len(suffix)]
    
    return truncated + suffix


def ensure_directory(path: Path) -> None:
    """
    确保目录存在
    
    Args:
        path: 目录路径
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"创建目录失败 {path}: {e}")
        raise


def get_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """
    获取文件的哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法 (md5, sha1, sha256)
        
    Returns:
        文件的哈希值
    """
    try:
        hash_func = getattr(hashlib, algorithm)()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
        
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"计算文件哈希失败 {file_path}: {e}")
        return ""


def format_timestamp(timestamp: Union[float, datetime] = None, 
                    format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: 时间戳或datetime对象
        format_str: 格式字符串
        
    Returns:
        格式化后的时间字符串
    """
    if timestamp is None:
        timestamp = datetime.now()
    elif isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp)
    
    return timestamp.strftime(format_str)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原文件名
        max_length: 最大长度
        
    Returns:
        清理后的文件名
    """
    import re
    
    # 移除非法字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # 移除控制字符
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # 截断长度
    if len(sanitized) > max_length:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized


def measure_execution_time(func):
    """
    测量函数执行时间的装饰器
    
    Args:
        func: 要测量的函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        logger = setup_logger(__name__)
        logger.debug(f"函数 {func.__name__} 执行时间: {execution_time:.3f}秒")
        
        return result
    
    return wrapper


def retry_with_exponential_backoff(max_retries: int = 3,
                                  base_delay: float = 1.0,
                                  max_delay: float = 60.0,
                                  exceptions: tuple = (Exception,)):
    """
    指数退避重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = setup_logger(__name__)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"函数 {func.__name__} 重试失败，已达到最大重试次数")
                        raise
                    
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次重试，{delay}秒后继续")
                    time.sleep(delay)
            
            return None
        
        return wrapper
    return decorator


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并字典
    
    Args:
        dict1: 基础字典
        dict2: 要合并的字典
        
    Returns:
        合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def get_nested_value(data: Dict[str, Any], 
                    key_path: str, 
                    default: Any = None,
                    separator: str = ".") -> Any:
    """
    获取嵌套字典中的值
    
    Args:
        data: 数据字典
        key_path: 键路径，用分隔符分隔
        default: 默认值
        separator: 键路径分隔符
        
    Returns:
        值或默认值
    """
    keys = key_path.split(separator)
    current = data
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def set_nested_value(data: Dict[str, Any], 
                    key_path: str, 
                    value: Any,
                    separator: str = ".") -> None:
    """
    设置嵌套字典中的值
    
    Args:
        data: 数据字典
        key_path: 键路径，用分隔符分隔
        value: 要设置的值
        separator: 键路径分隔符
    """
    keys = key_path.split(separator)
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


# 性能监控工具
class PerformanceMonitor:
    """简单的性能监控类"""
    
    def __init__(self):
        self.metrics = {}
        self.logger = setup_logger(f"{__name__}.performance")
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            "value": value,
            "timestamp": time.time(),
            "tags": tags or {}
        })
        
        self.logger.debug(f"记录指标 {name}: {value}")
    
    def get_metric_stats(self, name: str) -> Dict[str, float]:
        """获取指标统计"""
        if name not in self.metrics:
            return {}
        
        values = [m["value"] for m in self.metrics[name]]
        
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values)
        }
    
    def clear_metrics(self):
        """清空指标"""
        self.metrics.clear()
        self.logger.info("指标已清空")


# 全局性能监控器
performance_monitor = PerformanceMonitor()


def record_performance_metric(name: str, value: float, **tags):
    """记录性能指标"""
    performance_monitor.record_metric(name, value, tags)


def get_performance_stats(name: str) -> Dict[str, float]:
    """获取性能统计"""
    return performance_monitor.get_metric_stats(name)


def clear_performance_metrics():
    """清空性能指标"""
    performance_monitor.clear_metrics()