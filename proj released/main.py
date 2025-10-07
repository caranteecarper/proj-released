# from os import getcwd
from time import sleep

from datetime import datetime

# configure <current_time> instance object
current_time = datetime.now()

from ChromePageRender import (
    # something else
    Options as ChromeOptions,
    ChromePageRender
)

# configure chrome driver path
__chrome_driver_path: str = "D:\AAAAA兰州大学\人工智能\爬虫项目\proj released\proj released\chromedrivers\chromedriver-win64-v138.0.7204.92\chromedriver.exe"

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
    '国务院发展研究中心（中心动态）': {
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
    '中国宏观经济研究院（科研动态）': {
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

# ---------------------------------------------------------------------------------------------------------------------
# |                   The following code collects online data and generates a new HTML page.                          |
# ---------------------------------------------------------------------------------------------------------------------


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
    url_info['HTMLContentHandler'](
        chrome_page_render=chrome_page_render,
        document=new_document,
        url_name=url_name,
        url_info=url_info
    )

try:
    with open('./generated_html/index.html', 'w', encoding='utf-8') as html_file:
        html_file.write(new_document.render(pretty=True))  # pretty makes the HTML file human-readable
    print(f"Successfully output \"./generated_html/index.html\".")
except Exception as e:
    print(f"Failed to output \"./generated_html/index.html\". Error: {e}")
