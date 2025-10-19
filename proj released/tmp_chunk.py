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

        # 优先从常见列表结构提取
        candidate_li_nodes = []
        candidate_wrappers = [
            'div.list ul', 'div.newslist ul', 'div.article-list ul', 'div.con ul', 'div.main ul',
            'div.wp ul', 'div.container ul', 'ul.list', 'ul.listul', 'ul.newslist', 'ul.items',
        ]
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
