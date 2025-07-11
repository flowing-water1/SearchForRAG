"""
智能问答系统完整 Streamlit 应用
集成所有功能模块的主应用程序
"""

import streamlit as st
import asyncio
import json
import time
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import os
from pathlib import Path

# 设置页面配置
st.set_page_config(
    page_title="智能问答系统 - LightRAG + LangGraph",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': 'https://github.com/your-repo/issues',
        'About': "# 智能问答系统\n基于 LightRAG + LangGraph 构建的智能问答系统"
    }
)

# 设置样式
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e1e5e9;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .chat-message {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    .error-message {
        background: #fee;
        border-left: 4px solid #f56565;
    }
    .success-message {
        background: #f0fff4;
        border-left: 4px solid #48bb78;
    }
</style>
""", unsafe_allow_html=True)

# 添加项目路径
sys_path = str(Path(__file__).parent)
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

# 导入核心组件
try:
    from src.core.workflow import get_workflow, query_stream, get_workflow_info
    from src.core.config import config
    from src.utils.lightrag_client import initialize_lightrag, lightrag_client
    from src.utils.helpers import setup_logger
    from src.frontend.streaming_interface import render_advanced_interface
    
    logger = setup_logger(__name__)
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    st.error(f"导入模块失败: {e}")
    st.error("请确保已安装所有依赖包：pip install -r requirements.txt")
    IMPORTS_SUCCESSFUL = False

# 初始化会话状态
def initialize_session_state():
    """初始化会话状态"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
        st.session_state.chat_history = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.workflow_status = "未初始化"
        st.session_state.system_stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_response_time': 0,
            'last_query_time': None
        }
        st.session_state.query_config = {
            'mode': 'auto',
            'confidence_threshold': 0.6,
            'max_results': 5
        }

async def initialize_system():
    """异步初始化系统"""
    if not st.session_state.initialized:
        try:
            # 显示初始化进度
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 步骤1: 初始化 LightRAG
            status_text.text("正在初始化 LightRAG...")
            progress_bar.progress(0.3)
            await initialize_lightrag()
            
            # 步骤2: 初始化工作流
            status_text.text("正在初始化工作流...")
            progress_bar.progress(0.6)
            workflow = get_workflow()
            
            # 步骤3: 验证系统状态
            status_text.text("正在验证系统状态...")
            progress_bar.progress(0.8)
            
            # 检查各组件状态
            lightrag_status = lightrag_client.get_status()
            workflow_info = get_workflow_info()
            
            # 步骤4: 完成初始化
            status_text.text("初始化完成！")
            progress_bar.progress(1.0)
            
            st.session_state.initialized = True
            st.session_state.workflow_status = "已初始化"
            st.session_state.lightrag_status = lightrag_status
            st.session_state.workflow_info = workflow_info
            
            # 清空进度显示
            progress_bar.empty()
            status_text.empty()
            
            return True
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            st.error(f"❌ 系统初始化失败: {e}")
            st.session_state.workflow_status = f"初始化失败: {e}"
            return False
    return True

def render_header():
    """渲染页面头部"""
    st.markdown("""
    <div class="main-header">
        <h1>🤖 智能问答系统</h1>
        <p>基于 LightRAG + LangGraph 的下一代智能问答系统</p>
    </div>
    """, unsafe_allow_html=True)

def render_system_status():
    """渲染系统状态"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_color = "🟢" if st.session_state.initialized else "🔴"
        st.metric("系统状态", f"{status_color} {'在线' if st.session_state.initialized else '离线'}")
    
    with col2:
        stats = st.session_state.system_stats
        st.metric("总查询数", stats['total_queries'])
    
    with col3:
        success_rate = 0
        if stats['total_queries'] > 0:
            success_rate = (stats['successful_queries'] / stats['total_queries']) * 100
        st.metric("成功率", f"{success_rate:.1f}%")
    
    with col4:
        st.metric("平均响应时间", f"{stats['avg_response_time']:.1f}s")

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("🔧 控制面板")
        
        # 系统控制
        st.subheader("系统控制")
        
        if not st.session_state.initialized:
            if st.button("🚀 初始化系统", use_container_width=True):
                with st.spinner("正在初始化..."):
                    success = asyncio.run(initialize_system())
                    if success:
                        st.success("✅ 系统初始化成功！")
                        st.rerun()
        else:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 重启系统", use_container_width=True):
                    st.session_state.initialized = False
                    st.rerun()
            with col2:
                if st.button("🗑️ 清空历史", use_container_width=True):
                    st.session_state.chat_history = []
                    st.session_state.thread_id = str(uuid.uuid4())
                    st.rerun()
        
        # 配置设置
        st.subheader("配置设置")
        
        # 查询模式
        mode = st.selectbox(
            "查询模式",
            ["auto", "local", "global", "hybrid"],
            index=0,
            help="auto: 自动选择最佳模式\nlocal: 本地向量检索\nglobal: 全局图检索\nhybrid: 混合检索"
        )
        
        # 置信度阈值
        threshold = st.slider(
            "置信度阈值",
            0.0, 1.0, 0.6, 0.1,
            help="低于此阈值将触发网络搜索"
        )
        
        # 最大结果数
        max_results = st.slider(
            "最大搜索结果",
            1, 10, 5, 1,
            help="网络搜索的最大结果数量"
        )
        
        # 保存配置
        st.session_state.query_config = {
            'mode': mode,
            'confidence_threshold': threshold,
            'max_results': max_results
        }
        
        # 高级设置
        with st.expander("高级设置"):
            debug_mode = st.checkbox("调试模式", value=False)
            stream_mode = st.checkbox("流式输出", value=True)
            show_sources = st.checkbox("显示来源", value=True)
            
            st.session_state.advanced_settings = {
                'debug_mode': debug_mode,
                'stream_mode': stream_mode,
                'show_sources': show_sources
            }
        
        # 系统信息
        if st.session_state.initialized:
            st.subheader("系统信息")
            
            with st.expander("LightRAG 状态"):
                status = st.session_state.get('lightrag_status', {})
                st.json(status)
            
            with st.expander("工作流信息"):
                info = st.session_state.get('workflow_info', {})
                st.json(info)

def process_query(query: str) -> Dict[str, Any]:
    """处理查询请求"""
    start_time = time.time()
    
    try:
        # 更新统计
        st.session_state.system_stats['total_queries'] += 1
        
        # 获取配置
        config_override = st.session_state.query_config.copy()
        advanced_settings = st.session_state.get('advanced_settings', {})
        
        # 执行查询
        workflow = get_workflow()
        result = workflow.run(
            query, 
            config_override=config_override,
            thread_id=st.session_state.thread_id
        )
        
        # 计算处理时间
        processing_time = time.time() - start_time
        
        # 更新统计
        st.session_state.system_stats['successful_queries'] += 1
        st.session_state.system_stats['avg_response_time'] = (
            st.session_state.system_stats['avg_response_time'] + processing_time
        ) / 2
        st.session_state.system_stats['last_query_time'] = datetime.now()
        
        return {
            'success': True,
            'result': result,
            'processing_time': processing_time
        }
        
    except Exception as e:
        logger.error(f"查询处理失败: {e}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        
        # 更新统计
        st.session_state.system_stats['failed_queries'] += 1
        
        return {
            'success': False,
            'error': str(e),
            'processing_time': time.time() - start_time
        }

def render_chat_interface():
    """渲染聊天界面"""
    st.subheader("💬 智能对话")
    
    # 查询输入
    with st.form("query_form", clear_on_submit=True):
        query = st.text_area(
            "请输入您的问题:",
            height=100,
            placeholder="例如：什么是机器学习？机器学习与深度学习的区别是什么？",
            help="支持事实性查询、关系性查询和分析性查询"
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            submitted = st.form_submit_button("🚀 提交", use_container_width=True)
        
        with col2:
            if st.form_submit_button("💡 示例", use_container_width=True):
                examples = [
                    "什么是人工智能？",
                    "机器学习与深度学习的关系",
                    "分析当前AI技术的发展趋势",
                    "比较监督学习和无监督学习"
                ]
                
                with st.expander("示例问题", expanded=True):
                    for example in examples:
                        if st.button(f"📝 {example}", key=f"example_{example}"):
                            st.session_state.example_query = example
                            st.rerun()
        
        with col3:
            st.write("")  # 占位符
        
        # 处理提交
        if submitted and query.strip():
            if not st.session_state.initialized:
                st.error("⚠️ 请先初始化系统")
            else:
                # 显示处理状态
                with st.spinner("🔄 正在处理您的问题..."):
                    result = process_query(query.strip())
                
                # 添加到对话历史
                chat_item = {
                    'query': query.strip(),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'thread_id': st.session_state.thread_id,
                    'processing_time': result['processing_time']
                }
                
                if result['success']:
                    chat_item.update({
                        'answer': result['result'].get('final_answer', ''),
                        'sources': result['result'].get('sources', []),
                        'stats': {
                            'query_type': result['result'].get('query_type', ''),
                            'lightrag_mode': result['result'].get('lightrag_mode_used', ''),
                            'answer_confidence': result['result'].get('answer_confidence', 0.0),
                            'context_used': result['result'].get('context_used', 0)
                        }
                    })
                else:
                    chat_item['error'] = result['error']
                
                st.session_state.chat_history.append(chat_item)
                st.rerun()

def render_chat_history():
    """渲染对话历史"""
    if not st.session_state.chat_history:
        st.info("💭 开始您的第一个问题吧！")
        return
    
    st.subheader("📚 对话历史")
    
    # 显示对话
    for i, item in enumerate(reversed(st.session_state.chat_history)):
        with st.container():
            st.markdown(f"""
            <div class="chat-message">
                <h4>👤 用户 [{item['timestamp']}]</h4>
                <p>{item['query']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 显示回答或错误
            if 'answer' in item:
                st.markdown(f"""
                <div class="chat-message success-message">
                    <h4>🤖 助手</h4>
                    <p>{item['answer']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 显示统计信息
                if 'stats' in item:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("查询类型", item['stats']['query_type'])
                    with col2:
                        st.metric("检索模式", item['stats']['lightrag_mode'])
                    with col3:
                        st.metric("置信度", f"{item['stats']['answer_confidence']:.2f}")
                    with col4:
                        st.metric("处理时间", f"{item['processing_time']:.1f}s")
                
                # 显示来源
                if st.session_state.get('advanced_settings', {}).get('show_sources', True):
                    if 'sources' in item and item['sources']:
                        with st.expander("📖 信息来源"):
                            for j, source in enumerate(item['sources'], 1):
                                if source.get('type') == 'lightrag_knowledge':
                                    st.write(f"**{j}. 本地知识库** ({source.get('mode', 'unknown')})")
                                    st.write(f"置信度: {source.get('confidence', 0):.2f}")
                                elif source.get('type') == 'web_search':
                                    st.write(f"**{j}. 网络搜索**: {source.get('title', '')}")
                                    st.write(f"来源: {source.get('domain', '')}")
                                    st.write(f"相关度: {source.get('score', 0):.2f}")
            
            elif 'error' in item:
                st.markdown(f"""
                <div class="chat-message error-message">
                    <h4>❌ 错误</h4>
                    <p>{item['error']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")

def main():
    """主函数"""
    # 检查导入状态
    if not IMPORTS_SUCCESSFUL:
        st.stop()
    
    # 初始化会话状态
    initialize_session_state()
    
    # 渲染页面头部
    render_header()
    
    # 渲染系统状态
    render_system_status()
    
    # 渲染侧边栏
    render_sidebar()
    
    # 主要内容区域
    if st.session_state.initialized:
        # 创建标签页
        tab1, tab2, tab3 = st.tabs(["💬 智能对话", "🔄 高级功能", "📊 系统监控"])
        
        with tab1:
            render_chat_interface()
            render_chat_history()
        
        with tab2:
            render_advanced_interface()
        
        with tab3:
            st.subheader("📊 系统监控")
            
            # 系统状态详情
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("LightRAG 状态")
                if 'lightrag_status' in st.session_state:
                    st.json(st.session_state.lightrag_status)
            
            with col2:
                st.subheader("工作流状态")
                if 'workflow_info' in st.session_state:
                    st.json(st.session_state.workflow_info)
            
            # 系统统计
            st.subheader("系统统计")
            stats = st.session_state.system_stats
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总查询数", stats['total_queries'])
                st.metric("成功查询", stats['successful_queries'])
            with col2:
                st.metric("失败查询", stats['failed_queries'])
                success_rate = 0
                if stats['total_queries'] > 0:
                    success_rate = (stats['successful_queries'] / stats['total_queries']) * 100
                st.metric("成功率", f"{success_rate:.1f}%")
            with col3:
                st.metric("平均响应时间", f"{stats['avg_response_time']:.1f}s")
                if stats['last_query_time']:
                    st.metric("最后查询时间", stats['last_query_time'].strftime("%H:%M:%S"))
    
    else:
        # 系统未初始化
        st.warning("⚠️ 系统未初始化，请在侧边栏点击'初始化系统'按钮")
        
        # 显示系统要求
        st.subheader("系统要求")
        st.markdown("""
        在使用本系统前，请确保：
        
        1. **环境配置**: 已正确配置 `.env` 文件
        2. **API 密钥**: 已配置 OpenAI API 密钥和 Tavily API 密钥
        3. **数据库**: PostgreSQL 和 Neo4j 数据库已正确配置
        4. **依赖包**: 已安装所有必要的依赖包
        
        ```bash
        pip install -r requirements.txt
        ```
        """)

if __name__ == "__main__":
    main()