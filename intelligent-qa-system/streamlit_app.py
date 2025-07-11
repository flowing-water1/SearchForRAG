"""
智能问答系统 Streamlit 前端
基于 LightRAG + LangGraph 的智能问答系统界面
"""

import streamlit as st
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

# 设置页面配置
st.set_page_config(
    page_title="智能问答系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 添加项目路径
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# 导入核心组件
try:
    from src.core.workflow import get_workflow, query_stream, get_workflow_info
    from src.core.config import config
    from src.utils.lightrag_client import initialize_lightrag, lightrag_client
    from src.utils.helpers import setup_logger
except ImportError as e:
    st.error(f"导入错误: {e}")
    st.stop()

logger = setup_logger(__name__)

# 初始化会话状态
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.chat_history = []
    st.session_state.current_query = ""
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.workflow_status = "未初始化"

def initialize_system():
    """初始化系统"""
    if not st.session_state.initialized:
        with st.spinner("正在初始化智能问答系统..."):
            try:
                # 初始化 LightRAG
                asyncio.run(initialize_lightrag())
                
                # 初始化工作流
                workflow = get_workflow()
                
                st.session_state.initialized = True
                st.session_state.workflow_status = "已初始化"
                st.success("✅ 系统初始化成功！")
                
            except Exception as e:
                st.error(f"❌ 系统初始化失败: {e}")
                st.session_state.workflow_status = f"初始化失败: {e}"

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("🤖 智能问答系统")
        
        # 系统状态
        st.subheader("系统状态")
        
        status_color = "🟢" if st.session_state.initialized else "🔴"
        st.write(f"{status_color} {st.session_state.workflow_status}")
        
        # 初始化按钮
        if st.button("🔄 重新初始化", key="reinit"):
            st.session_state.initialized = False
            st.rerun()
        
        # 系统信息
        if st.session_state.initialized:
            st.subheader("系统信息")
            
            try:
                workflow_info = get_workflow_info()
                st.write(f"**工作流**: {workflow_info['name']}")
                st.write(f"**版本**: {workflow_info['version']}")
                st.write(f"**节点数**: {len(workflow_info['nodes'])}")
                
                # 显示节点信息
                with st.expander("节点详情"):
                    for node in workflow_info['nodes']:
                        st.write(f"• **{node['name']}**: {node['description']}")
                        
            except Exception as e:
                st.error(f"获取系统信息失败: {e}")
        
        # 配置设置
        st.subheader("配置设置")
        
        # 查询模式选择
        query_mode = st.selectbox(
            "查询模式",
            ["auto", "local", "global", "hybrid"],
            index=0,
            help="auto: 自动选择最佳模式"
        )
        
        # 置信度阈值
        confidence_threshold = st.slider(
            "置信度阈值",
            0.0, 1.0, 0.6, 0.1,
            help="低于此阈值将触发网络搜索"
        )
        
        # 最大结果数
        max_results = st.slider(
            "最大搜索结果数",
            1, 10, 5, 1,
            help="网络搜索的最大结果数量"
        )
        
        # 保存配置到会话状态
        st.session_state.query_config = {
            "mode": query_mode,
            "confidence_threshold": confidence_threshold,
            "max_results": max_results
        }
        
        # 清空对话历史
        if st.button("🗑️ 清空对话历史"):
            st.session_state.chat_history = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

def render_chat_history():
    """渲染对话历史"""
    st.subheader("💬 对话历史")
    
    if not st.session_state.chat_history:
        st.info("还没有对话记录，开始提问吧！")
        return
    
    # 显示对话历史
    for i, item in enumerate(st.session_state.chat_history):
        timestamp = item.get("timestamp", "")
        
        # 用户查询
        with st.container():
            st.write(f"**👤 用户 [{timestamp}]:**")
            st.write(item["query"])
            
            # 回答
            if "answer" in item:
                st.write(f"**🤖 助手:**")
                st.write(item["answer"])
                
                # 显示来源信息
                if "sources" in item and item["sources"]:
                    with st.expander("📖 信息来源"):
                        for j, source in enumerate(item["sources"], 1):
                            if source.get("type") == "lightrag_knowledge":
                                st.write(f"{j}. **本地知识库** ({source.get('mode', 'unknown')})")
                                st.write(f"   置信度: {source.get('confidence', 0):.2f}")
                            elif source.get("type") == "web_search":
                                st.write(f"{j}. **网络搜索**: {source.get('title', '')}")
                                st.write(f"   来源: {source.get('domain', '')}")
                                st.write(f"   评分: {source.get('score', 0):.2f}")
                
                # 显示统计信息
                if "stats" in item:
                    stats = item["stats"]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("查询类型", stats.get("query_type", ""))
                    with col2:
                        st.metric("检索模式", stats.get("lightrag_mode", ""))
                    with col3:
                        st.metric("置信度", f"{stats.get('answer_confidence', 0):.2f}")
            
            elif "error" in item:
                st.error(f"❌ {item['error']}")
            
            st.divider()

def process_query_stream(query: str):
    """处理流式查询"""
    if not st.session_state.initialized:
        st.error("系统未初始化，请先初始化系统")
        return
    
    # 添加用户查询到历史
    chat_item = {
        "query": query,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "thread_id": st.session_state.thread_id
    }
    
    # 创建状态容器
    status_container = st.container()
    answer_container = st.container()
    
    # 执行流式查询
    try:
        with status_container:
            st.write("🔄 **处理中...**")
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # 获取配置
        config_override = st.session_state.get("query_config", {})
        
        # 流式执行
        step_count = 0
        total_steps = 5  # 预估总步数
        final_result = None
        
        workflow = get_workflow()
        
        for step in workflow.stream(
            query, 
            config_override=config_override,
            thread_id=st.session_state.thread_id
        ):
            step_count += 1
            progress = min(step_count / total_steps, 1.0)
            progress_bar.progress(progress)
            
            # 更新状态信息
            node_name = list(step.keys())[0] if step else "处理中"
            node_names = {
                "query_analysis": "查询分析",
                "lightrag_retrieval": "知识检索",
                "quality_assessment": "质量评估",
                "web_search": "网络搜索",
                "answer_generation": "答案生成"
            }
            
            display_name = node_names.get(node_name, node_name)
            status_text.text(f"正在执行: {display_name}")
            
            # 保存最终结果
            if step:
                final_result = list(step.values())[0]
        
        # 处理最终结果
        if final_result:
            # 清空状态容器
            status_container.empty()
            
            # 显示答案
            with answer_container:
                st.write("**🤖 回答:**")
                st.write(final_result.get("final_answer", "未能生成答案"))
                
                # 保存到对话历史
                chat_item.update({
                    "answer": final_result.get("final_answer", ""),
                    "sources": final_result.get("sources", []),
                    "stats": {
                        "query_type": final_result.get("query_type", ""),
                        "lightrag_mode": final_result.get("lightrag_mode_used", ""),
                        "answer_confidence": final_result.get("answer_confidence", 0.0),
                        "context_used": final_result.get("context_used", 0),
                        "generation_time": final_result.get("generation_time", 0.0)
                    }
                })
        else:
            chat_item["error"] = "未能获取查询结果"
    
    except Exception as e:
        logger.error(f"查询处理失败: {e}")
        status_container.empty()
        answer_container.error(f"❌ 查询处理失败: {e}")
        chat_item["error"] = str(e)
    
    # 添加到对话历史
    st.session_state.chat_history.append(chat_item)

def render_main_interface():
    """渲染主界面"""
    st.title("🤖 智能问答系统")
    st.markdown("基于 **LightRAG + LangGraph** 的智能问答系统")
    
    # 系统状态检查
    if not st.session_state.initialized:
        st.warning("⚠️ 系统未初始化，请先在侧边栏点击初始化按钮")
        return
    
    # 查询输入
    with st.form("query_form", clear_on_submit=True):
        st.subheader("💭 请输入您的问题")
        
        # 查询输入框
        query = st.text_area(
            "问题",
            height=100,
            placeholder="例如：什么是机器学习？机器学习的发展趋势如何？",
            label_visibility="collapsed"
        )
        
        # 提交按钮
        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("🚀 提交问题", use_container_width=True)
        with col2:
            if st.form_submit_button("💡 示例问题", use_container_width=True):
                examples = [
                    "什么是深度学习？",
                    "机器学习与人工智能的关系是什么？",
                    "分析当前AI技术的发展趋势和挑战",
                    "比较监督学习和无监督学习的优缺点"
                ]
                st.info("示例问题：\n" + "\n".join(f"• {ex}" for ex in examples))
        
        # 处理提交
        if submitted and query.strip():
            st.session_state.current_query = query.strip()
            
            # 处理查询
            process_query_stream(query.strip())
    
    # 显示对话历史
    render_chat_history()

def render_system_monitor():
    """渲染系统监控页面"""
    st.title("📊 系统监控")
    
    if not st.session_state.initialized:
        st.warning("系统未初始化")
        return
    
    # 系统状态
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("系统状态", "正常运行" if st.session_state.initialized else "未初始化")
    
    with col2:
        st.metric("对话数量", len(st.session_state.chat_history))
    
    with col3:
        st.metric("当前线程", st.session_state.thread_id[:8])
    
    # LightRAG 状态
    st.subheader("LightRAG 状态")
    try:
        status = lightrag_client.get_status()
        
        col1, col2 = st.columns(2)
        with col1:
            st.json({
                "初始化状态": status.get("initialized", False),
                "工作目录": status.get("working_dir", ""),
                "支持模式": status.get("supported_modes", [])
            })
        
        with col2:
            st.json({
                "PostgreSQL": status.get("pgvector_available", False),
                "Neo4j": status.get("neo4j_available", False)
            })
    except Exception as e:
        st.error(f"获取状态失败: {e}")
    
    # 工作流信息
    st.subheader("工作流信息")
    try:
        workflow_info = get_workflow_info()
        st.json(workflow_info)
    except Exception as e:
        st.error(f"获取工作流信息失败: {e}")

def main():
    """主函数"""
    # 渲染侧边栏
    render_sidebar()
    
    # 系统初始化
    initialize_system()
    
    # 页面导航
    tab1, tab2 = st.tabs(["💬 智能问答", "📊 系统监控"])
    
    with tab1:
        render_main_interface()
    
    with tab2:
        render_system_monitor()

if __name__ == "__main__":
    main()