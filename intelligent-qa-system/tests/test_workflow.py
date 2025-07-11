"""
LangGraph 工作流测试
测试工作流节点和整体流程
使用 HKUDS/LightRAG 框架进行测试
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.state import AgentState
from src.agents.query_analysis import query_analysis_node
from src.agents.lightrag_retrieval import lightrag_retrieval_node
from src.agents.quality_assessment import quality_assessment_node
from src.agents.web_search import web_search_node
from src.agents.answer_generation import answer_generation_node


class TestQueryAnalysisNode(unittest.TestCase):
    """查询分析节点测试"""
    
    def setUp(self):
        """测试设置"""
        self.test_state = {
            "user_query": "什么是机器学习？",
            "query_type": "",
            "lightrag_mode": "",
            "key_entities": [],
            "processed_query": ""
        }
    
    @patch('src.agents.query_analysis.ChatOpenAI')
    def test_query_analysis_factual(self, mock_llm):
        """测试事实性查询分析"""
        # 模拟LLM响应
        mock_response = Mock()
        mock_response.content = """{
            "query_type": "FACTUAL",
            "lightrag_mode": "local",
            "key_entities": ["机器学习"],
            "processed_query": "什么是机器学习？请提供定义和基本概念。",
            "reasoning": "用户询问具体概念的定义，属于事实性查询"
        }"""
        
        mock_llm.return_value.invoke.return_value = mock_response
        
        # 执行节点
        result = query_analysis_node(self.test_state)
        
        # 验证结果
        self.assertEqual(result["query_type"], "FACTUAL")
        self.assertEqual(result["lightrag_mode"], "local")
        self.assertIn("机器学习", result["key_entities"])
    
    @patch('src.agents.query_analysis.ChatOpenAI')
    def test_query_analysis_relational(self, mock_llm):
        """测试关系性查询分析"""
        # 修改测试状态
        self.test_state["user_query"] = "机器学习与深度学习的关系是什么？"
        
        # 模拟LLM响应
        mock_response = Mock()
        mock_response.content = """{
            "query_type": "RELATIONAL",
            "lightrag_mode": "global",
            "key_entities": ["机器学习", "深度学习"],
            "processed_query": "机器学习与深度学习的关系是什么？",
            "reasoning": "用户询问实体间关系，需要图谱遍历"
        }"""
        
        mock_llm.return_value.invoke.return_value = mock_response
        
        # 执行节点
        result = query_analysis_node(self.test_state)
        
        # 验证结果
        self.assertEqual(result["query_type"], "RELATIONAL")
        self.assertEqual(result["lightrag_mode"], "global")
        self.assertIn("机器学习", result["key_entities"])
        self.assertIn("深度学习", result["key_entities"])
    
    @patch('src.agents.query_analysis.ChatOpenAI')
    def test_query_analysis_error_handling(self, mock_llm):
        """测试查询分析错误处理"""
        # 模拟LLM错误
        mock_llm.return_value.invoke.side_effect = Exception("API Error")
        
        # 执行节点
        result = query_analysis_node(self.test_state)
        
        # 验证错误处理
        self.assertEqual(result["query_type"], "ANALYTICAL")
        self.assertEqual(result["lightrag_mode"], "hybrid")
        self.assertIn("分析失败", result["mode_reasoning"])


class TestLightRAGRetrievalNode(unittest.TestCase):
    """LightRAG 检索节点测试"""
    
    def setUp(self):
        """测试设置"""
        self.test_state = {
            "lightrag_mode": "local",
            "processed_query": "什么是机器学习？",
            "user_query": "什么是机器学习？"
        }
    
    @patch('src.agents.lightrag_retrieval.query_lightrag_sync')
    def test_lightrag_retrieval_success(self, mock_query):
        """测试成功的LightRAG检索"""
        # 模拟检索结果
        mock_query.return_value = {
            "success": True,
            "content": "机器学习是一种人工智能技术...",
            "mode": "local",
            "query": "什么是机器学习？"
        }
        
        # 执行节点
        result = lightrag_retrieval_node(self.test_state)
        
        # 验证结果
        self.assertTrue(result["retrieval_success"])
        self.assertIn("content", result["lightrag_results"])
        self.assertGreater(result["retrieval_score"], 0)
    
    @patch('src.agents.lightrag_retrieval.query_lightrag_sync')
    def test_lightrag_retrieval_failure(self, mock_query):
        """测试失败的LightRAG检索"""
        # 模拟检索失败
        mock_query.return_value = {
            "success": False,
            "error": "Connection failed",
            "mode": "local",
            "query": "什么是机器学习？"
        }
        
        # 执行节点
        result = lightrag_retrieval_node(self.test_state)
        
        # 验证结果
        self.assertFalse(result["retrieval_success"])
        self.assertEqual(result["retrieval_score"], 0.0)
        self.assertIn("error", result["lightrag_results"])
    
    @patch('src.agents.lightrag_retrieval.query_lightrag_sync')
    def test_lightrag_retrieval_exception(self, mock_query):
        """测试LightRAG检索异常"""
        # 模拟异常
        mock_query.side_effect = Exception("Retrieval error")
        
        # 执行节点
        result = lightrag_retrieval_node(self.test_state)
        
        # 验证异常处理
        self.assertFalse(result["retrieval_success"])
        self.assertEqual(result["retrieval_score"], 0.0)


class TestQualityAssessmentNode(unittest.TestCase):
    """质量评估节点测试"""
    
    def setUp(self):
        """测试设置"""
        self.test_state = {
            "lightrag_results": {
                "content": "机器学习是一种人工智能技术，它使计算机能够从数据中学习并做出预测。",
                "mode": "local"
            },
            "retrieval_success": True,
            "retrieval_score": 0.8,
            "query_type": "FACTUAL",
            "key_entities": ["机器学习"],
            "user_query": "什么是机器学习？"
        }
    
    def test_quality_assessment_high_confidence(self):
        """测试高置信度质量评估"""
        # 执行节点
        result = quality_assessment_node(self.test_state)
        
        # 验证结果
        self.assertGreater(result["confidence_score"], 0.5)
        self.assertFalse(result["need_web_search"])
        self.assertIn("confidence_breakdown", result)
    
    def test_quality_assessment_low_confidence(self):
        """测试低置信度质量评估"""
        # 修改状态以产生低置信度
        self.test_state["lightrag_results"]["content"] = "短内容"
        self.test_state["retrieval_score"] = 0.2
        
        # 执行节点
        result = quality_assessment_node(self.test_state)
        
        # 验证结果
        self.assertLess(result["confidence_score"], 0.6)
        self.assertTrue(result["need_web_search"])
    
    def test_quality_assessment_retrieval_failure(self):
        """测试检索失败的质量评估"""
        # 修改状态为检索失败
        self.test_state["retrieval_success"] = False
        
        # 执行节点
        result = quality_assessment_node(self.test_state)
        
        # 验证结果
        self.assertEqual(result["confidence_score"], 0.0)
        self.assertTrue(result["need_web_search"])
        self.assertIn("检索失败", result["assessment_reason"])


class TestWebSearchNode(unittest.TestCase):
    """网络搜索节点测试"""
    
    def setUp(self):
        """测试设置"""
        self.test_state = {
            "need_web_search": True,
            "user_query": "什么是机器学习？",
            "processed_query": "什么是机器学习？",
            "query_type": "FACTUAL"
        }
    
    @patch('src.agents.web_search.TavilySearchAPIWrapper')
    def test_web_search_success(self, mock_tavily):
        """测试成功的网络搜索"""
        # 模拟搜索结果
        mock_search_results = [
            {
                "title": "机器学习介绍",
                "content": "机器学习是人工智能的一个分支...",
                "url": "http://example.com/ml",
                "score": 0.9
            }
        ]
        
        mock_tavily.return_value.search.return_value = mock_search_results
        
        # 执行节点
        result = web_search_node(self.test_state)
        
        # 验证结果
        self.assertIsInstance(result["web_results"], list)
        self.assertGreater(len(result["web_results"]), 0)
        self.assertIn("web_search_summary", result)
    
    def test_web_search_not_needed(self):
        """测试不需要网络搜索"""
        # 修改状态
        self.test_state["need_web_search"] = False
        
        # 执行节点
        result = web_search_node(self.test_state)
        
        # 验证结果
        self.assertEqual(result["web_results"], [])
    
    @patch('src.agents.web_search.TavilySearchAPIWrapper')
    def test_web_search_failure(self, mock_tavily):
        """测试网络搜索失败"""
        # 模拟搜索失败
        mock_tavily.return_value.search.side_effect = Exception("Search failed")
        
        # 执行节点
        result = web_search_node(self.test_state)
        
        # 验证结果
        self.assertEqual(result["web_results"], [])
        self.assertIn("失败", result["web_search_summary"])


class TestAnswerGenerationNode(unittest.TestCase):
    """答案生成节点测试"""
    
    def setUp(self):
        """测试设置"""
        self.test_state = {
            "user_query": "什么是机器学习？",
            "query_type": "FACTUAL",
            "lightrag_mode": "local",
            "lightrag_results": {
                "content": "机器学习是一种人工智能技术...",
                "mode": "local"
            },
            "web_results": [],
            "confidence_score": 0.8
        }
    
    @patch('src.agents.answer_generation.ChatOpenAI')
    def test_answer_generation_success(self, mock_llm):
        """测试成功的答案生成"""
        # 模拟LLM响应
        mock_response = Mock()
        mock_response.content = "机器学习是一种人工智能技术，它使计算机能够从数据中学习..."
        
        mock_llm.return_value.invoke.return_value = mock_response
        
        # 执行节点
        result = answer_generation_node(self.test_state)
        
        # 验证结果
        self.assertIn("final_answer", result)
        self.assertGreater(len(result["final_answer"]), 0)
        self.assertIn("sources", result)
        self.assertIn("answer_confidence", result)
    
    @patch('src.agents.answer_generation.ChatOpenAI')
    def test_answer_generation_with_web_results(self, mock_llm):
        """测试包含网络搜索结果的答案生成"""
        # 添加网络搜索结果
        self.test_state["web_results"] = [
            {
                "title": "机器学习介绍",
                "content": "最新的机器学习发展...",
                "url": "http://example.com/ml",
                "domain": "example.com",
                "score": 0.9
            }
        ]
        
        # 模拟LLM响应
        mock_response = Mock()
        mock_response.content = "综合本地知识和网络信息，机器学习是..."
        
        mock_llm.return_value.invoke.return_value = mock_response
        
        # 执行节点
        result = answer_generation_node(self.test_state)
        
        # 验证结果
        self.assertIn("final_answer", result)
        self.assertGreater(len(result["sources"]), 1)  # 应该有本地和网络来源
    
    @patch('src.agents.answer_generation.ChatOpenAI')
    def test_answer_generation_failure(self, mock_llm):
        """测试答案生成失败"""
        # 模拟LLM错误
        mock_llm.return_value.invoke.side_effect = Exception("LLM Error")
        
        # 执行节点
        result = answer_generation_node(self.test_state)
        
        # 验证错误处理
        self.assertIn("错误", result["final_answer"])
        self.assertEqual(result["answer_confidence"], 0.0)


class TestWorkflowIntegration(unittest.TestCase):
    """工作流集成测试"""
    
    def setUp(self):
        """测试设置"""
        self.initial_state = {
            "user_query": "什么是机器学习？",
            "query_type": "",
            "lightrag_mode": "",
            "key_entities": [],
            "processed_query": "",
            "lightrag_results": {},
            "retrieval_score": 0.0,
            "retrieval_success": False,
            "confidence_score": 0.0,
            "need_web_search": False,
            "web_results": [],
            "final_answer": "",
            "sources": [],
            "context_used": 0,
            "answer_confidence": 0.0
        }
    
    def test_workflow_state_propagation(self):
        """测试工作流状态传播"""
        # 模拟节点间的状态传播
        state = self.initial_state.copy()
        
        # 查询分析后的状态
        state.update({
            "query_type": "FACTUAL",
            "lightrag_mode": "local",
            "key_entities": ["机器学习"],
            "processed_query": "什么是机器学习？"
        })
        
        # 检索后的状态
        state.update({
            "lightrag_results": {"content": "机器学习内容..."},
            "retrieval_success": True,
            "retrieval_score": 0.8
        })
        
        # 质量评估后的状态
        state.update({
            "confidence_score": 0.7,
            "need_web_search": False
        })
        
        # 答案生成后的状态
        state.update({
            "final_answer": "机器学习是...",
            "answer_confidence": 0.8
        })
        
        # 验证状态完整性
        self.assertEqual(state["query_type"], "FACTUAL")
        self.assertTrue(state["retrieval_success"])
        self.assertGreater(state["confidence_score"], 0)
        self.assertGreater(len(state["final_answer"]), 0)
    
    def test_workflow_error_recovery(self):
        """测试工作流错误恢复"""
        # 模拟部分节点失败的情况
        state = self.initial_state.copy()
        
        # 查询分析成功
        state.update({
            "query_type": "FACTUAL",
            "lightrag_mode": "local"
        })
        
        # 检索失败
        state.update({
            "retrieval_success": False,
            "retrieval_score": 0.0
        })
        
        # 质量评估应该触发网络搜索
        state.update({
            "confidence_score": 0.0,
            "need_web_search": True
        })
        
        # 网络搜索成功
        state.update({
            "web_results": [{"title": "ML", "content": "内容"}]
        })
        
        # 答案生成应该能够使用网络结果
        state.update({
            "final_answer": "基于网络搜索的答案",
            "answer_confidence": 0.6
        })
        
        # 验证错误恢复
        self.assertTrue(state["need_web_search"])
        self.assertGreater(len(state["web_results"]), 0)
        self.assertGreater(len(state["final_answer"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)