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


# ------------------------------ 通用抓取 ------------------------------
def crawl_article_content(url, publish_date, headers, title_hint=None):
    lower_url = (url or '').lower()

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
def main(only_domain: str = ''):
    print("开始提取聚合页面的条目...")
    OUTPUT_JSON_PATH = 'output_complete.json'
    existing_items, seen_urls = load_existing_results(OUTPUT_JSON_PATH)
    print(f"已有历史条目 {len(existing_items)}，将跳过已抓取 URL")

    try:
        with open('generated_html/index.html', 'r', encoding='utf-8') as f:
            s = f.read()
    except Exception as e:
        print(f"读取 generated_html/index.html 失败: {e}")
        return

    soup = BeautifulSoup(s, 'lxml')
    nodes = soup.select('.page-board-item')
    if only_domain:
        def _u(n):
            try:
                return n.select('a')[0]['href']
            except Exception:
                return ''
        nodes = [n for n in nodes if only_domain.lower() in (_u(n) or '').lower()]

    print(f"找到 {len(nodes)} 条待处理" + (f"（仅 {only_domain}）" if only_domain else ''))
    lst = []
    run_seen = set()

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
            nu = normalize_url(url)
            if (not nu) or (nu in seen_urls) or (nu in run_seen):
                continue
            run_seen.add(nu)
            print(f"[{i}/{len(nodes)}] 抓取: {url}")
            data = crawl_article_content(url, pub, headers)
            if data:
                lst.append(data)
                print(f"成功: {data['title'][:60]}...")
            else:
                print("失败或跳过")
            time.sleep(0.5)
        except Exception as e:
            print(f"条目处理异常: {e}")
            continue

    if lst:
        combined = existing_items + lst
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(combined, f, ensure_ascii=False, indent=2, default=str)
        print(f"已保存到 {OUTPUT_JSON_PATH}，新增 {len(lst)}，累计 {len(combined)} 条")
    else:
        print("未新增数据，output_complete.json 保持不变")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == '--only-domain':
        dom = sys.argv[2]
        main(only_domain=dom)
    else:
        main()

