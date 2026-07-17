# Report Contract v2

本文件定义扫描器与人工报告共享的 schema、coverage 和 evidence gate。字段可以扩展，不能删除或改义；其他 reference 的旧输出示例与本文件冲突时，以本文件为准。

## CLI 契约

保留：`--root`、`--domain`、`--keywords`、`--adsense`、`--out`。

新增：

- `--base-url URL`：对本轮本地服务或用户指定站点取 HTTP 证据；
- `--routes-file PATH`：显式页面意图和关键词映射；
- `--rendered-root PATH`：只接收本轮生成的静态 HTML 目录；
- `--exclude GLOB`：可重复，追加到硬排除列表；
- `--reciprocal-links auto|off`：默认 `auto`；同时存在 `--base-url` 和 `--domain` 时受控访问站外目标页与其首页，`off` 明确禁止第三方请求。
- `--adsense-assessments PATH`：只与 `--adsense --domain` 同用；加载通过独立校验的 73 项人工/外部证据。

`--keywords` 只生成未映射词清单，不应用到所有页面。推荐 routes file：

```json
{
  "routes": {
    "/bank-statement-to-csv": {
      "index_intent": "index",
      "priority": "core",
      "keywords": ["bank statement to csv"],
      "intent_source": "product registry"
    }
  }
}
```

允许 `index_intent: index | noindex | unknown`；`priority` 至少支持 `core | normal | low`。缺失字段不得靠全局关键词补齐。

## 顶层 schema

```json
{
  "schema_version": 2,
  "scope": {},
  "coverage": {},
  "routes": [],
  "findings": [],
  "link_analysis": {},
  "adsense": {}
}
```

这六个对象/数组始终存在；未运行互链验证时保留 `link_analysis.status: not_run`，未启用 AdSense 时保留 `adsense.enabled: false`。

### `scope`

至少包含：

- `root`、`domain`、`base_url`、`rendered_root`；
- `reciprocal_links: auto | off`；
- `framework`、`mode: source-only | runtime | rendered`；
- `source_commit`、`started_at`；
- `route_sources`、`excludes`、`output_paths`；
- `unmapped_keywords`；
- `adsense_assessments: {mode, sha256}`：只记录 `provided | not_provided` 和输入字节 SHA-256，不记录输入路径或原始证据；
- `provenance`：对象，至少含 `mode`；按模式记录本轮 build/serve、commit、开始时间或静态目录来源；`result_hash` 是排除时间字段后的稳定结果哈希，用于复跑比较。

不得把 secret 值、原始上传路径内的用户内容或环境变量片段放进 scope。

### `coverage`

至少包含：

```json
{
  "target_total": 0,
  "verified_total": 0,
  "gap_total": 0,
  "complete": false,
  "by_source": {},
  "by_route_kind": {},
  "gaps": [],
  "confirmed_counts": {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
}
```

- `target_total` 是实际 sitemap、routes file、框架公开路由和已注册内容的去重并集；已注册但不在 sitemap 的内容仍须纳入。
- `verified_total` 只计算取得本轮 HTTP 或显式 current-run rendered 证据的评分目标。
- API、auth、admin、error、redirect 和未注册内容可标“不评分”，但仍要进入分类覆盖。
- 动态 pattern 若被受信任的具体路由覆盖，可标 `classified` 并记录 `matched_routes`；否则必须进入 gap。
- 每个 `gaps[]` 对象至少包含 `route`、`reason` 和 `evidence_needed`；可附加 `source`、`path_or_url`。
- `complete` 只有在所有应评分目标已验证、所有非评分目标已分类时为 true。
- `confirmed_counts` 只统计 `status=Confirmed`；Candidate/Unknown 不进入 P0–P2 headline。

### `routes[]`

每条路由至少包含：

- `route`、`route_kind`；
- `index_intent`、`intent_source`、`priority`、`keywords`；
- `sources`：sitemap/routes file/framework/registry 中的一个或多个；
- `scored` 与不评分原因；
- `runtime_reachable`、`status_code`、`final_url`；
- `indexability`、`evidence_kind`、`path_or_url`、`provenance`；
- `coverage_status: verified | gap | classified`。

建议 `route_kind` 使用 `public | metadata | api | auth | admin | error | redirect | unregistered | unknown`。`indexability` 使用 `indexable | noindex | blocked | redirect | error | unknown`。

### `link_analysis`

固定包含：

```json
{
  "status": "not_run",
  "reason": "runtime_required",
  "candidate_domain_total": 0,
  "selected_domain_total": 0,
  "skipped_domain_total": 0,
  "verified_page_total": 0,
  "reciprocal_domain_total": 0,
  "targets": [],
  "gaps": []
}
```

- `status` 只使用 `not_run | complete | partial`。source-only、rendered、显式 `off` 或缺少 `--domain` 时为 `not_run` 并记录原因。
- `targets[]` 按最终站外主机去重，记录有限的正向链接样本、实际检查 URL、`reverse_status`、有限的反向链接样本和客观风险信号；不得保存完整第三方页面正文。
- `reverse_status` 使用 `reverse_link_observed | not_observed_on_checked_pages | unknown`。“未观察到”只描述已检查的目标页和首页，不能代表整个域名没有回链。
- `gaps[]` 记录请求失败、非 HTML、截断、安全拒绝和预算跳过。互链 gap 只影响 `link_analysis.status`，不得改变主站 `coverage.complete`。
- 普通互链只进入 `targets[]`。只有满足 rubric 组合条件时才生成 `RECIPROCAL_LINK_NETWORK_PATTERN` finding；跨路由 finding 使用 `route: null` 并增加 `affected_routes`、`affected_hosts`。

### `findings[]`

每条 finding 必须包含：

| 字段 | 允许值/说明 |
|---|---|
| `code` | 稳定规则 ID |
| `status` | `Confirmed | Candidate | Unknown` |
| `impact` | `P0 | P1 | P2 | P3` |
| `route` | URL path；无法映射时为 `null` |
| `route_kind` | 与 routes 相同 |
| `index_intent` | `index | noindex | unknown` |
| `indexability` | `indexable | noindex | blocked | redirect | error | unknown` |
| `runtime_reachable` | `true | false | null` |
| `status_code` | HTTP code 或 `null` |
| `evidence_kind` | `http | current_rendered | repo_fact | source_heuristic | read_state | parse_state` |
| `path_or_url` | 公开 URL 或安全的仓库相对路径 |
| `provenance` | 对象，至少包含 `mode` |

还应包含简短的 `evidence` 和 `recommendation`。`provenance` 按证据增加 `paths`、`content_hash`、`source_commit`、`build_started_at` 等字段，但不能包含私密内容。证据只写证明规则所需的最小片段，不复制 secret、环境变量、日志、数据库或原始用户数据。

## Evidence gate

- `Confirmed`：本轮 HTTP/current-rendered 响应直接证明，或确定性仓库事实可复现；“没有搜到”不是确定性事实。
- `Candidate`：源码正则、静态组件模式、未确认 registry 映射或需人工解释的文案。
- `Unknown`：读取失败、截断、无法解析、路由/意图无法映射或当前没有页面覆盖。
- 同一问题按 `route + code + content_hash` 去重，不能因 `.next`、standalone、OpenNext 或重复文件复制计数。
- Next.js 既有构建目录永远不能成为 evidence；静态 `--rendered-root` 必须有 current-run provenance。
- 连续运行比较 `scope.provenance.result_hash`；时间、输出路径和可能含构建 nonce 的 runtime/current-rendered 原始正文哈希不参与，已提取语义字段、assessment 内容及其 SHA-256 仍参与。
- 互链 `Confirmed` 只确认当前双方 HTTP 页面呈现的可观察链接模式，不确认站点所有权、付费关系、主题相关性或操纵排名意图。

## AdSense 对象

```json
{
  "enabled": false,
  "status": "N/A",
  "requirement_total": 73,
  "reported_total": 0,
  "missing_ids": [],
  "status_counts": {"Pass": 0, "Fail": 0, "Unknown": 0, "N/A": 0},
  "items": [],
  "article_count": 0,
  "complete": false,
  "conclusion": null,
  "readiness": null,
  "remediation_order": []
}
```

- 每个 ADS ID 只能为 `Pass / Fail / Unknown / N/A`，不存在 `warn`。
- 每项包含 `evidence`、`evidence_kind`、`path_or_url`、`evidence_ref`、`provenance`、`next_action`、`effort` 和 `applicability_reason`。`effort` 只使用 `S / M / L / Unknown / N/A`。
- `Pass/Fail` 需要非占位直接证据、有效 provenance，以及相应公开 URL、仓库相对路径或不透明 evidence ref；`coverage_gap` 不能冒充证据。
- `Unknown` 必须说明缺口和下一步；`N/A` 必须说明不适用理由。没有覆盖就是 `Unknown`。
- 页面数、文章数、必备页和内容质量只按已验证 URL 统计，源码文件数不能冒充页面数。
- 73 个 ID 未全部报告、存在 coverage gap，或任一项为 `Unknown` 时，`complete` 为 false，`conclusion` 与 `readiness` 均为 `null`。
- coverage 完整且不存在 `Unknown` 时：存在 Blocker `Fail` 为 `NOT_READY`；仅有 High/Medium `Fail` 为 `READY_AFTER_FIXES`；全部 `Pass/N/A` 为 `READY`。
- `conclusion` 是兼容字段：完整且有 `Fail` 为 `Fail`，完整且无 `Fail` 为 `Pass`，否则为 `null`。
- `remediation_order` 只列 `Fail`，按 `Blocker > High > Medium`、同级 `S > M > L`、最后 ADS ID 排序。

### Assessment 输入

```json
{
  "schema_version": 1,
  "target_domain": "https://example.com",
  "items": [
    {
      "id": "ADS-ELIG-01",
      "status": "Unknown",
      "evidence": "当前没有账户持有人年龄证据。",
      "evidence_kind": "coverage_gap",
      "path_or_url": null,
      "evidence_ref": null,
      "provenance": {"mode": "coverage-gap"},
      "next_action": "由账户持有人确认资格并提供不透明证据编号。",
      "effort": "Unknown",
      "applicability_reason": null
    }
  ]
}
```

实际输入必须包含全部 73 项且每个 ID 恰好一次。目标域名必须与最终报告 `scope.domain` 一致。assessment 文件自动从源码扫描中排除；授权原件、后台截图、个人信息、密钥和本地绝对路径不得进入输入或报告。

使用 `scripts/adsense_report_validator.py --check-assessments` 校验输入，再用 `--check-report` 重算最终报告的计数、`complete`、`conclusion`、`readiness` 和 `remediation_order`。校验器保证结构与派生结果自洽，不证明证据陈述真实。

## Markdown 汇报顺序

1. scope 与 coverage；
2. 互链验证覆盖与证据；
3. Confirmed P0–P2；
4. Candidate 与 Unknown；
5. 路由/关键词覆盖；
6. 条件 AdSense completeness；
7. 最小修复与验证方法。

coverage 不完整时，结论必须写明“未完成目标路由验证”，禁止写“未发现 SEO 问题”。
