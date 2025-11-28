# 项目使用说明

本项目把多个网站的列表页采集到一个汇总页，再按链接抓取正文，并支持把英文正文翻译成中文。下面按“做什么、怎么做、注意什么”写清楚。

## 主要文件和作用
- `main.py`：跑列表页，生成 `generated_html/index.html`。里面包含每个站点的标题、链接、日期和 Logo。
- `ChromePageRender.py`：Selenium 封装，负责打开网页、等待元素、点击分页。
- `generated_html/`：汇总页和静态资源（`index.html`、`index.css`、`index.js`、`Logos/` 等）。`index.js` 提供日期筛选和导出 PDF。
- `内页爬取_完整版.py`：读取 `generated_html/index.html` 的每条链接，按域名调用对应的解析函数，抓取正文、日期、作者、附件等，写入/追加到 `output_complete.json`。
- `output_complete.json`：所有抓取到的正文库；用它判断是否已抓取过某条链接。
- `translator_client.py` + `translate_output.py`：调用腾讯云“文本翻译”接口，把 `output_complete.json` 里的 `title`/`content` 翻译成中文。
- `Conda Environment/Python311_WebpageDataCollection.yaml`：依赖清单。
- `chromedrivers/`：预置的 ChromeDriver（多平台）。

## 运行前准备
1. 安装依赖（任选一种）  
   - `conda env create -f "Conda Environment/Python311_WebpageDataCollection.yaml"`  
   - 或手动安装：`selenium`、`beautifulsoup4`、`requests`、`dominate`、`undetected-chromedriver`、`tqdm`、`tencentcloud-sdk-python`。
2. ChromeDriver：如需手动指定，修改 `main.py` 里的 `__chrome_driver_path`；不改则使用自动管理。
3. （可选，翻译用）设置环境变量：  
   ```
   set TENCENTCLOUD_SECRET_ID=你的SecretId
   set TENCENTCLOUD_SECRET_KEY=你的SecretKey
   set TENCENTCLOUD_REGION=ap-beijing
   ```

## 标准流程（建议顺序）
1. **跑列表页**  
   `python main.py`  
   - 会先做“变更检测”：如果所有列表页都没变，直接提示并退出，复用旧的 `generated_html/index.html`。
   - 产出：`generated_html/index.html`。
2. **抓取内页**  
   `python 内页爬取_完整版.py`  
   - 读取 `generated_html/index.html` 的所有链接，按域名路由到解析函数，抓正文并写入 `output_complete.json`。  
   - 去重规则：只看 `url`，已存在的链接跳过。翻译不会影响去重，只要 `url` 不变。
   - 可选参数：`--only-domain foo.com` 只抓该后缀；`--force-domain foo.com` 即使抓过也强制重抓该后缀。
3. **翻译（可选）**  
   `python translate_output.py --input output_complete.json --output output_complete.json`  
   - 默认：源语言 auto，目标 zh，软限速约 4.5 QPS（接口上限 5 QPS），单次最多 4500 字符，自动分段拼回。  
   - 默认跳过已含中文的字段；要强制翻译可加 `--no-skip-chinese`。  
   - 覆盖原文件；若想保留原文，改用 `--output output_translated.json`。  
   - 只改 `title`、`content`，不改 `url` 等去重关键字段。
4. **查看/导出**  
   打开 `generated_html/index.html`；可按日期筛选、导出 PDF（`html2pdf`）。

## 关键设计与逻辑
- **变更检测（main.py）**：对列表页做 ETag/Last-Modified/前 4KB 哈希比对，结果存 `generated_html/index.fingerprints.json`。若无变化且已有 `index.html`，直接退出。
- **列表抓取**：每个站点有独立 handler，Selenium 渲染后用 BeautifulSoup 抽取，输出 `.page-board-item`。
- **内页抓取**：按域名路由到专用解析函数（BCG/Bain/EY/德勤/清华国情/复旦/IISS/KPMG/PwC/JPM/RAND 等），抽取正文、日期、作者、附件，追加到 `output_complete.json`，URL 归一化去重。
- **翻译**：调用腾讯云 TextTranslate；分段后逐段翻译再拼接；默认覆盖文件但不影响去重（去重只看 URL）。

## 可能遇到的问题与处理
- **网络/代理**：翻译调用失败常见报错为 `ProxyError`/`SSL`；需确保本机可直连 `https://tmt.tencentcloudapi.com`，或配置可用代理。
- **凭证缺失**：未设置 SecretId/SecretKey 会报错，请先设置环境变量。
- **限频**：接口上限 5 QPS，默认 4.5 QPS；如仍超限，可用 `--qps 3`。
- **文件覆盖风险**：翻译默认覆盖 `output_complete.json`，若需保留原文请输出到新文件。
- **Chrome/Driver 版本**：如遇浏览器版本不匹配，更新 `chromedrivers/` 或指定有效路径；部分站点需要 undetected-chromedriver（代码已处理）。
- **列表未更新**：main.py 输出“未变更”直接退出是正常行为；若要强制重抓，可删除 `generated_html/index.fingerprints.json` 后重跑。

## 时间与调用量预估（粗略）
- 列表页：20+ 站点，通常几分钟（取决于网络和页面加载）。
- 内页：数百到上千条，含 0.5s 间隔，视站点和网络情况，可能需要十几分钟到数十分钟。
- 翻译：上限 5 QPS，默认 4.5 QPS。假设 1000 条记录、每条 2 段，需要约 4 分钟起；长文本分段会增加调用次数和时间。

## 安全与备份建议
- 翻译前最好备份 `output_complete.json` 或输出到新文件。
- 不要把 SecretId/SecretKey 写入仓库，仅用环境变量。
- 保持“先列表→再内页→再翻译”的顺序，避免数据不同步。
