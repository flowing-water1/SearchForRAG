"""
高级流式界面组件
提供实时更新、进度跟踪和交互式显示
"""

import streamlit as st
import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Iterator
from datetime import datetime
import threading
from queue import Queue, Empty

class StreamingInterface:
    """流式界面管理器"""
    
    def __init__(self):
        self.is_streaming = False
        self.stream_queue = Queue()
        self.current_step = ""
        self.progress = 0.0
        
    def start_stream(self, query: str, config: Dict[str, Any] = None):
        """开始流式处理"""
        self.is_streaming = True
        self.progress = 0.0
        
        # 创建流式处理线程
        thread = threading.Thread(
            target=self._stream_worker,
            args=(query, config or {}),
            daemon=True
        )
        thread.start()
    
    def _stream_worker(self, query: str, config: Dict[str, Any]):
        """流式处理工作线程"""
        try:
            from src.core.workflow import get_workflow
            
            workflow = get_workflow()
            step_count = 0
            
            for step in workflow.stream(query, config_override=config):
                step_count += 1
                self.progress = min(step_count / 5, 1.0)  # 假设5个步骤
                
                # 将步骤结果放入队列
                self.stream_queue.put({
                    "type": "step",
                    "step": step,
                    "progress": self.progress,
                    "step_count": step_count
                })
                
                # 更新当前步骤
                if step:
                    node_name = list(step.keys())[0]
                    self.current_step = node_name
            
            # 处理完成
            self.stream_queue.put({
                "type": "complete",
                "progress": 1.0
            })
            
        except Exception as e:
            self.stream_queue.put({
                "type": "error",
                "error": str(e)
            })
        
        finally:
            self.is_streaming = False
    
    def get_stream_updates(self) -> List[Dict[str, Any]]:
        """获取流式更新"""
        updates = []
        
        while not self.stream_queue.empty():
            try:
                update = self.stream_queue.get_nowait()
                updates.append(update)
            except Empty:
                break
        
        return updates

def render_streaming_query_interface():
    """渲染流式查询界面"""
    st.subheader("🔄 实时查询处理")
    
    # 初始化流式接口
    if 'streaming_interface' not in st.session_state:
        st.session_state.streaming_interface = StreamingInterface()
    
    streaming = st.session_state.streaming_interface
    
    # 查询输入
    with st.form("streaming_query_form"):
        query = st.text_area(
            "输入您的问题",
            height=80,
            placeholder="例如：解释机器学习的基本概念..."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("🚀 开始处理", disabled=streaming.is_streaming)
        with col2:
            if st.form_submit_button("⏹️ 停止处理", disabled=not streaming.is_streaming):
                streaming.is_streaming = False
    
    # 处理查询提交
    if submitted and query.strip() and not streaming.is_streaming:
        config = st.session_state.get("query_config", {})
        streaming.start_stream(query.strip(), config)
        st.rerun()
    
    # 显示流式处理状态
    if streaming.is_streaming or streaming.progress > 0:
        render_streaming_status(streaming)

def render_streaming_status(streaming: StreamingInterface):
    """渲染流式处理状态"""
    
    # 进度显示
    progress_container = st.container()
    with progress_container:
        st.write("**处理进度:**")
        progress_bar = st.progress(streaming.progress)
        
        # 步骤名称映射
        step_names = {
            "query_analysis": "🔍 分析查询",
            "lightrag_retrieval": "📚 检索知识",
            "quality_assessment": "✅ 评估质量",
            "web_search": "🌐 网络搜索",
            "answer_generation": "💬 生成答案"
        }
        
        current_step_name = step_names.get(streaming.current_step, streaming.current_step)
        st.write(f"当前步骤: {current_step_name}")
    
    # 实时更新
    updates = streaming.get_stream_updates()
    
    # 结果显示容器
    result_container = st.container()
    
    for update in updates:
        if update["type"] == "step":
            # 更新进度
            progress_bar.progress(update["progress"])
            
            # 显示步骤详情
            step_data = update["step"]
            if step_data:
                node_name = list(step_data.keys())[0]
                node_data = step_data[node_name]
                
                # 显示节点执行结果
                with st.expander(f"步骤 {update['step_count']}: {step_names.get(node_name, node_name)}"):
                    st.json(node_data)
        
        elif update["type"] == "complete":
            # 处理完成
            with result_container:
                st.success("✅ 处理完成！")
                progress_bar.progress(1.0)
        
        elif update["type"] == "error":
            # 处理错误
            with result_container:
                st.error(f"❌ 处理失败: {update['error']}")
    
    # 自动刷新
    if streaming.is_streaming:
        time.sleep(0.5)
        st.rerun()

def render_interactive_workflow_diagram():
    """渲染交互式工作流图"""
    st.subheader("🔄 工作流程图")
    
    # 工作流步骤
    steps = [
        {"name": "查询分析", "icon": "🔍", "description": "分析查询类型，选择检索模式"},
        {"name": "知识检索", "icon": "📚", "description": "使用LightRAG进行智能检索"},
        {"name": "质量评估", "icon": "✅", "description": "评估检索结果质量"},
        {"name": "网络搜索", "icon": "🌐", "description": "补充网络信息（条件性）"},
        {"name": "答案生成", "icon": "💬", "description": "生成最终答案"}
    ]
    
    # 创建交互式流程图
    cols = st.columns(len(steps))
    
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            # 步骤卡片
            with st.container():
                st.markdown(f"""
                <div style="
                    border: 2px solid #ddd;
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                    background-color: #f8f9fa;
                    margin: 5px;
                ">
                    <h3>{step['icon']}</h3>
                    <h4>{step['name']}</h4>
                    <p style="font-size: 12px; color: #666;">
                        {step['description']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # 添加箭头（除了最后一个）
            if i < len(steps) - 1:
                st.markdown("→", unsafe_allow_html=True)
    
    # 工作流统计
    st.subheader("📊 工作流统计")
    
    # 模拟统计数据
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总查询数", len(st.session_state.get("chat_history", [])))
    
    with col2:
        # 计算平均置信度
        history = st.session_state.get("chat_history", [])
        avg_confidence = 0
        if history:
            confidences = [
                item.get("stats", {}).get("answer_confidence", 0) 
                for item in history if "stats" in item
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        st.metric("平均置信度", f"{avg_confidence:.2f}")
    
    with col3:
        # 计算网络搜索使用率
        web_search_count = sum(
            1 for item in history 
            if any(s.get("type") == "web_search" for s in item.get("sources", []))
        )
        web_search_rate = web_search_count / len(history) if history else 0
        st.metric("网络搜索率", f"{web_search_rate:.1%}")
    
    with col4:
        # 计算平均响应时间
        avg_time = 0
        if history:
            times = [
                item.get("stats", {}).get("generation_time", 0) 
                for item in history if "stats" in item
            ]
            avg_time = sum(times) / len(times) if times else 0
        st.metric("平均响应时间", f"{avg_time:.1f}s")

def render_advanced_settings():
    """渲染高级设置"""
    st.subheader("⚙️ 高级设置")
    
    with st.expander("查询优化设置"):
        # 查询重写
        enable_query_rewrite = st.checkbox("启用查询重写", value=True)
        
        # 上下文窗口大小
        context_window = st.slider("上下文窗口大小", 1000, 8000, 4000, 500)
        
        # 检索深度
        retrieval_depth = st.selectbox(
            "检索深度",
            ["basic", "advanced", "deep"],
            index=1
        )
    
    with st.expander("答案生成设置"):
        # 温度参数
        temperature = st.slider("创造性温度", 0.0, 1.0, 0.7, 0.1)
        
        # 最大tokens
        max_tokens = st.slider("最大Token数", 500, 4000, 2000, 100)
        
        # 答案风格
        answer_style = st.selectbox(
            "答案风格",
            ["详细", "简洁", "学术", "通俗"],
            index=0
        )
    
    with st.expander("网络搜索设置"):
        # 搜索引擎选择
        search_engine = st.selectbox(
            "搜索引擎",
            ["tavily", "google", "bing"],
            index=0
        )
        
        # 搜索结果数
        search_results = st.slider("搜索结果数", 1, 10, 5, 1)
        
        # 搜索深度
        search_depth = st.selectbox(
            "搜索深度",
            ["basic", "advanced"],
            index=1
        )
    
    # 保存设置
    advanced_config = {
        "query_rewrite": enable_query_rewrite,
        "context_window": context_window,
        "retrieval_depth": retrieval_depth,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "answer_style": answer_style,
        "search_engine": search_engine,
        "search_results": search_results,
        "search_depth": search_depth
    }
    
    st.session_state.advanced_config = advanced_config
    
    if st.button("💾 保存设置"):
        st.success("设置已保存！")

def render_query_templates():
    """渲染查询模板"""
    st.subheader("📝 查询模板")
    
    templates = {
        "事实性查询": [
            "什么是{概念}？",
            "{概念}的定义是什么？",
            "请解释{概念}的基本原理"
        ],
        "关系性查询": [
            "{实体A}与{实体B}之间的关系是什么？",
            "{实体}对{领域}有什么影响？",
            "分析{实体A}和{实体B}的联系"
        ],
        "分析性查询": [
            "分析{主题}的发展趋势",
            "比较{选项A}和{选项B}的优缺点",
            "评估{主题}的现状和未来发展"
        ]
    }
    
    selected_category = st.selectbox("选择查询类型", list(templates.keys()))
    
    if selected_category:
        st.write(f"**{selected_category}模板：**")
        
        for template in templates[selected_category]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.code(template)
            with col2:
                if st.button("使用", key=f"use_{template}"):
                    st.session_state.template_query = template
                    st.info(f"已选择模板: {template}")

def render_export_options():
    """渲染导出选项"""
    st.subheader("📤 导出选项")
    
    if not st.session_state.get("chat_history"):
        st.info("没有对话历史可导出")
        return
    
    # 导出格式选择
    export_format = st.selectbox(
        "选择导出格式",
        ["JSON", "CSV", "Markdown", "PDF"],
        index=0
    )
    
    # 导出内容选择
    export_content = st.multiselect(
        "选择导出内容",
        ["查询", "答案", "来源", "统计信息", "时间戳"],
        default=["查询", "答案", "来源"]
    )
    
    if st.button("📥 导出对话历史"):
        # 准备导出数据
        export_data = []
        
        for item in st.session_state.chat_history:
            export_item = {}
            
            if "查询" in export_content:
                export_item["query"] = item.get("query", "")
            if "答案" in export_content:
                export_item["answer"] = item.get("answer", "")
            if "来源" in export_content:
                export_item["sources"] = item.get("sources", [])
            if "统计信息" in export_content:
                export_item["stats"] = item.get("stats", {})
            if "时间戳" in export_content:
                export_item["timestamp"] = item.get("timestamp", "")
            
            export_data.append(export_item)
        
        # 根据格式导出
        if export_format == "JSON":
            st.download_button(
                label="下载 JSON 文件",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        elif export_format == "Markdown":
            md_content = "# 对话历史\n\n"
            for i, item in enumerate(export_data, 1):
                md_content += f"## 对话 {i}\n\n"
                md_content += f"**查询:** {item.get('query', '')}\n\n"
                md_content += f"**回答:** {item.get('answer', '')}\n\n"
                md_content += "---\n\n"
            
            st.download_button(
                label="下载 Markdown 文件",
                data=md_content,
                file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
        
        st.success("导出完成！")

# 主要的高级界面渲染函数
def render_advanced_interface():
    """渲染高级界面"""
    
    # 创建标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔄 实时查询", 
        "🎯 查询模板", 
        "⚙️ 高级设置", 
        "📊 工作流图", 
        "📤 导出选项"
    ])
    
    with tab1:
        render_streaming_query_interface()
    
    with tab2:
        render_query_templates()
    
    with tab3:
        render_advanced_settings()
    
    with tab4:
        render_interactive_workflow_diagram()
    
    with tab5:
        render_export_options()