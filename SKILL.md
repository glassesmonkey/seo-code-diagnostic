---
name: seo-code-diagnostic
description: "Run URL-first, evidence-gated SEO audits of website codebases and current-run pages. Use for technical/on-page SEO, crawlability, SSR/prerendering, content or copy risks, AdSense rejection diagnosis, and prioritized fix plans."
---

# SEO Code Diagnostic

采用 **URL-first** 和 **evidence gate**：先证明审计了哪些目标 URL，再判断页面问题。源码正则是线索，不是线上事实。

## 固定契约

- P0–P3 只从 [`references/diagnostic-rubric.md`](references/diagnostic-rubric.md) 取值。
- JSON/Markdown 字段、coverage 和证据状态遵循 [`references/report-contract.md`](references/report-contract.md)。
- 识别路由、metadata 继承或渲染方式时，必须加载 [`references/framework-adapters.md`](references/framework-adapters.md)。
- 判断页面类型、搜索意图与内容价值时，按需加载 [`references/seo-principles.md`](references/seo-principles.md)。
- 只有需要对照 Ahrefs crawler 术语时才加载 [`references/ahrefs-learning-notes.md`](references/ahrefs-learning-notes.md)；严重度仍以 rubric 为准。
- 不编造排名、搜索量、流量、外链、GSC/GA、版权、政策或生产状态。
- 永久排除构建产物、历史报告、Agent 配置、`.env*`、`.dev.vars`、日志、数据库、原始上传和用户数据；报告不得泄露其片段。

## 分支选择

| 条件 | 模式 | 结论上限 |
|---|---|---|
| 有本轮服务 | `--base-url` | HTTP 证据可进入 `Confirmed`；同时有 `--domain` 时默认受控验证站外互链 |
| 有本轮静态输出 | `--rendered-root` | 当前 HTML 可进入 `Confirmed` |
| 无法构建/启动 | source-only | 源码启发式最多 `Candidate` |
| 用户明确要求 AdSense | 以上模式 + `--adsense` | 仍受 73 ID completeness 约束 |

## 五步流程

### 1. 固定范围

读取项目 `AGENTS.md`、`ROADMAP.md` 和框架配置，记录：

- `root`、commit、框架、目标域名和审计时间；
- 可否执行本轮 build/start；
- 证据模式：`--base-url`、`--rendered-root` 或 source-only；
- 互链验证模式：运行时默认 `--reciprocal-links auto`，需要禁止第三方请求时显式使用 `off`；
- 页面级 `index_intent`、`priority`、`keywords` 和来源；需要显式映射时使用 `--routes-file`；
- 用户给出的 `--keywords` 只作为未映射词清单，禁止套用到每个页面。

routes file 使用 `{"routes": {"/path": {...}}}`；完整字段见报告协议。
输出必须放在扫描根目录外；额外忽略项使用可重复的 `--exclude`。

**完成标准：** `scope` 可复现，输出和隐私路径已排除，每个关键词都标明页面映射或“未映射”。

### 2. 建立路由真相

目标路由是以下来源的并集：实际 sitemap、显式 routes file、框架公开路由、已注册内容。按适配规则处理 route group、locale、动态/catch-all、layout metadata 继承、metadata routes 和内容注册表。

为每条路由记录 `route_kind`、`index_intent`、`intent_source` 和预期验证方式。API、认证、管理、错误、redirect 和未注册内容默认不做 on-page 评分，但必须分类。意图无法证明时用 `Unknown`，不能猜成 indexable。

**完成标准：** 每个已发现路由只出现一次；每个动态路由有具体 URL 来源或 coverage gap；排除评分的路由有明确类别和原因。

### 3. 获取本轮页面证据

Next.js 不解析已有 `.next`/`.open-next`。获准运行时，先成功执行本轮 build，再启动服务并传 `--base-url`；静态框架只有显式传入本轮生成的 `--rendered-root` 才可作为渲染证据。

无法运行页面时，明确执行 source-only：

```bash
python /path/to/seo-code-diagnostic/scripts/seo_code_audit.py \
  --root . \
  --out "../seo-audit"
```

URL-first 示例：

```bash
python /path/to/seo-code-diagnostic/scripts/seo_code_audit.py \
  --root . \
  --domain "https://example.com" \
  --base-url "http://127.0.0.1:3000" \
  --routes-file "seo-routes.json" \
  --keywords "unmapped keyword" \
  --exclude "private-content/**" \
  --out "../seo-audit"
```

静态站把 `--base-url` 换成本轮目录：

```bash
python /path/to/seo-code-diagnostic/scripts/seo_code_audit.py \
  --root . \
  --rendered-root "./dist" \
  --out "../seo-audit"
```

对目标 URL 检查 HTTP 状态、redirect、robots、title、description、H1、canonical、正文、内链和 JSON-LD。本地动态集合增加不存在 slug 的 soft-404 sentinel。运行时同时有 `--domain` 时，从已验证公开 HTML 提取未限定站外链接，受控检查目标页和对方首页是否出现回链；source-only 和 rendered 模式不访问第三方。source-only 仍可运行，但所有源码启发式最多为 `Candidate`。

**完成标准：** 每个目标 URL 有本轮 HTTP/静态证据，或在 `coverage.gaps` 中说明失败原因；构建 provenance 可追溯。

### 4. 通过 evidence gate

- `Confirmed`：当前 URL 响应或可复现仓库事实直接证明。
- `Candidate`：源码正则、未验证映射或需人工解释的内容线索。
- `Unknown`：未覆盖、截断、读取/解析失败或索引意图不明。
- P0–P2 汇总只计算 `Confirmed`；status 与 impact 独立。
- 按 `route + code + content hash` 合并 standalone、OpenNext 等重复证据。
- `alt=""` 是合法的装饰图语义；JSX spread props 不能确认缺 alt。
- 多个 H1 只有在多个同等显著标题导致主标题不清时报告；`"use client"` 不等于 CSR-only。
- 缺 canonical、缺 description 或固定字数不足都不能脱离索引意图、重复信号和页面任务自动升为 P1。
- 文案规则只检查可映射到公开页面的用户可见内容；PRD、注释、法律免责声明不能直接升级为页面问题。
- 普通互链、单向外链和“已检查页面未观察到回链”都不是垃圾链接结论；只有 rubric 定义的多域模板/伙伴页组合模式才能生成 P2。

**完成标准：** 每条 finding 满足报告协议的必填证据字段；没有由“未搜到”、路径污染或读取失败生成的已确认结论。

### 5. 报告并复核

按 schema v2 输出固定的 `scope`、`coverage`、`routes`、`findings`、`link_analysis`、`adsense`。中文结论先写 coverage 和互链验证覆盖，再写 Confirmed 问题，再列 Candidate/Unknown 和最小修复动作。互链验证失败只影响 `link_analysis`，不得污染主站 coverage；coverage 不完整时禁止写“未发现问题”。

仅当用户明确要求 AdSense 时加 `--adsense`，并加载：

- [`references/adsense-requirements.md`](references/adsense-requirements.md)：只取全部 73 个 ADS ID 及其证据要求；
- [`references/adsense-review-diagnostic.md`](references/adsense-review-diagnostic.md)：游戏/工具站内容与政策判断。

状态和 readiness 以 report contract 为准。每个 ADS ID 只能是 `Pass / Fail / Unknown / N/A`。页面数、文章数和内容判断只使用已验证 URL；未覆盖就是 `Unknown`。73 项未完整覆盖或关键外部证据未取得时，`readiness` 保持 `null`。

需要合并人工、后台、授权、analytics 或法律证据时，按以下顺序执行：

1. 用 `scripts/adsense_report_validator.py --template --target-domain URL` 生成 73 项模板；
2. 只填写非敏感摘要、公开 URL、仓库相对路径和不透明 `evidence_ref`；
3. 用 `--check-assessments` 校验后，将文件传给扫描器的 `--adsense-assessments`；
4. 用 `--check-report` 复核最终 JSON 的计数、结论、readiness 和修复顺序。

`--adsense-assessments` 必须与 `--adsense --domain` 同时使用。扫描器排除该输入，只在 scope 记录模式和 SHA-256。校验器只能证明结构与聚合自洽，不能证明证据内容真实。

连续运行两次，比较 `scope.provenance.result_hash`，确认第二次不扫描第一次报告且结果稳定；验证报告没有密钥或原始用户数据。若执行了代码修改，再运行项目 lint/build/test 并只声明实际验证结果。

**完成标准：** schema v2 可解析、coverage 与汇总一致、AdSense completeness 可核对、重复运行稳定、隐私检查通过。
