import streamlit as st
import subprocess
import os
import time
import json
import pandas as pd
import random
from datetime import datetime, timedelta

# ================= 核心配置区 =================
# 【截图神器】True = 演示模式（生成假数据填充表格，适合做软著截图）
# 【生产模式】False = 真实模式（读取 output_complete.json）
DEMO_MODE = True 

JSON_FILE_PATH = "output_complete.json"

# 尝试导入 main.py 中的配置 (URLData)
# 这样你的界面就和 main.py 里的配置完全同步了（名字、Logo都对得上）
try:
    from main import URLData
except ImportError:
    st.error("未找到 main.py，请确保 app_gui.py 和 main.py 在同一目录下。")
    URLData = {} # 防止崩溃的空字典

# ============================================

st.set_page_config(page_title="多源异构智库数据汇聚系统 Pro", layout="wide", page_icon="🛡️")

# --- 1. Logo 路径修正函数 ---
def get_corrected_logo_path(relative_path_in_main):
    """
    main.py 里的路径是 './Logos/xxx' (相对于 generated_html)
    但 app_gui.py 在根目录运行，所以需要改为 'generated_html/Logos/xxx'
    """
    if not relative_path_in_main:
        return "https://img.icons8.com/color/96/library.png"
    
    # 将 ./Logos 替换为 generated_html/Logos
    corrected_path = relative_path_in_main.replace("./Logos", "generated_html/Logos")
    
    # 兼容 Windows 反斜杠
    corrected_path = corrected_path.replace("/", os.sep)
    
    if os.path.exists(corrected_path):
        return corrected_path
    else:
        # 如果找不到图，返回一个默认图标，防止界面挂掉
        return "https://img.icons8.com/fluency/96/image-file.png"

# --- 2. 状态管理初始化 ---
if 'nav_level' not in st.session_state:
    st.session_state['nav_level'] = 'gallery' # gallery=墙, list=列表, detail=详情
if 'selected_source_name' not in st.session_state:
    st.session_state['selected_source_name'] = None
if 'selected_article' not in st.session_state:
    st.session_state['selected_article'] = None

# --- 3. 数据加载函数 ---
@st.cache_data
def load_data():
    # 获取 main.py 里所有的智库中文名
    all_thinktank_names = list(URLData.keys()) if URLData else ["示例智库A", "示例智库B"]

    if DEMO_MODE or not os.path.exists(JSON_FILE_PATH):
        # === 生成演示数据 (为了截图好看) ===
        data = []
        for i in range(120): # 生成120条假数据
            # 随机从 URLData 里挑一个名字
            source_name = random.choice(all_thinktank_names)
            date = datetime.now() - timedelta(days=random.randint(0, 365))
            
            data.append({
                "id": i,
                "title": f"关于 {source_name} 数字化转型与全球战略分析报告 - Vol.{i}",
                "url": f"https://www.example.com/report/{i}",
                "thinktank_name": source_name, # 核心字段：智库名称
                "date": date.strftime("%Y-%m-%d"),
                "summary": f"本报告深入探讨了 {source_name} 在新一轮科技革命中的定位与挑战...",
                "content": f"这里是 {source_name} 的详细正文内容...\n\n(此处为演示数据，用于软件著作权申请截图展示)", 
                "authors": "张研究员, 李博士",
                "status": "已翻译" if random.random() > 0.2 else "待处理"
            })
        return pd.DataFrame(data)
    else:
        # === 读取真实 JSON ===
        try:
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            
            # 数据清洗：确保有 thinktank_name 字段
            # 如果真实数据里没有中文名，我们尝试通过 url 来匹配 main.py 里的配置，反推中文名
            if 'thinktank_name' not in df.columns:
                def match_name_by_url(url):
                    if not url: return "未知来源"
                    for name, config in URLData.items():
                        # 简单的包含关系匹配
                        urls = config.get('URLs', [])
                        # 取域名前段做匹配，比如 ciecc.com
                        if any(u in url for u in urls): 
                            return name
                        # 或者尝试匹配 URLData 里的 URL host
                        # 这里简单处理，直接返回 url 的域名部分
                    return url.split('/')[2] if len(url.split('/')) > 2 else "其他智库"

                if 'url' in df.columns:
                    df['thinktank_name'] = df['url'].apply(match_name_by_url)
                else:
                    df['thinktank_name'] = "未知智库"

            # 补全其他可能缺失的字段
            if 'summary' not in df.columns: df['summary'] = df['title']
            if 'content' not in df.columns: df['content'] = "暂无正文"
            df['id'] = range(len(df))
            return df
        except Exception as e:
            st.error(f"数据读取失败: {e}")
            return pd.DataFrame()

df = load_data()

# --- 4. 侧边栏 ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/data-configuration.png", width=70)
    st.markdown("### 智库数据情报平台")
    st.caption("V3.0.0 Enterprise Edition")
    
    st.markdown("---")
    st.subheader("全局过滤器")
    if not df.empty and 'thinktank_name' in df.columns:
        # 使用中文名做筛选
        unique_names = list(df['thinktank_name'].unique())
        selected_sources_sidebar = st.multiselect("智库筛选", unique_names, default=unique_names[:5])
    
    st.markdown("---")
    if st.button("🔄 重置系统状态"):
        st.session_state['nav_level'] = 'gallery'
        st.rerun()

# --- 5. 主界面构建 ---
st.title("🛡️ 多源异构智库数据汇聚与分析系统")

# 定义四个大标签页
tab1, tab2, tab3, tab4 = st.tabs(["🖥️ 系统控制台", "🗃️ 数据资产库", "📈 情报分析看板", "📚 智库专栏浏览"])

# === Tab 1: 控制台 ===
with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("📡 **列表采集引擎**")
        if st.button("▶ 启动增量扫描 (main.py)", use_container_width=True):
            if DEMO_MODE:
                with st.status("正在执行扫描...", expanded=True):
                    time.sleep(1)
                    st.write("加载 URLData 配置... OK")
                    st.write("检测 ETag 变更... OK")
                    st.success("扫描完成")
            else:
                subprocess.run(["python", "main.py"])
    with col_b:
        st.info("📝 **深度解析引擎**")
        if st.button("▶ 启动深度抓取 (内页爬取.py)", use_container_width=True):
            st.toast("任务已下发...")
            if not DEMO_MODE:
                subprocess.run(["python", "内页爬取_完整版.py"])
    
    st.divider()
    st.text_area("系统实时日志", "2025-12-11 15:30:00 [INFO] System Ready.\n2025-12-11 15:30:05 [INFO] Loaded 24 think tank configurations.", height=150)

# === Tab 2: 表格列表 ===
with tab2:
    if not df.empty:
        # 安全的表格配置
        try:
            cfg = {
                "url": st.column_config.LinkColumn("原始链接"),
                "date": "发布日期", 
                "title": "报告标题", 
                "thinktank_name": "所属智库",
                "status": "状态"
            }
        except:
            cfg = {} 
        
        # 展示列
        cols_to_show = ['id', 'title', 'thinktank_name', 'date', 'url', 'status']
        # 过滤 df 中存在的列
        final_cols = [c for c in cols_to_show if c in df.columns]
        
        st.dataframe(df[final_cols], column_config=cfg, use_container_width=True, height=500)

# === Tab 3: 可视化 ===
with tab3:
    if not df.empty and 'thinktank_name' in df.columns:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("各智库收录量分布")
            st.bar_chart(df['thinktank_name'].value_counts(), color="#FF4B4B")
        with c2:
            st.subheader("收录趋势")
            # 简单模拟数据
            chart_data = pd.DataFrame(
                {"count": [random.randint(10, 50) for _ in range(10)]},
                index=[f"2024-{i+1}" for i in range(10)]
            )
            st.line_chart(chart_data)

# === Tab 4: 智库专栏浏览 (核心改动区) ===
with tab4:
    # 逻辑层级 1: 智库墙 (Gallery)
    if st.session_state['nav_level'] == 'gallery':
        st.subheader("🏛️ 全球智库索引")
        st.caption("点击卡片进入对应智库的专属文献库")
        
        # 获取 main.py 里的所有配置项
        # 这里的 items 就是 ('中国国际工程咨询有限公司', {'LogoPath': ...})
        items = list(URLData.items())
        
        # 分列显示（每行 4 个）
        cols = st.columns(4)
        for idx, (name, config) in enumerate(items):
            with cols[idx % 4]:
                with st.container(border=True):
                    c_img, c_txt = st.columns([1, 3])
                    with c_img:
                        # === 关键修正：读取 Logo ===
                        # 这里的 config['LogoPath'] 是 './Logos/xxx'
                        # 我们转换成 'generated_html/Logos/xxx'
                        real_logo_path = get_corrected_logo_path(config.get('LogoPath', ''))
                        st.image(real_logo_path, width=50)
                    
                    with c_txt:
                        # === 关键修正：显示 main.py 里的中文 Key ===
                        st.markdown(f"**{name}**")
                    
                    # 统计该智库有多少篇文章 (从 df 里查)
                    if 'thinktank_name' in df.columns:
                        count = len(df[df['thinktank_name'] == name])
                    else:
                        count = 0
                    
                    st.caption(f"收录文献: {count} 篇")
                    
                    if st.button(f"进入专栏 →", key=f"btn_src_{idx}"):
                        st.session_state['selected_source_name'] = name
                        st.session_state['nav_level'] = 'list'
                        st.rerun()

    # 逻辑层级 2: 文章列表 (List)
    elif st.session_state['nav_level'] == 'list':
        current_name = st.session_state['selected_source_name']
        
        # 顶部返回栏
        col_back, col_title = st.columns([1, 6])
        with col_back:
            if st.button("⬅ 返回索引", type="secondary"):
                st.session_state['nav_level'] = 'gallery'
                st.rerun()
        with col_title:
            st.markdown(f"### 📂 {current_name} - 文献列表")

        # 筛选数据
        if 'thinktank_name' in df.columns:
            sub_df = df[df['thinktank_name'] == current_name]
        else:
            sub_df = pd.DataFrame()
            st.warning("数据表中未找到智库名称字段，无法筛选。")
        
        if sub_df.empty:
            st.info("该智库暂无入库数据。")
        else:
            # 遍历展示文章卡片
            for idx, row in sub_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"#### {row['title']}")
                        st.caption(f"📅 发布日期: {row['date']} | ✍ 作者: {row.get('authors', 'Unknown')}")
                        st.write(f"{str(row.get('summary', ''))[:80]}...") 
                    with c2:
                        st.write("\n")
                        # 确保 key 唯一
                        if st.button("阅读正文", key=f"btn_read_{row['id']}_{idx}"):
                            st.session_state['selected_article'] = row
                            st.session_state['nav_level'] = 'detail'
                            st.rerun()

    # 逻辑层级 3: 文章详情 (Detail)
    elif st.session_state['nav_level'] == 'detail':
        article = st.session_state['selected_article']
        
        if st.button("⬅ 返回列表"):
            st.session_state['nav_level'] = 'list'
            st.rerun()
            
        st.markdown("---")
        st.title(article['title'])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("来源智库", article.get('thinktank_name', 'Unknown'))
        c2.metric("发布日期", article['date'])
        c3.metric("翻译状态", article.get('status', '未知'))
        
        st.markdown(f"🔗 **原文链接**: [{article['url']}]({article['url']})")
        st.divider()
        st.markdown("### 📄 报告正文 (中英对照)")
        st.markdown(article.get('content', '暂无内容'))
        st.divider()
        st.info("提示：本文由系统自动抓取并翻译，仅供研究参考。")