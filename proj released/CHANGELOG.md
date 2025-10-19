# 更新日志 (Changelog)

## 2025-10-19 (新增 复旦大学中国研究院 内页爬取)
- 内页爬取_完整版.py
  - 新增 `parse_fudan_article`，并在 `crawl_article_content` 中接入域名路由（`cifu.fudan.edu.cn`）。
  - 字段与规则：
    - `title`/`content`：优先常见正文容器（`div.wp_articlecontent` 等），不足时回退通用提取。
    - `publish_date`：优先解析“发布日期/发布时间”等字段；识别 `YYYY-MM-DD` 或 `YYYY年MM月DD日` 并标准化为 `YYYY-MM-DD`；缺失则使用列表页日期。
    - `authors`：尽力从“作者/撰文/撰稿/文/”等文本提取作者姓名（可检测到则写作者姓名）。
    - `thinkank_name`：统一填写为“复旦大学中国研究院”。
    - `attachments`：优先返回文档（pdf/doc/xls/ppt 等）；若无文档且存在音频/视频则返回其 URL；当文档与音/视频并存时仅保留文档 URL。
  - 保持既有输出 JSON 结构与其它设置不变，不新增其他文件。

## 2025-10-19 (新增 德勤中国 月度经济概览)
- main.py
  - 新增 `handler22_deloitte_monthly`，抓取“德勤中国（Deloitte）—月度经济概览”栏目，按期号链接抽取并渲染 `.page-board-item`（标题+日期）。
  - 新增 `DELOITTE_URLData`，标题为“德勤中国(Deloitte)（月度经济概览）”，Logo `./Logos/handler22_deloitte.png`，默认取前 5 条。
- 内页爬取_完整版.py
  - 新增 `parse_deloitte_article` 并在 `crawl_article_content` 中接入域名 `deloitte.com`。
  - 字段与规则：authors 能检测到则写作者姓名；`thinkank_name` 固定“德勤中国（Deloitte）”；附件优先文档（pdf/doc/xls/ppt 等），若无文档而有音/视频则返回其 URL；若文档与音/视频并存仅保留文档 URL。

## 2025-10-17 (新增 清华大学国情研究院)
- main.py
  - 新增 `handler21_iccs_research`，用于清华大学国情研究院网站研究栏目列表页解析，抽取链接/标题/日期并渲染为 `.page-board-item`。
  - 在 `URLData` 末尾新增 3 个分组：
    - 清华大学国情研究院（世情研究）：https://www.iccs.tsinghua.edu.cn/research/155.html
    - 清华大学国情研究院（国情研究）：https://www.iccs.tsinghua.edu.cn/research/164.html
    - 清华大学国情研究院（区情研究）：https://www.iccs.tsinghua.edu.cn/research/165.html
    每组 `MaxItems=6`，`LogoPath=./Logos/handler21_Tsinghua.png`，标题与 Logo 已确认。
- 内页爬取.py（将新增 iccs 详情页解析函数与域名分发分支）
  - parse_iccs_article：
    - 标题：h1/og:title/title 兜底；
    - 正文：常见正文容器优先，回退通用提取；
    - 日期：time/meta/正文文本中的 YYYY-MM-DD/年-月-日 提取为 YYYY-MM-DD；
    - 作者：可检测到“作者/撰文/撰稿”等字段则写作者姓名；
    - 附件：优先文档（pdf/doc/xls/ppt 等），若仅有音/视频则返回其 URL；并存时仅保留文档；
    - thinkank_name：统一为“清华大学国情研究院”。
  - 在 `crawl_article_content` 中接入 `iccs.tsinghua.edu.cn` 分支，使用 requests 抓取并路由到 `parse_iccs_article`。
- 保持其它设置与输出格式不变；仅修改上述三个文件，无新增其他文件。

## 2025-10-15 (追加 — EY China)
- 新增：安永中国（EY）两栏目（各取前 10 条）：
  - 安永中国(EY)（中国税务快讯）：https://www.ey.com/zh_cn/technical/china-tax-alerts
  - 安永中国(EY)（中国会计通讯）：https://www.ey.com/zh_cn/technical/assurance/china-accounting-alerts
- main.py：
  - 新增 `handler19_ey_hub`（动态渲染 hub 列表，抽取链接/标题/日期，统一渲染为 page-board-item）。
  - 在 URLData 末尾加入上述两项，`MaxItems=10`，`LogoPath=./Logos/handler19_EY_zh.png`，标题按“安永中国(EY)（…）”。
- 内页爬取_完整版.py：
  - 新增 `parse_ey_article` 并接入域名路由（ey.com）。
  - 字段对齐既有格式：title/url/publish_date/authors/thinkank_name/summary/content/attachments。
  - authors：可检测到则写入作者姓名；`thinkank_name` 统一为“安永中国（EY）”。
  - 附件：优先文档（pdf/doc/xls/ppt 等）；若仅有音频/视频则返回其 URL；并存时仅保留文档。
- 未新增其他文件，沿用既有流程与设置。

## 2025-10-15 (追加)
- 新增：贝恩咨询（Bain & Company）（中文观点栏目）
  - main.py：新增 `handler18_bain_news`，抓取四个栏目，每栏最多 10 条：
    - 聚焦中国：https://www.bain.cn/news.php?id=15
    - 全球视野：https://www.bain.cn/news.php?id=14
    - 总裁专栏：https://www.bain.cn/news.php?id=32
    - 署名文章：https://www.bain.cn/news.php?id=26
    列表卡片解析（div.card → a[href]、.card-body .card-title、.card-footer），必要时按 `&page=` 翻页直至凑满 10 条；
    在 `URLData` 末尾加入四个分组，板块标题分别为“贝恩咨询(Bain & Company)观点-聚焦中国/全球视野/总裁专栏/署名文章”，
    Logo 统一使用 `./Logos/handler18_BAIN_zh.png`。
  - 内页爬取_完整版.py：新增 `parse_bain_article` 并在域名分发中接入（bain.cn）。
    - 标题与正文：优先 `div.detail-content .content-title h3` 与 `div.detail-content .content`，不足时回退通用解析；
    - 日期：优先 meta/time，缺失则使用列表页日期；
    - 作者：可检测到时写入作者姓名（meta[name=author] 或含“作者：”的文本）;
    - 附件：优先文档（pdf/doc/xls/ppt 等）；若仅有音频/视频则将其 URL 作为附件；若与文档并存仅保留文档；
    - `thinkank_name` 统一填写为“贝恩咨询（Bain & Company）”。
  - 未新增其他文件，沿用原有输出结构与流程，保持设置不变。

## 2025-10-13 (追加)
- 新增：麦肯锡中国（McKinsey & Company）（洞察）
  - main.py：新增 `handler15_mck_insights`（滚动加载，无“加载更多”按钮），采集前 20 条并输出为 `page-board-item`，加入 `MCK_URLData` 配置（Logo `./Logos/handler15_McK_zh.png`）。
  - 内页爬取_完整版.py：新增 `parse_mck_article` 并在域名分发中接入（mckinsey.com.cn）。解析标题、正文、日期（JSON-LD/Meta/Time 兜底），作者（可检出时使用文章作者姓名），附件遵循“优先文档（pdf/doc/xls/ppt），无文档则音/视频”的规则；`thinkank_name` 统一为“麦肯锡中国（McKinsey & Company）”。
  - 未新增其他文件，沿用原有流程与输出结构。

## 2025-10-14
- 优化：麦肯锡列表与详情抓取耗时
  - main.py：在 `handler15_mck_insights` 中过滤 `/insights/page/…` 与 `/insights` 聚合页链接，避免将分页页当作详情造成长时间超时。
  - 内页爬取_完整版.py：对 `mckinsey.com.cn` 启用域名定制抓取策略：
    - 增加 HEAD 预检（≤8s）用于快速失败；
    - 将详情 GET 的重试次数从 3 调整为 2，每次超时 12s，重试间隔 1s；
    - 其他域名保持原有策略不变。

## 2025-10-12

- 移除 Brookings Institution（美国布鲁金斯学会）相关集成与解析，保持其余站点流程不变�?- 新增 RAND Corporation 列表抓取与渲染：
  - 添加 `handler11_rand_topics`（主题栏目，每组�?30 条）�?  - 新增工具函数 `_rand_parse_en_date_to_iso` 用于英文日期规范化；`URLData` 中保�?14 个主题分组；`LogoPath` 统一使用 `./Logos/handler10.svg`�?- 内页解析扩展�?  - 新增 `parse_rand_article` 与改进版 `parse_rand_article2`，优先提取出版物摘要容器；不足时回退 meta 摘要或通用正文提取�?  - 路由已启�?`rand.org` 支持�?- 维护工具�?  - �?`内页爬取_完整�?py` 中提�?`--repair-rand` 参数，识别并移除正文异常�?RAND 条目，便于二次重抓�?

- 新增 JPMorgan Insights（摩根大通研究院）支持：
  - 列表页：新增 `handler12_jpm_insights`，支持点击“Load more”抓取前 80 条，输出至 `generated_html/index.html` 的 `page-board-item`，Logo 使用 `./Logos/handler12_JPMorgan.svg`。
  - 详情页：新增 `parse_jpm_article`，实现标题、正文、日期（JSON-LD/Meta/Time）解析；作者优先提取页面作者（JSON-LD 或 meta/DOM），`thinkank_name` 统一为“摩根大通研究院”。
  - 附件策略：优先提取文件类附件（pdf/doc/xls/ppt 等）；若仅有音频/视频则将音视频 URL 作为附件；若文件与音视频并存，仅保留文件附件。
  - 未更改现有统一等待/超时与渲染逻辑；不新增额外文件。
# CHANGELOG

## 2025-10-14 (追加)
- 新增：普华永道（PwC）（洞察）集成（中文站 https://www.pwccn.com/zh/research-and-insights.html）
  - main.py：新增 `handler16_pwc_zh_insights`（无需点击“加载更多”，抓取前 12 条）；
    解析 `article` 卡片，抽取链接、标题、日期（统一 YYYY-MM-DD），输出到主页板块；
    新增 `PWC_ZH_URLData` 配置（Logo `./Logos/handler16_pwc.png`，`MaxItems=12`）。
  - 内页爬取_完整版.py：新增 `parse_pwc_article` 并在域名分发中接入（pwccn.com）。
    标题/正文按富文本容器优先，日期优先 JSON-LD；作者若可检测则写入作者姓名；
    附件遵循“优先文档（pdf/doc/xls/ppt），无文档则回退音视频；若二者并存仅保留文档”的规则；
    `thinkank_name` 统一填写为“普华永道（PwC）”。
  - 未新增其他文件，保持现有流程与输出结构不变。

## 2025-10-13
- 新增：KPMG 中国（毕马威中国）洞察列表抓取与渲染
  - main.py：新增 `handler14_kpmg_insights`，进入 `https://kpmg.com/cn/zh/home/insights.html`，先处理 Cookie 同意，再通过滚动加载收集前 40 条，渲染到主页；加入 `KPMG_URLData` 站点配置（Logo `./Logos/handler14_KPMG_zh.png`）。
  - 内页爬取_完整版.py：新增 `parse_kpmg_article` 并接入路由（kpmg.com），解析标题、日期（JSON-LD/Meta/Time 兜底）、正文与附件（优先文档，若无文档则音/视频），authors 能检测到则填姓名，`thinkank_name` 统一为“毕马威中国(KPMG)”。
  - 行为保持与既有流程一致，输出结构不变。

## 2025-10-14 (追加2)
- 新增：波士顿咨询(BCG)（洞察/Publications）
  - main.py：新增 `handler17_bcg_publications`，支持点击“View more”加载，抓取前 28 条；
    解析 `div.items.js-result-container` 下卡片 `div.Promo-title a.Link[href]` 的链接与标题，日期若有统一为 YYYY-MM-DD；
    加入 `BCG_URLData` 配置（Logo `./Logos/handler17_BCG.png`，`MaxItems=28`）。
  - 内页爬取_完整版.py：新增 `parse_bcg_article` 并接入域名分发（bcg.com），解析标题、正文、日期与作者；
    附件策略与既有一致：优先文档，其次音/视频；并存时仅保留文档；`thinkank_name` 统一为“波士顿咨询（BCG）”。
  - 未新增其他文件，输出结构与现有完全一致。
## 2025-10-17 (新增 IISS Online Analysis)
- main.py
  - 新增 `handler20_iiss_online_analysis`，定位 `div.filter_results.feature_list a.feature[href]` 并通过 `a.pagination__next` 翻页，收集前 40 条；标题显示为“国际战略研究所(iiss)（在线分析）”；Logo 使用 `./Logos/handler20_iiss.png`。
  - 在 URLData 末尾新增 IISS 配置：`MaxItems=40`、`MaxPages=4`、`WaitingTimeLimitInSeconds=30`。
- 内页爬取_完整版.py
  - 新增 `parse_iiss_article`，抽取 `title/url/publish_date/authors/thinkank_name/summary/content/attachments`；`authors` 能检测到则使用文章作者姓名；`thinkank_name` 固定为“国际战略研究所(iiss)”。
  - `attachments` 规则：优先返回文档型（pdf/doc/xls/ppt 等），若无则返回音频/视频链接；若文档与音视频同时存在，则仅返回文档链接。
  - 在 `crawl_article_content` 中增加 `iiss.org` 分支：优先 `requests`，403/空白时回退到 `undetected-chromedriver` 获取 HTML。
- 保持 index 渲染与既有站点一致，不改动其它设置。
