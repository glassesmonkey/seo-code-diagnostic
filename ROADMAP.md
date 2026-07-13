# ROADMAP

## 当前阶段

两阶段可信度重构：阶段 0（治理边界）和阶段 1（source-only 可信度）完成，阶段 2（URL-first 运行时验证）进行中。

## 已完成

- 建立源码仓库、安装副本和 Exact-Statement 只读验收样本之间的边界。
- 固定 URL-first、evidence gate、隐私硬排除、AdSense 73 项完整性和验证命令。
- 记录旧扫描器基准：Exact-Statement 为 `P0=6 / P1=12 / P2=13`，其中 26/31 条 P0-P2 来自 `.next/.open-next`；其余 5 条也没有线上确认依据。
- 完成 schema v2 基础、source-only evidence gate、结构化 coverage gap、对象化 provenance 和 Confirmed-only 汇总。
- 完成 allowlist、构建/报告/Agent/隐私硬排除、自输出隔离、读取/截断 Unknown 与安全证据脱敏。
- 修复 Next metadata route、空 alt/spread props、`use client`、公开文案映射、routes-file 关键词映射和 AdSense 无覆盖 Unknown 语义。
- 增加 17 个标准库 CLI 行为测试；Exact-Statement source-only 验收为 `Confirmed P0-P2=0`，已知五类误报消失。

## 进行中

- 合并 sitemap、routes file、框架路由和注册内容，建立 URL-first coverage。

## 待办

### 阶段 2：URL-first 运行时验证

- 合并 sitemap、routes file、框架路由和注册内容，建立 coverage。
- 增加 Next.js route group、locale、catch-all、metadata 继承和路由分类适配。
- 验证 HTTP、redirect、robots、TDK、H1、canonical、正文、内链、JSON-LD 和 soft-404 sentinel。
- 完成 Exact-Statement fresh build 的 27 个 sitemap URL 验收。

### 文档与交付

- 将主 `SKILL.md` 收敛为五步流程，建立框架适配和报告协议 reference。
- 完成两阶段中文 commit；验证后同步安装副本并做内容 diff。

## 阻塞

- 无。

## 最近验证

1. 2026-07-13：fresh clone 位于 `main`，起点 commit 为 `3eda8b2`，工作区 clean。
2. 2026-07-13：fresh clone 与当前安装副本内容一致（排除 `.git` 和 `__pycache__`）。
3. 2026-07-13：Exact-Statement 基准与路由真相采用只读检查获得，项目 Git 状态保持 clean。
4. 2026-07-13：`python3 -m unittest discover -s tests -v` 为 17/17 通过，`py_compile` 与 `git diff --check` 通过。
5. 2026-07-13：阶段 1 fixture 端到端扫描为 `Confirmed P0-P3=0`，无 URL 证据的 AdSense 73 项保持 Unknown。
6. 2026-07-13：Exact-Statement source-only 扫描不读取 `.next/.open-next/.source/reports/output/.env*`，`Confirmed P0-P2=0`。
7. 2026-07-13：Exact source-only 连续两次规范化结果哈希一致，第二次没有扫描第一次报告。
8. 2026-07-13：隔离且不含 `.env*/.dev.vars` 的 Exact 验收 clone 在 commit `b23660f` fresh build 成功；原项目与 clone Git 状态 clean。
