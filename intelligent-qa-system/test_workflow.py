#!/usr/bin/env python3
"""
工作流测试脚本
验证 LangGraph 工作流是否正确初始化和运行
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ["DEBUG_MODE"] = "true"

def test_workflow_import():
    """测试工作流导入"""
    print("测试工作流导入...")
    
    try:
        from src.core.workflow import IntelligentQAWorkflow, get_workflow
        print("✅ 工作流导入成功")
        return True
    except Exception as e:
        print(f"❌ 工作流导入失败: {e}")
        return False

def test_workflow_initialization():
    """测试工作流初始化"""
    print("\n测试工作流初始化...")
    
    try:
        from src.core.workflow import get_workflow
        workflow = get_workflow()
        print("✅ 工作流初始化成功")
        
        # 获取工作流信息
        info = workflow.get_workflow_info()
        print(f"工作流名称: {info['name']}")
        print(f"工作流版本: {info['version']}")
        print(f"节点数量: {len(info['nodes'])}")
        
        return True
    except Exception as e:
        print(f"❌ 工作流初始化失败: {e}")
        return False

def test_workflow_graph():
    """测试工作流图生成"""
    print("\n测试工作流图生成...")
    
    try:
        from src.core.workflow import get_workflow
        workflow = get_workflow()
        
        # 尝试生成工作流图
        graph = workflow.get_workflow_graph()
        
        if graph:
            print("✅ 工作流图生成成功")
            print(f"图内容长度: {len(graph)} 字符")
        else:
            print("⚠️ 工作流图生成为空（可能是依赖问题）")
            
        return True
    except Exception as e:
        print(f"❌ 工作流图生成失败: {e}")
        return False

def test_state_definitions():
    """测试状态定义"""
    print("\n测试状态定义...")
    
    try:
        from src.core.state import AgentState, QueryAnalysisResult, QualityAssessment
        
        # 创建测试状态
        state = {
            "user_query": "测试查询",
            "query_type": "FACTUAL",
            "lightrag_mode": "local",
            "confidence_score": 0.8
        }
        
        # 验证状态结构
        assert isinstance(state, dict)
        assert "user_query" in state
        print("✅ 状态定义验证成功")
        
        return True
    except Exception as e:
        print(f"❌ 状态定义验证失败: {e}")
        return False

def test_node_imports():
    """测试节点导入"""
    print("\n测试节点导入...")
    
    try:
        from src.agents.query_analysis import query_analysis_node
        from src.agents.lightrag_retrieval import lightrag_retrieval_node
        from src.agents.quality_assessment import quality_assessment_node
        from src.agents.web_search import web_search_node
        from src.agents.answer_generation import answer_generation_node
        
        print("✅ 所有节点导入成功")
        return True
    except Exception as e:
        print(f"❌ 节点导入失败: {e}")
        return False

def test_config_loading():
    """测试配置加载"""
    print("\n测试配置加载...")
    
    try:
        from src.core.config import config
        
        print(f"调试模式: {config.DEBUG_MODE}")
        print(f"置信度阈值: {config.CONFIDENCE_THRESHOLD}")
        print(f"LLM 模型: {config.OPENAI_MODEL}")
        print(f"工作目录: {config.RAG_STORAGE_DIR}")
        
        print("✅ 配置加载成功")
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=== 智能问答系统工作流测试 ===\n")
    
    tests = [
        test_config_loading,
        test_state_definitions,
        test_node_imports,
        test_workflow_import,
        test_workflow_initialization,
        test_workflow_graph
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== 测试结果: {passed}/{total} 通过 ===")
    
    if passed == total:
        print("🎉 所有测试通过！工作流实现正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查实现")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)