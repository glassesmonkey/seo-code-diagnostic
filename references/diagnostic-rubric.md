# SEO 诊断严重度 Rubric

本文件是 SEO finding 的 `impact: P0 | P1 | P2 | P3` 唯一事实源。页面类型与内容判断见 [`seo-principles.md`](seo-principles.md)；框架证据边界见 [`framework-adapters.md`](framework-adapters.md)；`status` 与输出字段见 [`report-contract.md`](report-contract.md)。

## 先分开 status 与 impact

- `status` 回答“证据是否证明”：`Confirmed / Candidate / Unknown`。
- `impact` 回答“如果成立，影响多大”：`P0 / P1 / P2 / P3`。
- P0–P2 汇总只统计 `Confirmed`。一个源码命中的 P0 候选仍不是“已发现 P0”。
- 源码正则最多是 `Candidate`；读取失败、截断、未映射或意图未知是 `Unknown`。
- 升级 impact 必须有目标页优先级、受影响路由数和索引意图证据；不能因规则名看起来严重而升级。

## P0：已确认的索引阻断或核心路由失效

只在目标路由明确希望索引且当前证据证明阻断时使用。

| Rule | P0 条件 | 不满足时 |
|---|---|---|
| `INDEX_INTENT_CONFLICT` | 核心目标页实际 `noindex`，或 robots 明确阻止该页抓取 | 意图未知为 `Unknown`；非核心页通常 P1 |
| `HTTP_UNREACHABLE` | 核心目标页稳定返回 4xx/5xx、认证拦截或不可达 | 临时失败先 `Unknown`；非核心页按 P1/P2 |
| `ROBOTS_SITE_BLOCK` | 当前 robots 对目标 crawler 封锁全部核心公开路由 | 单一路由冲突按该路由优先级判断 |
| `CANONICAL_CONFLICT` | 核心页 canonical 指向错误主机、不可达 URL 或明显不同实体，造成合并风险 | 仅缺 canonical 不能使用 P0/P1 |
| `ROUTE_OUTPUT_COLLAPSE` | 多个核心动态 URL 当前响应为同一错误/占位实体，且无法形成独立页面 | 只有源码复用线索时为 `Candidate` |

## P1：已确认的高影响页面或系统性问题

| Rule | P1 条件 | 降级/排除条件 |
|---|---|---|
| `TITLE_MISSING` | 可索引目标页的当前 HTML 没有可用 title | 意图未知为 `Unknown` |
| `MAIN_HEADING_UNCLEAR` | 页面没有可识别主标题，或多个同等显著标题让主标题不清 | 仅 `<h1>` 数量大于 1 不成立 |
| `METADATA_COLLISION` | 多个不同意图的目标 URL 当前输出相同 title/canonical 等冲突信号 | 单一源码模板线索为 `Candidate` |
| `SOFT_404` | 无效 slug 返回 200 且呈现空白、占位或与有效实体近似的可索引页面 | 正确 404/redirect 不评分 |
| `RENDERED_CONTENT_MISSING` | 核心目标页当前 HTML 缺少完成主要任务所需的正文/控件语义 | `"use client"` 本身不是证据 |
| `INTERNAL_COPY_LEAK` | 内部 prompt、执行说明或模型过程已确认出现在公开页面 | PRD、注释、测试和历史报告不评分 |
| `YMYL_UNSUPPORTED_CLAIM` | 公开页对健康、财务、法律或安全给出无依据承诺/保证，且可能影响重大决策 | 法律免责声明、一般信息和内部草稿不成立 |

## P2：已确认的页面质量、发现性或意图覆盖缺口

| Rule | P2 条件 | 降级/排除条件 |
|---|---|---|
| `SITEMAP_COVERAGE_GAP` | 明确应索引的路由未进入实际 sitemap，且没有其他发现信号 | 只在源码未找到 sitemap 时是 `Unknown` |
| `ORPHAN_ROUTE` | 已验证目标页没有任何有效站内入口 | 未完成全站内链覆盖时为 `Unknown` |
| `DESCRIPTION_GAP` | description 缺失或失真，且页面搜索摘要/意图表达确实受损 | 仅缺标签不自动 P1；可为 P3 |
| `CANONICAL_GAP` | 存在可验证重复 URL，且缺 canonical 加剧信号分散 | 无重复证据时至多 P3 |
| `IMAGE_ALT_MISSING` | 承载内容的信息图像在当前 HTML 中没有 `alt` 属性 | `alt=""` 合法；源码 spread props 不确认 |
| `INTENT_CONTENT_GAP` | 页面未回答其目标任务中的关键问题，证据来自页面类型和已映射关键词 | 禁止用固定字数阈值或关键词密度判断 |
| `INTERNAL_LINK_GAP` | 重要上下级/相关页面之间缺少可验证的上下文入口 | 尚未覆盖全部相关页时为 `Candidate/Unknown` |
| `STRUCTURED_DATA_INVALID` | 已输出的 JSON-LD 无效、与可见事实冲突或包含虚构评分/实体 | 单纯没有可选 schema 通常 P3 |
| `RECIPROCAL_LINK_NETWORK_PATTERN` | 本轮运行时 HTML 确认至少 3 个不同站外主机与本站存在双方未限定的 follow 链接，且这些链接形成全站模板重复或集中伙伴页模式 | 单个/少量普通互链、任一方向使用 `nofollow/sponsored/ugc`、只检查有限页面但未观察到回链，均不成立；Confirmed 只证明模式，不证明操纵排名的主观意图 |

## P3：增强项

P3 用于不阻断索引、也没有证据表明显著损害意图满足的改进：

- 无重复 URL 证据时建议自引用 canonical；
- description 可改进，但页面仍能清晰表达任务；
- title/摘要表达、OG/Twitter、favicon、manifest 可增强；
- 可选且与真实可见内容一致的 JSON-LD；
- 图片文件名、尺寸声明、压缩和非关键语义结构可改善；
- 多个 H1 但主标题仍清楚，或标题层级可读性优化。

## Source-only 与证据状态辅助规则

以下 ID 只定义默认 impact；status 仍由 evidence gate 决定。源码存在模式最多为 `Candidate`，源码“未找到”与读取失败必须为 `Unknown`。

| 默认 impact | Rule IDs |
|---|---|
| P0 | `ROBOTS_DISALLOW_ALL`（仅源码候选；运行时全站阻断使用 `ROBOTS_SITE_BLOCK`） |
| P1 | `CANONICAL_NOT_ABSOLUTE`、`NO_METADATA_SOURCE_FOUND`、`NO_CANONICAL_SOURCE_FOUND`、`SITEMAP_MISSING`、`SITEMAP_DOMAIN_MISMATCH`、`YMYL_COPY_REVIEW` |
| P2 | `CANONICAL_NOT_HTTPS`、`HEADING_SKIP`、`KEYWORD_NOT_FOUND`、`LOW_INTERNAL_LINKS`、`MISSING_VIEWPORT`、`RENDERED_TEXT_COVERAGE_CANDIDATE`、`ROBOTS_MISSING`、`SITEMAP_EMPTY`、`SOURCE_IMG_WITHOUT_ALT` |
| P3 | `CONTENT_DEPTH_REVIEW`、`DESCRIPTION_LENGTH`、`FAQ_MODULE_ABSENT`、`IMAGE_DIMENSIONS_MISSING`、`META_KEYWORDS_PRESENT`、`NOINDEX_SOURCE_SIGNAL`、`NO_SCHEMA_SOURCE_FOUND`、`OG_URL_CANONICAL_MISMATCH`、`ROBOTS_NO_SITEMAP`、`TITLE_LENGTH` |
| P3 Unknown | `HTML_PARSE_FAILED`、`HTML_READ_FAILED`、`HTML_READ_TRUNCATED`、`ROUTES_FILE_UNREADABLE`、`SOURCE_IMG_ALT_UNKNOWN`、`SOURCE_READ_FAILED`、`SOURCE_READ_TRUNCATED`、`UNKNOWN_RULE` |

其中 `ROBOTS_MISSING`、`SITEMAP_MISSING`、三个 `NO_*_SOURCE_FOUND` 都是缺失搜索结果，固定为 `Unknown`；它们不能单独生成 Confirmed，也不能在已有 URL 证据时制造全局 coverage gap。

## 禁止使用的自动阈值

- 不存在“最佳关键词密度”，不得用 `3%–5%`、`8%` 或其他比例定级。
- 不得用固定字符数把页面判为薄内容；先判断页面类型、用户任务和信息增益。
- 缺 description、缺 canonical、多个 H1 都不是无条件 P1。
- `"use client"` 不是 CSR-only 的证明；必须检查当前 HTTP/渲染 HTML。
- 站外链接数量或一次普通互链不能单独证明链接垃圾；必须取得双方页面证据并满足 `RECIPROCAL_LINK_NETWORK_PATTERN` 的组合条件。

解释依据：

- [Google Search Central: January 2023 SEO office hours](https://developers.google.com/search/help/office-hours/2023/january?hl=en)
- [Google Search Central: title links](https://developers.google.com/search/docs/appearance/title-link)
- [Google Search Central: canonical consolidation](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Google Search Central: spam policies - link spam](https://developers.google.com/search/docs/essentials/spam-policies#link-spam)
- [Google Search Central: qualify outbound links](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links)

## AdSense 与 P0–P3 的边界

`adsense-requirements.md` 的 `Severity` 是 ADS 审核优先级，不是本报告的 SEO `impact`。ADS ID 的结论只使用 `Pass / Fail / Unknown / N/A`；如同一证据还要生成 SEO finding，再按本文件独立定 P0–P3，禁止机械映射。
