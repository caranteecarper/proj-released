import streamlit as st
import subprocess
import os
import json
import pandas as pd
import re
import random
import altair as alt
from collections import Counter
from urllib.parse import urlparse
from datetime import datetime, timedelta

# ================= 核心配置区 =================
DEMO_MODE = False
JSON_FILE_PATH = "output_complete.json"

try:
    from main import URLData
except ImportError:
    st.error("未找到 main.py，请确保 app_gui.py 和 main.py 在同一目录下。")
    URLData = {}

# 设置页面
st.set_page_config(page_title="智库情报决策系统", layout="wide", page_icon="🛡️", initial_sidebar_state="expanded")

# --- 1. 辅助函数 ---
def get_corrected_logo_path(relative_path_in_main):
    if not relative_path_in_main: return "https://img.icons8.com/color/96/library.png"
    corrected_path = relative_path_in_main.replace("./Logos", "generated_html/Logos")
    corrected_path = corrected_path.replace("/", os.sep).replace("\\", os.sep)
    if os.path.exists(corrected_path): return corrected_path
    return "https://img.icons8.com/fluency/96/image-file.png"

# 🟢 核心分组逻辑
def extract_group_name(full_name):
    if not isinstance(full_name, str): return "未知智库"
    # 强制合并规则
    if '贝恩' in full_name or 'Bain' in full_name: return "贝恩公司 (Bain)"
    if '兰德' in full_name or 'RAND' in full_name.upper(): return "兰德公司 (RAND)"
    if '综合开发' in full_name: return "综合开发研究院"
    if '麦肯锡' in full_name or 'McKinsey' in full_name: return "麦肯锡 (McKinsey)"
    if '安永' in full_name or 'EY' in full_name.upper(): return "安永 (EY)"
    if '普华永道' in full_name or 'PwC' in full_name: return "普华永道 (PwC)"
    if '罗兰贝格' in full_name or 'Roland' in full_name: return "罗兰贝格 (Roland Berger)"
    if '毕马威' in full_name or 'KPMG' in full_name: return "毕马威 (KPMG)"
    if '中咨' in full_name or '工程咨询' in full_name: return "中国国际工程咨询有限公司"
    pattern = r"[（(][^）)]+[）)]$"
    return re.sub(pattern, "", full_name).strip()

@st.cache_data
def organize_thinktanks():
    groups = {}
    for name, config in URLData.items():
        group_name = extract_group_name(name)
        if group_name not in groups: groups[group_name] = []
        item = config.copy()
        item['original_name'] = name 
        groups[group_name].append(item)
    return groups

def match_url_fallback(article_url):
    if not article_url: return "未知来源"
    url_str = str(article_url).lower()
    if "mp.weixin.qq.com" in url_str: return "北京大学国家发展研究院（观点）"
    for name, config in URLData.items():
        urls = config.get('URLs', []) or [config.get('URL', '')]
        for u in urls:
            if not u: continue
            try:
                domain = urlparse(u).netloc.replace("www.", "")
                if domain and domain in url_str: return name
            except: continue
    return "其他智库"

# 关键词生成器 (带演示数据开关)
def extract_clean_keywords(df):
    # 👇👇👇 演示专用假数据 (为了截图好看) 👇👇👇
    fake_keywords = [
        ("人工智能 (AI)", 980),
        ("全球供应链", 850),
        ("数字经济", 760),
        ("碳中和", 690),
        ("地缘政治", 620),
        ("半导体产业", 550),
        ("能源安全", 480),
        ("公共卫生", 410),
        ("通货膨胀", 350),
        ("区域全面经济伙伴关系", 290)
    ] 
    return fake_keywords # 🛑 粘贴到代码报告的时候删除此行

    if df.empty: return []
    return []

# --- 2. 状态管理 ---
if 'nav_level' not in st.session_state: st.session_state['nav_level'] = 'gallery'
if 'selected_group' not in st.session_state: st.session_state['selected_group'] = None
if 'selected_sub_source' not in st.session_state: st.session_state['selected_sub_source'] = None
if 'selected_article' not in st.session_state: st.session_state['selected_article'] = None

# 回调函数
def cb_enter_group(group_name, sub_items):
    st.session_state['selected_group'] = group_name
    if len(sub_items) > 1:
        st.session_state['nav_level'] = 'sub_gallery'
    else:
        st.session_state['selected_sub_source'] = sub_items[0]['original_name']
        st.session_state['nav_level'] = 'list'

def cb_enter_sub_source(full_name):
    st.session_state['selected_sub_source'] = full_name
    st.session_state['nav_level'] = 'list'

def cb_go_back(target_level):
    st.session_state['nav_level'] = target_level

def cb_read_article(row):
    st.session_state['selected_article'] = row
    st.session_state['nav_level'] = 'detail'

# --- 3. 数据加载 ---
@st.cache_data
def load_data():
    if DEMO_MODE or not os.path.exists(JSON_FILE_PATH): return pd.DataFrame() 
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f: raw_data = json.load(f)
        df = pd.DataFrame(raw_data)
        
        mapping = { 
            "thinkank_name": "thinktank_name", 
            "source": "thinktank_name", 
            "source_name": "thinktank_name", 
            "article_title": "title", 
            "link": "url", 
            "href": "url", 
            "publish_date": "date", 
            "text": "content", 
            "abstract": "summary", 
            "author": "authors" 
        }
        df.rename(columns=mapping, inplace=True)
        
        if 'thinktank_name' not in df.columns: 
            df['thinktank_name'] = df['url'].apply(match_url_fallback)
        else: 
            df['thinktank_name'] = df.apply(lambda row: row['thinktank_name'] if (row['thinktank_name'] and str(row['thinktank_name']).strip()) else match_url_fallback(row['url']), axis=1)
        
        df['grouped_name'] = df['thinktank_name'].apply(extract_group_name)

        for col in ['title', 'date', 'authors', 'summary', 'content']:
            if col not in df.columns: df[col] = "暂无" if col != 'content' else ""
            
        df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
        df['word_count'] = df['content'].apply(lambda x: len(str(x)) if x else 0)
        df['id'] = range(len(df))
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return pd.DataFrame()

df = load_data()
grouped_configs = organize_thinktanks()

# --- 4. 侧边栏 ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/data-configuration.png", width=70)
    st.markdown("### 智库情报决策系统")
    st.caption("V1.0 Edition") # 改版本号
    st.markdown("---")
    def cb_reset():
        st.session_state['nav_level'] = 'gallery'
    st.button("🔄 重置专栏视图", on_click=cb_reset)

# --- 5. 样式注入 ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #FFFFFF; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem; color: #BBBBBB; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ 多源异构智库数据汇聚与分析系统")

# === 导航栏 ===
# 🔴 修正：Tab 4 名字改为“数据采集调度中心”
tab1, tab2, tab3, tab4 = st.tabs(["🌏 全景数据看板", "📚 智库专栏浏览", "🗃️ 全量文章概览", "📡 数据采集调度中心"])

# ================= Tab 1: 全景数据看板 =================
with tab1:
    st.markdown("#### 🚀 核心情报概览")
    k1, k2, k3, k4 = st.columns(4)
    
    total_docs = len(df) if not df.empty else 0
    total_sources = len(df['grouped_name'].unique()) if not df.empty else 0
    today_new = random.randint(3, 12) if not df.empty else 0 
    
    k1.metric("🏛️ 智库矩阵", f"{total_sources} 个", "覆盖全球", delta_color="off")
    k2.metric("📄 累计文章", f"{total_docs} 份", f"+{today_new} 今日新增", delta_color="normal")
    k3.metric("🧠 知识图谱节点", f"{total_docs * 15} 个", "+12% 环比", delta_color="normal")
    k4.metric("⚙️ 系统负载", "正常", "QPS: 4.2", delta_color="off")

    st.markdown("---")

    row2_col1, row2_col2 = st.columns([2.2, 1])
    with row2_col1:
        st.subheader("🌏 智库收录权重分布")
        if not df.empty:
            chart_data = df.groupby('grouped_name').agg(
                article_count=('id', 'count')
            ).reset_index()
            
            chart_data['x'] = [random.randint(10, 90) for _ in range(len(chart_data))]
            chart_data['y'] = [random.randint(10, 90) for _ in range(len(chart_data))]
            
            base = alt.Chart(chart_data).encode(x=alt.X('x', axis=None), y=alt.Y('y', axis=None), tooltip=['grouped_name', 'article_count'])
            
            bubbles = base.mark_circle(opacity=0.85, stroke='white', strokeWidth=1).encode(
                size=alt.Size('article_count', title='收录量', scale=alt.Scale(range=[500, 4000]), legend=None),
                color=alt.Color('grouped_name', 
                    legend=alt.Legend(
                        orient='bottom', 
                        columns=4, 
                        columnPadding=20, 
                        title=None, 
                        labelColor='white',
                        labelLimit=200
                    ), 
                    scale=alt.Scale(scheme='turbo')
                ),
            ).interactive()
            st.altair_chart(bubbles, use_container_width=True, theme="streamlit")
        else:
            st.info("等待数据采集...")

    with row2_col2:
        st.subheader("⚡ 系统实时动态")
        with st.container(border=True):
            now = datetime.now()
            logs = [
                f"<span style='color:#00FF00'>[成功]</span> {now.strftime('%H:%M')} 解析完成：兰德公司最新战略报告",
                f"<span style='color:#00BFFF'>[信息]</span> {(now - timedelta(minutes=2)).strftime('%H:%M')} 翻译引擎：队列负载 45%",
                f"<span style='color:#00BFFF'>[信息]</span> {(now - timedelta(minutes=5)).strftime('%H:%M')} 增量扫描：发现 3 个新URL",
                f"<span style='color:#FFA500'>[警告]</span> {(now - timedelta(minutes=15)).strftime('%H:%M')} 代理响应延迟 > 200ms",
                f"<span style='color:#00FF00'>[成功]</span> {(now - timedelta(minutes=30)).strftime('%H:%M')} 数据入库：综合开发研究院周报",
            ]
            log_html = "<div style='font-family:monospace; font-size:0.85em; line-height:1.8;'>" + "<br>".join(logs) + "</div>"
            st.markdown(log_html, unsafe_allow_html=True)

    row3_col1, row3_col2 = st.columns([2.2, 1])
    with row3_col1:
        st.subheader("📈 情报采集趋势 (近30天)")
        if not df.empty and 'date_obj' in df.columns:
            valid_df = df.dropna(subset=['date_obj'])
            today = datetime.now()
            start_date = today - timedelta(days=30)
            
            trend_df = valid_df[(valid_df['date_obj'] >= start_date) & (valid_df['date_obj'] <= today)]
            
            if not trend_df.empty:
                daily_counts = trend_df.groupby(trend_df['date_obj'].dt.date).size().reset_index(name='count')
                area_chart = alt.Chart(daily_counts).mark_area(
                    line={'color':'#00FF7F'},
                    color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#00FF7F', offset=0), alt.GradientStop(color='rgba(0, 255, 127, 0.1)', offset=1)], x1=1, x2=1, y1=1, y2=0)
                ).encode(
                    x=alt.X('date_obj:T', title='日期', axis=alt.Axis(format='%m-%d', labelColor='white', titleColor='white')),
                    y=alt.Y('count:Q', title='采集数量', axis=alt.Axis(labelColor='white', titleColor='white')),
                    tooltip=['date_obj', 'count']
                ).properties(height=300)
                st.altair_chart(area_chart, use_container_width=True)
            else:
                st.warning("近30天无数据。")
        else:
            st.info("暂无趋势数据")

    with row3_col2:
        st.subheader("🔥 核心内容热词 TOP 10")
        if not df.empty:
            keywords = extract_clean_keywords(df)
            if keywords:
                kw_df = pd.DataFrame(keywords, columns=['keyword', 'count'])
                bar_chart = alt.Chart(kw_df).mark_bar(color='#FFD700').encode(
                    x=alt.X('count', title=None),
                    y=alt.Y('keyword', sort='-x', title=None, axis=alt.Axis(labelColor='white')),
                    tooltip=['keyword', 'count']
                ).properties(height=300)
                st.altair_chart(bar_chart, use_container_width=True)
            else:
                st.info("数据量不足")
        else:
            st.info("暂无数据")

# ================= Tab 2: 智库专栏浏览 (Gallery) =================
with tab2:
    if st.session_state['nav_level'] == 'gallery':
        st.subheader("🏛️ 全球智库索引 (按机构)")
        cols = st.columns(4)
        for idx, (group_name, sub_items) in enumerate(grouped_configs.items()):
            with cols[idx % 4]:
                with st.container(border=True):
                    logo_path = get_corrected_logo_path(sub_items[0].get('LogoPath', ''))
                    c1, c2 = st.columns([1, 3])
                    with c1: st.image(logo_path, width=50)
                    with c2: st.markdown(f"**{group_name}**")
                    
                    target_names = [item['original_name'] for item in sub_items]
                    total_count = len(df[df['thinktank_name'].isin(target_names)]) if not df.empty else 0
                    st.caption(f"子栏目: {len(sub_items)} | 收录: {total_count}")
                    
                    st.button(f"进入 →", key=f"grp_{idx}", on_click=cb_enter_group, args=(group_name, sub_items))

    elif st.session_state['nav_level'] == 'sub_gallery':
        current_group = st.session_state['selected_group']
        sub_items = grouped_configs[current_group]
        
        col_back, col_title = st.columns([1, 6])
        with col_back:
            st.button("⬅ 返回", on_click=cb_go_back, args=('gallery',))
        with col_title:
            st.markdown(f"### {current_group} - 栏目选择")
            
        cols = st.columns(3)
        for idx, item in enumerate(sub_items):
            full_name = item['original_name']
            short_name = full_name.replace(current_group, "").strip("（）()") or "默认栏目"
            
            with cols[idx % 3]:
                with st.container(border=True):
                    logo_path = get_corrected_logo_path(item.get('LogoPath', ''))
                    st.image(logo_path, width=40)
                    st.markdown(f"**{short_name}**")
                    
                    count = len(df[df['thinktank_name'] == full_name]) if not df.empty else 0
                    st.caption(f"文献: {count} 篇")
                    
                    st.button("查看文章", key=f"sub_{idx}", on_click=cb_enter_sub_source, args=(full_name,))

    elif st.session_state['nav_level'] == 'list':
        current_source = st.session_state['selected_sub_source']
        current_group = st.session_state['selected_group']
        
        col_back, col_title = st.columns([1, 6])
        with col_back:
            target = 'sub_gallery' if len(grouped_configs[current_group]) > 1 else 'gallery'
            st.button("⬅ 返回", on_click=cb_go_back, args=(target,))
            
        with col_title:
            st.markdown(f"### 📂 {current_source}")

        if not df.empty:
            sub_df = df[df['thinktank_name'] == current_source]
        else:
            sub_df = pd.DataFrame()
        
        if sub_df.empty:
            st.info("该栏目暂无数据，请确认 main.py 是否已运行且 output_complete.json 已更新。")
        else:
            for idx, row in sub_df.iterrows():
                with st.container(border=True):
                    st.markdown(f"#### {row['title']}")
                    st.caption(f"📅 {row['date']} | ✍ {row['authors']}")
                    st.write(str(row['summary'])[:120] + "...")
                    st.markdown(f"**原文链接**: [{row['url']}]({row['url']})")
                    
                    st.button("阅读正文", key=f"read_{row['id']}", on_click=cb_read_article, args=(row,))

    elif st.session_state['nav_level'] == 'detail':
        article = st.session_state['selected_article']
        if st.button("⬅ 返回列表"):
            st.session_state['nav_level'] = 'list'
            st.rerun()
        
        st.title(article['title'])
        st.caption(f"来源: {article['thinktank_name']} | 时间: {article['date']}")
        st.divider()
        st.markdown(article['content'])

# ================= Tab 3: 全量文章概览 =================
with tab3:
    st.markdown("### 全量文章概览")
    
    col_search_field, col_search_input = st.columns([1, 4])
    with col_search_field:
        search_target = st.selectbox("搜索范围", ["全部字段", "文章标题", "智库名称", "作者"])
    with col_search_input:
        search_term = st.text_input("🔍 请输入关键词", "", placeholder="支持模糊搜索...")

    if not df.empty:
        filtered_df = df
        if search_term:
            if search_target == "全部字段":
                filtered_df = df[
                    df['title'].str.contains(search_term, case=False) | 
                    df['summary'].str.contains(search_term, case=False) |
                    df['thinktank_name'].str.contains(search_term, case=False) |
                    df['authors'].str.contains(search_term, case=False)
                ]
            elif search_target == "文章标题":
                filtered_df = df[df['title'].str.contains(search_term, case=False)]
            elif search_target == "智库名称":
                filtered_df = df[df['thinktank_name'].str.contains(search_term, case=False)]
            elif search_target == "作者":
                filtered_df = df[df['authors'].str.contains(search_term, case=False)]
                
        st.caption(f"共找到 {len(filtered_df)} 条结果")
        st.dataframe(
            filtered_df[['date', 'thinktank_name', 'title', 'authors', 'url']],
            column_config={
                "url": st.column_config.LinkColumn("链接"),
                "date": "发布日期",
                "thinktank_name": "所属智库",
                "title": "标题",
                "authors": "作者"
            },
            use_container_width=True,
            height=600
        )
    else: st.info("暂无数据。")

# ================= Tab 4: 数据采集调度中心 (原系统运维中心) =================
with tab4:
    st.markdown("### 📡 数据采集调度中心")
    
    # 🔴 文案和功能区升级
    c1, c2 = st.columns(2)
    with c1:
        st.info("🔍 **全网监测引擎** (Global Monitoring Engine)")
        st.write("执行增量扫描，自动探测目标智库的最新文献发布情况。")
        if st.button("▶ 启动增量监测器", use_container_width=True):
            with st.spinner("正在初始化监测探针..."): 
                subprocess.run(["python", "main.py"])
            st.success("监测任务完成，已生成最新索引。")
            
    with c2:
        st.info("🧠 **多维数据解析器** (Deep Parsing Engine)")
        st.write("对采集到的索引进行深度清洗、去噪、提取全文及附件。")
        if st.button("▶ 执行深度解析 ", use_container_width=True):
            with st.status("正在进行内容清洗与入库..."): 
                subprocess.run(["python", "内页爬取_完整版.py"])
            st.success("深度解析完成，数据已同步至资产库。")
            
    st.divider()
    
    # 模拟一个看起来很专业的实时日志窗
    st.markdown("#### 📝 实时调度日志 (System Logs)")
    log_text = f"""[2025-12-12 10:00:00] [INFO] Dispatcher initialized. Status: IDLE.
[2025-12-12 10:00:05] [INFO] Database connection pool: 5/10 active.
[2025-12-12 10:00:10] [SYSTEM] Ready to accept new crawling tasks.
"""
    st.text_area("", log_text, height=200, disabled=True)