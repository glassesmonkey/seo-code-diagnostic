# Ahrefs SEO 学习笔记（用于本 skill 的诊断规则）

Last reviewed: 2026-09-13

这些笔记是对 Ahrefs 官方 SEO 教程/指南的诊断化整理，目的是让 Codex 在看代码时有统一判断标准。不要把这些笔记当作排名保证；它们只提供 on-page、technical、content、internal link 的审计框架。

与 `zyppy-2026-ranking-factors.md` 冲突时：以 SKILL 的 F1–F10 主骨架 + 不编造线上指标为准。description 只进 F5 CTR；密度不是目标；F8 是 table stakes。这些笔记不再当诊断目录。

## 参考来源

- Ahrefs, “A Comprehensive On-Page SEO Checklist for 2026”  
  https://ahrefs.com/blog/on-page-seo-checklist/
- Ahrefs, “Internal Links for SEO: An Actionable Guide”  
  https://ahrefs.com/blog/internal-links-for-seo/
- Ahrefs, “The Beginner’s Guide to Technical SEO”  
  https://ahrefs.com/seo/technical-seo
- Ahrefs, “JavaScript SEO Issues & Best Practices”  
  https://ahrefs.com/blog/javascript-seo/
- Ahrefs, “Canonical Tags Explained: Why They Matter For SEO”  
  https://ahrefs.com/blog/canonical-tags/
- Ahrefs, “Content Pillars: What They Are & How to Build Them for SEO”  
  https://ahrefs.com/blog/content-pillars/
- Ahrefs, “The Ultimate 82-Point Checklist for SEO & AI Visibility”  
  https://ahrefs.com/blog/seo-ai-search-checklist/
- Ahrefs, “SEO for Startups: How to Grow Search Visibility on a Budget”  
  https://ahrefs.com/blog/seo-for-startups/
- Ahrefs, “Automated SEO: What It Is and How It Works in 2026”  
  https://ahrefs.com/blog/automated-seo/
- Ahrefs, “How to Use Keywords for SEO: The Complete Beginner’s Guide”  
  https://ahrefs.com/blog/how-to-use-keywords-for-seo/
- Ahrefs, “SEO Writing: 8 Steps to Create Search-Optimized Content”  
  https://ahrefs.com/blog/seo-writing/
- Ahrefs, “Content Optimization: The Complete Guide”  
  https://ahrefs.com/blog/content-optimization/

## 对代码诊断最有用的 Ahrefs 结论

### 1. On-page SEO 不是“塞关键词”，而是让页面满足搜索意图

诊断代码时，不只看页面有没有 target keyword，还要判断：

- title、H1、首屏内容是否清楚承诺了搜索者要解决的问题；
- H2/H3 是否覆盖该关键词背后的主要子问题；
- 页面是否一开始就给出用户需要的信息，而不是大段空泛营销文案；
- FAQ、步骤、比较、表格、示例是否帮助用户快速理解；
- 页面是否有足够独特信息，而不是和竞品模板化重复。

### 2. Title 相关性、H1 是基础；meta description 主要是 CTR

代码审计时应检查：

- 每个核心页面都有唯一 title；
- title 里自然表达主关键词或主意图（相关性，不是密度）；
- description 扩展 title，说明具体价值，利于点击；**不要把它当成已被证明的排名因子**，缺了按 P2/P3 CTR 处理；
- 页面有一个 H1，通常表达页面标题或主搜索意图；
- H2/H3 用来建立清晰信息层级，而不是做视觉样式。

### 3. URL slug 和 canonical 要统一

检查项：

- URL slug 简短、描述性强，通常可包含目标关键词；
- 避免 URL 里带过时年份、重复词、无意义参数；
- canonical 使用绝对 URL；
- 每页只设置一个 canonical；
- canonical 指向 HTTPS 和正确域名；
- sitemap 只包含希望被索引的 canonical URL；
- internal links 尽量直接链接 canonical URL，不要链接到参数 URL 或跳转 URL。

### 4. Technical SEO 的底层任务是让页面可发现、可抓取、可理解、可索引

这是 table stakes：坏的技术实现会输，好的技术实现不会把平庸内容抬上去。不要把 CWV 写成主增长项。

代码审计要优先发现阻断问题：

- robots.txt 是否误封；
- meta robots 是否误设 noindex/nofollow；
- sitemap 是否缺失或列出错误 URL；
- 重要页面是否能返回实际 HTML；
- JS-heavy 页面是否依赖客户端渲染才出现核心内容；
- 动态路由是否为每个页面生成唯一 metadata；
- 重要资源是否可访问；
- canonical 是否冲突。

### 5. JavaScript SEO：JS 不是坏事，但要确认爬虫能读到核心内容

对 React/Vite SPA、Next.js Client Component、Vue SPA 等尤其要检查：

- 查看源代码或构建产物能否看到正文、H1/H2、title、description、canonical；
- 首页和核心落地页不要只返回空 root div；
- 能 SSG/SSR 的页面优先 SSG/SSR；
- 动态 metadata 不要只在客户端设置；
- canonical 不要在 HTML 里一个值，JS 渲染后又替换成另一个值。

### 6. Internal links 是页面权重和主题理解的关键杠杆

代码诊断要输出内链建议，而不是只说“增加内链”：

- 哪个页面提到了哪个目标词；
- 应用什么锚文本；
- 应该链接到哪个目标页面；
- 这个链接属于上级、下级、同级相关还是支柱页回流；
- 是否存在孤儿页；
- 是否有重要页面只在 sitemap 出现但没有站内入口。

### 7. Content pillars / topic clusters 适合站点结构诊断

把关键词库映射为层级：

- 支柱页：主词、上位概念、高搜索量/高竞争；
- cluster pages：二级/三级长尾词、具体场景、具体问题；
- spoke pages 要链接回 pillar page；
- pillar page 要链接到重要 spoke pages；
- 站点导航、面包屑、页脚、相关内容模块应支撑这个层级。

### 8. SEO + AI 可见性要求内容更结构化、可引用、可信

诊断时检查：

- 是否有清晰段落、列表、表格、FAQ；
- 每节是否只回答一个问题；
- 是否定义关键术语；
- 是否有作者/团队/品牌信任信号；
- 是否有原创数据、案例、专家引用或真实证言；
- 表格和关键数据是否是 HTML 文本而不是图片；
- schema 是否与页面真实内容一致。

### 9. 自动化 SEO 应该是链式流程，不是一次性让 AI 写文章

当用户要求“让 Codex 自动修 SEO”时，用这个链条：

1. 关键词/页面映射；
2. SERP/search intent 分析（需要用户提供数据或允许联网）；
3. 内容 gap 分析；
4. 页面大纲和模块规划；
5. 文案改写；
6. title（相关性 + CTR）、canonical/schema/internal links 实现；description 按 CTR 处理；
7. 构建后查看 HTML；
8. 发布后若用户提供 GSC/Ahrefs，观察收录、点击质量、意图匹配、内链，以及外链是否来自受信任、主题相关、有真实访问的页面；没有数据就标 Unknown，不要编造指标。

