# SEO Code Diagnostic

一个 URL-first、evidence-gated 的 SEO 诊断 skill。它把路由覆盖、当前 HTTP/静态渲染证据和源码线索分开，避免把构建产物或启发式命中误报成线上问题；运行时模式还会受控验证站外互链。上线前另有一道 GEO 闸门：只走这次要公开的页面，以普通用户打开、点链接、读文案。扫描器通过不等于可以上线。

报告主表按 F1–F10 组织。实战口径以哥飞为准（TDH + 密度看聚焦、一个关键词组一个页面、举全站之力、新词新站可无链 / 老词新站必须有链）。Zyppy 调研只校准排序。没有 GSC/外链表/品牌数据时，F2/F5/F6/F7/F9 的线上信号必须 `Unknown`，但 F2 仍要写出场景口径。关键词域名是 F1 加分，品牌域不是关键词域不 Fail。

## 安装

安装副本可放到以下任意位置：

- 仓库级：`<repo>/.codex/skills/seo-code-diagnostic/`
- 用户级：`~/.agents/skills/seo-code-diagnostic/`

如果从 GitHub 安装，先保留独立源码 clone，再同步安装副本：

```bash
git clone https://github.com/glassesmonkey/seo-code-diagnostic.git ~/seo-code-diagnostic-src
rsync -a --exclude .git ~/seo-code-diagnostic-src/ ~/.agents/skills/seo-code-diagnostic/
```

GitHub clone 是可提交源码；`~/.agents/skills/seo-code-diagnostic` 是安装副本。Codex、Claude、Grok、Hermes 都符号链接到这个目录。修改和验证应在源码 clone 中完成，再机械同步到安装副本。

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

上线前 GEO 走查：

```text
Use the $seo-code-diagnostic skill before this site goes live.
Launch pages: /, /tool, /pricing
Open each page as a visitor on desktop and mobile, click every link, read every visible line, and fix what is unfinished.
Do not call it ready from the ranking table alone. A first version of 3–5 finished pages is a valid launch set.
```

AdSense 申请审核不在本 skill，改用 `adsense-site-auditor`。

## 包含内容

- `SKILL.md`：URL-first 六步流程；报告按 F1–F10 组织，上线结论另看 GEO 闸门。
- `references/geo-launch-gate.md`：GEO 上线闸门。只检查这次要公开的页面，不并进 F1–F10。
- `scripts/seo_code_audit.py`：源码与 URL/渲染证据扫描器，输出 schema v2 JSON/Markdown 和 Top 10 因素表。
- `references/gefei-ranking-practice.md`：哥飞实战口径（与 Zyppy 冲突时以本文件为准）。
- `references/zyppy-2026-ranking-factors.md`：调研排序校准。
- `references/ahrefs-learning-notes.md`：Ahrefs 官方教程的诊断化学习笔记（与 Zyppy 冲突时以证据门为准）。
- `references/seo-principles.md`：页面类型、搜索意图和内容价值判断。
- `references/diagnostic-rubric.md`：P0–P3 严重度唯一事实源，含规则→因素映射。
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

同时提供 `--base-url` 和 `--domain` 时，`--reciprocal-links auto` 默认检查未限定站外链接的目标页和对方首页。每个站外请求都会暴露扫描 IP 与工具 User-Agent；如需保持纯站内验证，显式添加：

```bash
--reciprocal-links off
```

互链本身不会自动成为问题。只有至少 3 个不同站外主机形成已确认的双方 follow 链接，并同时出现全站模板重复或集中伙伴页模式，才会生成 `RECIPROCAL_LINK_NETWORK_PATTERN` P2。

静态框架可传入本轮生成的目录：

```bash
python scripts/seo_code_audit.py \
  --root . \
  --rendered-root ./dist \
  --out ../seo-audit
```

Next.js 不读取既有 `.next`/`.open-next`；应在本轮 build 成功后启动本地服务，再使用 `--base-url`。

脚本会生成：

- `seo-audit.json`
- `seo-audit.md`

每份 JSON 固定包含 `scope`、`coverage`、`routes`、`findings`、`link_analysis`。finding 的证据状态为：

- `Confirmed`：当前 URL 响应或可复现仓库事实已证明；
- `Candidate`：源码启发式或仍需映射/解释的线索；
- `Unknown`：覆盖、读取或解析证据不足。

P0–P2 汇总只统计 `Confirmed`。coverage 不完整时不能得出“未发现问题”。第三方请求失败只进入 `link_analysis.gaps`，不会污染主站 coverage。报告不再包含 AdSense 对象。

复跑稳定性使用 `scope.provenance.result_hash` 比较；生成时间不参与该哈希。

## 开发验证

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/seo_code_audit.py
git diff --check
```
