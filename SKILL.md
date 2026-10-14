---
name: seo-code-diagnostic
description: "Use when SEO 诊断, AdSense, or GEO 上线前走查. URL-first ranking audit plus a visitor launch gate: pages shipping now must be finished before GPT traffic can arrive. Follow 哥飞. Do not invent GSC metrics. Scanner pass is not GEO ready."
---

# SEO Code Diagnostic

采用 **URL-first** 和 **evidence gate**：先证明审计了哪些目标 URL，再判断页面问题。源码正则是线索，不是线上事实。

本 skill 有两段诊断，不要混成一张清单。搜索排名仍是 F1–F10。GEO 只指上线闸门：新站一公开就可能有 GPT 流量，这次要公开的页面必须已经是陌生人能用完的成品。扫描器通过不等于 GEO 就绪。闸门细则只从 [`references/geo-launch-gate.md`](references/geo-launch-gate.md) 取值。

报告主表仍是 F1–F10（相关性 → 内链）。**实战口径**只从 [`references/gefei-ranking-practice.md`](references/gefei-ranking-practice.md) 取值。Zyppy 调研见 [`references/zyppy-2026-ranking-factors.md`](references/zyppy-2026-ranking-factors.md)，只校准排序和「没数据就 Unknown」。与哥飞冲突时以哥飞为准。

## 固定契约

- P0–P3 只从 [`references/diagnostic-rubric.md`](references/diagnostic-rubric.md) 取值。
- F1–F10 实战检查只从 [`references/gefei-ranking-practice.md`](references/gefei-ranking-practice.md) 取值。
- GEO 上线闸门只从 [`references/geo-launch-gate.md`](references/geo-launch-gate.md) 取值。不要把它并进 F1–F10，也不要用因素表通过代替闸门通过。
- JSON/Markdown 字段、coverage 和证据状态遵循 [`references/report-contract.md`](references/report-contract.md)。
- 识别路由、metadata 继承或渲染方式时，必须加载 [`references/framework-adapters.md`](references/framework-adapters.md)。
- 判断页面类型、搜索意图与内容价值时，按需加载 [`references/seo-principles.md`](references/seo-principles.md)。
- 只有需要对照 Ahrefs crawler 术语时才加载 [`references/ahrefs-learning-notes.md`](references/ahrefs-learning-notes.md)；与哥飞冲突时以哥飞为准，严重度仍以 rubric 为准。
- 不编造排名、搜索量、流量、外链、GSC/GA、CTR、品牌词量、版权、政策或生产状态。没有这些数据时，F2/F5/F6/F7/F9 的线上强度必须 `Unknown`。
- 永久排除构建产物、历史报告、Agent 配置、`.env*`、`.dev.vars`、日志、数据库、原始上传和用户数据；报告不得泄露其片段。

## 分支选择

| 条件 | 模式 | 结论上限 |
|---|---|---|
| 有本轮服务 | `--base-url` | HTTP 证据可进入 `Confirmed`；同时有 `--domain` 时默认受控验证站外互链 |
| 有本轮静态输出 | `--rendered-root` | 当前 HTML 可进入 `Confirmed` |
| 无法构建/启动 | source-only | 源码启发式最多 `Candidate` |
| 用户明确要求 AdSense | 以上模式 + `--adsense` | 仍受 73 ID completeness 约束 |
| 即将上线，或用户问能不能上线 | 必跑 GEO 闸门 | 扫描器结论不能写成「可以上线」 |
| 已上线，且只要排名诊断 | 不跑全站点击 | 写明「GEO 闸门：未纳入本次范围」，不得声称上线就绪 |

## 六步流程

### 1. 固定范围

读取项目 `AGENTS.md`、`ROADMAP.md` 和框架配置，记录：

- `root`、commit、框架、目标域名和审计时间；
- 可否执行本轮 build/start；
- 证据模式：`--base-url`、`--rendered-root` 或 source-only；
- 互链验证模式：运行时默认 `--reciprocal-links auto`，需要禁止第三方请求时显式使用 `off`；
- 页面级 `index_intent`、`priority`、`keywords` 和来源；需要显式映射时使用 `--routes-file`；
- 用户给出的 `--keywords` 只作为未映射词清单，禁止套用到每个页面。
- 本次是否包含上线或「能不能上线」；
- 若包含，本次要公开的页面清单。用户没给清单就问，不要用扫描器发现的全部路由填这个空。第一版只有三五个页面是合格范围。

routes file 使用 `{"routes": {"/path": {...}}}`；完整字段见报告协议。
输出必须放在扫描根目录外；额外忽略项使用可重复的 `--exclude`。

**完成标准：** `scope` 可复现，输出和隐私路径已排除，每个关键词都标明页面映射或“未映射”。上线范围要么是明确页面清单，要么已写明本次不跑闸门的原因。

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
- 因素状态 `Pass / Fail / Unknown / N/A` 与 finding 的 `status`/`impact` 独立：`Fail` 只由映射到该因素的 Confirmed finding 产生；hybrid/线上因素没有用户数据时不得 `Pass`。
- 已映射关键词要做 F1 的 TDH / 标题 / H1 / 副标题 / URL / Meta / 语言检查；缺 description 不得升为 P1，但 Meta 与词无关要进 F1，并同时记 F5 CTR。
- 密度用来判断页面是否聚焦：发散或词只在角落出现要报不聚焦，堆砌也要报。不用 `3%–5%` 当达标线。
- 关键词域名是 F1 加分；已有品牌域不是关键词域不得 Fail。不要买连字符堆词的垃圾 EMD。
- F2：新词新站可以无链拿排名；老词新站必须有链；有竞争的词通常必须有链。无链接表时因素仍 `Unknown`，但必须写出场景口径。精确匹配锚文本是优选，同时要有围绕核心词的多样性。Nofollow 仍有小正面效果。高权站孤岛目录（如 Adsy 自定义目录）按无效页级权处理。
- F5 行为数据可以以小博大。F7 可并入 F5，但好行为 ≠ 最佳体验。禁止假排队或伪造行为。
- F9 执行「一个关键词组一个页面」和「举全站之力来打一个词」。
- F8 `Pass` 不等于会排名；正文应在后端渲染的初始 HTML 里。CWV 不当 P1 增长项。

**完成标准：** 每条 finding 满足报告协议的必填证据字段；没有由“未搜到”、路径污染或读取失败生成的已确认结论。

### 5. GEO 上线闸门

先加载 [`references/geo-launch-gate.md`](references/geo-launch-gate.md)，按该文件执行。不要在这里另写一套标准，也不要用扫描器、截图或子代理审代码来代替打开页面。

**完成标准：** 本次若包含上线或「能不能上线」，范围内每页都有电脑和手机的查看记录，每个可见链接和主按钮都点过，可见文案都读过，主任务要么做完要么写明卡在哪。问题已改完才能写「GEO 就绪」。只授权诊断时，结论只能是「未就绪」。本次不包含上线时，写明「GEO 闸门：未纳入本次范围」，不得写可以上线。

### 6. 报告并复核

按 schema v2 输出固定的 `scope`、`coverage`、`routes`、`findings`、`link_analysis`、`adsense`，并附 10 行 `factor_summary`。中文结论先写 GEO 闸门结论（就绪 / 未就绪 / 未纳入本次范围），再写 coverage 和互链验证覆盖，再写 Top 10 因素表（F1 含 TDH/聚焦和域名加分观察；F2 含新词新站/老词新站口径），再写 Confirmed 问题，再列 Candidate/Unknown 和按因素排序的最小修复动作。互链验证失败只影响 `link_analysis`，不得污染主站 coverage；coverage 不完整时禁止写“未发现问题”。

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

**完成标准：** schema v2 可解析、coverage 与汇总一致、Top 10 因素表 10 行且无编造线上指标、AdSense completeness 可核对、重复运行稳定、隐私检查通过。GEO 闸门结论与走查记录一致，没有用扫描器通过代替闸门通过。
