# SEO Code Diagnostic

一个 URL-first、evidence-gated 的 Codex SEO 诊断 skill。它把路由覆盖、当前 HTTP/静态渲染证据和源码线索分开，避免把构建产物或启发式命中误报成线上问题。

## 安装

安装副本可放到以下任意位置：

- 仓库级：`<repo>/.codex/skills/seo-code-diagnostic/`
- 用户级：`~/.codex/skills/seo-code-diagnostic/`

如果从 GitHub 安装，先保留独立源码 clone，再同步安装副本：

```bash
git clone https://github.com/glassesmonkey/seo-code-diagnostic.git ~/seo-code-diagnostic-src
rsync -a --exclude .git ~/seo-code-diagnostic-src/ ~/.codex/skills/seo-code-diagnostic/
```

GitHub clone 是可提交源码；`~/.codex/skills/seo-code-diagnostic` 是安装副本。修改和验证应在源码 clone 中完成，再机械同步到安装副本。

在 Codex 中可显式调用 `$seo-code-diagnostic`，也可在 SEO 代码审计任务中自动触发。

## 推荐提示词

```text
Use the $seo-code-diagnostic skill to audit this website codebase.
Target domain: https://example.com
Primary keyword: background remover
Secondary keywords: remove background, transparent background, AI background remover
Please produce a Chinese SEO diagnosis and suggest minimal code fixes.
Use current-run URL evidence where available and list every coverage gap.
```

AdSense 审核诊断：

```text
Use the $seo-code-diagnostic skill to audit this game/tool site for AdSense approval readiness.
Target domain: https://example.com
Primary keyword: suika game
The site was rejected for low value content. Produce a Chinese AdSense review diagnosis with prioritized fixes.
Cover every ADS-* requirement ID with Pass/Fail/Unknown/N/A, evidence, next action, and a Completeness Check.
```

## 包含内容

- `SKILL.md`：Codex 主要工作流和诊断规则。
- `scripts/seo_code_audit.py`：源码与 URL/渲染证据扫描器，输出 schema v2 JSON/Markdown。
- `references/ahrefs-learning-notes.md`：Ahrefs 官方教程的诊断化学习笔记。
- `references/adsense-requirements.md`：AdSense 官方来源驱动的 73 个 ADS ID 和证据要求。
- `references/adsense-review-diagnostic.md`：AdSense 审核、low value content 和游戏/工具站薄壳风险诊断。
- `references/seo-principles.md`：页面类型、搜索意图和内容价值判断。
- `references/diagnostic-rubric.md`：P0–P3 严重度唯一事实源。
- `references/framework-adapters.md`：框架路由、metadata 和渲染证据适配规则。
- `references/report-contract.md`：schema v2、coverage 和 evidence gate 协议。
- `agents/openai.yaml`：Codex UI 元信息。

## 扫描用法

source-only（源码命中最多是 `Candidate`）：

```bash
python scripts/seo_code_audit.py --root . --out ../seo-audit
```

URL-first（推荐）：

```bash
python scripts/seo_code_audit.py \
  --root . \
  --domain "https://example.com" \
  --base-url "http://127.0.0.1:3000" \
  --routes-file "seo-routes.json" \
  --keywords "unmapped keyword" \
  --exclude "private-content/**" \
  --out ../seo-audit
```

`--routes-file` 提供页面级 `index_intent`、`priority`、`keywords` 和 `intent_source`。`--keywords` 只保留为未映射词清单，不会应用到每个页面。

静态框架可传入本轮生成的目录：

```bash
python scripts/seo_code_audit.py \
  --root . \
  --rendered-root ./dist \
  --out ../seo-audit
```

Next.js 不读取既有 `.next`/`.open-next`；应在本轮 build 成功后启动本地服务，再使用 `--base-url`。

只有用户明确要求 AdSense 审核时才添加：

```bash
python scripts/seo_code_audit.py \
  --root . \
  --domain "https://example.com" \
  --base-url "http://127.0.0.1:3000" \
  --adsense \
  --out ../seo-audit
```

脚本会生成：

- `seo-audit.json`
- `seo-audit.md`

每份 JSON 固定包含 `scope`、`coverage`、`routes`、`findings`、`adsense`。finding 的证据状态为：

- `Confirmed`：当前 URL 响应或可复现仓库事实已证明；
- `Candidate`：源码启发式或仍需映射/解释的线索；
- `Unknown`：覆盖、读取或解析证据不足。

P0–P2 汇总只统计 `Confirmed`。coverage 不完整时不能得出“未发现问题”。AdSense 页面数、文章数和内容状态只按已验证 URL 计算；完整审核必须覆盖 73 个 ADS ID，且状态只能是 `Pass / Fail / Unknown / N/A`。

复跑稳定性使用 `scope.provenance.result_hash` 比较；生成时间不参与该哈希。

## 开发验证

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/seo_code_audit.py
git diff --check
```
