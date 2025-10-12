# 更新日志 (Changelog)

## 2025-10-12

- 移除 Brookings Institution（美国布鲁金斯学会）相关集成与解析，保持其余站点流程不变�?- 新增 RAND Corporation 列表抓取与渲染：
  - 添加 `handler11_rand_topics`（主题栏目，每组�?30 条）�?  - 新增工具函数 `_rand_parse_en_date_to_iso` 用于英文日期规范化；`URLData` 中保�?14 个主题分组；`LogoPath` 统一使用 `./Logos/handler10.svg`�?- 内页解析扩展�?  - 新增 `parse_rand_article` 与改进版 `parse_rand_article2`，优先提取出版物摘要容器；不足时回退 meta 摘要或通用正文提取�?  - 路由已启�?`rand.org` 支持�?- 维护工具�?  - �?`内页爬取_完整�?py` 中提�?`--repair-rand` 参数，识别并移除正文异常�?RAND 条目，便于二次重抓�?

- 新增 JPMorgan Insights（摩根大通研究院）支持：
  - 列表页：新增 `handler12_jpm_insights`，支持点击“Load more”抓取前 80 条，输出至 `generated_html/index.html` 的 `page-board-item`，Logo 使用 `./Logos/handler12_JPMorgan.svg`。
  - 详情页：新增 `parse_jpm_article`，实现标题、正文、日期（JSON-LD/Meta/Time）解析；作者优先提取页面作者（JSON-LD 或 meta/DOM），`thinkank_name` 统一为“摩根大通研究院”。
  - 附件策略：优先提取文件类附件（pdf/doc/xls/ppt 等）；若仅有音频/视频则将音视频 URL 作为附件；若文件与音视频并存，仅保留文件附件。
  - 未更改现有统一等待/超时与渲染逻辑；不新增额外文件。

