# Report Contract v2

本文件定义扫描器与人工报告共享的 schema、coverage 和 evidence gate。字段可以扩展，不能删除或改义；其他 reference 的旧输出示例与本文件冲突时，以本文件为准。

## CLI 契约

保留：`--root`、`--domain`、`--keywords`、`--adsense`、`--out`。

新增：

- `--base-url URL`：对本轮本地服务或用户指定站点取 HTTP 证据；
- `--routes-file PATH`：显式页面意图和关键词映射；
- `--rendered-root PATH`：只接收本轮生成的静态 HTML 目录；
- `--exclude GLOB`：可重复，追加到硬排除列表。

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
  "adsense": {}
}
```

这五个对象/数组始终存在；未启用 AdSense 时也保留 `adsense.enabled: false`。

### `scope`

至少包含：

- `root`、`domain`、`base_url`、`rendered_root`；
- `framework`、`mode: source-only | runtime | rendered`；
- `source_commit`、`started_at`；
- `route_sources`、`excludes`、`output_paths`；
- `unmapped_keywords`；
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
- 连续运行比较 `scope.provenance.result_hash`；`generated_at` 和 `started_at` 不参与稳定哈希。

## AdSense 对象

```json
{
  "enabled": false,
  "requirement_total": 73,
  "reported_total": 0,
  "missing_ids": [],
  "status_counts": {"Pass": 0, "Fail": 0, "Unknown": 0, "N/A": 0},
  "items": [],
  "article_count": 0,
  "complete": false,
  "conclusion": null
}
```

- 每个 ADS ID 只能为 `Pass / Fail / Unknown / N/A`，不存在 `warn`。
- `Pass` 需要该 ID 所要求的直接证据；没有覆盖就是 `Unknown`。
- 页面数、文章数、必备页和内容质量只按已验证 URL 统计，源码文件数不能冒充页面数。
- 73 个 ID 未全部报告、存在 coverage gap，或关键后台/授权/政策证据为 Unknown 时，`complete` 为 false、`conclusion` 保持 `null`，不得输出 `Ready` 或 `Ready after fixes`。

## Markdown 汇报顺序

1. scope 与 coverage；
2. Confirmed P0–P2；
3. Candidate 与 Unknown；
4. 路由/关键词覆盖；
5. 条件 AdSense completeness；
6. 最小修复与验证方法。

coverage 不完整时，结论必须写明“未完成目标路由验证”，禁止写“未发现 SEO 问题”。
