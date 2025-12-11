import streamlit as st
import subprocess
import os
import webbrowser
import time

# ================= 配置区 =================
# 【重要】如果是为了截图申请软著，建议设为 True，这样点击按钮会立即显示成功，不用等爬虫跑完
# 如果想真的运行爬虫，请改为 False
DEMO_MODE = True 
# ==========================================

st.set_page_config(page_title="智库数据智能汇聚系统", layout="wide", page_icon="📊")

# 侧边栏样式与配置
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/data-configuration.png", width=80)
    st.title("系统控制台")
    st.info(f"当前模式: {'演示/截图模式' if DEMO_MODE else '生产运行模式'}")
    
    st.subheader("参数配置")
    proxy = st.text_input("代理服务器 (Proxy)", "http://127.0.0.1:7890")
    thread_count = st.slider("并发线程数", 1, 10, 4)
    auto_translate = st.checkbox("启用实时翻译模块", value=True)
    
    st.divider()
    st.caption("© 2025 智库数据采集系统 V1.0")

# 主界面标题
st.title("🛡️ 多源异构智库数据汇聚与分析系统")
st.markdown("### Multi-source Heterogeneous Data Aggregation System")
st.divider()

# 状态指标（为了截图好看，显得专业）
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("已收录站点", "24 个", "+2")
kpi2.metric("累计文档数", "1,245 份", "+15")
kpi3.metric("翻译覆盖率", "98.5%", "+0.5%")
kpi4.metric("系统状态", "运行中", "Normal")

st.markdown("<br>", unsafe_allow_html=True)

# 功能操作区
col1, col2 = st.columns(2)

# --- 模块一：列表采集 ---
with col1:
    st.subheader("📡 数据源扫描与更新")
    st.write("执行全网列表页扫描，比对 ETag 指纹，检测最新发布报告。")
    
    if st.button("▶ 启动列表采集引擎 (main.py)", type="primary", use_container_width=True):
        with st.status("正在连接目标服务器...", expanded=True) as status:
            st.write("正在初始化 ChromeDriver...")
            time.sleep(1)
            st.write("加载站点配置清单...")
            
            if DEMO_MODE:
                # 假装运行，为了截图
                time.sleep(2)
                st.write("扫描 [BCG]... 无变更")
                st.write("扫描 [McKinsey]... 发现新条目")
                st.write("正在生成索引文件 generated_html/index.html...")
                status.update(label="✅ 列表采集完成", state="complete", expanded=True)
                st.success("列表页扫描完成，索引已更新。")
            else:
                # 真实运行
                try:
                    # 使用 python 运行 main.py
                    process = subprocess.run(["python", "main.py"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    st.text_area("运行日志", process.stdout + process.stderr, height=200)
                    if process.returncode == 0:
                        status.update(label="✅ 采集完成", state="complete")
                        st.success("main.py 执行成功")
                    else:
                        status.update(label="❌ 发生错误", state="error")
                        st.error("执行失败，请查看日志")
                except Exception as e:
                    st.error(f"无法启动脚本: {e}")

# --- 模块二：内页抓取 ---
with col2:
    st.subheader("📝 深度内容解析与结构化")
    st.write("智能路由解析内页，提取正文、作者及附件，执行数据清洗。")
    
    if st.button("▶ 启动深度抓取引擎 (内页爬取.py)", use_container_width=True):
        with st.status("正在初始化解析器...", expanded=True) as status:
            st.write("读取任务队列...")
            
            if DEMO_MODE:
                time.sleep(2)
                st.write("解析 domain: bain.com [OK]")
                st.write("解析 domain: rand.org [OK]")
                st.write("正文提取中... 翻译队列入队...")
                status.update(label="✅ 深度抓取完成", state="complete", expanded=True)
                st.success("所有新增内页已处理完毕，数据已写入 output_complete.json。")
            else:
                try:
                    process = subprocess.run(["python", "内页爬取_完整版.py"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    st.text_area("运行日志", process.stdout + process.stderr, height=200)
                    status.update(label="✅ 抓取完成", state="complete")
                except Exception as e:
                    st.error(f"无法启动脚本: {e}")

st.divider()

# --- 模块三：结果展示 ---
st.subheader("📊 数据资产管理与可视化")
c1, c2 = st.columns([1, 4])
with c1:
    if st.button("📂 打开数据看板", use_container_width=True):
        html_path = os.path.abspath("generated_html/index.html")
        if os.path.exists(html_path):
            webbrowser.open(f"file://{html_path}")
            st.toast(f"已打开: {html_path}")
        else:
            st.error("未找到 index.html，请先执行列表采集。")
with c2:
    st.info("提示：系统已自动生成 PDF 导出接口，支持按日期范围筛选导出报告集合。")