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


def handler21_iccs_research(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    清华大学国情研究院（ICCS）研究栏目通用列表抓取。
    - 输入：一个或多个栏目列表页 URL（如：世情研究/国情研究/区情研究）。
    - 解析：尽量从常见列表结构中提取条目（a[href] + 标题 + 日期），若失败则回退到通过 URL 规则匹配提取。
    - 输出：与既有页面一致的 DOM 结构（.page-board/.page-board-item）。
    """
    urls = url_info.get('URLs', []) or []
    if len(urls) <= 0:
        return None

    max_items = int(url_info.get('MaxItems', 12))
    all_items = []  # list of (href, title, date)
    seen = set()

    for base_url in urls:
        html_content = None
        try:
            is_timeout = chrome_page_render.goto_url_waiting_for_selectors(
                url=base_url,
                selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
                waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
                print_error_log_to_console=True
            )
            if not is_timeout:
                html_content = chrome_page_render.get_page_source()
        except Exception:
            html_content = None
        if not html_content:
            continue

        soup = BeautifulSoup(html_content, 'html.parser')

        # ICCS: 优先限定到主体列表容器，避免抓到公共模块导致三栏一致
        preselected_iccs_nodes = []
        try:
            for _sel in [
                'div.i_main div.wp.cle.p_main div.p_l.fl div.publish ul.noticeul > li.noticeItem',
                'div.i_main div.p_l.fl div.publish ul.noticeul > li.noticeItem',
                'div.publish ul.noticeul > li.noticeItem',
            ]:
                _nodes = soup.select(_sel)
                if _nodes:
                    preselected_iccs_nodes = _nodes
                    break
        except Exception:
            preselected_iccs_nodes = []

        # 优先从常见列表结构提取
        candidate_li_nodes = preselected_iccs_nodes or []
        candidate_wrappers = [
            'div.list ul', 'div.newslist ul', 'div.article-list ul', 'div.con ul', 'div.main ul',
            'div.wp ul', 'div.container ul', 'ul.list', 'ul.listul', 'ul.newslist', 'ul.items',
        ]
        if not candidate_li_nodes:
            for ul_sel in candidate_wrappers:
                try:
                    ul_node = soup.select_one(ul_sel)
                    if ul_node is not None:
                        lis = ul_node.select('li')
                        if lis:
                            candidate_li_nodes = lis
                            break
                except Exception:
                    continue
        if not candidate_li_nodes:
            # 回退：页面中所有可能的 li
            try:
                candidate_li_nodes = soup.select('li')
            except Exception:
                candidate_li_nodes = []

        # 逐个 li 提取 a/title/date
        for li in candidate_li_nodes:
            try:
                a = li.select_one('h3 a') or li.select_one('h4 a') or li.select_one('a[href]')
                if a is None or (not a.get('href')):
                    continue
                href = url_join(base_url, a.get('href'))
                if href in seen:
                    continue
                # 过滤明显的导航/社交/空链接
                if a.find_parent('nav') is not None:
                    continue
                # 标题
                title_node = a.select_one('h3, h4') or a
                title_text = title_node.get_text(strip=True) if title_node is not None else ''
                if not title_text:
                    title_text = a.get('title', '').strip()
                # 日期：从 li 中常见位置提取，或者用正则从文本中提取
                date_node = (
                    li.select_one('span') or li.select_one('em') or li.select_one('i') or
                    li.select_one('time') or li.select_one('.date') or li.select_one('.time')
                )
                date_text = ''
                if date_node is not None:
                    raw = date_node.get_text(strip=True)
                    m = re.search(r'(\d{4})[./\-年](\d{1,2})[./\-月](\d{1,2})', raw)
                    if m:
                        date_text = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                if not date_text:
                    # 从 li 的整体文本尝试兜底
                    txt = li.get_text(' ', strip=True)
                    m2 = re.search(r'(\d{4})[./\-年](\d{1,2})[./\-月](\d{1,2})', txt)
                    if m2:
                        date_text = f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"

                if not title_text:
                    continue
                seen.add(href)
                all_items.append((href, title_text, date_text))
                if len(all_items) >= max_items:
                    break
            except Exception:
                continue
        if len(all_items) >= max_items:
            break

        # 若未采到，回退：页面上筛选符合研究详情链接规律的 a 标签
        if len(all_items) < max_items:
            for a in soup.select('a[href]'):
                try:
                    href = a.get('href', '')
                    if not href:
                        continue
                    full = url_join(base_url, href)
                    if full in seen:
                        continue
                    # 研究/发布/动态等详情页的常见路径片段
                    if not re.search(r'/(research|publish|dynamic)_info/\d+\.html', full):
                        continue
                    title_text = a.get_text(strip=True) or a.get('title', '').strip()
                    if not title_text:
                        continue
                    all_items.append((full, title_text, ''))
                    seen.add(full)
                    if len(all_items) >= max_items:
                        break
                except Exception:
                    continue

    # 渲染至页面
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=urls[0]):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in all_items[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
    return None

def handler11_rand_topics(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    新增：RAND Topics 列表处理器（每组近 30 条）。
    解析 ul.teasers 列表，抽取 a[href]、h3.title、p.date，输出与既有结构一致。
    """
    urls = url_info.get('URLs', []) or []
    if len(urls) <= 0:
        return None
    results = []
    seen_links = set()
    max_items = int(url_info.get('MaxItems', 30))
    for url in urls:
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
        if not html_content:
            continue
        soup = BeautifulSoup(html_content, 'html.parser')
        container = soup.select_one('ul.teasers.list.filterable.hasImg') or soup.select_one('ul.teasers.list.hasImg') or soup.select_one('ul.teasers')
        if container is None:
            continue
        for li in container.select('li'):
            a = li.select_one('a[href]')
            if a is None or not a.get('href'):
                continue
            link = url_join(url, a['href'])
            if link in seen_links:
                continue
            title_node = li.select_one('h3.title') or a.select_one('h3') or li.select_one('h3') or a
            title_text = title_node.get_text(strip=True) if title_node is not None else ''
            date_node = li.select_one('p.date') or li.select_one('time')
            date_text = _rand_parse_en_date_to_iso(date_node.get_text(strip=True)) if date_node is not None else ''
            seen_links.add(link)
            results.append((link, title_text, date_text))
            if len(results) >= max_items:
                break
        if len(results) >= max_items:
            break

    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=urls[0]):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in results[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text)
    return None


def _jpm_parse_en_date_to_iso(date_text: str) -> str:
    """Parse common English date strings into YYYY-MM-DD for JPM pages."""
    try:
        if not isinstance(date_text, str):
            return ''
        s = (date_text or '').strip()
        if not s:
            return ''
        m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
        if m:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        months = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'sept': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12,
        }
        # e.g., "Oct 8, 2025"
        m = re.search(r'([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})', s)
        if m:
            mo = months.get(m.group(1).lower(), 0)
            if mo:
                return f"{int(m.group(3)):04d}-{mo:02d}-{int(m.group(2)):02d}"
        # e.g., "8 Oct 2025"
        m = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{4})', s)
        if m:
            mo = months.get(m.group(2).lower(), 0)
            if mo:
                return f"{int(m.group(3)):04d}-{mo:02d}-{int(m.group(1)):02d}"
        return ''
    except Exception:
        return ''


def handler12_jpm_insights(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    JPMorgan Insights list handler
    - Loads the main insights page and clicks "Load more" until MaxItems are collected or no more items.
    - Extracts link, title, and date (if present) and appends to the document.
    """
    urls = url_info.get('URLs', []) or []
    if len(urls) <= 0:
        return None

    def _extract_items(html: str, base_url: str):
        soup = BeautifulSoup(html, 'html.parser')
        # Scope strictly within All Insights grid
        root = soup.select_one('#all-insights') or soup
        grid = root.select_one('.cmp-dynamic-grid-content') or root
        items = []
        seen = set()
        # Cards: article-card / jpma-article-card / podcast-card
        cards = grid.select('ul.grid > li.article-card, ul.grid > li.jpma-article-card, ul.grid > li.podcast-card')
        if not cards:
            cards = grid.select('ul li.article-card, ul li.jpma-article-card, ul li.podcast-card')
        # Fallback: any li under grid
        if not cards:
            cards = grid.select('ul.grid > li, ul li')
        for node in cards:
            # Anchor inside CTA
            a = (
                node.select_one('p.dynamic-grid__cta-link a[href]') or
                node.select_one('a[href*="/insights/"]') or
                node.select_one('a[href]')
            )
            if not a or not a.get('href'):
                continue
            href = url_join(base_url, a['href'])
            if href in seen:
                continue
            if a.find_parent('nav') is not None:
                continue
            # Title/Date within dynamic-grid__title-date
            td = node.select_one('.dynamic-grid__title-date')
            title_node = (td.select_one('.dynamic-grid__title') if td else None) or node.select_one('.dynamic-grid__title') or node.select_one('h3, h2') or a
            title = title_node.get_text(strip=True) if title_node is not None else ''
            date_node = (td.select_one('.dynamic-grid__date') if td else None) or node.select_one('time[datetime]') or node.select_one('time')
            date_text = ''
            if date_node is not None:
                date_text = _jpm_parse_en_date_to_iso(date_node.get_text(strip=True) or date_node.get('datetime', ''))
            seen.add(href)
            if title:
                items.append((href, title, date_text))
        # As a fallback, greedily scan anchors in main content
        if not items:
            for a in root.select('a[href*="/insights/"]'):
                if a.find_parent('nav') is not None:
                    continue
                href = url_join(base_url, a.get('href', ''))
                if not href or href in seen:
                    continue
                title = a.get_text(strip=True)
                if not title:
                    continue
                items.append((href, title, ''))
                seen.add(href)
        return items

    def _try_accept_cookies():
        # Best-effort cookie/consent dismissal
        for sel in [
            'button#onetrust-accept-btn-handler',
            'button[aria-label*="Accept"]',
            'button[aria-label*="agree"]',
            'button[class*="cookie"][class*="accept"]',
        ]:
            try:
                is_timeout = _local_cpr.click_on_html_element(
                    click_element_selector_type='css',
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if is_timeout is False:
                    break
            except Exception:
                pass

    def _try_click_load_more() -> bool:
        # Attempt several likely selectors for load-more button
        selectors = [
            '#all-insights .load-more-container .load-more-card.active button[aria-label="load more content"]',
            '#all-insights .load-more-container .load-more-card.active button',
            '#all-insights .load-more-container button',
            '#all-insights button[aria-label*="load more" i]',
            '#all-insights button[class*="load" i]',
        ]
        for sel in selectors:
            try:
                timed_out = _local_cpr.click_on_html_element(
                    click_element_selector_type='css',
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if timed_out is False:
                    return True
            except Exception:
                continue
        return False

    max_items = int(url_info.get('MaxItems', 80))
    base_url = urls[0]

    # Use a dedicated undetected driver for JPM to ensure dynamic grid loads reliably
    local_options = ChromeOptions()
    try:
        local_options.page_load_strategy = 'none'
    except Exception:
        pass
    local_options.add_argument('--disable-blink-features=AutomationControlled')
    local_options.add_argument('--ignore-certificate-errors')
    local_options.add_argument('--ignore-ssl-errors')
    local_options.add_argument('--allow-running-insecure-content')
    local_options.add_argument('--disable-web-security')
    local_options.add_argument('--disable-site-isolation-trials')
    local_options.add_argument('--test-type')
    local_options.set_capability('acceptInsecureCerts', True)
    local_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )

    _local_cpr = ChromePageRender(
        chrome_driver_filepath=__chrome_driver_path,
        options=local_options,
        use_undetected_chromedriver=True
    )
    try:
        # Open and wait for the insights grid to mount
        is_timeout = _local_cpr.goto_url_waiting_for_selectors(
            url=base_url,
            selector_types_rules=[
                ('css', '#all-insights'),
            ],
            waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
            print_error_log_to_console=True
        )
        if is_timeout:
            return None

        # Scroll the insights section into view to trigger lazy loading
        try:
            _local_cpr.click_on_html_element(
                click_element_selector_type='css',
                click_element_selector_rule='#all-insights',
                use_javascript=True,
                max_trials_for_unstable_page=1,
                click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                print_error_log_to_console=False
            )
        except Exception:
            pass

        # Poll for the insights grid list to load
        results = []
        max_wait = int(url_info.get('WaitingTimeLimitInSeconds', 10))
        for _ in range(max(10, max_wait * 3)):  # 0.5s x loops
            html = _local_cpr.get_page_source()
            results = _extract_items(html, base_url)
            if results:
                break
            sleep(0.5)

        # Keep clicking load-more while we need more items
        while len(results) < max_items:
            before = len(results)
            clicked = _try_click_load_more()
            if not clicked:
                break
            for _ in range(24):  # wait up to ~12s for new cards
                sleep(0.5)
                html = _local_cpr.get_page_source()
                results = _extract_items(html, base_url)
                if len(results) > before:
                    break
            if len(results) <= before:
                break

        # Render collected items to the main document (same format as others)
        try:
            print(f"JPM handler: collected {len(results)} items (limit {max_items}).")
        except Exception:
            pass
        with document.body:
            with HTMLTags.div(cls='page-board'):
                HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
                with HTMLTags.a(href=base_url):
                    HTMLTags.h2(url_name)
                for (a_href, h3_text, span_text) in results[:max_items]:
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text or '')
        return None
    finally:
        try:
            _local_cpr.close()
        except Exception:
            pass

## 删除：原 RAND Research & Commentary 列表处理器已按需求移除

def _rand_parse_en_date_to_iso(date_text: str) -> str:
    """RAND 列表常用英文日期（如 "Oct 8, 2025"）转为 YYYY-MM-DD。"""
    if not isinstance(date_text, str):
        return ''
    return ''




# 覆盖修复：重新定义英文日期解析，避免上方精简实现的缩进问题
def _rand_parse_en_date_to_iso(date_text: str) -> str:
    try:
        if not isinstance(date_text, str):
            return ''
        s = (date_text or '').strip()
        if not s:
            return ''
        m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
        if m:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        months = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'sept': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12,
        }
        m = re.search(r'([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})', s)
        if m:
            mo = months.get(m.group(1).lower(), 0)
            if mo:
                return f"{int(m.group(3)):04d}-{mo:02d}-{int(m.group(2)):02d}"
        m = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{4})', s)
        if m:
            mo = months.get(m.group(2).lower(), 0)
            if mo:
                return f"{int(m.group(3)):04d}-{mo:02d}-{int(m.group(1)):02d}"
        return ''
    except Exception:
        return ''
    s = date_text.strip()
    if not s:
        return ''
    m0 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', s)
    if m0:
        return f"{int(m0.group(1)):04d}-{int(m0.group(2)):02d}-{int(m0.group(3)):02d}"
    months = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    m = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})', s)
    if m:
        mon = months.get(m.group(1).lower(), 0)
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}"
    m2 = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', s)
    if m2:
        mon = months.get(m2.group(2).lower(), 0)
        if mon:
            return f"{int(m2.group(3)):04d}-{mon:02d}-{int(m2.group(1)):02d}"
    return s

def handler10_nsd(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    # Beijing University NSD (观点) list handler
    if len(url_info['URLs']) <= 0:
        return None
    urls_contents = {}
    for url in url_info['URLs']:
        try:
            content = None
            is_timeout = chrome_page_render.goto_url_waiting_for_selectors(
                url=url,
                selector_types_rules=url_info['RulesAwaitingSelectors(Types,Rules)'],
                waiting_timeout_in_seconds=url_info['WaitingTimeLimitInSeconds'],
                print_error_log_to_console=True
            )
            if not is_timeout:
                content = chrome_page_render.get_page_source()
        except Exception:
            content = None
        urls_contents[url] = content
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=url_info['URLs'][0]):
                HTMLTags.h2(url_name)
            for (base_url, html_content) in urls_contents.items():
                if html_content is None:
                    continue
                soup = BeautifulSoup(html_content, 'html.parser')
                li_nodes = []
                candidate_selectors = [
                    'div.maincontent ul.captions li',
                    'ul.captions li',
                    'div.container ul.list li',
                    'div.con_main ul.list li',
                    'div.con-left ul.list li',
                    'ul.list li',
                    'div.list ul li'
                ]
                for sel in candidate_selectors:
                    li_nodes = soup.select(sel)
                    if li_nodes:
                        break
                # fallback: try any li that contains an anchor under main content
                if not li_nodes:
                    try:
                        main_container = soup.select_one('div.wrapper') or soup.select_one('div.container') or soup
                        li_nodes = [li for li in main_container.select('li') if li.select_one('a')]
                    except Exception:
                        li_nodes = []
                for old_li in li_nodes:
                    # NSD 结构：li > div.caption > h4.title > a
                    old_a = old_li.select_one('h4.title a') or old_li.select_one('a')
                    if old_a is None or not old_a.get('href'):
                        continue
                    a_href = url_join(base_url, old_a.get('href'))
                    # 仅保留观点栏目常见的详情链接（站内 /info/ 或微信外链）
                    href_l = a_href.lower()
                    if not (('mp.weixin.qq.com' in href_l) or ('/info/' in href_l)):
                        continue
                    # title text: prefer attribute title then text
                    h3_text = (old_a.get('title') or old_a.get_text(strip=True) or '').strip()
                    # date text: common span/em/time; fallback by regex inside li text
                    span_node = old_li.select_one('span.date') or old_li.select_one('span') or old_li.select_one('em') or old_li.select_one('time')
                    span_text_raw = span_node.get_text(strip=True) if span_node is not None else ''
                    m = re.search(r'(\d{4})[-./年](\d{1,2})[-./月](\d{1,2})', span_text_raw)
                    if m:
                        span_text = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                    else:
                        # try to extract from li text if span missing
                        text_all = old_li.get_text(" ", strip=True)
                        m2 = re.search(r'(\d{4})[-./年](\d{1,2})[-./月](\d{1,2})', text_all)
                        span_text = (
                            f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
                            if m2 else ''
                        )
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=a_href):
                            HTMLTags.h3(h3_text)
                            HTMLTags.span(span_text)
    return None


def handler14_kpmg_insights(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    KPMG China Insights list handler (scroll-to-load, take first N items)

    Behavior
    - Open the insights page and wait for results container to appear.
    - Best-effort accept cookie/consent banners.
    - Repeatedly scroll to the bottom to trigger client-side loading until
      at least `MaxItems` items are collected or no further growth observed.
    - Extract (link, title, date?) from grid tiles and render to document.

    HTML patterns (best-effort and resilient):
    - Root: section.module-resultslisting
    - Container: #resultsListingContainer or div.resultslistContainer
    - Items: div.grid-tiles ... with an anchor carrying href to /insights/...
      Title nodes may be h3/h2 or elements with class containing title.
      Date nodes may be <time datetime> or visible date text.
    """
    urls = url_info.get('URLs', []) or []
    if len(urls) <= 0:
        return None

    base_url = urls[0]
    max_items = int(url_info.get('MaxItems', 40))

    def _try_accept_cookies():
        # Common consent buttons (OneTrust and variations)
        candidates = [
            ('css', 'button#onetrust-accept-btn-handler'),
            ('css', 'button[aria-label*="accept all" i]'),
            ('css', 'button[aria-label*="accept" i]'),
            ('css', 'button[aria-label*="同意" i]'),
            ('css', 'button[title*="接受" i], button[title*="同意" i]'),
            ('css', 'button[class*="cookie" i][class*="accept" i]'),
            # Text-based fallbacks
            ('xpath', "//button[contains(., '接受') or contains(., '同意') or contains(., '允许') or contains(., '接受所有') or contains(., '同意所有')]"),
            ('xpath', "//a[contains(., '接受') or contains(., '同意')]"),
        ]
        for (typ, sel) in candidates:
            try:
                is_timeout = chrome_page_render.click_on_html_element(
                    click_element_selector_type=typ,
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if is_timeout is False:
                    break
            except Exception:
                continue

    def _parse_date_to_iso(s: str) -> str:
        """Parse visible date text to YYYY-MM-DD if possible; else return ''."""
        try:
            if not isinstance(s, str):
                return ''
            s = s.strip()
            if not s:
                return ''
            # 2025-10-08 / 2025/10/08 / 2025.10.08
            m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            # 2025年10月08日 或 2025年10月8日
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            pass
        return ''

    def _extract_items(html: str, base: str):
        soup = BeautifulSoup(html, 'html.parser')
        # Scope to results listing
        root = soup.select_one('#resultsListingContainer') or soup.select_one('div.resultslistContainer') or soup.select_one('section.module-resultslisting') or soup
        items = []
        seen = set()
        # Likely tile nodes with anchors
        tiles = root.select('div.grid-tiles')
        if not tiles:
            tiles = root.select('div[class*="grid"] div[class*="tiles"], div[class*="results"] li, div[class*="results"] article')
        for node in tiles:
            a = node.select_one('a[href]')
            if not a or not a.get('href'):
                continue
            href = url_join(base, a['href'])
            if href in seen:
                continue
            # Avoid nav anchors
            if a.find_parent('nav') is not None:
                continue
            # Title
            title_node = (
                node.select_one('h3, h2') or
                a.select_one('h3, h2') or
                node.select_one('[class*="title" i]') or
                a
            )
            title = title_node.get_text(strip=True) if title_node is not None else ''
            # Date
            date_node = node.select_one('time[datetime]') or node.select_one('time') or node.select_one('[class*="date" i]')
            date_text = ''
            if date_node is not None:
                date_text = _parse_date_to_iso(date_node.get('datetime', '') or date_node.get_text(strip=True))
            if title:
                items.append((href, title, date_text))
                seen.add(href)
            if len(items) >= max_items:
                break
        # Fallback: greedily scan result anchors if we still have none
        if not items:
            for a in root.select('a[href*="/insights/" i]'):
                if a.find_parent('nav') is not None:
                    continue
                href = url_join(base, a.get('href', ''))
                if not href or href in seen:
                    continue
                title = a.get_text(strip=True)
                if not title:
                    continue
                items.append((href, title, ''))
                seen.add(href)
                if len(items) >= max_items:
                    break
        return items

    # Open base page first, then try accept cookies before any strict waits
    page_opened = True
    try:
        chrome_page_render.goto_url(url=base_url)
    except Exception:
        # Do not abort; we will try HTTP fallback later
        page_opened = False

    _try_accept_cookies()
    # Soft wait for results container, but do not bail out on timeout
    try:
        chrome_page_render.wait_for_selectors(
            wait_type='appear',
            selector_types_rules=url_info.get('RulesAwaitingSelectors(Types,Rules)', [('css', 'section.module-resultslisting')]),
            waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
            print_error_log_to_console=False
        )
    except Exception:
        pass

    # Progressive scroll to load more results
    results = []
    last_len = 0
    stagnation_rounds = 0

    def _exec_js(script: str):
        # Access underlying webdriver; safe no-op if not available
        try:
            browser = getattr(chrome_page_render, f"_ChromePageRender__browser", None)
            if browser is not None:
                return browser.execute_script(script)
        except Exception:
            pass
        return None

    # Initial wait loop to ensure React list paints (only when page opened)
    max_wait = max(6, int(url_info.get('WaitingTimeLimitInSeconds', 10)) * 2)
    if page_opened:
        for _ in range(max_wait):
            try:
                html = chrome_page_render.get_page_source()
            except Exception:
                html = ''
            results = _extract_items(html, base_url)
            if results:
                break
            sleep(0.5)

        while len(results) < max_items:
            # Scroll near the bottom
            try:
                before_h = _exec_js('return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);') or 0
                _exec_js('window.scrollTo(0, document.body.scrollHeight);')
                sleep(0.9)
                after_h = _exec_js('return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);') or before_h
            except Exception:
                after_h = 0

            # Try accept cookies again in case banner re-appears or first click failed
            _try_accept_cookies()

            # Re-parse items
            try:
                html = chrome_page_render.get_page_source()
            except Exception:
                html = ''
            current = _extract_items(html, base_url)
            # Merge with de-dup
            if current:
                seen = set(x[0] for x in results)
                for it in current:
                    if it[0] not in seen:
                        results.append(it)
                        seen.add(it[0])

            # Convergence check
            if len(results) == last_len and (after_h <= (before_h or 0)):
                stagnation_rounds += 1
            else:
                stagnation_rounds = 0
            last_len = len(results)
            if stagnation_rounds >= 3:
                break

    # If still empty, try static HTTP fallback (SSR may render a list)
    if not results:
        try:
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
            }
            resp = requests.get(base_url, headers=headers, timeout=20)
            if not resp.encoding or resp.encoding.lower() in ['iso-8859-1', 'ascii']:
                resp.encoding = resp.apparent_encoding or 'utf-8'
            if resp.status_code == 200:
                results = _extract_items(resp.text or '', base_url)
        except Exception:
            pass

    # Render collected items
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=base_url):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in results[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
    return None


def handler15_mck_insights(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    麦肯锡中国（McKinsey & Company）（洞察）列表页处理器

    行为概述：
    - 打开 insights 列表页并等待主体容器出现；
    - 若出现 Cookie/隐私弹窗，尝试接受；
    - 通过连续下滑触发列表懒加载，直到收集到 MaxItems 条或页面不再增长；
    - 解析条目 (link, title, date) 并以统一结构输出。

    选择器策略（尽量健壮）：
    - 根容器：'main' 或包含 insights 列表的 section/article 容器
    - 条目锚点：优先匹配含 '/insights/' 的链接；排除导航/页脚
    - 标题：h3/h2/含 title 类名的元素；兜底 a 的文本
    - 日期：<time datetime> 或带有 date 类名的文本，规范为 YYYY-MM-DD
    """
    urls = url_info.get('URLs', []) or []
    if not urls:
        return None

    base_url = urls[0]
    max_items = int(url_info.get('MaxItems', 20))

    def _try_accept_cookies():
        candidates = [
            ('css', 'button#onetrust-accept-btn-handler'),
            ('css', 'button[aria-label*="accept" i]'),
            ('css', 'button[title*="接受" i], button[title*="同意" i]'),
            ('xpath', "//button[contains(., '接受') or contains(., '同意') or contains(., '允许')]"),
        ]
        for (typ, sel) in candidates:
            try:
                is_timeout = chrome_page_render.click_on_html_element(
                    click_element_selector_type=typ,
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if is_timeout is False:
                    break
            except Exception:
                continue

    def _parse_date_to_iso(s: str) -> str:
        try:
            if not isinstance(s, str):
                return ''
            s = s.strip()
            if not s:
                return ''
            m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            pass
        return ''

    def _extract_items(html: str, base: str):
        soup = BeautifulSoup(html, 'html.parser')
        # 根作用域：优先 main，其次默认 soup
        root = soup.select_one('main') or soup
        items = []
        seen = set()
        # 优先网格/列表容器
        containers = [
            root.select_one('section[class*="insight" i]'),
            root.select_one('div[class*="insight" i]'),
            root.select_one('section[class*="list" i]'),
            root
        ]
        for container in containers:
            if not container:
                continue
            # 候选卡片节点：article/li/div 块
            cards = container.select('article, li, div')
            for node in cards:
                # 排除导航/页脚
                if node.find_parent('nav') is not None or 'footer' in (getattr(node, 'name', '') or '').lower():
                    continue
                a = node.select_one('a[href*="/insights/" i]') or node.select_one('a[href]')
                if not a or not a.get('href'):
                    continue
                href = url_join(base, a['href'])
                # 过滤分页/聚合链接，避免误入列表页造成详情抓取超时
                href_l = href.lower().rstrip('/')
                if href_l.endswith('/insights') or '/insights/page/' in href_l:
                    continue
                if href in seen:
                    continue
                title_node = (
                    node.select_one('h3, h2') or a.select_one('h3, h2') or node.select_one('[class*="title" i]') or a
                )
                title = title_node.get_text(strip=True) if title_node is not None else ''
                if not title:
                    continue
                date_node = node.select_one('time[datetime]') or node.select_one('time') or node.select_one('[class*="date" i]')
                date_text = ''
                if date_node is not None:
                    date_text = _parse_date_to_iso(date_node.get('datetime', '') or date_node.get_text(strip=True))
                items.append((href, title, date_text))
                seen.add(href)
                if len(items) >= max_items:
                    break
            if len(items) >= max_items:
                break
        return items

    # 打开列表页
    try:
        chrome_page_render.goto_url(url=base_url)
    except Exception:
        pass

    _try_accept_cookies()
    # 等待 main/列表容器出现（软等待）
    try:
        chrome_page_render.wait_for_selectors(
            wait_type='appear',
            selector_types_rules=url_info.get('RulesAwaitingSelectors(Types,Rules)', [('css', 'main')]),
            waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
            print_error_log_to_console=False
        )
    except Exception:
        pass

    results = []
    last_len = 0
    stagnation_rounds = 0

    def _exec_js(script: str):
        try:
            browser = getattr(chrome_page_render, f"_ChromePageRender__browser", None)
            if browser is not None:
                return browser.execute_script(script)
        except Exception:
            pass
        return None

    # 初次解析
    max_wait = max(6, int(url_info.get('WaitingTimeLimitInSeconds', 10)) * 2)
    for _ in range(max_wait):
        try:
            html = chrome_page_render.get_page_source()
        except Exception:
            html = ''
        results = _extract_items(html, base_url)
        if results:
            break
        sleep(0.5)

    # 连续下滑以触发懒加载（无 Load More 按钮）
    while len(results) < max_items:
        try:
            before_h = _exec_js('return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);') or 0
            _exec_js('window.scrollTo(0, document.body.scrollHeight);')
            sleep(0.9)
            after_h = _exec_js('return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);') or before_h
        except Exception:
            after_h = 0

        _try_accept_cookies()

        try:
            html = chrome_page_render.get_page_source()
        except Exception:
            html = ''
        current = _extract_items(html, base_url)
        if current:
            seen = set(x[0] for x in results)
            for it in current:
                if it[0] not in seen:
                    results.append(it)
                    seen.add(it[0])

        if len(results) == last_len and (after_h <= (before_h or 0)):
            stagnation_rounds += 1
        else:
            stagnation_rounds = 0
        last_len = len(results)
        if stagnation_rounds >= 3:
            break

    # 渲染到聚合页
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=base_url):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in results[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
    return None

def handler16_pwc_zh_insights(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    普华永道（PwC）中国（洞察）列表页处理器

    需求与行为：
    - 仅抓取前 12 条（无需点击“加载更多”）。
    - 页面初始即呈现若干 <article> 卡片；提取每条的链接、标题、日期（若有）。
    - 输出格式与既有站点一致。

    解析策略（尽量健壮）：
    - 作用域：优先 main，然后容器内查找 article/卡片。
    - 卡片链接：优先匹配 a[href*="/zh/research-and-insights" i]；兜底 a[href]。
    - 标题：h3/h2 或 class 含 title 的节点；兜底 a 文本。
    - 日期：time[datetime] 或包含 "date" 类名的节点文本，统一 YYYY-MM-DD。
    """
    urls = url_info.get('URLs', []) or []
    if not urls:
        return None

    base_url = urls[0]
    max_items = int(url_info.get('MaxItems', 12))

    def _try_accept_cookies():
        candidates = [
            ('css', 'button#onetrust-accept-btn-handler'),
            ('css', 'button[aria-label*="accept" i]'),
            ('css', 'button[title*="接受" i], button[title*="同意" i]'),
            ('xpath', "//button[contains(., '接受') or contains(., '同意') or contains(., '允许')]")
        ]
        for (typ, sel) in candidates:
            try:
                is_timeout = chrome_page_render.click_on_html_element(
                    click_element_selector_type=typ,
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if is_timeout is False:
                    break
            except Exception:
                continue

    def _parse_date_to_iso(s: str) -> str:
        try:
            if not isinstance(s, str):
                return ''
            s = s.strip()
            if not s:
                return ''
            m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            pass
        return ''

    def _extract_items(html: str, base: str):
        soup = BeautifulSoup(html, 'html.parser')
        root = soup.select_one('main') or soup.select_one('div.cmp-container') or soup
        items = []
        seen = set()
        containers = [
            root.select_one('div[class*="collectionv2" i]'),
            root.select_one('section[class*="collection" i]'),
            root
        ]
        for container in containers:
            if not container:
                continue
            cards = container.select('article, li, div')
            for node in cards:
                a = node.select_one('a[href*="/zh/research-and-insights" i]') or node.select_one('a[href]')
                if not a or not a.get('href'):
                    continue
                href = url_join(base, a['href'])
                if href in seen:
                    continue
                title_node = (
                    node.select_one('h3, h2') or a.select_one('h3, h2') or node.select_one('[class*="title" i]') or a
                )
                title = title_node.get_text(strip=True) if title_node is not None else ''
                if not title:
                    continue
                date_node = node.select_one('time[datetime]') or node.select_one('time') or node.select_one('[class*="date" i]')
                date_text = ''
                if date_node is not None:
                    date_text = _parse_date_to_iso(date_node.get('datetime', '') or date_node.get_text(strip=True))
                items.append((href, title, date_text))
                seen.add(href)
                if len(items) >= max_items:
                    break
            if len(items) >= max_items:
                break
        return items

    try:
        chrome_page_render.goto_url(url=base_url)
    except Exception:
        pass
    _try_accept_cookies()
    try:
        chrome_page_render.wait_for_selectors(
            wait_type='appear',
            selector_types_rules=url_info.get('RulesAwaitingSelectors(Types,Rules)', [('css', 'main')]),
            waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
            print_error_log_to_console=False
        )
    except Exception:
        pass

    results = []
    max_wait = max(6, int(url_info.get('WaitingTimeLimitInSeconds', 10)) * 2)
    for _ in range(max_wait):
        try:
            html = chrome_page_render.get_page_source()
        except Exception:
            html = ''
        results = _extract_items(html, base_url)
        if results:
            break
        sleep(0.5)

    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=base_url):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in results[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
    return None

def handler17_bcg_publications(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    波士顿咨询（BCG）（洞察/Publications）列表页处理器

    行为：
    - 打开 publications 列表页，等待主容器出现；
    - 若存在 Cookie/同意弹窗，尝试接受；
    - 点击“View more”按钮以加载更多，直到收集到 MaxItems 条或再无增长；
    - 抽取卡片的链接、标题、日期（若有），以统一结构渲染。

    选择器策略：
    - 列表容器：div.items.js-result-container
    - 卡片标题/链接：div.Promo-title a.Link[href]
    - 日期：卡片内 time[datetime] 或 class 包含 date 的节点文本
    """
    urls = url_info.get('URLs', []) or []
    if not urls:
        return None

    base_url = urls[0]
    max_items = int(url_info.get('MaxItems', 28))

    def _try_accept_cookies():
        candidates = [
            ('css', 'button#onetrust-accept-btn-handler'),
            ('css', 'button[aria-label*="accept" i]'),
            ('xpath', "//button[contains(., 'Accept') or contains(., '同意') or contains(., '接受')]"),
        ]
        for (typ, sel) in candidates:
            try:
                is_timeout = chrome_page_render.click_on_html_element(
                    click_element_selector_type=typ,
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if is_timeout is False:
                    break
            except Exception:
                continue

    def _parse_date_to_iso(s: str) -> str:
        try:
            if not isinstance(s, str):
                return ''
            s = s.strip()
            if not s:
                return ''
            m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            pass
        return ''

    def _extract_items(html: str, base: str):
        soup = BeautifulSoup(html, 'html.parser')
        root = soup.select_one('div.items.js-result-container') or soup.select_one('main') or soup
        items = []
        seen = set()
        cards = []
        if root:
            cards = root.select('div.Promo-title, div.promo-title, div[class*="Promo-title" i]')
        for node in cards:
            a = node.select_one('a.Link[href]') or node.select_one('a[href]')
            if not a or not a.get('href'):
                continue
            href = url_join(base, a['href'])
            if href in seen:
                continue
            title = a.get_text(strip=True) or (node.get_text(strip=True) if node else '')
            if not title:
                continue
            # 查找日期
            container = node
            date_node = container.select_one('time[datetime]') if container else None
            if not date_node:
                # 往上找一层卡片容器
                cap = node.find_parent('div') or node
                date_node = cap.select_one('time[datetime]') if cap else None
            date_text = ''
            if date_node is not None:
                date_text = _parse_date_to_iso(date_node.get('datetime', '') or date_node.get_text(strip=True))
            items.append((href, title, date_text))
            seen.add(href)
            if len(items) >= max_items:
                break
        return items

    def _exec_js(script: str):
        try:
            browser = getattr(chrome_page_render, f"_ChromePageRender__browser", None)
            if browser is not None:
                return browser.execute_script(script)
        except Exception:
            pass
        return None

    def _try_click_view_more() -> bool:
        candidates = [
            ('css', 'button.js-result-show-more'),
            ('css', 'button[data-module-type*="load" i]'),
            ('css', 'button[class*="show" i][class*="more" i]'),
            ('css', 'button[class*="view" i][class*="more" i]'),
            ('xpath', "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'view more') or contains(., 'Load more') or contains(., '更多')]")
        ]
        for (typ, sel) in candidates:
            try:
                # 滚动到底部以确保按钮可见
                _exec_js('window.scrollTo(0, document.body.scrollHeight);')
                t = chrome_page_render.click_on_html_element(
                    click_element_selector_type=typ,
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(6, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if t is False:
                    return True
            except Exception:
                continue
        # JS 直接点击首个包含文案的按钮（兜底）
        try:
            _exec_js("var btn=[...document.querySelectorAll('button')].find(b=>/view\s*more|load\s*more|更多/i.test((b.innerText||'').trim())); if(btn){btn.click();}")
            return True
        except Exception:
            pass
        return False

    # 打开列表页
    try:
        chrome_page_render.goto_url(url=base_url)
    except Exception:
        pass
    _try_accept_cookies()
    try:
        chrome_page_render.wait_for_selectors(
            wait_type='appear',
            selector_types_rules=url_info.get('RulesAwaitingSelectors(Types,Rules)', [('css', 'div.items.js-result-container')]),
            waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
            print_error_log_to_console=False
        )
    except Exception:
        pass

    # 初始解析
    results = []
    max_wait = max(6, int(url_info.get('WaitingTimeLimitInSeconds', 10)) * 2)
    for _ in range(max_wait):
        try:
            html = chrome_page_render.get_page_source()
        except Exception:
            html = ''
        results = _extract_items(html, base_url)
        if results:
            break
        sleep(0.5)

    # 点击 View more 直到足量
    stagnation_rounds = 0
    last_len = len(results)
    while len(results) < max_items and stagnation_rounds < 4:
        clicked = _try_click_view_more()
        if not clicked:
            break
        # 等待新卡片出现
        for _ in range(24):
            sleep(0.5)
            try:
                html = chrome_page_render.get_page_source()
            except Exception:
                html = ''
            cur = _extract_items(html, base_url)
            if len(cur) > len(results):
                results = cur
                break
        if len(results) == last_len:
            stagnation_rounds += 1
        else:
            stagnation_rounds = 0
        last_len = len(results)
        # 轻微滚动一次，触发惰性渲染
        _exec_js('window.scrollTo(0, document.body.scrollHeight);')

    # 渲染到聚合页
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=base_url):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in results[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
    return None


def handler18_bain_news(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    贝恩咨询（Bain & Company）中文站栏目列表抓取（最多 N 条）。

    页面结构特征：
    - 列表页面：每条为 div.card，链接在 card 内的 a[href]（指向 news_info.php?id=...），
      标题在 .card-body .card-title，日期在 .card-footer（形如 YYYY-MM-DD）。
    - 翻页：通过 &page=2, 3... 翻页；通常首页已足够，此处按需翻页直至凑满 MaxItems。

    渲染：输出到主页的一个 page-board 板块，内部若干 page-board-item，结构与既有站点一致。
    """
    base_urls = url_info.get('URLs', []) or []
    if not base_urls:
        return None

    max_items = int(url_info.get('MaxItems', 10))

    def _extract_items(html: str, base_url: str):
        items = []
        seen = set()
        if not html:
            return items
        soup = BeautifulSoup(html, 'html.parser')
        # 以详情页链接作为锚点，向上找卡片容器，抽取标题与日期
        for a in soup.select('a[href*="news_info.php?id="]'):
            href = a.get('href') or ''
            if not href:
                continue
            full = url_join(base_url, href)
            if full in seen:
                continue
            card = a
            # 就近查找 div.card 容器
            try:
                card = a.find_parent('div', class_='card') or a
            except Exception:
                card = a
            # 标题
            tnode = (card.select_one('.card-body .card-title') or
                     card.select_one('.card-title') or
                     card.select_one('img[alt]') or a)
            title = ''
            try:
                if tnode:
                    title = (tnode.get_text(strip=True) or (tnode.get('alt') or '').strip())
            except Exception:
                title = ''
            if not title:
                continue
            # 日期
            date_text = ''
            try:
                dnode = card.select_one('.card-footer')
                if dnode:
                    date_text = dnode.get_text(strip=True)
            except Exception:
                date_text = ''
            items.append((full, title, date_text))
            seen.add(full)
            if len(items) >= max_items:
                break
        return items

    # 逐个 base_url 处理（通常每个栏目仅一个 URL）
    aggregated = []
    for base in base_urls:
        # 首页
        html = None
        try:
            is_timeout = chrome_page_render.goto_url_waiting_for_selectors(
                url=base,
                selector_types_rules=url_info.get('RulesAwaitingSelectors(Types,Rules)', [('css', 'div.card')]),
                waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
                print_error_log_to_console=False
            )
            # 即使等待超时，也尽力读取页面源代码进行解析（以防选择器不稳定）
            html = chrome_page_render.get_page_source()
        except Exception:
            html = None
        aggregated.extend(_extract_items(html or '', base))
        if len(aggregated) >= max_items:
            break

        # 若不足，尝试翻页（page=2 开始）直至凑满或停滞
        page_no = 2
        stagnate = 0
        while len(aggregated) < max_items and stagnate < 2 and page_no <= 5:
            if '?' in base:
                next_url = f"{base}&page={page_no}"
            else:
                next_url = f"{base}?page={page_no}"
            html2 = None
            before = len(aggregated)
            try:
                is_timeout = chrome_page_render.goto_url_waiting_for_selectors(
                    url=next_url,
                    selector_types_rules=url_info.get('RulesAwaitingSelectors(Types,Rules)', [('css', 'div.card')]),
                    waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
                    print_error_log_to_console=False
                )
                # 读取页面源代码（无论 wait 是否超时）
                html2 = chrome_page_render.get_page_source()
            except Exception:
                html2 = None
            cur = _extract_items(html2 or '', base)
            # 去重合并
            if cur:
                exist = set(x[0] for x in aggregated)
                for it in cur:
                    if it[0] not in exist:
                        aggregated.append(it)
                        exist.add(it[0])
            if len(aggregated) == before:
                stagnate += 1
            else:
                stagnate = 0
            page_no += 1

    # 渲染
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info.get('LogoPath', './Logos/handler18_BAIN_zh.png'), alt='Missing Logo')
            with HTMLTags.a(href=base_urls[0]):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in aggregated[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
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


def handler19_ey_hub(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    EY China hub/list handler

    - 动态渲染列表页（technical/... hubs），抓取前 N 条
    - 字段：link/title/date(若有)，渲染成统一的 page-board-item
    - 选择器尽量宽松以适配站点改版；同时避免导航/页脚
    """
    urls = url_info.get('URLs', []) or []
    if not urls:
        return None

    max_items = int(url_info.get('MaxItems', 10))

    def _try_accept_cookies():
        candidates = [
            ('css', 'button#onetrust-accept-btn-handler'),
            ('css', 'button[aria-label*="accept" i]'),
            ('css', 'button[aria-label*="agree" i]'),
            ('css', 'button[class*="cookie" i][class*="accept" i]'),
        ]
        for (typ, sel) in candidates:
            try:
                t = chrome_page_render.click_on_html_element(
                    click_element_selector_type=typ,
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if t is False:
                    break
            except Exception:
                continue

    def _parse_date_to_iso(s: str) -> str:
        try:
            if not isinstance(s, str):
                return ''
            s = (s or '').strip()
            if not s:
                return ''
            m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            pass
        return ''

    def _extract_items(html: str, base: str):
        soup = BeautifulSoup(html or '', 'html.parser')
        root = soup.select_one('main') or soup
        items = []
        seen = set()

        # 针对不同栏目限定子路径，避免误抓首页导航
        base_l = (base or '').lower()
        required_subpaths = []
        if 'china-tax-alerts' in base_l:
            required_subpaths = [
                '/technical/china-tax-alerts/',
                '/zh_cn/technical/china-tax-alerts/',
                '/content/ey-unified-site/ey-com/local/cn/zh_cn/technical/china-tax-alerts/'
            ]
        elif 'china-accounting-alerts' in base_l:
            required_subpaths = [
                '/technical/assurance/china-accounting-alerts/',
                '/zh_cn/technical/assurance/china-accounting-alerts/',
                '/content/ey-unified-site/ey-com/local/cn/zh_cn/technical/assurance/china-accounting-alerts/'
            ]

        def _is_detail_link(href: str) -> bool:
            try:
                if not href:
                    return False
                hl = href.lower()
                # 排除锚点/协议链接
                if hl.startswith('javascript:') or hl.startswith('mailto:') or hl.endswith('#'):
                    return False
                # 仅保留本站
                if ('ey.com' not in hl) and (not hl.startswith('/')) and ('content/ey-unified-site' not in hl):
                    return False
                # 必须包含栏目子路径且不是栏目根本身
                for sub in required_subpaths:
                    if sub in hl and not hl.rstrip('/').endswith(sub.rstrip('/')):
                        return True
                return False
            except Exception:
                return False

        card_nodes = []
        for sel in [
            'main article',
            'main ul li',
            'main section article',
            'main [class*="card" i]',
            'main [class*="list" i] li'
        ]:
            card_nodes = root.select(sel)
            if card_nodes:
                break
        if not card_nodes:
            try:
                card_nodes = [n for n in root.select('div, section, article, li') if n.select_one('a[href]')]
            except Exception:
                card_nodes = []

        for node in card_nodes:
            a = (
                node.select_one('a[href^="/zh_cn/" i]') or
                node.select_one('a[href*="/zh_cn/" i]') or
                node.select_one('a[href^="/" i]') or
                node.select_one('a[href^="https://www.ey.com" i]') or
                node.select_one('a[href]')
            )
            if not a or not a.get('href'):
                continue
            href = url_join(base, a.get('href'))
            if not _is_detail_link(href):
                continue
            if not href or href in seen:
                continue
            try:
                if a.find_parent('nav') is not None:
                    continue
            except Exception:
                pass

            title_node = node.select_one('h3, h2') or a
            title = title_node.get_text(strip=True) if title_node is not None else ''
            if not title:
                continue

            date_node = node.select_one('time[datetime]') or node.select_one('time') or node.select_one('[class*="date" i]')
            date_text = ''
            if date_node is not None:
                date_text = _parse_date_to_iso(date_node.get('datetime', '') or date_node.get_text(strip=True))

            items.append((href, title, date_text))
            seen.add(href)
            if len(items) >= max_items:
                break

        if not items:
            for a in root.select('a[href]'):
                try:
                    if a.find_parent('nav') is not None:
                        continue
                except Exception:
                    pass
                href = url_join(base, a.get('href', ''))
                if not _is_detail_link(href):
                    continue
                if not href or href in seen:
                    continue
                title = a.get_text(strip=True) or a.get('aria-label', '').strip()
                if not title:
                    continue
                items.append((href, title, ''))
                seen.add(href)
                if len(items) >= max_items:
                    break
        return items

    results = []
    base_url = urls[0]
    try:
        chrome_page_render.goto_url(url=base_url)
    except Exception:
        pass
    _try_accept_cookies()
    try:
        chrome_page_render.wait_for_selectors(
            wait_type='appear',
            selector_types_rules=url_info.get('RulesAwaitingSelectors(Types,Rules)', [('css', 'main')]),
            waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
            print_error_log_to_console=False
        )
    except Exception:
        pass

    max_wait = max(6, int(url_info.get('WaitingTimeLimitInSeconds', 10)) * 2)
    for _ in range(max_wait):
        try:
            html = chrome_page_render.get_page_source()
        except Exception:
            html = ''
        results = _extract_items(html, base_url)
        if results:
            break
        sleep(0.5)

    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=base_url):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in results[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
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


def handler20_iiss_online_analysis(
        chrome_page_render: ChromePageRender,
        document: HTMLDocument,
        url_name: str,
        url_info: dict
) -> None:
    """
    IISS Online Analysis list handler

    - Opens the main list page and parses anchor cards under
      `div.filter_results.feature_list a.feature[href]`.
    - Uses the native pagination "next" control that navigates to page 2, 3, ...
      We click the `a.pagination__next` and wait for page content to update.
    - Collects up to MaxItems (default 40), which is 4 pages x 10 items each as requested.
    - Renders each item as page-board-item: <a><h3>title</h3><span>date?></span>
      Date may be empty when not present in the list; detail page parser will fill real publish date.
    """
    urls = url_info.get('URLs', []) or []
    if not urls:
        return None
    base_url = urls[0]
    max_items = int(url_info.get('MaxItems', 40))
    max_pages = int(url_info.get('MaxPages', max(1, (max_items + 9) // 10)))

    # Build a local undetected chrome instance for robustness (403 avoidance, consent banners)
    local_options = ChromeOptions()
    try:
        local_options.page_load_strategy = 'none'
    except Exception:
        pass
    local_options.add_argument('--disable-blink-features=AutomationControlled')
    local_options.add_argument('--ignore-certificate-errors')
    local_options.add_argument('--ignore-ssl-errors')
    local_options.add_argument('--allow-running-insecure-content')
    local_options.add_argument('--disable-web-security')
    local_options.add_argument('--disable-site-isolation-trials')
    local_options.add_argument('--test-type')
    local_options.set_capability('acceptInsecureCerts', True)
    local_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )

    _local_cpr = ChromePageRender(
        chrome_driver_filepath=__chrome_driver_path,
        options=local_options,
        use_undetected_chromedriver=True
    )

    def _try_accept_cookies():
        # Best-effort cookie/consent dismissal
        for sel in [
            'button#onetrust-accept-btn-handler',
            'button[aria-label*="accept" i]',
            'button[aria-label*="agree" i]',
            'button[class*="cookie" i][class*="accept" i]',
        ]:
            try:
                is_timeout = _local_cpr.click_on_html_element(
                    click_element_selector_type='css',
                    click_element_selector_rule=sel,
                    use_javascript=True,
                    max_trials_for_unstable_page=2,
                    click_waiting_timeout_in_seconds=min(5, url_info.get('WaitingTimeLimitInSeconds', 10)),
                    print_error_log_to_console=False
                )
                if is_timeout is False:
                    break
            except Exception:
                continue

    def _extract_items(html: str, base: str):
        soup = BeautifulSoup(html or '', 'html.parser')
        root = soup.select_one('div.filter_results.feature_list') or soup
        items = []
        seen = set()
        anchors = root.select('a.feature[href]')
        if not anchors:
            # Fallback: any anchor pointing to /online-analysis/
            anchors = root.select('a[href*="/online-analysis/" i]')
        for a in anchors:
            href = a.get('href')
            if not href:
                continue
            full = url_join(base, href)
            if full in seen:
                continue
            title = a.get_text(strip=True) or ''
            if not title:
                # Try inner heading
                h = a.select_one('h2, h3')
                if h and h.get_text(strip=True):
                    title = h.get_text(strip=True)
            # Optional date (not always present in list)
            date_text = ''
            t = a.select_one('time[datetime]')
            if t is None:
                # Sometimes placed near the anchor
                t = a.find_next('time')
            if t is not None:
                raw = t.get('datetime') or t.get_text(strip=True)
                try:
                    m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', raw or '')
                    if m:
                        date_text = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                except Exception:
                    date_text = ''
            if title:
                items.append((full, title, date_text))
                seen.add(full)
        return items

    def _goto(url: str) -> bool:
        is_timeout = _local_cpr.goto_url_waiting_for_selectors(
            url=url,
            selector_types_rules=[
                ('css', 'div.filter_results.feature_list'),
            ],
            waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
            print_error_log_to_console=True
        )
        if is_timeout:
            return False
        _try_accept_cookies()
        return True

    def _current_page_num(html: str) -> int:
        try:
            soup = BeautifulSoup(html or '', 'html.parser')
            s = soup.select_one('div.pagination span.pagination__title')
            if s and s.get_text(strip=True):
                m = re.search(r'(\d+)', s.get_text(strip=True))
                if m:
                    return int(m.group(1))
        except Exception:
            pass
        return 0

    def _try_click_next(curr_html: str) -> bool:
        try:
            pg = _current_page_num(curr_html)
        except Exception:
            pg = 0
        try:
            # Click next; if disabled or missing, stop
            soup = BeautifulSoup(curr_html or '', 'html.parser')
            nxt = soup.select_one('a.pagination__next')
            if nxt is None:
                return False
            cls = (nxt.get('class') or [])
            if any('disabled' == c or 'is-disabled' == c for c in cls):
                return False
            is_timeout = _local_cpr.click_on_html_element(
                click_element_selector_type='css',
                click_element_selector_rule='a.pagination__next',
                use_javascript=True,
                max_trials_for_unstable_page=2,
                click_waiting_timeout_in_seconds=min(6, url_info.get('WaitingTimeLimitInSeconds', 10)),
                print_error_log_to_console=False
            )
            if is_timeout:
                return False
            # Wait for page number to change or list to refresh
            for _ in range(24):  # ~12s
                sleep(0.5)
                new_html = _local_cpr.get_page_source()
                new_pg = _current_page_num(new_html)
                if (pg and new_pg and new_pg != pg) or (new_html and new_html != curr_html):
                    return True
            return False
        except Exception:
            return False

    # 1) Open base page
    if not _goto(base_url):
        return None

    # 2) Collect across pages until MaxItems or MaxPages
    results = []
    visited_pages = 0
    while visited_pages < max_pages and len(results) < max_items:
        html = _local_cpr.get_page_source()
        items = _extract_items(html, base_url)
        if items:
            # Deduplicate while preserving order
            seen = set(u for (u, _, _) in results)
            for it in items:
                if it[0] not in seen:
                    results.append(it)
                    seen.add(it[0])
        visited_pages += 1
        if visited_pages >= max_pages or len(results) >= max_items:
            break
        # Move next page
        if not _try_click_next(html):
            break

    # 3) Render into the document
    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info['LogoPath'], alt='Missing Logo')
            with HTMLTags.a(href=base_url):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in results[:max_items]:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
    return None


def handler22_deloitte_monthly(chrome_page_render: ChromePageRender, document: HTMLDocument, url_name: str, url_info: dict) -> None:
    """
    德勤中国（Deloitte）《月度经济概览》栏目列表抓取（仅取前 MaxItems 条，默认 5 条）

    页面为 AEM 站点，结构会随组件变化，但“期号”链接稳定为
    /cn/zh/services/consulting/perspectives/deloitte-research-issue-XX.html。

    抽取策略：
    - 加载栏目页，尽力关闭 Cookie/隐私弹窗（OneTrust）。
    - 在页面内查找所有 a[href*="deloitte-research-issue-"] 的链接；
      对于“了解更多”等无标题的链接，尝试就近的 h3/h4 文本作为标题；
      如仍为空，则用“第{issue}期”占位。
    - 日期：优先在同一文本块内解析中文日期（YYYY年M月D日）；若未找到则置空，
      详细发布日期由内页解析时弥补。
    - 去重：按 issue 序号去重，并按序号倒序取前 MaxItems。

    渲染：与既有板块一致，生成 .page-board/.page-board-item 结构，
    每条包含 <a><h3>标题</h3><span>日期(可空)</span>。
    """
    urls = url_info.get('URLs', []) or []
    if not urls:
        return None

    base_url = urls[0]
    max_items = int(url_info.get('MaxItems', 5))

    # 1) 打开栏目页并等待主要内容
    try:
        chrome_page_render.goto_url(url=base_url)
    except Exception:
        pass

    # 关 Cookie 弹窗（若存在）
    for sel in [
        ('css', 'button#onetrust-accept-btn-handler'),
        ('css', 'button[aria-label*="accept" i]'),
        ('css', 'button[aria-label*="同意" i]'),
        ('xpath', "//button[contains(., 'Accept') or contains(., '同意')]"),
    ]:
        try:
            chrome_page_render.click_on_html_element(
                click_element_selector_type=sel[0],
                click_element_selector_rule=sel[1],
                use_javascript=True,
                max_trials_for_unstable_page=1,
                click_waiting_timeout_in_seconds=min(6, url_info.get('WaitingTimeLimitInSeconds', 10)),
                print_error_log_to_console=False,
            )
        except Exception:
            continue

    try:
        chrome_page_render.wait_for_selectors(
            wait_type='appear',
            selector_types_rules=url_info.get('RulesAwaitingSelectors(Types,Rules)', [
                ('css', 'main'),
                ('css', 'a[href*="deloitte-research-issue-"]'),
                ('css', 'div.cmp-text'),
            ]),
            waiting_timeout_in_seconds=url_info.get('WaitingTimeLimitInSeconds', 10),
            print_error_log_to_console=False,
        )
    except Exception:
        pass

    # 2) 解析条目
    try:
        html = chrome_page_render.get_page_source()
    except Exception:
        html = ''

    soup = BeautifulSoup(html or '', 'html.parser')

    def _parse_cn_date_to_iso(s: str) -> str:
        try:
            if not isinstance(s, str):
                return ''
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
            if m:
                return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            pass
        return ''

    # 收集 issue -> (href, title, date)
    issue_map = {}
    seen_hrefs = set()
    anchors = soup.select('a[href*="deloitte-research-issue-"]')
    for a in anchors:
        href = a.get('href') or ''
        if not href:
            continue
        full = url_join(base_url, href)
        if full in seen_hrefs:
            continue
        seen_hrefs.add(full)

        m = re.search(r'issue[-_/]?(\d+)', href)
        issue_no = int(m.group(1)) if m else -1

        # 标题：优先同块中 h3/h4，其次 a 文本，最后占位
        title = (a.get_text(strip=True) or '').strip()
        if (not title) or ('了解更多' in title) or (len(title) <= 2):
            block = None
            try:
                for _ in range(3):
                    block = (block or a)
                    block = block.find_parent('div')
                    if block is None:
                        break
                    classes = ' '.join(block.get('class') or [])
                    if ('cmp-text' in classes) or ('text-v2' in classes):
                        break
            except Exception:
                block = a.find_parent('div') or a
            ctx_title = ''
            if block is not None:
                h = block.select_one('h4, h3')
                if h and h.get_text(strip=True):
                    ctx_title = h.get_text(strip=True)
            title = ctx_title or title
        if (not title) and issue_no > 0:
            title = f"第{issue_no}期"

        # 日期：就近文本内解析中文日期
        date_text = ''
        block = a.find_parent('div') or a
        try:
            blk_txt = block.get_text(' ', strip=True)
            date_text = _parse_cn_date_to_iso(blk_txt)
        except Exception:
            date_text = ''

        # 写入：按 issue 去重，优先保留标题更长/带日期的版本
        if issue_no not in issue_map:
            issue_map[issue_no] = (full, title, date_text)
        else:
            old = issue_map[issue_no]
            better = old
            if (len(title) > len(old[1])) or (not old[2] and date_text):
                better = (full, title, date_text)
            issue_map[issue_no] = better

    # 3) 排序与渲染
    entries = []
    for k, v in issue_map.items():
        if k > 0:
            entries.append((k, v))
    entries.sort(key=lambda x: x[0], reverse=True)
    items = [v for (_, v) in entries][:max_items]

    with document.body:
        with HTMLTags.div(cls='page-board'):
            HTMLTags.img(cls='site-logo', src=url_info.get('LogoPath', './Logos/handler22_deloitte.png'), alt='Missing Logo')
            with HTMLTags.a(href=base_url):
                HTMLTags.h2(url_name)
            for (a_href, h3_text, span_text) in items:
                with HTMLTags.div(cls='page-board-item'):
                    with HTMLTags.a(href=a_href):
                        HTMLTags.h3(h3_text)
                        HTMLTags.span(span_text or '')
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
    '北京大学国家发展研究院（观点）': {
        'URLs': [
            'https://nsd.pku.edu.cn/sylm/gd/index.htm',
            'https://nsd.pku.edu.cn/sylm/gd/index1.htm',
            'https://nsd.pku.edu.cn/sylm/gd/index2.htm',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.wrapper'),
            ('css', 'div.container'),
            ('css', 'ul.list'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler9.png',
        'HTMLContentHandler': handler10_nsd
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

# --------------------------- RAND Corporation 新增站点配置（封装为独立分组） ---------------------------
RAND_URLData = {
    '兰德公司(RAND Corporation)（主题-儿童、家庭与社区）': {
        'URLs': [
            'https://www.rand.org/topics/children-families-and-communities.html?start=0#topicLandingPageList-1969427548-form',
            'https://www.rand.org/topics/children-families-and-communities.html?start=12#topicLandingPageList-1969427548-form',
            'https://www.rand.org/topics/children-families-and-communities.html?start=24#topicLandingPageList-1969427548-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-网络与数据科学）': {
        'URLs': [
            'https://www.rand.org/topics/cyber-and-data-sciences.html?start=0#topicLandingPageList-435430008-form',
            'https://www.rand.org/topics/cyber-and-data-sciences.html?start=12#topicLandingPageList-435430008-form',
            'https://www.rand.org/topics/cyber-and-data-sciences.html?start=24#topicLandingPageList-435430008-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-教育与读写素养）': {
        'URLs': [
            'https://www.rand.org/topics/education-and-literacy.html?start=0#topicLandingPageList-1672457942-form',
            'https://www.rand.org/topics/education-and-literacy.html?start=12#topicLandingPageList-1672457942-form',
            'https://www.rand.org/topics/education-and-literacy.html?start=24#topicLandingPageList-1672457942-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-能源与环境）': {
        'URLs': [
            'https://www.rand.org/topics/energy-and-environment.html?start=0#topicLandingPageList-1130360820-form',
            'https://www.rand.org/topics/energy-and-environment.html?start=12#topicLandingPageList-1130360820-form',
            'https://www.rand.org/topics/energy-and-environment.html?start=24#topicLandingPageList-1130360820-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-健康、医疗与老龄化）': {
        'URLs': [
            'https://www.rand.org/topics/health-health-care-and-aging.html?start=0#topicLandingPageList-2050784518-form',
            'https://www.rand.org/topics/health-health-care-and-aging.html?start=12#topicLandingPageList-2050784518-form',
            'https://www.rand.org/topics/health-health-care-and-aging.html?start=24#topicLandingPageList-2050784518-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-国土安全与公共安全）': {
        'URLs': [
            'https://www.rand.org/topics/homeland-security-and-public-safety.html?start=0#topicLandingPageList-1814846118-form',
            'https://www.rand.org/topics/homeland-security-and-public-safety.html?start=12#topicLandingPageList-1814846118-form',
            'https://www.rand.org/topics/homeland-security-and-public-safety.html?start=24#topicLandingPageList-1814846118-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-基础设施与交通运输）': {
        'URLs': [
            'https://www.rand.org/topics/infrastructure-and-transportation.html?start=0#topicLandingPageList-876753564-form',
            'https://www.rand.org/topics/infrastructure-and-transportation.html?start=12#topicLandingPageList-876753564-form',
            'https://www.rand.org/topics/infrastructure-and-transportation.html?start=24#topicLandingPageList-876753564-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-国际事务）': {
        'URLs': [
            'https://www.rand.org/topics/international-affairs.html?start=0#topicLandingPageList-728393285-form',
            'https://www.rand.org/topics/international-affairs.html?start=12#topicLandingPageList-728393285-form',
            'https://www.rand.org/topics/international-affairs.html?start=24#topicLandingPageList-728393285-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-法律与商业）': {
        'URLs': [
            'https://www.rand.org/topics/law-and-business.html?start=0#topicLandingPageList-1200689853-form',
            'https://www.rand.org/topics/law-and-business.html?start=12#topicLandingPageList-1200689853-form',
            'https://www.rand.org/topics/law-and-business.html?start=24#topicLandingPageList-1200689853-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-国家安全）': {
        'URLs': [
            'https://www.rand.org/topics/national-security.html?start=0#topicLandingPageList-609677611-form',
            'https://www.rand.org/topics/national-security.html?start=12#topicLandingPageList-609677611-form',
            'https://www.rand.org/topics/national-security.html?start=24#topicLandingPageList-609677611-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-科学与技术）': {
        'URLs': [
            'https://www.rand.org/topics/science-and-technology.html?start=0#topicLandingPageList-2049255161-form',
            'https://www.rand.org/topics/science-and-technology.html?start=12#topicLandingPageList-2049255161-form',
            'https://www.rand.org/topics/science-and-technology.html?start=24#topicLandingPageList-2049255161-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-社会公平）': {
        'URLs': [
            'https://www.rand.org/topics/social-equity.html?start=0#topicLandingPageList-1898844437-form',
            'https://www.rand.org/topics/social-equity.html?start=12#topicLandingPageList-1898844437-form',
            'https://www.rand.org/topics/social-equity.html?start=24#topicLandingPageList-1898844437-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
    '兰德公司(RAND Corporation)（主题-劳动者与工作场所）': {
        'URLs': [
            'https://www.rand.org/topics/workers-and-the-workplace.html?start=0#topicLandingPageList-918846908-form',
            'https://www.rand.org/topics/workers-and-the-workplace.html?start=12#topicLandingPageList-918846908-form',
            'https://www.rand.org/topics/workers-and-the-workplace.html?start=24#topicLandingPageList-918846908-form',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main#page-content'),
            ('css', 'ul.teasers')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler10.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler11_rand_topics
    },
}

URLData.update(RAND_URLData)

JPM_URLData = {
    '摩根大通研究院（All Insights）': {
        'URLs': [
            'https://www.jpmorgan.com/insights#all-insights',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', '#all-insights'),
            ('css', '#all-insights .cmp-dynamic-grid-content ul.grid'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler12_JPMorgan.svg',
        'MaxItems': 30,
        'HTMLContentHandler': handler12_jpm_insights
    },
}

URLData.update(JPM_URLData)

KPMG_URLData = {
    '毕马威中国(KPMG)（洞察）': {
        'URLs': [
            'https://kpmg.com/cn/zh/home/insights.html',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'section.module-resultslisting'),
            ('css', '#resultsListingContainer'),
            ('css', 'div.resultslistContainer'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler14_KPMG_zh.png',
        'MaxItems': 40,
        'HTMLContentHandler': handler14_kpmg_insights,
    },
}

URLData.update(KPMG_URLData)

# 麦肯锡中国（洞察）
MCK_URLData = {
    '麦肯锡中国（McKinsey & Company）（洞察）': {
        'URLs': [
            'https://www.mckinsey.com.cn/insights/',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler15_McK_zh.png',
        'MaxItems': 20,
        'HTMLContentHandler': handler15_mck_insights,
    },
}

URLData.update(MCK_URLData)

# 普华永道中国（洞察）
PWC_ZH_URLData = {
    '普华永道（PwC）（洞察）': {
        'URLs': [
            'https://www.pwccn.com/zh/research-and-insights.html',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main'),
            ('css', 'article a[href*="/zh/research-and-insights" i]'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler16_pwc.png',
        'MaxItems': 12,
        'HTMLContentHandler': handler16_pwc_zh_insights,
    },
}

URLData.update(PWC_ZH_URLData)

# 波士顿咨询（BCG）（洞察/Publications）
BCG_URLData = {
    '波士顿咨询(BCG)（洞察）': {
        'URLs': [
            'https://www.bcg.com/publications',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.items.js-result-container'),
            ('css', 'div.Promo-title a.Link')
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler17_BCG.png',
        'MaxItems': 28,
        'HTMLContentHandler': handler17_bcg_publications,
    },
}

URLData.update(BCG_URLData)


# 贝恩咨询（Bain & Company）观点
BAIN_URLData = {
    '贝恩咨询(Bain & Company)观点-聚焦中国': {
        'URLs': [
            'https://www.bain.cn/news.php?id=15',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.card'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler18_BAIN_zh.png',
        'MaxItems': 10,
        'HTMLContentHandler': handler18_bain_news,
    },
    '贝恩咨询(Bain & Company)观点-全球视野': {
        'URLs': [
            'https://www.bain.cn/news.php?id=14',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.card'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler18_BAIN_zh.png',
        'MaxItems': 10,
        'HTMLContentHandler': handler18_bain_news,
    },
    '贝恩咨询(Bain & Company)观点-总裁专栏': {
        'URLs': [
            'https://www.bain.cn/news.php?id=32',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.card'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler18_BAIN_zh.png',
        'MaxItems': 10,
        'HTMLContentHandler': handler18_bain_news,
    },
    '贝恩咨询(Bain & Company)观点-署名文章': {
        'URLs': [
            'https://www.bain.cn/news.php?id=26',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.card'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler18_BAIN_zh.png',
        'MaxItems': 10,
        'HTMLContentHandler': handler18_bain_news,
    },
}

URLData.update(BAIN_URLData)


# EY China（新增两个栏目）
EY_URLData = {
    '安永中国(EY)（中国税务快讯）': {
        'URLs': [
            'https://www.ey.com/zh_cn/technical/china-tax-alerts',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler19_EY_zh.png',
        'MaxItems': 10,
        'HTMLContentHandler': handler19_ey_hub,
    },
    '安永中国(EY)（中国会计通讯）': {
        'URLs': [
            'https://www.ey.com/zh_cn/technical/assurance/china-accounting-alerts',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler19_EY_zh.png',
        'MaxItems': 10,
        'HTMLContentHandler': handler19_ey_hub,
    },
}

URLData.update(EY_URLData)

IISS_URLData = {
    '国际战略研究所(iiss)（在线分析）': {
        'URLs': [
            'https://www.iiss.org/online-analysis/',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.filter_results.feature_list'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler20_iiss.png',
        'MaxItems': 10,
        'MaxPages': 1,
        'HTMLContentHandler': handler20_iiss_online_analysis,
    },
}

URLData.update(IISS_URLData)

# --------------------------- 清华大学国情研究院（ICCS） ---------------------------
ICCS_URLData = {
    '清华大学国情研究院（世情研究）': {
        'URLs': [
            'https://www.iccs.tsinghua.edu.cn/research/155.html',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            # 等待主体容器，避免抓到公共模块
            ('css', 'div.i_main'),
            ('css', 'div.publish'),
            ('css', 'ul.noticeul'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler21_Tsinghua.png',
        'MaxItems': 6,
        'HTMLContentHandler': handler21_iccs_research,
    },
    '清华大学国情研究院（国情研究）': {
        'URLs': [
            'https://www.iccs.tsinghua.edu.cn/research/164.html',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.i_main'),
            ('css', 'div.publish'),
            ('css', 'ul.noticeul'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler21_Tsinghua.png',
        'MaxItems': 6,
        'HTMLContentHandler': handler21_iccs_research,
    },
    '清华大学国情研究院（区情研究）': {
        'URLs': [
            'https://www.iccs.tsinghua.edu.cn/research/165.html',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'div.i_main'),
            ('css', 'div.publish'),
            ('css', 'ul.noticeul'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler21_Tsinghua.png',
        'MaxItems': 6,
        'HTMLContentHandler': handler21_iccs_research,
    },
}

URLData.update(ICCS_URLData)

# --------------------------- 德勤中国（Deloitte） ---------------------------
DELOITTE_URLData = {
    '德勤中国(Deloitte)（月度经济概览）': {
        'URLs': [
            'https://www.deloitte.com/cn/zh/services/consulting/perspectives/deloitte-research-monthly-report.html',
        ],
        'RulesAwaitingSelectors(Types,Rules)': [
            ('css', 'main'),
            ('css', 'div.cmp-text'),
            ('css', 'a[href*="deloitte-research-issue-"]'),
        ],
        'WaitingTimeLimitInSeconds': 30,
        'LogoPath': './Logos/handler22_deloitte.png',
        'MaxItems': 5,
        'HTMLContentHandler': handler22_deloitte_monthly,
    },
}

URLData.update(DELOITTE_URLData)

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








