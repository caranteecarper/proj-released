# 更新日志 (Changelog)

## 2025-10-12

### Brookings Institution 集成

- main.py：新增 `handler12_brookings`，并在 `URLData` 中加入“美国布鲁金斯学会-研究与评论（Research & Commentary）”。
  - 分页使用 `?page=1..8`（8 页≈80 条）。
  - 等待选择器：`div#contentStream` 与 `div.articles-stream`。
  - `LogoPath` 使用 `./Logos/brookings.png`，输出结构沿用 `.page-board-item > a > h3 + span`。
- 内页爬取：新增 `parse_brookings_article` 并在路由中加入 `brookings.edu` 分支。
  - 标题从 `h1`/`og:title` 抽取；
  - 日期优先 JSON-LD `datePublished`，次选 `brookings.dataLayer.publish_date`，再退 `meta[article:published_time]`，最终统一为 `YYYY-MM-DD`；
  - 作者优先 `brookings.dataLayer.author`（多作者逗号分隔），再退 `meta[name=author]` 或页面 Authors 模块；
  - 附件优先 PDF/DOC/XLS 等文件链接；如无文件，则回退音视频（mp3/mp4/YouTube/Vimeo/SoundCloud/Libsyn 等）；
  - `thinkank_name` 固定为“美国布鲁金斯学会”。
  - 其他设置保持不变。

- 新增 RAND Corporation 列表抓取与渲染：
  - 添加 `handler11_rand_topics`（主题栏目，每组近 30 条）
  - 原 `handler12_rand_pubs`（研究与评论，按日期阈值 2025-09-26 截止）已按后续要求移除
  - 新增工具函数 `_rand_parse_en_date_to_iso` 用于英文日期规范化
  - 在 `URLData` 中追加 14 个主题分组（已保留）；“研究与评论”分组已删除，`LogoPath` 统一使用 `./Logos/handler10.svg`
- 内页解析扩展：
  - 新增 `parse_rand_article`（标题/正文/日期解析 + 附件抽取），并增加改进版 `parse_rand_article2`：
    - 优先提取出版物页面摘要容器（如 `div.product-main div.abstract.product-page-abstract`）
    - 过滤订阅与社交分享等噪声文本，缺失时回退到 meta 摘要或通用正文提取
    - 路由更新为使用 `parse_rand_article2`
  - 在 `crawl_article_content` 路由中加入 `rand.org` 支持（保留）
- 维护/修复工具：
  - 在 `内页爬取_完整版.py` 中新增 `--repair-rand` 命令行参数，可自动识别并移除 `output_complete.json` 中正文过短/元信息偏多的 RAND 条目，便于二次重抓。

备注：本次变更保持已有页面结构不变（`.page-board-item > a > h3 + span`），与 `内页爬取_完整版.py` 的处理流程兼容。
