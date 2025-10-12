# 更新日志 (Changelog)

## 2025-10-12

- 移除 Brookings Institution（美国布鲁金斯学会）相关集成与解析，保持其余站点流程不变。
- 新增 RAND Corporation 列表抓取与渲染：
  - 添加 `handler11_rand_topics`（主题栏目，每组约 30 条）。
  - 新增工具函数 `_rand_parse_en_date_to_iso` 用于英文日期规范化；`URLData` 中保留 14 个主题分组；`LogoPath` 统一使用 `./Logos/handler10.svg`。
- 内页解析扩展：
  - 新增 `parse_rand_article` 与改进版 `parse_rand_article2`，优先提取出版物摘要容器；不足时回退 meta 摘要或通用正文提取。
  - 路由已启用 `rand.org` 支持。
- 维护工具：
  - 在 `内页爬取_完整版.py` 中提供 `--repair-rand` 参数，识别并移除正文异常的 RAND 条目，便于二次重抓。

