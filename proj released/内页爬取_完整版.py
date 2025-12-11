import json
import re
import time
from datetime import datetime
from urllib.parse import urljoin as url_join

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# 明确禁用系统代理，避免 HTTPS 站点走到失效代理
NO_PROXIES = {"http": None, "https": None}


# ------------------------------ 通用工具 ------------------------------
def get_current_date():
    return datetime.now().date()


def clean_text(text: str) -> str:
    if not text:
        return ''
    return re.sub(r"\s+", " ", text.strip())


def generic_title_from_meta_or_h(soup: BeautifulSoup) -> str:
    m = soup.select_one('meta[property="og:title"][content]') or soup.select_one('meta[name="title"][content]')
    if m and m.get('content'):
        return clean_text(m['content'])
    for sel in ['h1', '.title h1', '.article-title h1', 'h2']:
        n = soup.select_one(sel)
        if n and n.get_text(strip=True):
            return clean_text(n.get_text())
    if soup.title and soup.title.string:
        return clean_text(soup.title.string)
    return ''


def generic_content_by_candidates(soup: BeautifulSoup) -> str:
    for tag in soup(['script', 'style', 'noscript']):
        tag.extract()
    candidates = [
        'article', '.article-content', '.content', '.text', '.cmp-text', '.rich-text', '#content'
    ]
    for sel in candidates:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            return clean_text(node.get_text("\n"))
    # 兜底：取文本量最大的块
    max_text = ''
    max_len = 0
    for node in soup.find_all(['article', 'section', 'div']):
        t = node.get_text("\n", strip=True)
        if len(t) > max_len:
            max_len = len(t)
            max_text = t
    return clean_text(max_text)


def normalize_url(u: str) -> str:
    try:
        from urllib.parse import urlparse, urlunparse
        u = (u or '').strip()
        parts = urlparse(u)
        if not parts.scheme:
            return u
        norm = parts._replace(scheme=parts.scheme.lower(), netloc=parts.netloc.lower(), fragment='')
        return urlunparse(norm)
    except Exception:
        return u or ''


def load_existing_results(json_path: str):
    items = []
    seen = set()
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                items = data
                for it in data:
                    u = normalize_url(it.get('url', ''))
                    if u:
                        seen.add(u)
    except Exception:
        pass
    return items, seen


# ------------------------------ 站点解析：BCG ------------------------------
def parse_bcg_article(soup: BeautifulSoup, url: str, publish_date: str):
    try:
        # 标题
        title = ''
        tnode = soup.select_one('h1') or soup.select_one('.article-title h1') or soup.select_one('.title h1')
        if tnode and tnode.get_text(strip=True):
            title = clean_text(tnode.get_text())
        if not title:
            title = generic_title_from_meta_or_h(soup)

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
            'article .rich-text', 'article .text', 'article .article-content', 'article .cmp-text',
            'div.rich-text', 'div.article-content', 'div.cmp-text', 'section.cmp-text', 'section.text',
        ]:
            candidates.extend(article_scope.select(css))
        if not candidates:
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
            def _add(x):
                if isinstance(x, str) and x.strip():
                    names.append(clean_text(x))
                elif isinstance(x, dict):
                    n = x.get('name') or x.get('author') or x.get('creator')
                    if isinstance(n, str) and n.strip():
                        names.append(clean_text(n))
                    elif isinstance(n, list):
                        for e in n:
                            _add(e)
                elif isinstance(x, list):
                    for e in x:
                        _add(e)
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                if isinstance(data, dict) and 'author' in data:
                    _add(data.get('author'))
                elif isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and 'author' in obj:
                            _add(obj.get('author'))
            if not names:
                meta_author = soup.select_one('meta[name="author"][content]')
                if meta_author and meta_author.get('content'):
                    names.append(clean_text(meta_author['content']))
            if not names:
                for sel in ['[class*="author" i]', 'a[href*="/people" i]', 'a[href*="/experts" i]']:
                    node = soup.select_one(sel)
                    if node and node.get_text(strip=True):
                        names.append(clean_text(node.get_text()))
                        break
            if names:
                seen = set(); uniq = []
                for n in names:
                    if n and n not in seen:
                        seen.add(n); uniq.append(n)
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
            lower = u.lower(); full = url_join(url, u)
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
            print(f"BCG 文章解析失败：标题或正文为空: {url}")
            return None
        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '波士顿咨询（BCG）',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 BCG 页面失败: {url} 错误: {e}")
        return None


def parse_bain_article(soup: BeautifulSoup, url: str, publish_date: str):
    """
    解析贝恩咨询（bain.cn）文章页：
    - 标题：优先 detail-content > .content-title h3；兜底 h1 / meta og:title / <title>
    - 正文：优先 detail-content > .content 段落文本；若抓空再回退通用提取
    - 日期：优先 meta/time；缺失则使用列表页日期
    - 作者：尝试从 meta[name=author]、正文“作者信息”块提取作者姓名
    - 附件：优先文档（pdf/doc/xls/ppt 等）；若仅有音/视频则返回其 URL；并存时仅保留文档
    - thinkank_name：统一填写为“贝恩咨询（Bain & Company）”
    """
    try:
        # 标题
        title = ''
        t = soup.select_one('div.detail-content .content-title h3') or soup.select_one('h1')
        if t and t.get_text(strip=True):
            title = clean_text(t.get_text())
        if not title:
            title = generic_title_from_meta_or_h(soup)

        # 正文：尽量按段落拼接，避免空段落与冗余样式干扰
        content = ''
        main_scope = soup.select_one('div.detail-content') or soup
        body = main_scope.select_one('div.content') or main_scope
        if body is not None:
            paras = []
            for node in body.select('p, li, h2, h3, h4'):
                txt = (node.get_text('\n', strip=True) or '').strip()
                # 跳过纯空/仅符号段落
                if not txt or len(txt.replace('\u3000', '').replace('\xa0', '').strip()) == 0:
                    continue
                paras.append(clean_text(txt))
            if not paras:
                # 兜底：直接取整个 body 文本
                bulk = body.get_text('\n', strip=True)
                if bulk:
                    content = clean_text(bulk)
            else:
                content = ' '.join(paras)
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期
        pub = ''
        try:
            mt = soup.select_one('meta[property="article:published_time"][content]')
            if mt and mt.get('content'):
                m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', mt['content'])
                if m:
                    pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            if not pub:
                tnode = soup.select_one('time[datetime]')
                if tnode and tnode.get('datetime'):
                    m2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', tnode['datetime'])
                    if m2:
                        pub = f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
        except Exception:
            pass
        if not pub:
            pub = publish_date or ''

        # 作者（可检测到则填写）
        authors = ''
        try:
            # meta 优先
            meta_author = soup.select_one('meta[name="author"][content]')
            if meta_author and meta_author.get('content'):
                authors = clean_text(meta_author['content'])
            if not authors:
                # 正文“作者信息”：定位包含“作者信息”的段落，收集其后的若干非空行
                scope = main_scope
                ps = scope.select('div.content p') or scope.select('p')
                idx = -1
                for i, p in enumerate(ps):
                    t0 = p.get_text(strip=True)
                    if t0 and ('作者信息' in t0 or '作者' in t0):
                        idx = i
                        break
                names = []
                if idx >= 0:
                    for j in range(idx + 1, min(idx + 6, len(ps))):  # 向后取最多 5 段
                        txt = (ps[j].get_text(' ', strip=True) or '').strip()
                        if not txt:
                            break
                        # 截断头尾标点/空字符
                        names.append(clean_text(txt))
                if names:
                    # 仅保留前两行作者简介中的姓名（逗号/顿号/空格分隔，取每行第一段）
                    extra = []
                    for line in names[:3]:
                        head = re.split(r'[，,\s]', line, maxsplit=1)[0]
                        if head:
                            extra.append(head)
                    if extra:
                        # 去重
                        seen=set(); uniq=[]
                        for n in extra:
                            if n and n not in seen:
                                seen.add(n); uniq.append(n)
                        authors = '；'.join(uniq)
        except Exception:
            authors = ''

        # 附件
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()

        def _maybe_add(u: str):
            if not u:
                return
            lower = (u or '').lower(); full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts) or any(x in lower for x in media_exts):
                media_urls.add(full)

        scope = main_scope
        for a in scope.select('a[href], a[data-href], a[data-url]'):
            _maybe_add(a.get('href') or a.get('data-href') or a.get('data-url'))
        for sel in ['audio source[src]', 'audio[src]', 'video source[src]', 'video[src]', 'iframe[src]']:
            for node in scope.select(sel):
                _maybe_add(node.get('src'))
        attachments = ''
        if file_urls:
            attachments = ' ; '.join(sorted(file_urls))
        elif media_urls:
            attachments = ' ; '.join(sorted(media_urls))

        if not title or not content:
            print(f"BAIN 文章解析失败：标题或正文为空: {url}")
            return None
        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '贝恩咨询（Bain & Company）',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 BAIN 页面失败: {url} 错误: {e}")
        return None


# ------------------------------ 站点解析：EY China ------------------------------
def parse_ey_article(soup: BeautifulSoup, url: str, publish_date: str):
    """
    解析安永中国（ey.com）文章页
    - 标题：优先 h1 / meta og:title / <title>
    - 正文：优先 main/article 内 cmp-text/rich-text 等；回退通用文本提取
    - 日期：优先 JSON-LD 的 datePublished / meta[property=article:published_time] / <time datetime>
    - 作者：优先 JSON-LD author / meta[name=author] / 含 author 文本或 /people/ 链接
    - 附件：优先文档（pdf/doc/xls/ppt 等），若无文档而存在音频/视频则返回其 URL；并存时仅保留文档
    """
    try:
        # 标题
        title = ''
        t = soup.select_one('h1')
        if t and t.get_text(strip=True):
            title = clean_text(t.get_text())
        if not title:
            title = generic_title_from_meta_or_h(soup)

        # 正文
        def _first_nonempty_text(nodes):
            for n in nodes or []:
                txt = n.get_text("\n", strip=True)
                if txt:
                    return clean_text(txt)
            return ''

        main_scope = soup.select_one('main') or soup
        article_scope = main_scope.select_one('article') or main_scope
        candidates = []
        for css in [
            'article .cmp-text', 'article .rich-text', 'article .text', 'article .article-content',
            'div.cmp-text', 'section.cmp-text', 'div.rich-text', 'div.article-content', 'section.text'
        ]:
            candidates.extend(article_scope.select(css))
        if not candidates:
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
            mt = soup.select_one('meta[property="article:published_time"][content]')
            if mt and mt.get('content'):
                m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', mt['content'])
                if m:
                    pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        if not pub:
            tnode = soup.select_one('time[datetime]')
            if tnode and tnode.get('datetime'):
                m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', tnode['datetime'])
                if m:
                    pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        if not pub:
            pub = publish_date or ''

        # 作者
        authors = ''
        try:
            import json as _json
            names = []
            def _add(x):
                if isinstance(x, str) and x.strip():
                    names.append(clean_text(x))
                elif isinstance(x, dict):
                    n = x.get('name') or x.get('author') or x.get('creator')
                    if isinstance(n, str) and n.strip():
                        names.append(clean_text(n))
                    elif isinstance(n, list):
                        for e in n:
                            _add(e)
                elif isinstance(x, list):
                    for e in x:
                        _add(e)
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                if isinstance(data, dict) and 'author' in data:
                    _add(data.get('author'))
                elif isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and 'author' in obj:
                            _add(obj.get('author'))
            if not names:
                meta_author = soup.select_one('meta[name="author"][content]')
                if meta_author and meta_author.get('content'):
                    names.append(clean_text(meta_author['content']))
            if not names:
                for sel in ['[class*="author" i]', 'a[rel="author"]', 'a[href*="/people/" i]']:
                    node = soup.select_one(sel)
                    if node and node.get_text(strip=True):
                        names.append(clean_text(node.get_text()))
                        break
            if names:
                seen = set(); uniq = []
                for n in names:
                    if n and n not in seen:
                        seen.add(n); uniq.append(n)
                authors = '、'.join(uniq)
        except Exception:
            authors = ''

        # 附件
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()
        def _maybe_add(u: str):
            if not u:
                return
            lower = (u or '').lower(); full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts) or any(x in lower for x in media_exts):
                media_urls.add(full)
        scope = article_scope or soup
        for a in scope.select('a[href], a[data-asset], a[data-href], a[data-url]'):
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
            print(f"EY 文章解析失败：标题或正文为空: {url}")
            return None
        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '安永中国（EY）',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 EY 页面失败: {url} 错误: {e}")
        return None

def parse_iiss_article(soup: BeautifulSoup, url: str, publish_date: str):
    """
    IISS Online Analysis article parser (iiss.org)
    - Title: prefer h1 / og:title / <title>
    - Content: attempt common article containers, then fallback to generic text extraction
    - Publish date: try JSON-LD -> meta(article:published_time) -> time[datetime] -> list date
    - Authors: try JSON-LD author(s), meta[name=author], or common author selectors/people links
    - Attachments: prefer document files (pdf/doc/xls/ppt), otherwise audio/video links if present
    """
    try:
        # 标题
        title = ''
        tnode = soup.select_one('h1') or soup.select_one('.article-title h1') or soup.select_one('.title h1')
        if tnode and tnode.get_text(strip=True):
            title = clean_text(tnode.get_text())
        if not title:
            title = generic_title_from_meta_or_h(soup)

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
            'article .rich-text', 'article .text', 'article .article-content', 'article .cmp-text',
            'div.rich-text', 'div.article-content', 'div.cmp-text', 'section.cmp-text', 'section.text',
        ]:
            candidates.extend(article_scope.select(css))
        if not candidates:
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
            def _add(x):
                if isinstance(x, str) and x.strip():
                    names.append(clean_text(x))
                elif isinstance(x, dict):
                    n = x.get('name') or x.get('author') or x.get('creator')
                    if isinstance(n, str) and n.strip():
                        names.append(clean_text(n))
                    elif isinstance(n, list):
                        for e in n:
                            _add(e)
                elif isinstance(x, list):
                    for e in x:
                        _add(e)
            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                if isinstance(data, dict) and 'author' in data:
                    _add(data.get('author'))
                elif isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and 'author' in obj:
                            _add(obj.get('author'))
            if not names:
                meta_author = soup.select_one('meta[name="author"][content]')
                if meta_author and meta_author.get('content'):
                    names.append(clean_text(meta_author['content']))
            if not names:
                for sel in ['[class*="author" i]', 'a[rel="author"]', 'a[href*="/people/" i]']:
                    node = soup.select_one(sel)
                    if node and node.get_text(strip=True):
                        names.append(clean_text(node.get_text()))
                        break
            if names:
                seen = set(); uniq = []
                for n in names:
                    if n and n not in seen:
                        seen.add(n); uniq.append(n)
                authors = '、'.join(uniq)
        except Exception:
            authors = ''

        # 附件（优先文档；否则音/视频）
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()
        def _maybe_add(u: str):
            if not u:
                return
            lower = (u or '').lower(); full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts) or any(x in lower for x in media_exts):
                media_urls.add(full)
        scope = (soup.select_one('article') or soup)
        for a in scope.select('a[href], a[data-asset], a[data-href], a[data-url]'):
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
            print(f"IISS 文章解析失败，标题或正文为空: {url}")
            return None
        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '国际战略研究所(iiss)',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 IISS 页面失败: {url} 原因: {e}")
        return None

# ------------------------------ 站点解析：Deloitte China ------------------------------
def parse_deloitte_article(soup: BeautifulSoup, url: str, publish_date: str):
    """
    解析德勤中国（deloitte.com）月度经济概览详情页
    - 标题：优先 h1/cmp-title__text/og:title/<title>
    - 正文：优先 main/article 内的 cmp-text/rich-text/text；回退到通用文本提取
    - 日期：优先 JSON-LD -> meta(article:published_time) -> time[datetime] -> 中文日期文本 -> 列表页日期
    - 作者：优先 JSON-LD author / meta[name=author] / 常见“作者/撰文/撰稿”文本
    - 附件：优先文档（pdf/doc/xls/ppt 等）；若无文档而存在音/视频则返回其 URL；并存时仅保留文档
    - thinkank_name：统一为“德勤中国（Deloitte）”
    """
    try:
        # 标题
        title = ''
        t = (
            soup.select_one('h1.cmp-title__text') or
            soup.select_one('h1')
        )
        if t and t.get_text(strip=True):
            title = clean_text(t.get_text())
        if not title:
            title = generic_title_from_meta_or_h(soup)

        # 正文
        def _first_nonempty_text(nodes):
            for n in nodes or []:
                txt = n.get_text("\n", strip=True)
                if txt:
                    return clean_text(txt)
            return ''

        main_scope = soup.select_one('main') or soup
        article_scope = main_scope.select_one('article') or main_scope
        candidates = []
        for css in [
            'article .cmp-text', 'article .rich-text', 'article .text', 'article .article-content',
            'div.cmp-text', 'section.cmp-text', 'div.rich-text', 'div.article-content', 'section.text'
        ]:
            candidates.extend(article_scope.select(css))
        if not candidates:
            candidates = [article_scope]
        content = _first_nonempty_text(candidates)
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期
        def _cn_date_to_iso(s: str) -> str:
            if not isinstance(s, str):
                return ''
            m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s or '')
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', s or '')
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            return ''

        pub = ''
        try:
            import json as _json

            def _find_date(obj):
                if isinstance(obj, dict):
                    for k in ['datePublished', 'dateCreated', 'dateModified']:
                        v = obj.get(k)
                        if isinstance(v, str):
                            iso = _cn_date_to_iso(v)
                            if iso:
                                return iso
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
                    pub = d
                    break
            if not pub:
                m = soup.select_one('meta[property="article:published_time"][content]')
                if m and m.get('content'):
                    pub = _cn_date_to_iso(m['content'])
            if not pub:
                tnode = soup.select_one('time[datetime]') or soup.select_one('time')
                if tnode:
                    pub = _cn_date_to_iso(tnode.get('datetime') or tnode.get_text(strip=True) or '')
            if not pub:
                pub = _cn_date_to_iso(soup.get_text(" ", strip=True)) or _cn_date_to_iso(publish_date)
        except Exception:
            pub = _cn_date_to_iso(publish_date)

        # 作者
        authors = ''
        try:
            import json as _json
            names = []

            def _add(x):
                if isinstance(x, dict):
                    _add(x.get('name') or x.get('author'))
                elif isinstance(x, (list, tuple)):
                    for e in x:
                        _add(e)
                elif isinstance(x, str):
                    if x.strip():
                        names.append(clean_text(x))

            for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                txt = sc.string or sc.get_text() or ''
                if not txt.strip():
                    continue
                try:
                    data = _json.loads(txt)
                except Exception:
                    continue
                if isinstance(data, dict) and 'author' in data:
                    _add(data.get('author'))
                elif isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and 'author' in obj:
                            _add(obj.get('author'))
            if not names:
                ma = soup.select_one('meta[name="author"][content]')
                if ma and ma.get('content'):
                    names.append(clean_text(ma['content']))
            if not names:
                # 常见中文“作者/撰文/撰稿：xxx”
                txt = soup.get_text("\n", strip=True)
                m1 = re.search(r'(作者|撰文|撰稿)[:：]\s*([^\n\r\t，。,;；/\\]+)', txt)
                if m1:
                    for seg in re.split(r'[、，,;；和与及/\\]+', m1.group(2)):
                        s = seg.strip()
                        if s and (2 <= len(s) <= 30):
                            names.append(clean_text(s))
            if names:
                uniq = []
                used = set()
                for n in names:
                    if n and n not in used:
                        used.add(n)
                        uniq.append(n)
                authors = '；'.join(uniq)
        except Exception:
            authors = ''

        # 附件：优先文档；否则音/视频
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()

        def _maybe_add(u: str):
            if not u:
                return
            lower = (u or '').lower(); full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts) or any(x in lower for x in media_exts):
                media_urls.add(full)

        scope = article_scope or soup
        for a in scope.select('a[href], a[data-asset], a[data-href], a[data-url]'):
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
            print(f"Deloitte 文章解析失败：标题或正文为空: {url}")
            return None
        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '德勤中国（Deloitte）',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 Deloitte 页面失败: {url} 错误: {e}")
        return None


# ------------------------------ 站点解析：清华大学国情研究院（ICCS） ------------------------------
def parse_iccs_article(soup: BeautifulSoup, url: str, publish_date: str):
    """
    解析 清华大学国情研究院（iccs.tsinghua.edu.cn） 文章页：
    - 标题：优先 h1 / og:title / <title>
    - 正文：优先常见正文容器，回退通用提取
    - 日期：尝试 time/meta/页面文本中的 YYYY-MM-DD/年-月-日
    - 作者：尽力从“作者/撰文/撰稿”等字段提取姓名；若无法可靠获取则留空
    - 附件：优先返回文档（pdf/doc/xls/ppt 等）；若无文档且存在音频/视频则返回其 URL；并存时仅返回文档
    - thinkank_name：统一填写为“清华大学国情研究院”
    """
    try:
        # 标题
        title = ''
        tnode = (
            soup.select_one('h1') or
            soup.select_one('.article-title h1') or
            soup.select_one('.title h1') or
            soup.select_one('.detail h1')
        )
        if tnode and tnode.get_text(strip=True):
            title = clean_text(tnode.get_text())
        if not title:
            title = generic_title_from_meta_or_h(soup)

        # 正文
        def _scope_text(scope: BeautifulSoup) -> str:
            if scope is None:
                return ''
            # 尽量按段落/标题拼接
            parts = []
            for node in scope.select('p, li, h2, h3, h4'):
                txt = (node.get_text('\n', strip=True) or '').strip()
                if not txt:
                    continue
                parts.append(clean_text(txt))
            if parts:
                return ' '.join(parts)
            bulk = scope.get_text('\n', strip=True)
            return clean_text(bulk)

        main_scope = (
            soup.select_one('article') or
            soup.select_one('div.article') or
            soup.select_one('div.content') or
            soup.select_one('div.text') or
            soup.select_one('div.con') or
            soup.select_one('div.detail') or
            soup
        )
        content = _scope_text(main_scope)
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期
        pub = ''
        # 优先 time/meta
        tmeta = soup.select_one('time[datetime]')
        if tmeta and tmeta.get('datetime'):
            m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', tmeta.get('datetime'))
            if m:
                pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        if not pub:
            # 常见“发布时间/日期”字段
            date_nodes = soup.select('span, em, i, .date, .time, p')
            for dn in date_nodes:
                raw = dn.get_text(' ', strip=True)
                m = re.search(r'(\d{4})[./\-年](\d{1,2})[./\-月](\d{1,2})', raw)
                if m:
                    pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                    break
        if not pub:
            pub = publish_date or ''

        # 作者（尽力提取“作者/撰文/撰稿”字段；避免把“来源”误当作者）
        authors = ''
        try:
            possible_blocks = soup.select('p, div, span, li')
            cand = []
            for n in possible_blocks:
                txt = (n.get_text(' ', strip=True) or '').strip()
                if not txt:
                    continue
                if any(k in txt for k in ['作者', '撰文', '撰稿', '文/']):
                    # 常见格式：“作者：张三 李四”、“撰文：张三”、“文/张三”
                    # 去掉“来源/责任编辑”等
                    if '来源' in txt or '责任编辑' in txt:
                        continue
                    cand.append(txt)
            # 解析候选文本中的人名
            names = []
            for c in cand:
                # 优先“作者：xxx”
                m = re.search(r'(作者|撰文|撰稿)[:：]\s*([^|；;、，。\s][^；;，。]*)', c)
                if m:
                    part = m.group(2)
                    # 分割常见分隔符
                    for seg in re.split(r'[、，,;；和与及/\\]+', part):
                        s = seg.strip()
                        if s and (2 <= len(s) <= 20):
                            names.append(clean_text(s))
                    continue
                # 次选“文/xxx”
                m2 = re.search(r'文[/：:]\s*([^|；;、，。\s][^；;，。]*)', c)
                if m2:
                    s = m2.group(1).strip()
                    if s and (2 <= len(s) <= 20):
                        names.append(clean_text(s))
            if names:
                uniq = []
                used = set()
                for n in names:
                    if n and n not in used:
                        used.add(n)
                        uniq.append(n)
                authors = '、'.join(uniq)
        except Exception:
            authors = ''

        # 附件：优先文档；否则音视频；并存仅保留文档
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()

        def _maybe_add(u: str):
            if not u:
                return
            lower = (u or '').lower()
            full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts) or any(x in lower for x in media_exts):
                media_urls.add(full)

        scope = soup.select_one('article') or soup
        for a in scope.select('a[href], a[data-asset], a[data-href], a[data-url]'):
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
            print(f"ICCS 文章解析失败：标题或正文为空: {url}")
            return None
        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '清华大学国情研究院',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 ICCS 页面失败: {url} 错误: {e}")
        return None

# ------------------------------ 站点解析：复旦大学中国研究院（cifu.fudan.edu.cn） ------------------------------
def parse_fudan_article(soup: BeautifulSoup, url: str, publish_date: str):
    """
    解析 复旦大学中国研究院（cifu.fudan.edu.cn）文章页：
    - 标题：优先 h1；回退 og:title / <title>
    - 正文：优先 div.wp_articlecontent；回退常见正文容器与通用提取
    - 日期：优先提取“发布日期/发布时间”或文本中的 YYYY-MM-DD / YYYY年MM月DD日；缺失则用列表页日期
    - 作者：尽力从“作者/撰文/撰稿/文/xxx”等字段提取；若无法可靠获取则留空
    - 附件：优先文档（pdf/doc/xls/ppt 等）；若无文档且存在音频/视频则返回其 URL；并存时仅返回文档
    - thinkank_name：统一填写为“复旦大学中国研究院”
    """
    try:
        # 标题
        title = ''
        tnode = (
            soup.select_one('h1') or
            soup.select_one('.article-title h1') or
            soup.select_one('.title h1')
        )
        if tnode and tnode.get_text(strip=True):
            title = clean_text(tnode.get_text())
        if not title:
            title = generic_title_from_meta_or_h(soup)

        # 正文
        def _scope_text(scope: BeautifulSoup) -> str:
            if scope is None:
                return ''
            parts = []
            for node in scope.select('p, li, h2, h3, h4'):
                txt = (node.get_text('\n', strip=True) or '').strip()
                if not txt:
                    continue
                parts.append(clean_text(txt))
            if parts:
                return ' '.join(parts)
            bulk = scope.get_text('\n', strip=True)
            return clean_text(bulk)

        main_scope = (
            soup.select_one('div.wp_articlecontent') or
            soup.select_one('div.article') or
            soup.select_one('div.content') or
            soup.select_one('div.text') or
            soup.select_one('div#vsb_content') or
            soup.select_one('div.v_news_content') or
            soup
        )
        content = _scope_text(main_scope)
        if not content:
            content = generic_content_by_candidates(soup)

        # 日期
        pub = ''
        try:
            # 常见“发布日期/发布时间”容器
            date_nodes = soup.select('span, em, i, .date, .time, p, div')
            for dn in date_nodes:
                raw = (dn.get_text(' ', strip=True) or '').strip()
                if not raw:
                    continue
                if any(k in raw for k in ['发布日期', '发布时间', '时间', '日期']):
                    m = re.search(r'(\d{4})[./\-年](\d{1,2})[./\-月](\d{1,2})', raw)
                    if m:
                        pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                        break
            if not pub:
                # 任意包含日期的节点
                for dn in date_nodes:
                    raw = (dn.get_text(' ', strip=True) or '').strip()
                    m = re.search(r'(\d{4})[./\-年](\d{1,2})[./\-月](\d{1,2})', raw)
                    if m:
                        pub = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                        break
        except Exception:
            pass
        if not pub:
            pub = publish_date or ''

        # 作者（尽力提取“作者/撰文/撰稿/文/xxx”，忽略“来源/责任编辑”等）
        authors = ''
        try:
            possible_blocks = soup.select('p, div, span, li')
            cand = []
            for n in possible_blocks:
                txt = (n.get_text(' ', strip=True) or '').strip()
                if not txt:
                    continue
                if any(k in txt for k in ['作者', '撰文', '撰稿', '文/']):
                    if '来源' in txt or '责任编辑' in txt:
                        continue
                    cand.append(txt)
            names = []
            for c in cand:
                m = re.search(r'(作者|撰文|撰稿)[:：]\s*([^|、，。\s][^，。]*)', c)
                if m:
                    part = m.group(2)
                    for seg in re.split(r'[、，,;；和与及/\\]+', part):
                        s = seg.strip()
                        if s and (2 <= len(s) <= 30):
                            names.append(clean_text(s))
                    continue
                m2 = re.search(r'文[/：]\s*([^|、，。\s][^，。]*)', c)
                if m2:
                    s = m2.group(1).strip()
                    if s and (2 <= len(s) <= 30):
                        names.append(clean_text(s))
            if names:
                uniq = []
                used = set()
                for n in names:
                    if n and n not in used:
                        used.add(n)
                        uniq.append(n)
                authors = '、'.join(uniq)
        except Exception:
            authors = ''

        # 附件：优先文档；否则音视频；并存仅保留文档
        file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        media_exts = ['.mp3', '.m4a', '.wav', '.mp4', '.m3u8', '.mov', '.m4v']
        file_urls, media_urls = set(), set()

        def _maybe_add(u: str):
            if not u:
                return
            lower = (u or '').lower()
            full = url_join(url, u)
            if any(lower.endswith(ext) for ext in file_exts):
                file_urls.add(full)
            elif any(lower.endswith(ext) for ext in media_exts) or any(x in lower for x in media_exts):
                media_urls.add(full)

        scope = main_scope or soup
        for a in scope.select('a[href], a[data-asset], a[data-href], a[data-url]'):
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
            print(f"FUDAN 文章解析失败：标题或正文为空: {url}")
            return None
        return {
            'title': title,
            'url': url,
            'publish_date': pub,
            'authors': authors,
            'thinkank_name': '复旦大学中国研究院',
            'summary': '',
            'content': content,
            'attachments': attachments,
            'crawl_date': get_current_date()
        }
    except Exception as e:
        print(f"解析 FUDAN 页面失败: {url} 错误: {e}")
        return None

# ------------------------------ 通用抓取 ------------------------------
def crawl_article_content(url, publish_date, headers, title_hint=None):
    lower_url = (url or '').lower()

    # Deloitte China：常规请求解析
    if 'deloitte.com' in lower_url:
        try:
            resp = requests.get(url, headers=headers or {}, timeout=20, proxies=NO_PROXIES)
            if resp is None or resp.status_code >= 400 or not resp.text:
                return None
            soup = BeautifulSoup(resp.text, 'lxml')
            return parse_deloitte_article(soup, url, publish_date)
        except Exception:
            return None

    # 清华大学国情研究院（iccs.tsinghua.edu.cn）：常规请求 + DOM 解析
    if 'iccs.tsinghua.edu.cn' in lower_url:
        try:
            resp = requests.get(url, headers=headers or {}, timeout=20, proxies=NO_PROXIES)
            if resp is None or resp.status_code >= 400 or not resp.text:
                return None
            soup = BeautifulSoup(resp.text, 'lxml')
            return parse_iccs_article(soup, url, publish_date)
        except Exception:
            return None

    # 复旦大学中国研究院（cifu.fudan.edu.cn）：常规请求 + DOM 解析
    if 'cifu.fudan.edu.cn' in lower_url:
        try:
            resp = requests.get(url, headers=headers or {}, timeout=20, proxies=NO_PROXIES)
            if resp is None or resp.status_code >= 400 or not resp.content:
                return None
            # 修正编码：若无 charset 或给出 iso-8859-1/ascii，则采用 apparent_encoding
            ct = (resp.headers.get('content-type') or '').lower()
            if (not resp.encoding) or (resp.encoding.lower() in ['iso-8859-1', 'ascii']) or ('charset=' not in ct):
                try:
                    resp.encoding = resp.apparent_encoding or 'utf-8'
                except Exception:
                    resp.encoding = 'utf-8'
            html = resp.text if resp.encoding else resp.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'lxml')
            return parse_fudan_article(soup, url, publish_date)
        except Exception:
            return None

    # IISS：iiss.org 先尝试 requests，若 403/空白再用 undetected-chromedriver 获取 HTML
    if 'iiss.org' in lower_url:
        # 尝试直接请求
        try:
            resp = requests.get(url, headers=headers or {}, timeout=20, proxies=NO_PROXIES)
            if resp is not None and resp.status_code < 400 and resp.text:
                soup = BeautifulSoup(resp.text, 'lxml')
                r = parse_iiss_article(soup, url, publish_date)
                if r:
                    return r
        except Exception:
            pass
        # 回退：用 undetected-chromedriver 获取渲染后的 HTML
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
                # Cookie 同意按钮（尽力点击）
                try:
                    _Wait(_driver, 8).until(_EC.presence_of_element_located((_By.CSS_SELECTOR, 'button#onetrust-accept-btn-handler')))
                    _driver.execute_script("var b=document.querySelector('button#onetrust-accept-btn-handler'); if(b){b.click()} ")
                except Exception:
                    pass
                try:
                    _Wait(_driver, 18).until(_EC.presence_of_element_located((_By.CSS_SELECTOR, 'main, article, h1')))
                except Exception:
                    pass
                html_text = _driver.page_source
            finally:
                try:
                    _driver.quit()
                except Exception:
                    pass
            if html_text and html_text.strip():
                soup = BeautifulSoup(html_text, 'lxml')
                return parse_iiss_article(soup, url, publish_date)
        except Exception:
            pass
        return None

    # Bain China（bain.cn）：常规请求 + DOM 解析（优先于通用逻辑）
    if 'bain.cn' in lower_url:
        try:
            resp = requests.get(url, headers=headers or {}, timeout=20, proxies=NO_PROXIES)
            if resp is None or resp.status_code >= 400 or not resp.text:
                return None
            soup = BeautifulSoup(resp.text, 'lxml')
            return parse_bain_article(soup, url, publish_date)
        except Exception:
            return None

    # EY China：常规请求解析
    if 'ey.com' in lower_url:
        try:
            resp = requests.get(url, headers=headers or {}, timeout=20, proxies=NO_PROXIES)
            if resp is None or resp.status_code >= 400 or not resp.text:
                return None
            soup = BeautifulSoup(resp.text, 'lxml')
            return parse_ey_article(soup, url, publish_date)
        except Exception:
            return None

    # BCG：优先浏览器渲染（requests 经常被拦）
    if 'bcg.com' in lower_url:
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
                    _Wait(_driver, 8).until(_EC.presence_of_element_located((_By.CSS_SELECTOR, 'button#onetrust-accept-btn-handler')))
                    _driver.execute_script("var b=document.querySelector('button#onetrust-accept-btn-handler'); if(b){b.click()} ")
                except Exception:
                    pass
                try:
                    _Wait(_driver, 18).until(_EC.presence_of_element_located((_By.CSS_SELECTOR, 'main, article, h1')))
                except Exception:
                    pass
                html_text = _driver.page_source
            finally:
                try:
                    _driver.quit()
                except Exception:
                    pass
            if html_text and html_text.strip():
                soup = BeautifulSoup(html_text, 'lxml')
                return parse_bcg_article(soup, url, publish_date)
        except Exception as e:
            print(f"BCG 无头浏览器抓取失败: {e}")
        return None

    # 其他域名（此简化版仅支持 BCG）
    return None


# ------------------------------ 主流程 ------------------------------
def main(only_domain: str = '', force_domain: str = ''):
    print("开始提取聚合页面的条目...")
    OUTPUT_JSON_PATH = 'output_complete.json'
    existing_items, seen_urls = load_existing_results(OUTPUT_JSON_PATH)
    print(f"已有历史条目 {len(existing_items)}，将跳过已抓取 URL")
    # 记录已存在条目的 URL -> 索引，便于更新 thinkank_name
    existing_map = {}
    for idx, rec in enumerate(existing_items):
        try:
            u = normalize_url(rec.get('url', ''))
            if u:
                existing_map[u] = idx
        except Exception:
            continue

    try:
        with open('generated_html/index.html', 'r', encoding='utf-8') as f:
            s = f.read()
    except Exception as e:
        print(f"读取 generated_html/index.html 失败: {e}")
        return

    soup = BeautifulSoup(s, 'lxml')
    nodes = soup.select('.page-board-item')
    if only_domain:
        # 仅保留指定主域名（后缀匹配），避免如 mckinsey.com.cn 误命中 "ey.com"
        from urllib.parse import urlparse as _urlparse
        target = (only_domain or '').lower().strip()
        def _host_ok(n):
            try:
                href = n.select('a')[0]['href']
                host = _urlparse(href).netloc.lower()
                return host.endswith(target)
            except Exception:
                return False
        nodes = [n for n in nodes if _host_ok(n)]

    print(f"找到 {len(nodes)} 条待处理" + (f"（仅 {only_domain}）" if only_domain else ''))
    lst = []
    run_seen = set()
    updated_existing = False

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
    }

    for i, n in enumerate(nodes, 1):
        try:
            a = n.select('a')[0]
            url = a['href']
            pub = ''
            try:
                pub = n.select('span')[0].get_text(strip=True)
            except Exception:
                pub = ''
            # 取所在板块标题作为 thinktank/栏目全名，避免多栏目合并后丢失栏目信息
            board_name = ''
            try:
                parent_board = n.find_parent('div', class_='page-board')
                h2 = parent_board.select_one('h2') if parent_board else None
                board_name = h2.get_text(strip=True) if h2 else ''
            except Exception:
                board_name = ''
            nu = normalize_url(url)
            # 若已有记录，且栏目名需要更新，则同步修正
            if board_name and nu in existing_map:
                try:
                    idx = existing_map[nu]
                    if existing_items[idx].get('thinkank_name') != board_name:
                        existing_items[idx]['thinkank_name'] = board_name
                        updated_existing = True
                except Exception:
                    pass
            # 若指定了 force_domain，且 URL 主机匹配该域，则忽略历史去重强制重抓
            skip_seen = True
            if force_domain:
                from urllib.parse import urlparse as _urlparse
                try:
                    host = _urlparse(nu).netloc.lower()
                    if host.endswith(force_domain.lower().strip()):
                        skip_seen = False
                    else:
                        skip_seen = True
                except Exception:
                    skip_seen = True
            if (not nu) or ((nu in seen_urls) and skip_seen) or (nu in run_seen):
                continue
            run_seen.add(nu)
            print(f"[{i}/{len(nodes)}] 抓取: {url}")
            data = crawl_article_content(url, pub, headers)
            if data:
                if board_name:
                    data['thinkank_name'] = board_name
                lst.append(data)
                print(f"成功: {data['title'][:60]}...")
            else:
                print("失败或跳过")
            time.sleep(0.5)
        except Exception as e:
            print(f"条目处理异常: {e}")
            continue

    if lst or updated_existing:
        combined = existing_items + lst
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(combined, f, ensure_ascii=False, indent=2, default=str)
        if lst and updated_existing:
            print(f"已保存到 {OUTPUT_JSON_PATH}，新增 {len(lst)}，并更新现有栏目名，累计 {len(combined)} 条")
        elif lst:
            print(f"已保存到 {OUTPUT_JSON_PATH}，新增 {len(lst)}，累计 {len(combined)} 条")
        else:
            print(f"已更新栏目名称，未新增内容，累计 {len(combined)} 条")
    else:
        print("未新增数据，output_complete.json 保持不变")


if __name__ == '__main__':
    import sys
    only = ''
    force = ''
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i] == '--only-domain' and i + 1 < len(argv):
            only = argv[i + 1]; i += 2; continue
        if argv[i] == '--force-domain' and i + 1 < len(argv):
            force = argv[i + 1]; i += 2; continue
        i += 1
    main(only_domain=only, force_domain=force)
