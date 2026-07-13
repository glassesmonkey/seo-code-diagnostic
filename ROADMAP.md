# ROADMAP

## 当前阶段

两阶段可信度重构、skill 文档收敛和安装副本同步全部完成。

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

## 进行中

- 无。

## 待办

- 无（本轮计划全部完成）。

## 阻塞

- 无。

## 最近验证

1. 2026-07-13：fresh clone 与初始安装副本内容一致（排除 `.git` 和 `__pycache__`）。
2. 2026-07-13：Exact-Statement 基准与路由真相采用只读检查获得，项目 Git 状态保持 clean。
3. 2026-07-13：阶段 1 的 17/17 测试、`py_compile` 与 `git diff --check` 通过。
4. 2026-07-13：阶段 1 fixture 端到端扫描为 `Confirmed P0-P3=0`，无 URL 证据的 AdSense 73 项保持 Unknown。
5. 2026-07-13：Exact-Statement source-only 扫描不读取 `.next/.open-next/.source/reports/output/.env*`，`Confirmed P0-P2=0`。
6. 2026-07-13：Exact source-only 连续两次规范化结果哈希一致，第二次没有扫描第一次报告。
7. 2026-07-13：隔离且不含 `.env*/.dev.vars` 的 Exact 验收 clone 在 commit `b23660f` fresh build 成功；原项目与 clone Git 状态 clean。
8. 2026-07-13：最终 `python3 -m unittest discover -s tests -v` 为 42/42 通过，`py_compile` 与 `git diff --check` 通过。
9. 2026-07-13：Exact fresh runtime 的 27/27 sitemap URL 均为 200；连续两次 `result_hash` 均为 `1a411abb8d2197495c74e38ec56e236333a32a1d246bf8014de1cc2d6d8be87d`，原项目与验收 clone 保持 clean。
10. 2026-07-13：安装副本与源码逐文件 diff 为空；安装副本 42/42 测试、`py_compile` 和 CLI help 验证通过。
