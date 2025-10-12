# 更新日志 (Changelog)

## 2025-10-12

- 新增 RAND Corporation 列表抓取与渲染：
  - 添加 `handler11_rand_topics`（主题栏目，每组近 30 条）
  - 原 `handler12_rand_pubs`（研究与评论，按日期阈值 2025-09-26 截止）已按后续要求移除
  - 新增工具函数 `_rand_parse_en_date_to_iso` 用于英文日期规范化
  - 在 `URLData` 中追加 14 个主题分组（已保留）；“研究与评论”分组已删除，`LogoPath` 统一使用 `./Logos/handler10.svg`
- 内页解析扩展：
  - 新增 `parse_rand_article`（标题/正文/日期解析 + 附件抽取）
  - 在 `crawl_article_content` 路由中加入 `rand.org` 支持（保留）

备注：本次变更保持已有页面结构不变（`.page-board-item > a > h3 + span`），与 `内页爬取_完整版.py` 的处理流程兼容。
