import json
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from requests.exceptions import RequestException
import time
import re
from urllib.parse import urljoin as url_join

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

def crawl_article_content(url, publish_date, headers, title_hint=None):
    """爬取文章内容的通用函数"""
    # 增加重试机制，最多重试3次
    retry_count = 3
    html = None
    lower_url = url.lower()
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
    
    while retry_count > 0:
        try:
            # 设置超时时间为15秒，避免无限等待
            html = requests.get(url=url, headers=headers, timeout=15)
            # 优先使用服务端声明编码，其次使用apparent_encoding，最后退回utf-8
            if not html.encoding or html.encoding.lower() in ['iso-8859-1', 'ascii']:
                html.encoding = html.apparent_encoding or 'utf-8'
            break  # 成功获取则退出重试循环
        except RequestException as e:
            retry_count -= 1
            print(f"请求 {url} 失败: {e}，剩余重试次数: {retry_count}")
            if retry_count == 0:
                print(f"多次请求失败，跳过该链接: {url}")
                return None
            time.sleep(2)  # 重试前等待2秒
    
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
        else:
            print(f"未知网站，无法解析: {url}")
            return None
            
    except Exception as e:
        print(f"解析页面 {url} 失败: {e}")
        return None

def main():
    """主函数"""
    print("开始爬取智库文章内容...")
    
    lst = []
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0'
    }
    
    try:
        # 读取生成的HTML文件
        with open('generated_html/index.html', 'r', encoding='utf-8') as f:
            s = f.read()
        
        soup = BeautifulSoup(s, 'lxml')
        sj_lst = soup.select('.page-board-item')
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
                        r = requests.get(url, headers=headers, timeout=15)
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
        
        print(f"找到 {len(sj_lst)} 篇文章需要爬取")
        
        # 遍历每篇文章
        for i, m in enumerate(sj_lst, 1):
            try:
                url = m.select('a')[0]['href']
                publish_date = m.select('span')[0].text
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
        
        # 保存结果
        if lst:
            with open('output_complete.json', 'w', encoding='utf-8') as f:
                json.dump(lst, f, ensure_ascii=False, indent=2, default=str)
            print(f"结果已保存到 output_complete.json")
        else:
            print("没有成功爬取到任何文章")
            
    except Exception as e:
        print(f"程序执行过程中发生错误: {e}")

if __name__ == "__main__":
    main()
