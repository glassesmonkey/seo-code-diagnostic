# ROADMAP

## 当前阶段

AdSense evidence validator、readiness 聚合和安装副本同步已完成；当前无未完成阶段。

## 已完成

- 建立源码仓库、安装副本和 Exact-Statement 只读验收样本之间的边界。
- 固定 URL-first、evidence gate、隐私硬排除、AdSense 73 项完整性和验证命令。
- 记录旧扫描器基准：Exact-Statement 为 `P0=6 / P1=12 / P2=13`，其中 26/31 条 P0-P2 来自 `.next/.open-next`；其余 5 条也没有线上确认依据。
- 完成 schema v2 基础、source-only evidence gate、结构化 coverage gap、对象化 provenance 和 Confirmed-only 汇总。
- 完成 allowlist、构建/报告/Agent/隐私硬排除、自输出隔离、读取/截断 Unknown 与安全证据脱敏。
- 修复 Next metadata route、空 alt/spread props、`use client`、公开文案映射、routes-file 关键词映射和 AdSense 无覆盖 Unknown 语义。
- 增加 17 个标准库 CLI 行为测试；Exact-Statement source-only 验收为 `Confirmed P0-P2=0`，已知五类误报消失。
- 完成 URL-first 路由并集、Next.js 路由/metadata/locale 适配、静态 rendered provenance、HTTP/on-page/robots/JSON-LD/soft-404 验证。
- 完成 routes-file 证据注入防护、越界 symlink/非法 URL 隔离、动态路由分类、注册内容边界和稳定结果哈希。
- 完成 AdSense 73 项正式清单契约；文章数只统计已验证的注册文章，coverage 不完整时结论保持 `null`。
- Exact-Statement fresh runtime 验收：27/27 sitemap URL 返回 200 并进入 coverage，4 篇文章计数正确，确认 1 个 P0 index/noindex 冲突和 1 个 P1 soft 404。
- 已将验证后的源码机械同步到 `~/.codex/skills/seo-code-diagnostic`；逐文件 diff 为空，安装副本 42/42 测试通过。
- 完成受控站外互链验证：限制公开 HTTP(S) 目标、逐跳校验重定向、隔离第三方 coverage gap，并只对至少 3 个双方 follow 主机组成的模板/伙伴页模式生成 P2。
- 增加独立 AdSense 校验器：动态读取 73 个 ADS ID，生成完整模板，并校验状态、直接证据、provenance、Unknown 下一步、N/A 理由、目标域名和敏感信息边界。
- 扫描器支持 `--adsense-assessments`，自动排除输入文件，只记录 SHA-256，并从明细重算 `complete`、兼容 `conclusion`、四态 `readiness` 和按 severity/effort 排序的修复顺序。
- 完成 Google 官方 AdSense 文档 2026-07-17 刷新核对；没有发现需要调整现有 73 项 registry 的明确变化，也未引入非官方冷却期或主观评分。
- 更新报告契约、Skill 和 README，固定 template → assessment 校验 → 扫描合并 → 最终报告校验流程，并声明校验器不证明证据陈述真实。

## 进行中

- 无。

## 待办

- 无。

## 阻塞

- 无。

## 最近验证

1. 2026-07-17：源码 67/67 单元测试、两个脚本的 `py_compile`、validator selftest 与 `git diff --check` 通过。
2. 2026-07-17：Exact-Statement fresh build 成功；source-only 与 fresh runtime 扫描完成，runtime 为 187 个目标、81 个已验证、7 个动态路由 gap，AdSense 最终报告校验通过。
3. 2026-07-17：Exact runtime 连续两次 `result_hash` 均为 `6b237340e4d1e9a581dc2877279bf925dcaa1f3b2dc35600ef5d726f14d9ba74`；样本 Git 状态保持 clean。
4. 2026-07-17：安装副本与源码逐文件 diff 为空，安装副本 67/67 测试通过。
5. 2026-07-17：互链 Phase 3 的 54/54 单元测试、`py_compile` 与 `git diff --check` 通过。
6. 2026-07-13：Exact-Statement source-only 扫描不读取 `.next/.open-next/.source/reports/output/.env*`，`Confirmed P0-P2=0`。
7. 2026-07-13：隔离且不含 `.env*/.dev.vars` 的 Exact 验收 clone 在 commit `b23660f` fresh build 成功；原项目与 clone Git 状态 clean。
8. 2026-07-13：Exact fresh runtime 的 27/27 sitemap URL 均为 200；连续两次 `result_hash` 均为 `1a411abb8d2197495c74e38ec56e236333a32a1d246bf8014de1cc2d6d8be87d`，原项目与验收 clone 保持 clean。
