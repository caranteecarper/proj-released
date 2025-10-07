import pandas as pd
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from requests.exceptions import RequestException
import time
import re

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

def crawl_article_content(url, publish_date, headers):
    """爬取文章内容的通用函数"""
    # 增加重试机制，最多重试3次
    retry_count = 3
    html = None
    
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
        
        print(f"找到 {len(sj_lst)} 篇文章需要爬取")
        
        # 遍历每篇文章
        for i, m in enumerate(sj_lst, 1):
            try:
                url = m.select('a')[0]['href']
                publish_date = m.select('span')[0].text
                
                print(f"正在处理第 {i}/{len(sj_lst)} 篇文章: {url}")
                
                # 爬取文章内容
                data = crawl_article_content(url, publish_date, headers)
                
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
            result = pd.DataFrame(lst)
            result.to_json('output_complete.json', orient='records', force_ascii=False, indent=2)
            print(f"结果已保存到 output_complete.json")
        else:
            print("没有成功爬取到任何文章")
            
    except Exception as e:
        print(f"程序执行过程中发生错误: {e}")

if __name__ == "__main__":
    main()
