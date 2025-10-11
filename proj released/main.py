# from os import getcwd
from time import sleep
import os
import re
import requests
import sys
import json
import hashlib

from datetime import datetime

# configure <current_time> instance object
current_time = datetime.now()

from ChromePageRender import (
    # something else
    Options as ChromeOptions,
    ChromePageRender
)

# configure chrome driver path
__chrome_driver_path: str = ""
from dominate import document as HTMLDocument, tags as HTMLTags, util as HTMLUtils
from bs4 import BeautifulSoup
from tqdm import tqdm as LoopMeter
from urllib.parse import urlparse as url_parse, urljoin as url_join


# ---------------------------------------------------------------------------------------------------------------------
# |                                The following code sets up data collectors.                                        |
# ---------------------------------------------------------------------------------------------------------------------


def handler1(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    # this function adds <site_name> and <site_urls_contents> into <document> in an elegant way
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = dict()
    for url in url_info['URLs']:
        urls_contents[
            url
        ] = chrome_page_render.get_page_source() if not chrome_page_render.goto_url_waiting_for_selectors(
            url=url,
            selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
            waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
            print_error_log_to_console=True
        ) else None
    # urls_contents_len = len(urls_contents)
    with document.body:
        with HTMLTags.div(cls='page-board'):  # create a new board for this url series
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt=f"Missing Logo for \"{url_name}\"")
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (index, (url, html_content)) in enumerate(urls_contents.items()):  # view each url-html pair
                url_parts = url_parse(url)
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')  # create HTML parser
                for old_newscontent in soup.select('div.newscontent'):  # !!! THIS IS DIFFERENT FROM WEBSITES !!!
                    old_a = old_newscontent.select_one('a')
                    if old_a is None:
                        continue
                    a_href = url_join(url, old_a['href'])
                    h3_text = old_a.select_one('h3').get_text(strip=True)
                    span_text = old_newscontent.select_one('span').get_text(strip=True)
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None


def handler2(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    # this function adds <site_name> and <site_urls_contents> into <document> in an elegant way
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = dict()
    for url in url_info['URLs']:
        urls_contents[
            url
        ] = chrome_page_render.get_page_source() if not chrome_page_render.goto_url_waiting_for_selectors(
            url=url,
            selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
            waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
            print_error_log_to_console=True
        ) else None
    # urls_contents_len = len(urls_contents)
    with document.body:
        with HTMLTags.div(cls='page-board'):  # create a new board for this url series
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (index, (url, html_content)) in enumerate(urls_contents.items()):  # view each url-html pair
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')  # create HTML parser
                for old_briefItem in soup.select('div.briefItem'):  # !!! THIS IS DIFFERENT FROM WEBSITES !!!
                    old_a = old_briefItem.select_one('a')
                    if old_a is None:
                        continue
                    a_href = url_join(url, old_a['href'])
                    h3_text = old_a.select_one('h3').get_text(strip=True)
                    span_text = old_a.select_one('span').get_text(strip=True)
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None


def handler3(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    # this function adds <site_name> and <site_urls_contents> into <document> in an elegant way
    url = url_info['URL']
    if chrome_page_render.goto_url_waiting_for_selectors(
            url=url,
            selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
            waiting_timeout_in_seconds=url_info['MainPageWaitingTimeLimitInSeconds'],
            print_error_log_to_console=True
    ):
        return None
    with document.body:
        with HTMLTags.div(cls='page-board'):  # create a new board for this url series
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url):
                HTMLTags.h2(url_name)
            for index in range(url_info['NumberOfPagesNeeded']):
                html_content = chrome_page_render.get_page_source()
                soup = BeautifulSoup(html_content, 'html.parser')  # create HTML parser
                for re_box in soup.select('div.re_box'):  # !!! THIS IS USUALLY DIFFERENT FROM WEBSITES !!!
                    old_a = re_box.select_one('a')
                    if old_a is None:
                        continue
                    a_href = url_join(url, old_a['href'])
                    h3_text = old_a['title']
                    span_text = re_box.select_one('span').get_text(strip=True)
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
                # update html_content by clicking page switching button
                if index != url_info['NumberOfPagesNeeded'] - 1:  # make sure that it's not the last round
                    if chrome_page_render.click_on_html_element(
                            click_element_selector_type="css",
                            click_element_selector_rule="a.p-next.p-elem",
                            use_javascript=False,
                            max_trials_for_unstable_page=4,
                            click_waiting_timeout_in_seconds=10,
                            print_error_log_to_console=True
                    ):
                        break
                    # wait for javascript to render html elements
                    sleep(url_info['PageUpdatesWaitingTimeLimitInSeconds'])
    return None


def handler4(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    # this function adds <site_name> and <site_urls_contents> into <document> in an elegant way
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = dict()
    for url in url_info['URLs']:
        urls_contents[
            url
        ] = chrome_page_render.get_page_source() if not chrome_page_render.goto_url_waiting_for_selectors(
            url=url,
            selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
            waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
            print_error_log_to_console=True
        ) else None
    # urls_contents_len = len(urls_contents)
    with document.body:
        with HTMLTags.div(cls='page-board'):  # create a new board for this url series
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (index, (url, html_content)) in enumerate(urls_contents.items()):  # view each url-html pair
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')  # create HTML parser
                for old_li in soup.select_one('ul.gl_list2').select('li'):
                    old_a = old_li.select_one('a')
                    if old_a is None:
                        continue
                    a_href = url_join(url, old_a['href'])
                    h3_text = old_a['title']
                    span_text = old_li.select_one('span').get_text(strip=True)
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None


def handler5(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    # this function adds <site_name> and <site_urls_contents> into <document> in an elegant way
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = dict()
    for url in url_info['URLs']:
        urls_contents[
            url
        ] = chrome_page_render.get_page_source() if not chrome_page_render.goto_url_waiting_for_selectors(
            url=url,
            selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
            waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
            print_error_log_to_console=True
        ) else None
    # urls_contents_len = len(urls_contents)
    with document.body:
        with HTMLTags.div(cls='page-board'):  # create a new board for this url series
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (index, (url, html_content)) in enumerate(urls_contents.items()):  # view each url-html pair
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')  # create HTML parser
                for old_li in soup.select_one('ul.u-list').select('li'):
                    old_a = old_li.select_one('a')
                    if old_a is None:
                        continue
                    a_href = url_join(url, old_a['href'])
                    h3_text = old_a['title']
                    span_text = old_li.select_one('span').get_text(strip=True)
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None


def handler6(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    # this function adds <site_name> and <site_urls_contents> into <document> in an elegant way
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = dict()
    for url in url_info['URLs']:
        urls_contents[
            url
        ] = chrome_page_render.get_page_source() if not chrome_page_render.goto_url_waiting_for_selectors(
            url=url,
            selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
            waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
            print_error_log_to_console=True
        ) else None
    # urls_contents_len = len(urls_contents)
    with document.body:
        with HTMLTags.div(cls='page-board'):  # create a new board for this url series
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (index, (url, html_content)) in enumerate(urls_contents.items()):  # view each url-html pair
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')  # create HTML parser
                for old_li in soup.select_one('div.new_list.new0').select_one('ul').select('li'):
                    old_a = old_li.select_one('a')
                    if old_a is None:
                        continue
                    a_href = url_join(url, old_a['href'])
                    h3_text = old_a.get_text(strip=True)
                    span_text = old_li.select_one('span').get_text(strip=True)
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None


def handler7(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    # this function adds <site_name> and <site_urls_contents> into <document> in an elegant way
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = dict()
    for url in url_info['URLs']:
        urls_contents[
            url
        ] = chrome_page_render.get_page_source() if not chrome_page_render.goto_url_waiting_for_selectors(
            url=url,
            selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
            waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
            print_error_log_to_console=True
        ) else None
    # urls_contents_len = len(urls_contents)
    with document.body:
        with HTMLTags.div(cls='page-board'):  # create a new board for this url series
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (index, (url, html_content)) in enumerate(urls_contents.items()):  # view each url-html pair
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')  # create HTML parser
                for old_li in soup.select_one('ul.cols_list.clearfix').select('li'):
                    old_a = old_li.select_one('a')
                    if old_a is None:
                        continue
                    a_href = url_join(url, old_a['href'])
                    h3_text = old_a.get_text(strip=True)
                    span_text = old_li.select_one('span.cols_meta').get_text(strip=True)
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None

def handler8_cdi_articles(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = {}
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
    }
    for url in url_info['URLs']:
        html_content = None
        try:
            is_timeout = chrome_page_render.goto_url_waiting_for_selectors(
                url=url,
                selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
                waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
                print_error_log_to_console=True
            )
            if not is_timeout:
                html_content = chrome_page_render.get_page_source()
        except Exception:
            html_content = None
        if html_content is None:
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if not resp.encoding or resp.encoding.lower() in ['iso-8859-1', 'ascii']:
                    resp.encoding = resp.apparent_encoding or 'utf-8'
                if resp.status_code == 200:
                    html_content = resp.text
            except Exception:
                html_content = None
        urls_contents[url] = html_content
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (url, html_content) in urls_contents.items():
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')
                container = soup.select_one('ul#ColumnsList')
                if container is None:
                    continue
                for old_li in container.select('li'):
                    old_a = old_li.select_one('div.img a') or old_li.select_one('div.details a.a-full') or old_li.select_one('a')
                    if old_a is None or not old_a.get('href'):
                        continue
                    a_href = url_join(url, old_a['href'])
                    title_node = old_li.select_one('div.info span') or old_li.select_one('span')
                    if title_node is None:
                        continue
                    h3_text = title_node.get_text(strip=True)
                    em_node = old_li.select_one('div.info em') or old_li.select_one('em')
                    span_text_raw = em_node.get_text(strip=True) if em_node is not None else ''
                    m = re.search(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', span_text_raw)
                    span_text = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else span_text_raw
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None


def handler9_cdi_files(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = {}
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
    }
    for url in url_info['URLs']:
        html_content = None
        try:
            is_timeout = chrome_page_render.goto_url_waiting_for_selectors(
                url=url,
                selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
                waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
                print_error_log_to_console=True
            )
            if not is_timeout:
                html_content = chrome_page_render.get_page_source()
        except Exception:
            html_content = None
        if html_content is None:
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if not resp.encoding or resp.encoding.lower() in ['iso-8859-1', 'ascii']:
                    resp.encoding = resp.apparent_encoding or 'utf-8'
                if resp.status_code == 200:
                    html_content = resp.text
            except Exception:
                html_content = None
        urls_contents[url] = html_content
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (url, html_content) in urls_contents.items():
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')
                columns_list = soup.select_one('div#ColumnsList')
                if columns_list is None:
                    continue
                for a_item in columns_list.select('ul.setimage320 li a.item'):
                    if not a_item.get('href'):
                        continue
                    a_href = url_join(url, a_item['href'])
                    info_span = a_item.select_one('div.info span')
                    h3_text = info_span.get_text(strip=True) if info_span is not None else a_item.get('title', '').strip()
                    em_node = a_item.select_one('div.info em')
                    span_text_raw = em_node.get_text(strip=True) if em_node is not None else ''
                    m = re.search(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', span_text_raw)
                    span_text = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else span_text_raw
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None


URLData = {
    '中国国际工程咨询有限公司（智库建议）': {
        'URLs': [
            'https://www.ciecc.com.cn/col/col3963/index.html',
            'https://www.ciecc.com.cn/col/col3963/index.html?uid=5248&pageNum=2',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.main_comr.fr'),
            ('css', 'div.default_pgContainer'),
            ('css', 'div.news-list'),
            ('css', 'div.newscontent')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler1.jpg',
        'HTMLContentHandler': handler1
    },
    '中国国际工程咨询有限公司（中咨视界）': {
        'URLs': [
            'https://www.ciecc.com.cn/col/col2218/index.html',
            'https://www.ciecc.com.cn/col/col2218/index.html?uid=5248&pageNum=2',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.main_comr.fr'),
            ('css', 'div.default_pgContainer'),
            ('css', 'div.news-list'),
            ('css', 'div.newscontent')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler1.jpg',
        'HTMLContentHandler': handler1
    },
    '中国人民大学国家发展与战略研究院（学者观点）': {
        'URLs': [
            'http://nads.ruc.edu.cn/zkdt/xzgd/index.htm',
            'http://nads.ruc.edu.cn/zkdt/xzgd/index1.htm',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.commonRight'),
            ('css', 'div.commonRightTitle'),
            ('css', 'div.Brief'),
            ('css', 'div.briefItem'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler2.png',
        'HTMLContentHandler': handler2
    },
    '中国人民大学国家发展与战略研究院（双周政策分析简报）': {
        'URLs': [
            'http://nads.ruc.edu.cn/zkcg/zcjb/szzcfxjb/index.htm',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.commonRight'),
            ('css', 'div.commonRightTitle'),
            ('css', 'div.Brief'),
            ('css', 'div.briefItem'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler2.png',
        'HTMLContentHandler': handler2
    },
    '国务院发展研究中心': {
        'URL': 'https://www.drc.gov.cn/Leaf.aspx?leafid=1346',
        'NumberOfPagesNeeded': 2,
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.conright.fr'),
            ('css', 'div.containerbg'),
            ('css', 'div.document-box'),
            ('css', 'div.rr3'),
            ('css', 'div.re_box'),
        ],
        'MainPageWaitingTimeLimitInSeconds': 30,
        'PageUpdatesWaitingTimeLimitInSeconds': 1,
        'LogoPath': './Logos/handler3.png',
        'HTMLContentHandler': handler3
    },
    '中国科学院（院内要闻）': {
        'URLs': [
            'https://www.cas.cn/yw/index.shtml',
            'https://www.cas.cn/yw/index_1.shtml'
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.container.boxcenter.main.pad_main'),
            ('css', 'div.xl.list_xl'),
            ('css', 'ul.gl_list2'),
            ('css', 'div#content')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler4.png',
        'HTMLContentHandler': handler4
    },
    '国家发改委宏观经济研究院（科研动态）': {
        'URLs': [
            'https://www.amr.org.cn/ghdt/kydt/index.html',
            'https://www.amr.org.cn/ghdt/kydt/index_1.html'
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.flex'),
            ('css', 'div.list'),
            ('css', 'ul.u-list')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler5.png',
        'HTMLContentHandler': handler5
    },
    'CCiD赛迪研究院（赛迪新闻）': {
        'URLs': [
            'https://www.ccidgroup.com/xwdt/sdxw.htm',
            'https://www.ccidgroup.com/xwdt/sdxw/91.htm'
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.layout_div1_list'),
            ('css', 'div.new_list.new0')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler6.png',
        'HTMLContentHandler': handler6
    },
    '上海社会科学院（新闻）': {
        'URLs': [
            'https://www.sass.org.cn/1198/list1.htm',
            'https://www.sass.org.cn/1198/list2.htm'
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.column-news-con'),
            ('css', 'div.column-news-list.clearfix'),
            ('css', 'ul.cols_list.clearfix')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler7.png',
        'HTMLContentHandler': handler7
    },
    '上海社会科学院（专家视点）': {
        'URLs': [
            'https://www.sass.org.cn/1201/list.htm',
            'https://www.sass.org.cn/1201/list2.htm'
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.column-news-con'),
            ('css', 'div.column-news-list.clearfix'),
            ('css', 'ul.cols_list.clearfix')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler7.png',
        'HTMLContentHandler': handler7
    },
    '上海社会科学院（习近平文化思想最佳实践地建设）': {
        'URLs': [
            'https://www.sass.org.cn/5867/list.htm',
            'https://www.sass.org.cn/5867/list2.htm'
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.column-news-con'),
            ('css', 'div.column-news-list.clearfix'),
            ('css', 'ul.cols_list.clearfix')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler7.png',
        'HTMLContentHandler': handler7
    },
}
CDI_URLData = {
    '综合开发研究院（樊纲观点）': {
        'URLs': [
            'http://www.cdi.com.cn/Article/List?ColumnId=102',
            'http://www.cdi.com.cn/Article/List?ColumnId=102&pageIndex=2',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'ul#ColumnsList'),
            ('css', 'div.content')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler8.png',
        'HTMLContentHandler': handler8_cdi_articles
    },
    '综合开发研究院（综研国策）': {
        'URLs': [
            'http://www.cdi.com.cn/Article/List?ColumnId=152',
            'http://www.cdi.com.cn/Article/List?ColumnId=152&pageIndex=2',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'ul#ColumnsList'),
            ('css', 'div.content')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler8.png',
        'HTMLContentHandler': handler8_cdi_articles
    },
    '综合开发研究院（综研观察）': {
        'URLs': [
            'http://www.cdi.com.cn/Article/List?ColumnId=150',
            'http://www.cdi.com.cn/Article/List?ColumnId=150&pageIndex=2',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'ul#ColumnsList'),
            ('css', 'div.content')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler8.png',
        'HTMLContentHandler': handler8_cdi_articles
    },
    '综合开发研究院（综研专访）': {
        'URLs': [
            'http://www.cdi.com.cn/Article/List?ColumnId=153',
            'http://www.cdi.com.cn/Article/List?ColumnId=153&pageIndex=2',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'ul#ColumnsList'),
            ('css', 'div.content')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler8.png',
        'HTMLContentHandler': handler8_cdi_articles
    },
    '综合开发研究院（综研视点）': {
        'URLs': [
            'http://www.cdi.com.cn/Article/List?ColumnId=154',
            'http://www.cdi.com.cn/Article/List?ColumnId=154&pageIndex=2',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'ul#ColumnsList'),
            ('css', 'div.content')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler8.png',
        'HTMLContentHandler': handler8_cdi_articles
    },
    '综合开发研究院（中国经济月报）': {
        'URLs': [
            'http://www.cdi.com.cn/Files/ListYear?ColumnId=155',
            'http://www.cdi.com.cn/Files/ListYear?ColumnId=155&pageIndex=2',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div#ColumnsList'),
            ('css', 'div.content')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler8.png',
        'HTMLContentHandler': handler9_cdi_files
    },
}
URLData.update(CDI_URLData)

# ---------------------------------------------------------------------------------------------------------------------
# |                                   Change Detection Module (轻量变更检测)                                          |
# ---------------------------------------------------------------------------------------------------------------------

# 说明：
# - 目标：在不改动其余逻辑的前提下，避免在“列表页完全未更新”的情况下重建 index.html，
#         显著减少 main.py 的运行时长。
# - 方法：
#   1) 为 URLData 中的每个列表页 URL 计算“轻量指纹”：ETag、Last-Modified、以及前若干字节内容的哈希；
#   2) 将指纹持久化到本地 JSON 文件；
#   3) 下次运行先读取旧指纹，对每个 URL 做条件请求（If-None-Match / If-Modified-Since）或轻量 GET；
#      若全部未变化，则直接跳过重建并复用上次生成的 HTML。

from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse as _cd_url_parse

FINGERPRINT_STORE_PATH = os.path.join('.', 'generated_html', 'index.fingerprints.json')


def _ensure_parent_dir(path: str) -> None:
    """确保指纹文件所在目录存在。"""
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def _normalize_url(u: str) -> str:
    """对 URL 做简单规范化（小写 scheme/host，去除首尾空格）。"""
    try:
        u = (u or '').strip()
        parts = _cd_url_parse(u)
        if not parts.scheme:
            return u
        # 仅规范化 scheme/host，保留 path/query 完整性
        norm = parts._replace(scheme=parts.scheme.lower(), netloc=parts.netloc.lower())
        return norm.geturl()
    except Exception:
        return u


def _load_fingerprints(path: str) -> Dict[str, Any]:
    """读取历史指纹；文件不存在时返回空字典。"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_fingerprints(path: str, data: Dict[str, Any]) -> None:
    """保存新的指纹。"""
    _ensure_parent_dir(path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _collect_seed_urls(url_data: Dict[str, Any]) -> List[str]:
    """收集 URLData 中的所有列表页 URL（去重、排序）。"""
    urls = set()
    for cfg in url_data.values():
        try:
            for u in cfg.get('URLs', []) or []:
                urls.add(_normalize_url(u))
        except Exception:
            continue
    return sorted(urls)


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b or b'')
    return h.hexdigest()


def _fetch_fingerprint(url: str, session: requests.Session, prev_fp: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], bool]:
    """
    获取单个 URL 的轻量指纹。
    返回 (fp_dict, not_modified)

    策略：
    - 先 HEAD，携带 If-None-Match / If-Modified-Since；若 304，则直接 not_modified=True；
    - 否则读取 ETag/Last-Modified；若均缺失，再做 Range: bytes=0-4095 的 GET 取前 4KB 做内容哈希；
    - 若服务端不支持 Range 也可接受，取较小响应体再哈希。
    """
    headers: Dict[str, str] = {}
    if prev_fp:
        if prev_fp.get('etag'):
            headers['If-None-Match'] = prev_fp['etag']
        if prev_fp.get('last_modified'):
            headers['If-Modified-Since'] = prev_fp['last_modified']

    # 先尝试 HEAD
    etag = ''
    last_modified = ''
    try:
        r = session.head(url, headers=headers, allow_redirects=True, timeout=10)
        if r.status_code == 304:
            # 未修改
            return ({
                'url': url,
                'etag': prev_fp.get('etag') if prev_fp else '',
                'last_modified': prev_fp.get('last_modified') if prev_fp else '',
                'content_hash': prev_fp.get('content_hash') if prev_fp else ''
            }, True)
        etag = r.headers.get('ETag', '') or r.headers.get('Etag', '')
        last_modified = r.headers.get('Last-Modified', '') or r.headers.get('Last-modified', '')
    except Exception:
        pass

    # 若头信息不足或可能变化，获取部分内容以计算哈希
    content_hash = ''
    try:
        range_headers = dict(headers)
        range_headers['Range'] = 'bytes=0-4095'
        r2 = session.get(url, headers=range_headers, allow_redirects=True, timeout=15, stream=True)
        if r2.status_code == 304:
            return ({
                'url': url,
                'etag': prev_fp.get('etag') if prev_fp else etag,
                'last_modified': prev_fp.get('last_modified') if prev_fp else last_modified,
                'content_hash': prev_fp.get('content_hash') if prev_fp else ''
            }, True)
        # 尽量只读取前 4KB
        chunk = b''
        try:
            for _ in range(4):  # 4 x 1KB
                part = next(r2.iter_content(1024))
                if not part:
                    break
                chunk += part
                if len(chunk) >= 4096:
                    break
        except StopIteration:
            pass
        except Exception:
            # 若流式读取异常，退回读取完整响应体（可能较小）
            try:
                chunk = r2.content or b''
            except Exception:
                chunk = b''
        content_hash = _sha256_bytes(chunk)
    except Exception:
        # GET 失败时保留已有的头部信息
        pass

    fp: Dict[str, Any] = {
        'url': url,
        'etag': etag or (prev_fp.get('etag') if prev_fp else ''),
        'last_modified': last_modified or (prev_fp.get('last_modified') if prev_fp else ''),
        'content_hash': content_hash or (prev_fp.get('content_hash') if prev_fp else '')
    }

    # 如果三者都为空，则无法判断，视为“可能有变动”
    if not (fp['etag'] or fp['last_modified'] or fp['content_hash']):
        return fp, False
    # 对比逻辑：
    if prev_fp:
        if fp['etag'] and prev_fp.get('etag') and fp['etag'] != prev_fp['etag']:
            return fp, False
        if fp['last_modified'] and prev_fp.get('last_modified') and fp['last_modified'] != prev_fp['last_modified']:
            return fp, False
        if fp['content_hash'] and prev_fp.get('content_hash') and fp['content_hash'] != prev_fp['content_hash']:
            return fp, False
        # 三者都存在时均相同，则未修改
        if (fp['etag'] or fp['last_modified'] or fp['content_hash']):
            return fp, True
    return fp, False


def detect_changes_and_maybe_exit(url_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行变更检测：
    - 若全部列表页未变化，直接打印提示并退出进程；
    - 若发现任意 URL 变化，返回新的指纹映射（供构建成功后落盘）。

    返回值：new_fingerprints: dict
    """
    seed_urls = _collect_seed_urls(url_data)
    if not seed_urls:
        # 没有任何 URL，放行构建
        return {}

    prev_store = _load_fingerprints(FINGERPRINT_STORE_PATH)
    prev_items = prev_store.get('items') if isinstance(prev_store, dict) else None
    prev_map: Dict[str, Any] = {}
    if isinstance(prev_items, list):
        for item in prev_items:
            try:
                prev_map[_normalize_url(item.get('url', ''))] = item
            except Exception:
                continue

    session = requests.Session()
    changed = False
    new_items: List[Dict[str, Any]] = []
    changed_urls: List[str] = []

    for u in seed_urls:
        prev_fp = prev_map.get(u)
        fp, not_modified = _fetch_fingerprint(u, session=session, prev_fp=prev_fp)
        new_items.append(fp)
        if not not_modified:
            # 若无历史记录也视为变化（首次运行）
            if prev_fp is None:
                changed = True
                changed_urls.append(u + ' (first-check)')
            else:
                # 进一步判断（当三要素均空时，也算变化）
                if not (fp.get('etag') or fp.get('last_modified') or fp.get('content_hash')):
                    changed = True
                    changed_urls.append(u + ' (undetermined)')
                else:
                    # 已比较过差异，标记变化
                    if fp.get('etag') != prev_fp.get('etag') or fp.get('last_modified') != prev_fp.get('last_modified') or (
                        fp.get('content_hash') and fp.get('content_hash') != prev_fp.get('content_hash')
                    ):
                        changed = True
                        changed_urls.append(u)

    # 如果没有任何历史指纹文件，同时 index.html 也不存在，则视为需要构建
    index_exists = os.path.isfile(os.path.join('.', 'generated_html', 'index.html'))
    if (not prev_store) and (not index_exists):
        changed = True

    if not changed:
        print('Change detection: no list pages updated; reuse existing generated_html/index.html. Skip rebuilding.')
        sys.exit(0)

    # 返回新的指纹，供构建成功后保存
    return {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'items': new_items,
        'changed_urls': changed_urls,
        'total_urls': len(seed_urls)
    }


# 在进入渲染构建之前执行变更检测
_CHANGE_DETECTION_RESULT = detect_changes_and_maybe_exit(URLData)

# ---------------------------------------------------------------------------------------------------------------------
# |                   The following code collects online data and generates a new HTML page.                          |
# ---------------------------------------------------------------------------------------------------------------------

# 全局每页最大等待时间（秒）。若 10 秒内未就绪则跳过该页面。
PER_PAGE_MAX_WAIT_SECONDS = int(os.getenv('MAIN_PER_PAGE_TIMEOUT', '10'))

# 将 URLData 中各站点配置的等待时间统一限制为不超过 5 秒。
for _site, _cfg in URLData.items():
    try:
        prev = _cfg.get('WaitingTimeLimitInSeconds')
        if isinstance(prev, (int, float)):
            _cfg['WaitingTimeLimitInSeconds'] = min(int(prev), PER_PAGE_MAX_WAIT_SECONDS)
        else:
            _cfg['WaitingTimeLimitInSeconds'] = PER_PAGE_MAX_WAIT_SECONDS
    except Exception:
        _cfg['WaitingTimeLimitInSeconds'] = PER_PAGE_MAX_WAIT_SECONDS


chrome_options = ChromeOptions()
# chrome_options.add_argument('--incognito')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--ignore-ssl-errors')
chrome_options.add_argument('--allow-running-insecure-content')
chrome_options.add_argument('--disable-web-security')
chrome_options.add_argument('--disable-site-isolation-trials')
chrome_options.add_argument('--test-type')
chrome_options.set_capability('acceptInsecureCerts', True)
chrome_options.add_argument(
    'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/110.0.0.0 Safari/537.36'
)

chrome_page_render = ChromePageRender(
    chrome_driver_filepath=__chrome_driver_path,
    options=chrome_options
)

# configure new HTML document header and body
new_document: HTMLDocument = HTMLDocument(title='知名智库精选数据', lang='zh')
with new_document.head:
    HTMLTags.meta(
        charset='utf-8',
        name='viewport',
        content='width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no'
    )
    HTMLTags.link(rel='stylesheet', href='./index.css')
    HTMLTags.script(src='./html2pdf.bundle.min.js')
    HTMLTags.script(src='./index.js')
with new_document.body:
    HTMLTags.h1(
        f"知名智库精选数据（更新时间：{current_time.year}/{current_time.month:02d}/{current_time.day:02d} "
        f"{current_time.hour:02d}:{current_time.minute:02d}:{current_time.second:02d}）"
    )
    HTMLTags.div(cls='page-board search-container', id='search-container')
for (url_name, url_info) in LoopMeter(URLData.items(), unit="site", unit_scale=False):
    try:
        url_info['HTMLContentHandler'](
            chrome_page_render=chrome_page_render,
            document=new_document,
            url_name=url_name,
            url_info=url_info
        )
    except Exception as e:
        print(f"Skip site '{url_name}' due to error: {e}")

try:
    with open('./generated_html/index.html', 'w', encoding='utf-8') as html_file:
        html_file.write(new_document.render(pretty=True))  # pretty makes the HTML file human-readable
    print(f"Successfully output \"./generated_html/index.html\".")
    # 构建成功后，更新指纹文件（非首次且检测模块已运行时）
    try:
        if isinstance(_CHANGE_DETECTION_RESULT, dict) and _CHANGE_DETECTION_RESULT:
            _save_fingerprints(FINGERPRINT_STORE_PATH, _CHANGE_DETECTION_RESULT)
    except Exception as e:
        print(f"Warning: failed to update fingerprints: {e}")
except Exception as e:
    print(f"Failed to output \"./generated_html/index.html\". Error: {e}")








