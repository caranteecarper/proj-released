import json
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from requests.exceptions import RequestException
import time
import re
from urllib.parse import urljoin as url_join

# 明确禁用系统代理，避免 HTTPS 站点走到失效代理
NO_PROXIES = {"http": None, "https": None}

# ------------------------------ RAND 专用文本工具 ------------------------------
def _lines_filter_noise(lines):
    """过滤明显的元信息/订阅/分享等噪声行。"""
    patterns = [
        r'^Subscribe\b', r'newsletter', r'^Share on ', r'@RANDCorporation', r'^For Media', r'^By\s+\w',
        r'^Published\s+in:', r'^Published\s+on', r'Posted on rand\.org', r'^Photo by', r'^Copyright',
        r'RAND\s+Education,?\s+Employment,?\s+and\s+Infrastructure', r'RAND\s+Europe',
        r'^Cite this', r'^BibTeX$', r'^RIS$', r'^Email$', r'^LinkedIn$', r'^Facebook$', r'^Twitter$'
    ]
    res = []
    for ln in lines:
        s = (ln or '').strip()
        if not s:
            continue
        bad = False
        for pat in patterns:
            if re.search(pat, s, re.I):
                bad = True
                break
        if not bad:
            res.append(s)
    return res

def _text_from_container(node):
    """提取容器内 p/li 文本，拼接并去噪。"""
    if node is None:
        return ''
    ps = []
    for p in node.select('p, li'):
        t = p.get_text(" ", strip=True)
        if t:
            ps.append(t)
    ps = _lines_filter_noise(ps)
    return clean_text("\n".join(ps))

# ------------------------------ 通用工具函数与回退提取 ------------------------------

def get_current_date():
    """获取当前日期和时间"""
    current_datetime = datetime.now()
    current_date = current_datetime.date()
    return current_date

def clean_text(text):
    """清理文本内容，去除多余空白字符"""
    if text:
        # 去除多余的空白字符，保留段落结构
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    return ''

def generic_title_from_meta_or_h(soup: BeautifulSoup) -> str:
    # meta 优先
    meta_title = soup.select_one('meta[property="og:title"][content]') or soup.select_one('meta[name="title"][content]')
    if meta_title and meta_title.get('content'):
        return clean_text(meta_title['content'])
    # h1/h2 次之
    for sel in ['h1', '.title h1', '.article-title h1', '.arti_title', '.wp_article_title', 'h2']:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            return clean_text(node.get_text())
    # 最后用 <title>
    if soup.title and soup.title.string:
        return clean_text(soup.title.string)
    return ''

def generic_content_by_candidates(soup: BeautifulSoup) -> str:
    # 移除无关节点
    for tag in soup(['script', 'style', 'noscript']):
        tag.extract()
    # 常见正文容器优先
    candidate_selectors = [
        '.TRS_Editor', '.v_news_content', '.wp_articlecontent', '.article-content',
        '.content', '.article', '.text', '.detail-content', '#content', '.read', '.articleText'
    ]
    for sel in candidate_selectors:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            return clean_text(node.get_text("\n"))
    # 兜底：选择文本量最大的块级元素
    max_text = ''
    max_len = 0
    for node in soup.find_all(['article', 'section', 'div']):
        text = node.get_text("\n", strip=True)
        tlen = len(text)
        if tlen > max_len:
            max_len = tlen
            max_text = text
    return clean_text(max_text)

# ------------------------------ 去重与缓存工具函数 ------------------------------
def normalize_url(u: str) -> str:
    """对 URL 做轻量规范化：去首尾空格，scheme/host 小写，去掉 fragment。"""
    try:
        from urllib.parse import urlparse, urlunparse
        u = (u or '').strip()
        parts = urlparse(u)
        if not parts.scheme:
            # 对于相对地址或空值，原样返回（上游基本已做绝对化）
            return u
        norm = parts._replace(scheme=parts.scheme.lower(), netloc=parts.netloc.lower(), fragment='')
        return urlunparse(norm)
    except Exception:
        return u or ''


def load_existing_results(json_path: str):
    """
    加载已有的抓取结果，返回 (items_list, seen_url_set)。
    - items_list: List[dict]
    - seen_url_set: Set[str]，保存规范化后的 URL，用于跳过已抓取内容
    读取失败时返回空列表与空集合。
    """
    items = []
    seen = set()
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                items = data
                for it in data:
                    try:
                        u = normalize_url(it.get('url', ''))
                        if u:
                            seen.add(u)
                    except Exception:
                        continue
    except Exception:
        # 无已有文件或解析失败，忽略
        pass
    return items, seen

def parse_ciecc_article(soup, url, publish_date):
    """解析中国国际工程咨询有限公司的文章"""
    try:
        data = {}
        data['title'] = soup.select('.comnewsl.fl tr')[0].text.strip()
        data['url'] = url
        data['publish_date'] = publish_date
        data['authors'] = '中国国际工程咨询有限公司（智库建议）'
        data['thinkank_name'] = '中国国际工程咨询有限公司'
        data['summary'] = ''
        data['content'] = soup.select('.bt_content')[0].text
        data['attachments'] = ''
        data['crawl_date'] = get_current_date()
        return data
    except (IndexError, AttributeError) as e:
        print(f"解析中国国际工程咨询有限公司页面 {url} 失败: {e}")
        return None

def parse_ruc_article(soup, url, publish_date):
    """解析中国人民大学国家发展与战略研究院的文章"""
    try:
        data = {}
        # 尝试多种可能的选择器
        title_selectors = [
            'h1.title',
            '.article-title h1',
            '.content-title h1',
            'h1',
            '.title'
        ]
        
        content_selectors = [
            '.article-content',
            '.content-text',
            '.article-text',
            '.content',
            '.text'
        ]
        
        # 获取标题
        title = ''
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text())
                break
        
        # 获取内容
        content = ''
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = clean_text(content_elem.get_text())
                break
        
        if not title:
            title = generic_title_from_meta_or_h(soup)
        if not content:
            content = generic_content_by_candidates(soup)
        if not title or not content:
            print(f"中国人民大学文章解析失败，标题或内容为空: {url}")
            return None
            
        data['title'] = title
        data['url'] = url
        data['publish_date'] = publish_date
        data['authors'] = '中国人民大学国家发展与战略研究院'
        data['thinkank_name'] = '中国人民大学国家发展与战略研究院'
        data['summary'] = ''
        data['content'] = content
        data['attachments'] = ''
        data['crawl_date'] = get_current_date()
        return data
    except Exception as e:
        print(f"解析中国人民大学页面 {url} 失败: {e}")
        return None

def parse_drc_article(soup, url, publish_date):
    """解析国务院发展研究中心的文章"""
    try:
        data = {}
        # 尝试多种可能的选择器
        title_selectors = [
            '.article-title',
            '.title',
            'h1',
            '.headline'
        ]
        
        content_selectors = [
            '.article-content',
            '.content',
            '.text',
            '.article-text',
            '.main-content'
        ]
        
        # 获取标题
        title = ''
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text())
                break
        
        # 获取内容
        content = ''
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = clean_text(content_elem.get_text())
                break
        
        if not title:
            title = generic_title_from_meta_or_h(soup)
        if not content:
            content = generic_content_by_candidates(soup)
        if not title or not content:
            print(f"国务院发展研究中心文章解析失败，标题或内容为空: {url}")
            return None
            
        data['title'] = title
        data['url'] = url
        data['publish_date'] = publish_date
        data['authors'] = '国务院发展研究中心'
        data['thinkank_name'] = '国务院发展研究中心'
        data['summary'] = ''
        data['content'] = content
        data['attachments'] = ''
        data['crawl_date'] = get_current_date()
        return data
    except Exception as e:
        print(f"解析国务院发展研究中心页面 {url} 失败: {e}")
        return None

def parse_cas_article(soup, url, publish_date):
    """解析中国科学院的文章"""
    try:
        data = {}
        # 尝试多种可能的选择器
        title_selectors = [
            '.article-title',
            '.title',
            'h1',
            '.headline',
            '.news-title'
        ]
        
        content_selectors = [
            '.article-content',
            '.content',
            '.text',
            '.article-text',
            '.news-content',
            '.main-content'
        ]
        
        # 获取标题
        title = ''
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text())
                break
        
        # 获取内容
        content = ''
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = clean_text(content_elem.get_text())
                break
        
        if not title:
            title = generic_title_from_meta_or_h(soup)
        if not content:
            content = generic_content_by_candidates(soup)
        if not title or not content:
            print(f"中国科学院文章解析失败，标题或内容为空: {url}")
            return None
            
        data['title'] = title
        data['url'] = url
        data['publish_date'] = publish_date
        data['authors'] = '中国科学院'
        data['thinkank_name'] = '中国科学院'
        data['summary'] = ''
        data['content'] = content
        data['attachments'] = ''
        data['crawl_date'] = get_current_date()
        return data
    except Exception as e:
        print(f"解析中国科学院页面 {url} 失败: {e}")
        return None

def parse_amr_article(soup, url, publish_date):
    """解析中国宏观经济研究院的文章"""
    try:
        data = {}
        # 尝试多种可能的选择器
        title_selectors = [
            '.article-title',
            '.title',
            'h1',
            '.headline',
            '.news-title'
        ]
        
        content_selectors = [
            '.article-content',
            '.content',
            '.text',
            '.article-text',
            '.news-content',
            '.main-content'
        ]
        
        # 获取标题
        title = ''
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text())
                break
        
        # 获取内容
        content = ''
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = clean_text(content_elem.get_text())
                break
        
        if not title:
            title = generic_title_from_meta_or_h(soup)
        if not content:
            content = generic_content_by_candidates(soup)
        if not title or not content:
            print(f"中国宏观经济研究院文章解析失败，标题或内容为空: {url}")
            return None
            
        data['title'] = title
        data['url'] = url
        data['publish_date'] = publish_date
        data['authors'] = '中国宏观经济研究院'
        data['thinkank_name'] = '中国宏观经济研究院'
        data['summary'] = ''
        data['content'] = content
        data['attachments'] = ''
        data['crawl_date'] = get_current_date()
        return data
    except Exception as e:
        print(f"解析中国宏观经济研究院页面 {url} 失败: {e}")
        return None

def parse_ccid_article(soup, url, publish_date):
    """解析CCiD赛迪研究院的文章"""
    try:
        data = {}
        # 尝试多种可能的选择器
        title_selectors = [
            '.article-title',
            '.title',
            'h1',
            '.headline',
            '.news-title'
        ]
        
        content_selectors = [
            '.article-content',
            '.content',
            '.text',
            '.article-text',
            '.news-content',
            '.main-content'
        ]
        
        # 获取标题
        title = ''
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text())
                break
        
        # 获取内容
        content = ''
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = clean_text(content_elem.get_text())
                break
        
        if not title:
            title = generic_title_from_meta_or_h(soup)
        if not content:
            content = generic_content_by_candidates(soup)
        if not title or not content:
            print(f"CCiD赛迪研究院文章解析失败，标题或内容为空: {url}")
            return None
            
        data['title'] = title
        data['url'] = url
        data['publish_date'] = publish_date
        data['authors'] = 'CCiD赛迪研究院'
        data['thinkank_name'] = 'CCiD赛迪研究院'
        data['summary'] = ''
        data['content'] = content
        data['attachments'] = ''
        data['crawl_date'] = get_current_date()
        return data
    except Exception as e:
        print(f"解析CCiD赛迪研究院页面 {url} 失败: {e}")
        return None

def parse_sass_article(soup, url, publish_date):
    """解析上海社会科学院的文章"""
    try:
        data = {}
        # 尝试多种可能的选择器
        title_selectors = [
            '.article-title',
            '.title',
            'h1',
            '.headline',
            '.news-title'
        ]
        
        content_selectors = [
            '.article-content',
            '.content',
            '.text',
            '.article-text',
            '.news-content',
            '.main-content'
        ]
        
        # 获取标题
        title = ''
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text())
                break
        
        # 获取内容
        content = ''
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = clean_text(content_elem.get_text())
                break
        
        if not title:
            title = generic_title_from_meta_or_h(soup)
        if not content:
            content = generic_content_by_candidates(soup)
        if not title or not content:
            print(f"上海社会科学院文章解析失败，标题或内容为空: {url}")
            return None
            
        data['title'] = title
        data['url'] = url
        data['publish_date'] = publish_date
        data['authors'] = '上海社会科学院'
        data['thinkank_name'] = '上海社会科学院'
        data['summary'] = ''
        data['content'] = content
        data['attachments'] = ''
        data['crawl_date'] = get_current_date()
        return data
    except Exception as e:
        print(f"解析上海社会科学院页面 {url} 失败: {e}")
        return None

def parse_cdi_article(soup, url, publish_date):
    """解析综合开发研究院（中国·深圳）的文章"""
    try:
        data = {}
        title_selectors = [
            'div.head h1',
            'h1',
            '.article-title',
            '.title'
        ]
        content_selectors = [
            '#info', 'div#info', '.article-content', '.content', '#content', '.text'
        ]
        title = ''
        for selector in title_selectors:
            node = soup.select_one(selector)
            if node and node.get_text(strip=True):
                title = clean_text(node.get_text())
                break
        content = ''
        for selector in content_selectors:
            node = soup.select_one(selector)
            if node and node.get_text(strip=True):
                content = clean_text(node.get_text("\n"))
                break
        if not title:
            title = generic_title_from_meta_or_h(soup)
        if not content:
            content = generic_content_by_candidates(soup)
        if not title or not content:
            print(f"综合开发研究院文章解析失败，标题或内容为空: {url}")
            return None
        data['title'] = title
        data['url'] = url
        data['publish_date'] = publish_date
        data['authors'] = '综合开发研究院（中国·深圳）'
        data['thinkank_name'] = '综合开发研究院（中国·深圳）'
        data['summary'] = ''
        data['content'] = content
        data['attachments'] = ''
        data['crawl_date'] = get_current_date()
        return data
    except Exception as e:
        print(f"解析综合开发研究院页面 {url} 失败: {e}")
        return None

def parse_rand_article(soup, url, publish_date):
    """解析 RAND 文章页。
    - 标题优先 h1#RANDTitleHeadingId / article h1 / meta og:title
    - 正文优先 <article>，否则退化到通用正文提取
    - 日期优先 JSON-LD 的 datePublished，再退化到传入 publish_date
    - 附件提取页面内的 PDF/DOC/XLS 等链接
    """
    try:
        # 标题
        title = ''
        title_node = (
            soup.select_one('h1#RANDTitleHeadingId') or
            soup.select_one('article h1') or
            soup.select_one('div.head h1') or
            soup.select_one('h1')
        )
        if title_node and title_node.get_text(strip=True):
            title = clean_text(title_node.get_text())
        if not title:
            meta_title = soup.select_one('meta[property="og:title"][content]')
            if meta_title and meta_title.get('content'):
                title = clean_text(meta_title['content'])

        # 正文
        content = ''
        art = soup.select_one('article')
        if art and art.get_text(strip=True):
            content = clean_text(art.get_text("\n"))
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期：JSON-LD datePublished -> YYYY-MM-DD
        pub = ''
        try:
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                m = re.search(r'"datePublished"\s*:\s*"(\d{4})-(\d{1,2})-(\d{1,2})"', txt)
                if m:
                    pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                    break
        except Exception:
            pass
        if not pub:
            # 备选 meta
            meta_time = soup.select_one('meta[property="article:published_time"][content]')
            if meta_time and meta_time.get('content'):
                mt = meta_time['content']
                m2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', mt)
                if m2:
                    pub = f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
        if not pub:
            pub = publish_date or ''

        # 附件（同域绝对化）
        attachments = []
        container = art or soup
        for a in container.select('a[href]'):
            href = a.get('href', '')
            lower = href.lower()
            if any(lower.endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                attachments.append(url_join(url, href))
        attach_str = ' ; '.join(attachments)

        if not title or not content:
            print(f"RAND 文章解析失败（标题或正文为空）: {url}")
            return None

        data = {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': '兰德公司（RAND Corporation）',
            'thinkank_name': '兰德公司（RAND Corporation）',
            'summary': '',
            'content': content,
            'attachments': attach_str,
            'crawl_date': get_current_date()
        }
        return data
    except Exception as e:
        print(f"解析 RAND 页面失败: {url} 错误: {e}")
        return None

def parse_rand_article2(soup, url, publish_date):
    """改进版：优先抽取 RAND 出版物摘要，过滤订阅/分享等噪声，兜底 meta 摘要。"""
    try:
        # 标题
        title = ''
        title_node = (
            soup.select_one('h1#RANDTitleHeadingId') or
            soup.select_one('article h1') or
            soup.select_one('div.head h1') or
            soup.select_one('h1')
        )
        if title_node and title_node.get_text(strip=True):
            title = clean_text(title_node.get_text())
        if not title:
            meta_title = soup.select_one('meta[property="og:title"][content]')
            if meta_title and meta_title.get('content'):
                title = clean_text(meta_title['content'])

        # 正文/摘要
        content = ''
        art = None
        for sel in [
            'div.product-main div.abstract.product-page-abstract',
            'div.product-main div.abstract',
            'section.abstract',
            'div#abstract',
            'div.abstract-first-letter',
        ]:
            node = soup.select_one(sel)
            if node and node.get_text(strip=True):
                content = _text_from_container(node)
                if content:
                    break
        if not content:
            art = soup.select_one('article.blog') or soup.select_one('article')
            if art and art.get_text(strip=True):
                content = _text_from_container(art)
        if not content:
            trn = soup.select_one('#transcript, div.transcript, section.transcript')
            if trn and trn.get_text(strip=True):
                content = _text_from_container(trn)
        if not content:
            meta_abs = soup.select_one('meta[name="citation_abstract"][content]')
            if meta_abs and meta_abs.get('content'):
                content = clean_text(meta_abs['content'])
        if not content:
            meta_desc = soup.select_one('meta[property="og:description"][content]') or soup.select_one('meta[name="description"][content]')
            if meta_desc and meta_desc.get('content'):
                content = clean_text(meta_desc['content'])
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期
        pub = ''
        try:
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                m = re.search(r'"datePublished"\s*:\s*"(\d{4})-(\d{1,2})-(\d{1,2})"', txt)
                if m:
                    pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                    break
        except Exception:
            pass
        if not pub:
            meta_time = soup.select_one('meta[property="article:published_time"][content]')
            if meta_time and meta_time.get('content'):
                mt = meta_time['content']
                m2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', mt)
                if m2:
                    pub = f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
        if not pub:
            pub = publish_date or ''

        # 附件
        attachments = []
        container = art or soup
        for a in container.select('a[href]'):
            href = a.get('href', '')
            lower = href.lower()
            if any(lower.endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                attachments.append(url_join(url, href))
        attach_str = ' ; '.join(attachments)

        if not title or not content:
            print(f"RAND 文章解析失败：正文为空: {url}")
            return None
        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': '兰德公司（RAND Corporation）',
            'thinkank_name': '兰德公司（RAND Corporation）',
            'summary': '',
            'content': content,
            'attachments': attach_str,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 RAND 页面失败: {url} 错误: {e}")
        return None

def parse_jpm_article(soup, url, publish_date):
    """解析 摩根大通研究院 JPMorgan Insights 详情页
    - 标题：优先 h1 / meta og:title
    - 摘要与正文分离：
        1) 先在 article 中按阅读顺序收集 h2/h3/p/li
        2) 若存在标题为 "Overview" 的小节，则该小节（至下一小节前）的段落作为 summary；其后作为 content
        3) 否则，取首段起连续 2~3 个段落为 summary；从第一个 h2/h3 起直至文末为 content
        4) 若 summary 为空，则用 meta 描述兜底；content 若过短再回退通用正文提取
    - 日期：JSON-LD datePublished > meta article:published_time > <time>
    - 作者：JSON-LD author / meta[name=author] / 页面作者节点
    - 附件：优先文档（pdf/doc/xls/ppt），若无则回退音视频（audio/video/iframe/m3u8/mp3 等）
    """
    try:
        # 标题
        title = ''
        title_node = (
            soup.select_one('h1') or
            soup.select_one('.article-title h1') or
            soup.select_one('.article-title') or
            soup.select_one('.title h1')
        )
        if title_node and title_node.get_text(strip=True):
            title = clean_text(title_node.get_text())
        if not title:
            meta_title = soup.select_one('meta[property="og:title"][content]') or soup.select_one('meta[name="title"][content]')
            if meta_title and meta_title.get('content'):
                title = clean_text(meta_title['content'])

        # 摘要 + 正文（按结构切分）
        def _clean_inline_footnotes(node):
            try:
                # 移除脚注上标及页内脚注链接
                for x in list(node.select('sup, a[href^="#footnote"], a[href^="#fn"], a.footnote')):
                    x.decompose()
            except Exception:
                pass
            return node

        def _collect_nodes(root):
            nodes = []
            if not root:
                return nodes
            # 优先 article 下的富文本块
            blocks = root.select('div.cmp-text--pt div.cmp-text')
            if not blocks:
                # 退化为 article 整体
                blocks = [root]
            for blk in blocks:
                _clean_inline_footnotes(blk)
                for n in blk.select('h2, h3, p, li'):
                    # h2/h3 内常包裹 span.section-header
                    t = clean_text(n.get_text(" "))
                    if not t:
                        continue
                    bad = False
                    for pat in [
                        r'^Share\b', r'^Subscribe\b', r'^Related ', r'^For media', r'^Media Contacts',
                        r'^Disclaimer', r'^Cite this', r'^References$', r'^Footnotes$', r'^Copyright'
                    ]:
                        if re.search(pat, t, re.I):
                            bad = True
                            break
                    if not bad:
                        nodes.append((n.name.lower(), t))
            return nodes

        article_root = soup.select_one('main article') or soup.select_one('article')
        nodes = _collect_nodes(article_root)

        def _split_summary_content(nodes):
            if not nodes:
                return '', ''
            # 找到第一个 h2/h3
            first_h_idx = -1
            for i, (tag, txt) in enumerate(nodes):
                if tag in ('h2', 'h3'):
                    first_h_idx = i
                    break
            # 查找 Overview 小节
            ov_idx = -1
            for i, (tag, txt) in enumerate(nodes):
                if tag in ('h2', 'h3') and re.search(r'\boverview\b', txt, re.I):
                    ov_idx = i
                    break
            summary_parts = []
            content_parts = []
            if ov_idx != -1:
                # 摘要：Overview 之后直到下一个小节前的 p/li
                j = ov_idx + 1
                while j < len(nodes) and nodes[j][0] not in ('h2', 'h3'):
                    if nodes[j][0] in ('p', 'li'):
                        summary_parts.append(nodes[j][1])
                    j += 1
                # 正文：从 j 起至文末
                for k in range(j, len(nodes)):
                    tag, txt = nodes[k]
                    if tag in ('h2', 'h3'):
                        content_parts.append(txt)
                    elif tag in ('p', 'li'):
                        content_parts.append(txt)
            else:
                # 首段起连续 2~3 个段落为摘要（不跨小节）
                i = 0
                added = 0
                while i < len(nodes) and nodes[i][0] not in ('h2', 'h3'):
                    if nodes[i][0] in ('p', 'li'):
                        summary_parts.append(nodes[i][1])
                        added += 1
                        if added >= 3:
                            break
                    i += 1
                # 正文：从第一个小节开始（如存在），否则从剩余段落开始
                start = first_h_idx if first_h_idx != -1 else i + 1
                for k in range(max(0, start), len(nodes)):
                    tag, txt = nodes[k]
                    if tag in ('h2', 'h3'):
                        content_parts.append(txt)
                    elif tag in ('p', 'li'):
                        content_parts.append(txt)
            return clean_text('\n'.join(summary_parts)), clean_text('\n'.join(content_parts))

        summary, content = _split_summary_content(nodes)
        if not summary:
            meta_desc = soup.select_one('meta[property="og:description"][content]') or soup.select_one('meta[name="description"][content]')
            if meta_desc and meta_desc.get('content'):
                summary = clean_text(meta_desc['content'])
        if not content:
            # 回退：聚合多个文本容器
            content = ''
            for sel in ['article .cmp-text', 'article .rich-text', 'article .article-content', 'article .content', 'article']:
                node = soup.select_one(sel)
                if node and node.get_text(strip=True):
                    _clean_inline_footnotes(node)
                    content = clean_text(node.get_text('\n'))
                    if content:
                        break
        # 若正文仍过短（<200词），尝试浏览器渲染获取后再解析一次；最后再回退通用解析
        def _word_count(s: str) -> int:
            try:
                return len([w for w in re.split(r'\s+', s.strip()) if w])
            except Exception:
                return 0
        if _word_count(content) < 200:
            # 浏览器渲染兜底（仅 JPM 调用）
            try:
                from selenium.webdriver.chrome.options import Options as _ChromeOptions
                import undetected_chromedriver as _uc
                from selenium.webdriver.common.by import By as _By
                from selenium.webdriver.support.ui import WebDriverWait as _Wait
                from selenium.webdriver.support import expected_conditions as _EC
                _opts = _ChromeOptions()
                try:
                    _opts.page_load_strategy = 'none'
                except Exception:
                    pass
                _opts.add_argument('--disable-blink-features=AutomationControlled')
                _opts.add_argument('--ignore-certificate-errors')
                _opts.add_argument('--ignore-ssl-errors')
                _opts.add_argument('--disable-site-isolation-trials')
                _opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                _driver = _uc.Chrome(options=_opts)
                try:
                    _driver.get(url)
                    try:
                        _Wait(_driver, 20).until(_EC.presence_of_element_located((_By.CSS_SELECTOR, 'main article')))
                        # 文章富文本块
                        _Wait(_driver, 10).until(_EC.presence_of_element_located((_By.CSS_SELECTOR, 'main article .cmp-text--pt, main article .cmp-text')))
                    except Exception:
                        pass
                    html2 = _driver.page_source
                finally:
                    try:
                        _driver.quit()
                    except Exception:
                        pass
                if html2:
                    sp2 = BeautifulSoup(html2, 'lxml')
                    art2 = sp2.select_one('main article') or sp2.select_one('article')
                    nodes2 = _collect_nodes(art2)
                    summary2, content2 = _split_summary_content(nodes2)
                    if summary2:
                        summary = summary2
                    if _word_count(content2) > _word_count(content):
                        content = content2
            except Exception:
                pass
            # 最终回退
            if _word_count(content) < 200:
                alt = generic_content_by_candidates(soup)
                if _word_count(alt) > _word_count(content):
                    content = alt

        # 日期（英文到 YYYY-MM-DD）
        pub = ''
        try:
            import json as _json
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                def _find_date(obj):
                    if isinstance(obj, dict):
                        for k in ['datePublished', 'dateCreated', 'dateModified']:
                            v = obj.get(k)
                            if isinstance(v, str) and re.search(r'\d{4}-\d{1,2}-\d{1,2}', v):
                                return v
                    if isinstance(obj, list):
                        for it in obj:
                            v = _find_date(it)
                            if v:
                                return v
                    return ''
                d = _find_date(data)
                if d:
                    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', d)
                    if m:
                        pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                        break
        except Exception:
            pass
        if not pub:
            meta_time = soup.select_one('meta[property="article:published_time"][content]')
            if meta_time and meta_time.get('content'):
                mt = meta_time['content']
                m2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', mt)
                if m2:
                    pub = f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
        if not pub:
            t = soup.select_one('time[datetime]')
            if t and t.get('datetime'):
                m3 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', t.get('datetime'))
                if m3:
                    pub = f"{int(m3.group(1)):04d}-{int(m3.group(2)):02d}-{int(m3.group(3)):02d}"
        if not pub:
            pub = publish_date or ''

        # 作者：JSON-LD / meta / 页面节点
        authors = ''
        try:
            import json as _json
            names = []
            def _add_name(x):
                if isinstance(x, str) and x.strip():
                    names.append(clean_text(x))
                elif isinstance(x, dict):
                    n = x.get('name') or x.get('author') or x.get('creator')
                    if isinstance(n, str) and n.strip():
                        names.append(clean_text(n))
                    elif isinstance(n, list):
                        for e in n:
                            _add_name(e)
                elif isinstance(x, list):
                    for e in x:
                        _add_name(e)
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                if isinstance(data, dict) and 'author' in data:
                    _add_name(data.get('author'))
                elif isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and 'author' in obj:
                            _add_name(obj.get('author'))
            if not names:
                meta_author = soup.select_one('meta[name="author"][content]')
                if meta_author and meta_author.get('content'):
                    names.append(clean_text(meta_author['content']))
            if not names:
                for sel in ['a[href*="/insights/author" i]', 'a[href*="/authors/" i]', 'span[class*="author" i]', 'p[class*="author" i]', 'div[class*="author" i]']:
                    node = soup.select_one(sel)
                    if node and node.get_text(strip=True):
                        names.append(clean_text(node.get_text()))
                        break
            if names:
                # 去重并保持顺序
                seen = set()
                uniq = []
                for n in names:
                    if n and n not in seen:
                        seen.add(n)
                        uniq.append(n)
                authors = '、'.join(uniq)
        except Exception:
            authors = ''

        # 附件：优先文档，否则音视频
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8']
        file_urls, media_urls = [], []
        container = soup.select_one('article') or soup.select_one('.content') or soup
        if container:
            for a in container.select('a[href]'):
                href = a.get('href', '')
                if not href:
                    continue
                lower = href.lower()
                full = url_join(url, href)
                if any(lower.endswith(ext) for ext in file_exts):
                    file_urls.append(full)
                elif any(lower.endswith(ext) for ext in media_exts):
                    media_urls.append(full)
        # audio/video/iframe 源
        for sel in ['audio source[src]', 'audio[src]', 'video source[src]', 'video[src]', 'iframe[src]']:
            for node in soup.select(sel):
                src = node.get('src', '')
                if not src:
                    continue
                lower = src.lower()
                full = url_join(url, src)
                if any(lower.endswith(ext) for ext in file_exts):
                    file_urls.append(full)
                elif any(ext in lower for ext in media_exts):
                    media_urls.append(full)

        attachments = ''
        if file_urls:
            attachments = ' ; '.join(file_urls)
        elif media_urls:
            attachments = ' ; '.join(media_urls)

        if not title or not content:
            print(f"JPM 文章解析失败，标题或正文为空: {url}")
            return None

        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '摩根大通研究院',
            'summary': summary,
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 JPM 页面失败: {url} 错误: {e}")
        return None

def parse_kpmg_article(soup, url, publish_date):
    """解析 毕马威中国(KPMG) 洞察文章页
    字段规则：
    - title: 优先 h1 或 og:title
    - content: 优先正文容器；兜底 generic_content_by_candidates
    - publish_date: 优先 JSON-LD 的 datePublished/dateCreated/dateModified；
                    其次 meta[article:published_time]；再其次 <time datetime>
                    最终兜底列表页传入 publish_date；统一 YYYY-MM-DD
    - authors: 优先 JSON-LD author；其次 meta[name=author]；再次页面作者节点
    - attachments: 若存在文档附件(\n    .pdf/.doc/.docx/.xls/.xlsx/.ppt/.pptx) 则只返回这些文件；
                   否则若有音/视频(.mp3/.m4a/.wav/.mp4/.m3u8/.mov/.m4v) 返回其 URL；
                   否则为空
    - thinkank_name: 固定 "毕马威中国(KPMG)"
    """
    try:
        # 标题
        title = ''
        title_node = (
            soup.select_one('main article h1') or
            soup.select_one('article h1') or
            soup.select_one('div.article-title h1') or
            soup.select_one('h1')
        )
        if title_node and title_node.get_text(strip=True):
            title = clean_text(title_node.get_text())
        if not title:
            meta_title = soup.select_one('meta[property="og:title"][content]') or soup.select_one('meta[name="title"][content]')
            if meta_title and meta_title.get('content'):
                title = clean_text(meta_title['content'])

        # 正文：优先 main/article 范围内的富文本块，按段落拼接
        content = ''
        def _first_nonempty_text(nodes):
            for n in nodes:
                t = _text_from_container(n)
                if t:
                    return t
            return ''
        main_scope = soup.select_one('main') or soup
        article_scope = main_scope.select_one('article') or main_scope
        candidates = []
        for css in [
            'article .cmp-text', 'article .rich-text', 'article .article-content', 'article .text',
            'div.article-content', 'div.cmp-text', 'div.rich-text', 'section.cmp-text', 'section.text',
            '.parbase.section.text', '.text.parbase', 'div[class*="article"] .cmp-text',
        ]:
            candidates.extend(article_scope.select(css))
        if not candidates:
            # 退而求其次：直接用 article 或 main
            candidates = [article_scope]
        content = _first_nonempty_text(candidates)
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期
        pub = ''
        try:
            import json as _json
            def _find_date(obj):
                if isinstance(obj, dict):
                    for k in ['datePublished', 'dateCreated', 'dateModified']:
                        v = obj.get(k)
                        if isinstance(v, str) and re.search(r'\d{4}-\d{1,2}-\d{1,2}', v):
                            return v
                    # 结构化对象里嵌套情况
                    for v in obj.values():
                        r = _find_date(v)
                        if r:
                            return r
                elif isinstance(obj, list):
                    for it in obj:
                        r = _find_date(it)
                        if r:
                            return r
                return ''
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                d = _find_date(data)
                if d:
                    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', d)
                    if m:
                        pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                        break
        except Exception:
            pass
        if not pub:
            meta_time = soup.select_one('meta[property="article:published_time"][content]')
            if meta_time and meta_time.get('content'):
                mt = meta_time['content']
                m2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', mt)
                if m2:
                    pub = f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
        if not pub:
            t = soup.select_one('time[datetime]')
            if t and t.get('datetime'):
                m3 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', t.get('datetime'))
                if m3:
                    pub = f"{int(m3.group(1)):04d}-{int(m3.group(2)):02d}-{int(m3.group(3)):02d}"
        if not pub:
            pub = publish_date or ''

        # 作者
        authors = ''
        try:
            import json as _json
            names = []
            def _add_name(x):
                if isinstance(x, str) and x.strip():
                    names.append(clean_text(x))
                elif isinstance(x, dict):
                    n = x.get('name') or x.get('author') or x.get('creator')
                    if isinstance(n, str) and n.strip():
                        names.append(clean_text(n))
                    elif isinstance(n, list):
                        for e in n:
                            _add_name(e)
                elif isinstance(x, list):
                    for e in x:
                        _add_name(e)
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                if isinstance(data, dict) and 'author' in data:
                    _add_name(data.get('author'))
                elif isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and 'author' in obj:
                            _add_name(obj.get('author'))
            if not names:
                meta_author = soup.select_one('meta[name="author"][content]')
                if meta_author and meta_author.get('content'):
                    names.append(clean_text(meta_author['content']))
            if not names:
                for sel in [
                    '[class*="author" i]',
                    'a[href*="/people" i]',
                    'a[href*="/authors" i]',
                    'a[href*="/insights/author" i]'
                ]:
                    node = soup.select_one(sel)
                    if node and node.get_text(strip=True):
                        names.append(clean_text(node.get_text()))
                        break
            if names:
                seen = set()
                uniq = []
                for n in names:
                    if n and n not in seen:
                        seen.add(n)
                        uniq.append(n)
                authors = '、'.join(uniq)
        except Exception:
            authors = ''

        # 附件：优先文档，其次音/视频（兼容 data-asset/data-href 及 AEM 资源路径）
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()
        def _maybe_add(u: str):
            if not u:
                return
            lower = u.lower()
            full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts):
                media_urls.add(full)

        scope = article_scope or soup
        # a[href]/data-asset/data-href
        for a in scope.select('a[href], a[data-asset], a[data-href], button[data-asset], button[data-href]'):
            _maybe_add(a.get('href') or a.get('data-asset') or a.get('data-href'))
        # source/src, video/audio/src
        for sel in ['audio source[src]', 'audio[src]', 'video source[src]', 'video[src]', 'iframe[src]']:
            for node in scope.select(sel):
                _maybe_add(node.get('src'))
        # 解析 JSON-LD 中的媒体/附件 URL
        try:
            import json as _json
            def _walk_urls(obj):
                if isinstance(obj, dict):
                    for k in ['contentUrl', 'url', 'embedUrl', 'downloadUrl']:
                        v = obj.get(k)
                        if isinstance(v, str):
                            _maybe_add(v)
                    for v in obj.values():
                        _walk_urls(v)
                elif isinstance(obj, list):
                    for it in obj:
                        _walk_urls(it)
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                _walk_urls(data)
        except Exception:
            pass

        attachments = ''
        if file_urls:
            attachments = ' ; '.join(sorted(file_urls))
        elif media_urls:
            attachments = ' ; '.join(sorted(media_urls))

        if not title or not content:
            print(f"KPMG 文章解析失败：标题或正文为空: {url}")
            return None

        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '毕马威中国(KPMG)',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 KPMG 页面失败: {url} 错误: {e}")
        return None

def parse_mck_article(soup, url, publish_date):
    """解析 麦肯锡中国（McKinsey & Company） 洞察文章页
    字段规则：
    - title: 优先 h1 或 og:title
    - content: 优先正文容器；兜底 generic_content_by_candidates
    - publish_date: 优先 JSON-LD 的 datePublished/dateCreated/dateModified；
                    其次 meta[article:published_time]；再其次 <time datetime>
                    最终兜底列表页传入 publish_date；统一 YYYY-MM-DD
    - authors: 优先 JSON-LD author；其次 meta[name=author]；再次页面作者节点（class*="author" / /authors/ /people/）
    - attachments: 若存在文档附件(.pdf/.doc/.docx/.xls/.xlsx/.ppt/.pptx) 则只返回这些文件；
                   否则若有音/视频(.mp3/.m4a/.wav/.mp4/.m3u8/.mov/.m4v) 返回其 URL；
                   否则为空
    - thinkank_name: 固定 "麦肯锡中国（McKinsey & Company）"
    """
    try:
        # 标题：h1 > og:title
        title = ''
        title_node = (
            soup.select_one('h1') or
            soup.select_one('.article-title h1') or
            soup.select_one('.title h1')
        )
        if title_node and title_node.get_text(strip=True):
            title = clean_text(title_node.get_text())
        if not title:
            meta_title = soup.select_one('meta[property="og:title"][content]') or soup.select_one('meta[name="title"][content]')
            if meta_title and meta_title.get('content'):
                title = clean_text(meta_title['content'])

        # 正文：优先文章容器的富文本块
        def _first_nonempty_text(nodes):
            for n in nodes or []:
                t = n.get_text("\n", strip=True)
                if t:
                    return clean_text(t)
            return ''

        main_scope = soup.select_one('main') or soup
        article_scope = soup.select_one('article') or main_scope
        candidates = []
        for css in [
            'article .cmp-text', 'article .rich-text', 'article .article-content', 'article .text',
            'div.article-content', 'div.cmp-text', 'div.rich-text', 'section.cmp-text', 'section.text',
            '.parbase.section.text', '.text.parbase', 'div[class*="article" i] .cmp-text',
        ]:
            candidates.extend(article_scope.select(css))
        if not candidates:
            candidates = [article_scope]
        content = _first_nonempty_text(candidates)
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期：JSON-LD / meta / time[datetime]
        pub = ''
        try:
            import json as _json
            def _find_date(obj):
                if isinstance(obj, dict):
                    for k in ['datePublished', 'dateCreated', 'dateModified']:
                        v = obj.get(k)
                        if isinstance(v, str) and re.search(r'\d{4}-\d{1,2}-\d{1,2}', v):
                            return v
                    for v in obj.values():
                        r = _find_date(v)
                        if r:
                            return r
                elif isinstance(obj, list):
                    for it in obj:
                        r = _find_date(it)
                        if r:
                            return r
                return ''
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                d = _find_date(data)
                if d:
                    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', d)
                    if m:
                        pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                        break
        except Exception:
            pass
        if not pub:
            meta_time = soup.select_one('meta[property="article:published_time"][content]')
            if meta_time and meta_time.get('content'):
                mt = meta_time['content']
                m2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', mt)
                if m2:
                    pub = f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
        if not pub:
            t = soup.select_one('time[datetime]')
            if t and t.get('datetime'):
                m3 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', t.get('datetime'))
                if m3:
                    pub = f"{int(m3.group(1)):04d}-{int(m3.group(2)):02d}-{int(m3.group(3)):02d}"
        if not pub:
            pub = publish_date or ''

        # 作者：JSON-LD author > meta[name=author] > 页面节点
        authors = ''
        try:
            import json as _json
            names = []
            def _add_name(x):
                if isinstance(x, str) and x.strip():
                    names.append(clean_text(x))
                elif isinstance(x, dict):
                    n = x.get('name') or x.get('author') or x.get('creator')
                    if isinstance(n, str) and n.strip():
                        names.append(clean_text(n))
                    elif isinstance(n, list):
                        for e in n:
                            _add_name(e)
                elif isinstance(x, list):
                    for e in x:
                        _add_name(e)
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                if isinstance(data, dict) and 'author' in data:
                    _add_name(data.get('author'))
                elif isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and 'author' in obj:
                            _add_name(obj.get('author'))
            if not names:
                meta_author = soup.select_one('meta[name="author"][content]')
                if meta_author and meta_author.get('content'):
                    names.append(clean_text(meta_author['content']))
            if not names:
                for sel in [
                    '[class*="author" i]',
                    'a[href*="/authors" i]',
                    'a[href*="/author" i]',
                    'a[href*="/people" i]'
                ]:
                    node = soup.select_one(sel)
                    if node and node.get_text(strip=True):
                        names.append(clean_text(node.get_text()))
                        break
            if names:
                seen = set()
                uniq = []
                for n in names:
                    if n and n not in seen:
                        seen.add(n)
                        uniq.append(n)
                authors = '、'.join(uniq)
        except Exception:
            authors = ''

        # 附件：优先文档，其次音/视频
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()
        def _maybe_add(u: str):
            if not u:
                return
            lower = u.lower()
            full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts) or any(x in lower for x in media_exts):
                media_urls.add(full)

        scope = article_scope or soup
        for a in scope.select('a[href], a[data-asset], a[data-href], a[data-url], button[data-asset], button[data-href], button[data-url]'):
            _maybe_add(a.get('href') or a.get('data-asset') or a.get('data-href') or a.get('data-url'))
        for sel in ['audio source[src]', 'audio[src]', 'video source[src]', 'video[src]', 'iframe[src]']:
            for node in scope.select(sel):
                _maybe_add(node.get('src'))

        attachments = ''
        if file_urls:
            attachments = ' ; '.join(sorted(file_urls))
        elif media_urls:
            attachments = ' ; '.join(sorted(media_urls))

        if not title or not content:
            print(f"MCK 文章解析失败：标题或正文为空: {url}")
            return None

        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '麦肯锡中国（McKinsey & Company）',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 MCK 页面失败: {url} 错误: {e}")
        return None

def parse_pwc_article(soup, url, publish_date):
    """解析 普华永道（PwC）中国 洞察文章页
    规则：
    - title: 优先 h1 或 og:title
    - content: 优先 article/main 范围的富文本块（.cmp-text/.rich-text/.article-content 等）；兜底通用提取
    - publish_date: 优先 JSON-LD datePublished/dateCreated/dateModified；
                    其次 meta[article:published_time]；再其次 <time datetime>；
                    最终兜底列表页传入 publish_date；统一 YYYY-MM-DD
    - authors: 优先 JSON-LD author；其次 meta[name=author]；再次页面作者节点（class*="author" / /authors/ /people/）
    - attachments: 若存在文档类附件(.pdf/.doc/.docx/.xls/.xlsx/.ppt/.pptx) 则仅返回这些文件；
                   若无文档但有音/视频(.mp3/.m4a/.wav/.mp4/.m3u8/.mov/.m4v) 则返回其 URL；
                   若文件与音/视频并存，仅保留文件附件
    - thinkank_name: 固定 "普华永道（PwC）"
    """
    try:
        # 标题
        title = ''
        title_node = (
            soup.select_one('h1') or
            soup.select_one('.article-title h1') or
            soup.select_one('.title h1')
        )
        if title_node and title_node.get_text(strip=True):
            title = clean_text(title_node.get_text())
        if not title:
            meta_title = soup.select_one('meta[property="og:title"][content]') or soup.select_one('meta[name="title"][content]')
            if meta_title and meta_title.get('content'):
                title = clean_text(meta_title['content'])

        # 正文
        def _first_nonempty_text(nodes):
            for n in nodes or []:
                t = n.get_text("\n", strip=True)
                if t:
                    return clean_text(t)
            return ''

        main_scope = soup.select_one('main') or soup
        article_scope = main_scope.select_one('article') or main_scope
        candidates = []
        for css in [
            'article .cmp-text', 'article .rich-text', 'article .article-content', 'article .text',
            'div.article-content', 'div.cmp-text', 'div.rich-text', 'section.cmp-text', 'section.text',
            '.parbase.section.text', '.text.parbase', 'div[class*="article" i] .cmp-text',
        ]:
            candidates.extend(article_scope.select(css))
        if not candidates:
            candidates = [article_scope]
        content = _first_nonempty_text(candidates)
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期：JSON-LD / meta / time[datetime]
        pub = ''
        try:
            import json as _json
            def _find_date(obj):
                if isinstance(obj, dict):
                    for k in ['datePublished', 'dateCreated', 'dateModified']:
                        v = obj.get(k)
                        if isinstance(v, str) and re.search(r'\d{4}-\d{1,2}-\d{1,2}', v):
                            return v
                    for v in obj.values():
                        r = _find_date(v)
                        if r:
                            return r
                elif isinstance(obj, list):
                    for it in obj:
                        r = _find_date(it)
                        if r:
                            return r
                return ''
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                d = _find_date(data)
                if d:
                    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', d)
                    if m:
                        pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                        break
        except Exception:
            pass
        if not pub:
            meta_time = soup.select_one('meta[property="article:published_time"][content]')
            if meta_time and meta_time.get('content'):
                mt = meta_time['content']
                m2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', mt)
                if m2:
                    pub = f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
        if not pub:
            t = soup.select_one('time[datetime]')
            if t and t.get('datetime'):
                m3 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', t.get('datetime'))
                if m3:
                    pub = f"{int(m3.group(1)):04d}-{int(m3.group(2)):02d}-{int(m3.group(3)):02d}"
        if not pub:
            pub = publish_date or ''

        # 作者：JSON-LD / meta / 页面节点
        authors = ''
        try:
            import json as _json
            names = []
            def _add_name(x):
                if isinstance(x, str) and x.strip():
                    names.append(clean_text(x))
                elif isinstance(x, dict):
                    n = x.get('name') or x.get('author') or x.get('creator')
                    if isinstance(n, str) and n.strip():
                        names.append(clean_text(n))
                    elif isinstance(n, list):
                        for e in n:
                            _add_name(e)
                elif isinstance(x, list):
                    for e in x:
                        _add_name(e)
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                if isinstance(data, dict) and 'author' in data:
                    _add_name(data.get('author'))
                elif isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and 'author' in obj:
                            _add_name(obj.get('author'))
            if not names:
                meta_author = soup.select_one('meta[name="author"][content]')
                if meta_author and meta_author.get('content'):
                    names.append(clean_text(meta_author['content']))
            if not names:
                for sel in [
                    '[class*="author" i]',
                    'a[href*="/people" i]',
                    'a[href*="/authors" i]',
                    'a[href*="/insights/author" i]'
                ]:
                    node = soup.select_one(sel)
                    if node and node.get_text(strip=True):
                        names.append(clean_text(node.get_text()))
                        break
            if names:
                seen = set()
                uniq = []
                for n in names:
                    if n and n not in seen:
                        seen.add(n)
                        uniq.append(n)
                authors = '、'.join(uniq)
        except Exception:
            authors = ''

        # 附件：优先文档，其次音/视频
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()
        def _maybe_add(u: str):
            if not u:
                return
            lower = u.lower()
            full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts) or any(x in lower for x in media_exts):
                media_urls.add(full)

        scope = article_scope or soup
        for a in scope.select('a[href], a[data-asset], a[data-href], a[data-url], button[data-asset], button[data-href], button[data-url]'):
            _maybe_add(a.get('href') or a.get('data-asset') or a.get('data-href') or a.get('data-url'))
        for sel in ['audio source[src]', 'audio[src]', 'video source[src]', 'video[src]', 'iframe[src]']:
            for node in scope.select(sel):
                _maybe_add(node.get('src'))

        attachments = ''
        if file_urls:
            attachments = ' ; '.join(sorted(file_urls))
        elif media_urls:
            attachments = ' ; '.join(sorted(media_urls))

        if not title or not content:
            print(f"PwC 文章解析失败：标题或正文为空: {url}")
            return None

        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '普华永道（PwC）',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 PwC 页面失败: {url} 错误: {e}")
        return None

def parse_wechat_article(soup, url, publish_date):
    """解析微信文章（mp.weixin.qq.com）"""
    try:
        def norm_date_from_ct(ct_val: str) -> str:
            try:
                import datetime
                ts = int(ct_val)
                dt = datetime.datetime.fromtimestamp(ts)
                return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
            except Exception:
                return ''

        # 标题
        title_node = (
            soup.select_one('h1#activity-name') or
            soup.select_one('h1.rich_media_title') or
            soup.select_one('meta[property="og:title"][content]')
        )
        title = ''
        if title_node:
            if getattr(title_node, 'name', '') == 'meta' and title_node.get('content'):
                title = clean_text(title_node['content'])
            else:
                title = clean_text(title_node.get_text())
        if not title:
            title = generic_title_from_meta_or_h(soup)

        # 正文
        content_node = soup.select_one('#js_content') or soup.select_one('div#js_content')
        content = clean_text(content_node.get_text("\n")) if content_node else generic_content_by_candidates(soup)

        # 发表日期
        pub_node = soup.select_one('#publish_time') or soup.select_one('span#publish_time')
        pub = clean_text(pub_node.get_text()) if pub_node else ''
        if not pub:
            # 部分页面在脚本变量中存放 ct（秒级时间戳）
            for sc in soup.find_all('script'):
                txt = sc.get_text() or ''
                m = re.search(r"var\s+ct\s*=\s*\"(\d+)\"", txt)
                if m:
                    pub = norm_date_from_ct(m.group(1))
                    break
        if not pub:
            # meta 兜底
            meta_pub = soup.select_one('meta[property="og:release_date"][content]')
            if meta_pub and meta_pub.get('content'):
                pub = clean_text(meta_pub['content'])
        if not pub:
            pub = publish_date or ''

        if not title or not content:
            print(f"微信文章解析失败，标题或内容为空: {url}")
            return None

        data = {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': '北京大学国家发展研究院',
            'thinkank_name': '北京大学国家发展研究院',
            'summary': '',
            'content': content,
            'attachments': '',
            'crawl_date': get_current_date()
        }
        return data
    except Exception as e:
        print(f"解析微信页面 {url} 失败: {e}")
        return None

def parse_nsd_article(soup, url, publish_date):
    """解析北京大学国家发展研究院站内文章"""
    try:
        # 标题候选
        title_selectors = [
            'h1', '.title h1', '.article-title', '.arti_title', '.wp_article_title', '.news-title'
        ]
        content_selectors = [
            '.TRS_Editor', '.v_news_content', '.wp_articlecontent', '.article-content', '.content', '#content', '.text', '.read'
        ]
        title = ''
        for sel in title_selectors:
            node = soup.select_one(sel)
            if node and node.get_text(strip=True):
                title = clean_text(node.get_text())
                break
        content = ''
        for sel in content_selectors:
            node = soup.select_one(sel)
            if node and node.get_text(strip=True):
                content = clean_text(node.get_text("\n"))
                break
        if not title:
            title = generic_title_from_meta_or_h(soup)
        if not content:
            content = generic_content_by_candidates(soup)
        if not title or not content:
            print(f"NSD文章解析失败，标题或内容为空: {url}")
            return None
        data = {
            'title': title,
            'url': url,
            'publish_date': publish_date,
            'authors': '北京大学国家发展研究院',
            'thinkank_name': '北京大学国家发展研究院',
            'summary': '',
            'content': content,
            'attachments': '',
            'crawl_date': get_current_date()
        }
        return data
    except Exception as e:
        print(f"解析NSD页面 {url} 失败: {e}")
        return None

def crawl_article_content(url, publish_date, headers, title_hint=None):
    """爬取文章内容的通用函数
    - 对大多数站点：延续原有 15s 超时、重试 3 次策略；
    - 定制域（mckinsey.com.cn）：增加 HEAD 预检（快速失败），减少重试并缩短重试间隔以避免长尾超时。
    """
    # 默认重试与超时策略
    default_retry = 3
    default_timeout = 15
    default_retry_sleep = 2

    html = None
    lower_url = url.lower()

    # MCKINSEY DISABLED: 跳过麦肯锡中国详情抓取，避免拖慢总体时间
    if ('mckinsey.com.cn' in lower_url) or ('www.mckinsey.com.cn' in lower_url):
        try:
            print(f"跳过麦肯锡详情（内页爬取已禁用）：{url}")
        except Exception:
            pass
        return None

    # 按域名定制请求头（例如微信需要 Referer）
    req_headers = dict(headers or {})
    if 'mp.weixin.qq.com' in lower_url and 'Referer' not in req_headers:
        req_headers['Referer'] = 'https://weixin.sogou.com/'
        req_headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        req_headers.setdefault('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8')
        req_headers.setdefault('Upgrade-Insecure-Requests', '1')

    # 直接文件链接（如月报 PDF/DOCX 等）
    if any(lower_url.endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
        data = {}
        data['title'] = title_hint or clean_text(lower_url.split('/')[-1])
        data['url'] = url
        data['publish_date'] = publish_date
        if 'cdi.com.cn' in lower_url:
            data['authors'] = '综合开发研究院（中国·深圳）'
            data['thinkank_name'] = '综合开发研究院（中国·深圳）'
        else:
            data['authors'] = ''
            data['thinkank_name'] = ''
        data['summary'] = ''
        data['content'] = ''
        data['attachments'] = url
        data['crawl_date'] = get_current_date()
        return data

    # 域名定制：麦肯锡中国（已禁用）保留默认策略变量
    is_mck = False
    retry_count = default_retry
    req_timeout = default_timeout
    retry_sleep = default_retry_sleep

    # GET 抓取（带重试）
    while retry_count > 0:
        try:
            html = requests.get(url=url, headers=req_headers, timeout=req_timeout, proxies=NO_PROXIES)
            # 优先使用服务端声明编码，其次使用 apparent_encoding，最后退回 utf-8
            if not html.encoding or html.encoding.lower() in ['iso-8859-1', 'ascii']:
                html.encoding = html.apparent_encoding or 'utf-8'
            break  # 成功获取则退出重试循环
        except RequestException as e:
            retry_count -= 1
            print(f"请求 {url} 失败: {e}，剩余重试次数: {retry_count}")
            if retry_count == 0:
                print(f"多次请求失败，跳过该链接: {url}")
                return None
            time.sleep(retry_sleep)
    
    if not html or html.status_code != 200:
        print(f"请求失败，状态码: {html.status_code if html else 'None'}")
        return None
    
    try:
        soup = BeautifulSoup(html.text, 'lxml')
        
        # 根据URL判断使用哪个解析函数
        if 'www.ciecc.com.cn' in url:
            return parse_ciecc_article(soup, url, publish_date)
        elif 'nads.ruc.edu.cn' in url:
            return parse_ruc_article(soup, url, publish_date)
        elif 'www.drc.gov.cn' in url:
            return parse_drc_article(soup, url, publish_date)
        elif 'www.cas.cn' in url:
            return parse_cas_article(soup, url, publish_date)
        elif 'www.amr.org.cn' in url:
            return parse_amr_article(soup, url, publish_date)
        elif 'www.ccidgroup.com' in url:
            return parse_ccid_article(soup, url, publish_date)
        elif 'www.sass.org.cn' in url:
            return parse_sass_article(soup, url, publish_date)
        elif 'www.cdi.com.cn' in url or 'cdi.com.cn' in url:
            return parse_cdi_article(soup, url, publish_date)
        elif 'pwccn.com' in url or 'www.pwccn.com' in url:
            return parse_pwc_article(soup, url, publish_date)
        elif 'kpmg.com' in url or 'www.kpmg.com' in url:
            return parse_kpmg_article(soup, url, publish_date)
        # elif 'mckinsey.com.cn' in url or 'www.mckinsey.com.cn' in url:
        #     # MCKINSEY DISABLED: 内页爬取已禁用
        #     return parse_mck_article(soup, url, publish_date)
        elif 'jpmorgan.com' in url or 'www.jpmorgan.com' in url:
            return parse_jpm_article(soup, url, publish_date)
        elif 'www.rand.org' in url or 'rand.org' in url:
            # 使用改进版解析器，优先提取摘要正文
            return parse_rand_article2(soup, url, publish_date)
        elif 'mp.weixin.qq.com' in url:
            return parse_wechat_article(soup, url, publish_date)
        elif 'nsd.pku.edu.cn' in url:
            return parse_nsd_article(soup, url, publish_date)
        else:
            print(f"未知网站，无法解析: {url}")
            return None
            
    except Exception as e:
        print(f"解析页面 {url} 失败: {e}")
        return None

def main(only_domain: str = ''):
    """主函数"""
    print("开始爬取智库文章内容...")
    
    lst = []  # 本次新增内容
    # 读取已有输出，准备跳过已抓取的 URL
    OUTPUT_JSON_PATH = 'output_complete.json'
    existing_items, seen_urls = load_existing_results(OUTPUT_JSON_PATH)
    print(f"已载入历史条目 {len(existing_items)} 条，将跳过重复 URL")
    run_seen_urls = set()  # 本轮去重，避免同一次运行内重复抓取
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0'
    }
    
    try:
        # 读取生成的HTML文件
        with open('generated_html/index.html', 'r', encoding='utf-8') as f:
            s = f.read()
        
        soup = BeautifulSoup(s, 'lxml')
        sj_lst = soup.select('.page-board-item')
        if only_domain:
            def _u(node):
                try:
                    return node.select('a')[0]['href']
                except Exception:
                    return ''
            sj_lst = [m for m in sj_lst if only_domain.lower() in (_u(m) or '').lower()]
        if len(sj_lst) == 0:
            print("聚合页没有发现条目，启用 CDI 栏目直抓模式...")
            def norm_date(text: str) -> str:
                if not text:
                    return ''
                m = re.search(r'(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})', text)
                if m:
                    y, m1, d = m.groups()
                    return f"{int(y):04d}-{int(m1):02d}-{int(d):02d}"
                return text
            def fetch(url: str):
                for _ in range(3):
                    try:
                        r = requests.get(url, headers=headers, timeout=15, proxies=NO_PROXIES)
                        if not r.encoding or r.encoding.lower() in ['iso-8859-1', 'ascii']:
                            r.encoding = r.apparent_encoding or 'utf-8'
                        if r.status_code == 200:
                            return r.text
                    except RequestException:
                        time.sleep(1)
                return ''
            base = 'http://www.cdi.com.cn'
            columns = [102, 152, 150, 153, 154]
            max_pages = 2
            detail_tasks = []
            for cid in columns:
                for p in range(1, max_pages + 1):
                    url = f"{base}/Article/List?ColumnId={cid}" + ('' if p == 1 else f"&pageIndex={p}")
                    html = fetch(url)
                    if not html:
                        continue
                    sp = BeautifulSoup(html, 'lxml')
                    ul = sp.select_one('ul#ColumnsList')
                    if not ul:
                        continue
                    for li in ul.select('li'):
                        a = li.select_one('div.img a') or li.select_one('div.details a.a-full') or li.select_one('a')
                        if not a or not a.get('href'):
                            continue
                        link = url_join(url, a['href'])
                        title_node = li.select_one('div.info span') or li.select_one('span')
                        title_hint = clean_text(title_node.get_text()) if title_node else ''
                        em = li.select_one('div.info em') or li.select_one('em')
                        pub = norm_date(em.get_text()) if em else ''
                        detail_tasks.append((link, pub, title_hint))
            for p in range(1, max_pages + 1):
                url = f"{base}/Files/ListYear?ColumnId=155" + ('' if p == 1 else f"&pageIndex={p}")
                html = fetch(url)
                if not html:
                    continue
                sp = BeautifulSoup(html, 'lxml')
                container = sp.select_one('div#ColumnsList')
                if not container:
                    continue
                for a in container.select('ul.setimage320 li a.item'):
                    if not a.get('href'):
                        continue
                    link = url_join(url, a['href'])
                    info_span = a.select_one('div.info span')
                    title_hint = clean_text(info_span.get_text()) if info_span else ''
                    em = a.select_one('div.info em')
                    pub = norm_date(em.get_text()) if em else ''
                    detail_tasks.append((link, pub, title_hint))
            # 过滤已存在的 URL，避免重复抓取
            _filtered = []
            _skip_cnt = 0
            for (_u, _pub, _t) in detail_tasks:
                _nu = normalize_url(_u)
                if (not _nu) or (_nu in seen_urls) or (_nu in run_seen_urls):
                    _skip_cnt += 1
                    continue
                run_seen_urls.add(_nu)
                _filtered.append((_u, _pub, _t))
            detail_tasks = _filtered
            print(f"已从直抓任务中过滤已存在 {_skip_cnt} 条，剩余 {len(detail_tasks)} 条需要处理")
            print(f"直抓模式共发现 {len(detail_tasks)} 篇文章/文件，开始逐条解析...")
            for i, (u, pub, t_hint) in enumerate(detail_tasks, 1):
                try:
                    print(f"[{i}/{len(detail_tasks)}] {u}")
                    data = crawl_article_content(u, pub, headers, title_hint=t_hint)
                    if data:
                        lst.append(data)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"处理 {u} 出错: {e}")
        
        print(f"找到 {len(sj_lst)} 篇文章需要爬取" + (f"（仅域名 {only_domain}）" if only_domain else ""))
        
        # 遍历每篇文章
        total_cnt = len(sj_lst)
        skipped_cnt = 0
        for i, m in enumerate(sj_lst, 1):
            try:
                url = m.select('a')[0]['href']
                publish_date = m.select('span')[0].text
                # 已存在则跳过（先于正文抓取与标题获取）
                nu = normalize_url(url)
                if (not nu) or (nu in seen_urls) or (nu in run_seen_urls):
                    skipped_cnt += 1
                    continue
                run_seen_urls.add(nu)
                # 从聚合页获取标题作为 hint（用于文件型链接）
                try:
                    title_hint = clean_text(m.select('h3')[0].get_text())
                except Exception:
                    title_hint = ''
                
                print(f"正在处理第 {i}/{len(sj_lst)} 篇文章: {url}")
                
                # 爬取文章内容
                data = crawl_article_content(url, publish_date, headers, title_hint=title_hint)
                
                if data:
                    lst.append(data)
                    print(f"成功爬取: {data['title'][:50]}...")
                else:
                    print(f"爬取失败: {url}")
                
                # 添加延迟，避免请求过于频繁
                time.sleep(1)
                
            except (IndexError, KeyError) as e:
                print(f"获取链接失败: {e}，跳过当前项")
                continue
            except Exception as e:
                print(f"处理文章时发生错误: {e}，跳过当前项")
                continue
        
        print(f"爬取完成，共成功爬取 {len(lst)} 篇文章")
        
        # 输出：仅在有新增时，将新增内容追加至历史结果尾部
        if lst:
            combined = existing_items + lst
            with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(combined, f, ensure_ascii=False, indent=2, default=str)
            print(f"已保存到 {OUTPUT_JSON_PATH}，新增 {len(lst)} 条，累计 {len(combined)} 条")
        else:
            print("无新增内容，保留已有 output_complete.json")
    except Exception as e:
        print(f"程序执行过程中发生错误: {e}")

def _identify_problematic_rand_urls_from_file(json_path='output_complete.json'):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []
    urls = []
    import re
    for it in data:
        u = (it.get('url') or '').lower()
        if 'rand.org' not in u:
            continue
        content = (it.get('content') or '').strip()
        too_short = len(content) < 300
        meta_sign = bool(re.search(r'(Published in:|Posted on rand\.org|RESEARCH\s+—|Published on|This commentary was originally published|RAND Europe|Keywords:)', content, re.I))
        if too_short or meta_sign:
            urls.append(it.get('url'))
    return urls

def _remove_items_by_urls_file(json_path, remove_urls):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = []
    s = set(remove_urls or [])
    kept = [it for it in data if (it.get('url') or '') not in s]
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2, default=str)
    return len(data), len(kept)


if __name__ == "__main__":
    import sys
    # JPM repair helpers (content too short => re-crawl). Threshold: 200 words.
    def _count_words_en(s: str) -> int:
        try:
            return len([w for w in re.split(r'\s+', (s or '').strip()) if w])
        except Exception:
            return 0

    def _identify_problematic_jpm_urls_from_file(json_path='output_complete.json', word_threshold=200):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return []
        urls = []
        for it in data:
            u = (it.get('url') or '').lower()
            if 'jpmorgan.com' not in u:
                continue
            content = (it.get('content') or '').strip()
            if _count_words_en(content) < word_threshold:
                urls.append(it.get('url'))
        return urls
    if len(sys.argv) > 1 and sys.argv[1] == '--repair-rand':
        urls = _identify_problematic_rand_urls_from_file('output_complete.json')
        print(f"检测到需修复的 RAND 条目: {len(urls)}")
        before, after = _remove_items_by_urls_file('output_complete.json', urls)
        print(f"已移除 {before-after} 条，剩余 {after} 条。")
    elif len(sys.argv) > 1 and sys.argv[1] == '--repair-jpm':
        urls = _identify_problematic_jpm_urls_from_file('output_complete.json', word_threshold=200)
        print(f"检测到待修复的 JPM 条目: {len(urls)} (content 词数 < 200)")
        before, after = _remove_items_by_urls_file('output_complete.json', urls)
        print(f"已移除 {before-after} 条，剩余 {after} 条。请再次运行本脚本以重抓这些链接。")
    elif len(sys.argv) > 2 and sys.argv[1] == '--only-domain':
        dom = sys.argv[2]
        main(only_domain=dom)
    else:
        main()
