# ROADMAP

## 当前阶段

两阶段可信度重构：阶段 0（治理边界）完成，阶段 1（source-only 可信度）待开始。

## 已完成

- 建立源码仓库、安装副本和 Exact-Statement 只读验收样本之间的边界。
- 固定 URL-first、evidence gate、隐私硬排除、AdSense 73 项完整性和验证命令。
- 记录旧扫描器基准：Exact-Statement 为 `P0=6 / P1=12 / P2=13`，其中 26/31 条 P0-P2 来自 `.next/.open-next`；其余 5 条也没有线上确认依据。

## 进行中

- 无。

## 待办

### 阶段 1：source-only 可信度

- schema v2、范围清单、隐私排除、自污染防护、读取状态和证据去重。
- 修复 Next metadata route 识别、JSX alt、文案映射、关键词映射和 AdSense Unknown 语义。
- 用标准库 `unittest` 覆盖隔离、隐私、去重、alt、文案、截断和 AdSense。

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
