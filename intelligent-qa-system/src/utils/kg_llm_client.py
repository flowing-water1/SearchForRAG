"""
知识图谱专用LLM客户端
提供知识图谱构建和实体关系提取的LLM服务
"""

import logging
from typing import Dict, Any, List, Optional
from ..core.config import config

logger = logging.getLogger(__name__)

def create_kg_llm_func():
    """
    创建知识图谱专用LLM函数
    使用独立的KG_LLM配置，优化用于实体关系提取
    
    Returns:
        知识图谱LLM函数
    """
    def kg_llm_func(prompt: str, **kwargs) -> str:
        """
        知识图谱专用LLM函数，使用KG_LLM配置
        """
        try:
            import openai
            
            # 创建OpenAI客户端，使用KG专用配置
            client = openai.OpenAI(
                api_key=config.KG_LLM_API_KEY,
                base_url=config.KG_LLM_BASE_URL
            )
            
            # 调用LLM API
            response = client.chat.completions.create(
                model=config.KG_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.KG_LLM_TEMPERATURE,
                max_tokens=config.KG_LLM_MAX_TOKENS,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"知识图谱LLM API 调用失败: {e}")
            raise
    
    return kg_llm_func

async def extract_entities_with_kg_llm(
    text: str, 
    entity_types: List[str] = None
) -> Dict[str, List[str]]:
    """
    使用知识图谱LLM提取实体
    
    Args:
        text: 待提取的文本
        entity_types: 要提取的实体类型列表
        
    Returns:
        提取的实体字典
    """
    if entity_types is None:
        entity_types = ["公司", "技术", "人物", "地点", "产品"]
    
    kg_llm = create_kg_llm_func()
    
    prompt = f"""
请从以下文本中提取实体，按类型分类返回。

文本：
{text}

请提取以下类型的实体：
{', '.join(entity_types)}

返回JSON格式，例如：
{{
    "公司": ["Google", "Microsoft"],
    "技术": ["AI", "机器学习"],
    "人物": ["萨提亚·纳德拉"],
    "地点": ["硅谷"],
    "产品": ["ChatGPT"]
}}

只返回JSON，不要其他说明。
"""
    
    try:
        result = kg_llm(prompt)
        # 这里可以添加JSON解析和验证
        import json
        entities = json.loads(result)
        return entities
    except Exception as e:
        logger.error(f"实体提取失败: {e}")
        return {}

async def extract_relationships_with_kg_llm(
    text: str,
    entities: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """
    使用知识图谱LLM提取实体关系
    
    Args:
        text: 待分析的文本
        entities: 已识别的实体
        
    Returns:
        实体关系列表
    """
    kg_llm = create_kg_llm_func()
    
    entities_str = ""
    for entity_type, entity_list in entities.items():
        entities_str += f"{entity_type}: {', '.join(entity_list)}\n"
    
    prompt = f"""
请分析以下文本中实体之间的关系。

文本：
{text}

已识别的实体：
{entities_str}

请提取实体间的关系，返回JSON格式，例如：
[
    {{
        "主体": "Google",
        "关系": "投资",
        "客体": "OpenAI",
        "置信度": 0.9
    }},
    {{
        "主体": "萨提亚·纳德拉",
        "关系": "担任CEO",
        "客体": "Microsoft",
        "置信度": 1.0
    }}
]

只返回JSON数组，不要其他说明。
"""
    
    try:
        result = kg_llm(prompt)
        import json
        relationships = json.loads(result)
        return relationships
    except Exception as e:
        logger.error(f"关系提取失败: {e}")
        return []

def get_kg_llm_status() -> Dict[str, Any]:
    """
    获取知识图谱LLM配置状态
    
    Returns:
        配置状态字典
    """
    return {
        "kg_model": config.KG_LLM_MODEL,
        "kg_base_url": config.KG_LLM_BASE_URL,
        "kg_temperature": config.KG_LLM_TEMPERATURE,
        "kg_max_tokens": config.KG_LLM_MAX_TOKENS,
        "vector_model": config.VECTOR_LLM_MODEL,
        "vector_base_url": config.VECTOR_LLM_BASE_URL,
        "separate_configs": True
    }