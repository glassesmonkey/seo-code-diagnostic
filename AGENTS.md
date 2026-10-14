# SEO Code Diagnostic 开发约定

## 边界

- 本仓库是可提交源码的唯一事实源；`~/.agents/skills/seo-code-diagnostic` 只是安装副本，只能在本仓库全部验证通过后做机械同步。Codex、Claude、Grok、Hermes 都符号链接到该目录。
- `/Users/gc/mydisk2/outsea/Exact-Statement` 是只读验收样本。不得修改其源码、配置、依赖、数据库或 Git 状态；构建只能产生项目已忽略的产物。
- 不在本任务中 push、发布、部署、修改 Cloudflare、修改 `.env*` 或引入全局依赖。

## 诊断契约

- 默认采用 URL-first：路由覆盖和 HTTP/本轮静态产物证据优先于源码正则。
- 报告主表按 F1–F10 组织。实战口径只从 `gefei-ranking-practice.md` 取值；与 Zyppy 冲突时以哥飞为准。
- 所有结论必须经过 evidence gate。源码启发式最多是 `Candidate`；读取失败、截断、无法映射或缺少运行时覆盖时是 `Unknown`；只有可复现的页面或仓库事实才能是 `Confirmed`。
- P0-P2 汇总只统计 `Confirmed`。因素 `Fail` 也只统计 Confirmed。覆盖不完整时必须列出 coverage gap，禁止输出“未发现问题”。
- `diagnostic-rubric.md` 是严重度唯一事实源；其他文档只能引用，不得复制另一套阈值。
- 不编造 GSC/Ahrefs/CTR/外链/品牌词。F2 及 F5/F6/F7/F9 线上强度默认 `Unknown`，但 F2 必须写新词新站/老词新站口径。已映射词的 Meta 相关性进 F1。品牌域非关键词域不 Fail。
- 本 skill 不做 AdSense 审核。申请就绪度使用独立 skill `adsense-site-auditor`，不要在本仓库补 ADS 清单或 readiness 结论。

## 扫描与隐私

- 扫描公开框架源码和已注册用户内容的 allowlist，不把整个仓库当作可见页面。
- 永久排除构建产物、历史报告、Agent 配置、`.env*`、`.dev.vars`、日志、数据库、原始上传和用户数据；报告不得包含密钥或原始用户数据片段。
- Next.js 不读取既有 `.next` 或 `.open-next`。运行时确认必须来自本轮成功 build 后启动的 HTTP 服务。
- 静态框架只有显式传入本轮生成的 `--rendered-root` 才能作为渲染证据。
- 输出默认位于扫描根目录之外，并始终排除自身输出。连续运行必须稳定，第二次不得扫描第一次报告。

## 开发流程

- 使用 Python 标准库，不新增依赖。
- 按可观察行为做纵向 TDD：一个失败测试、最小实现、测试转绿，再进入下一项。
- 只修改本次重构直接涉及的文件；保留现有 reference，通过改写和 context pointer 消除重复。
- 每个已验证阶段更新 `ROADMAP.md`，只把实际完成且通过验证的事项放入“已完成”；“最近验证”最多保留 10 条。
- 独立、范围清晰且验证通过的阶段用中文 commit 保存，前缀遵循 `docs:`、`fix:`、`feat:`、`refactor:` 或 `chore:`。

## 必跑验证

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/seo_code_audit.py
git diff --check
```

阶段验收还必须包含：端到端 fixture 扫描、Exact-Statement source-only 扫描、fresh local runtime 扫描、连续运行一致性检查，以及源码与安装副本内容 diff。无法完成的验证必须在 `ROADMAP.md` 标为阻塞或待确认。
