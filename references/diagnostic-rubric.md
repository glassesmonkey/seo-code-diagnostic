# SEO 代码诊断 Rubric

技术 SEO 是 table stakes：P0/部分 P1 是「会输」的阻断项，不是把平庸内容做上去的增长开关。meta description 按 CTR 杠杆（P2/P3），不是排名 P1。关键词密度只在异常高时标堆砌，不标「密度太低」。行为、品牌、外链质量没有用户数据时标 Unknown，见 `zyppy-2026-ranking-factors.md`。

## P0：必须优先修复

| 检查项 | 代码证据 | 典型修复 |
|---|---|---|
| 核心页面 noindex | `<meta name="robots" content="noindex">` | 去掉 noindex 或按页面类型条件化 |
| robots.txt 误封全站 | `User-agent: *` + `Disallow: /` | 生产环境允许核心页面抓取 |
| 纯 CSR 无正文 | 初始 HTML 只有 root div 和 script | SSR/SSG/prerender；把核心文案放进 HTML |
| canonical 错域名/死链 | canonical 指向 staging、localhost、旧域名、404 | 使用生产 HTTPS 绝对 URL |
| 动态页面无唯一 HTML | 所有动态页复用同一 title/H1/内容 | 基于 slug 数据生成唯一 metadata 和正文 |
| sitemap/robots 指向测试域 | sitemap URL 是 localhost/staging | 统一生产 canonical host |

## P1：高影响问题

| 检查项 | 代码证据 | 典型修复 |
|---|---|---|
| 缺 title | 无 `<title>` / metadata.title | 为每页生成唯一 title，表达主搜索意图/任务 |
| 缺 H1 或多个 H1 | `<h1>` 为 0 或多个 | 每页一个主 H1 |
| 缺 canonical | 无 rel canonical | 生成自引用 canonical |
| sitemap 缺失 | 无 sitemap 文件/路由 | 增加 sitemap，列 canonical URL |
| 重要页面孤儿 | sitemap 有但站内无链接 | 从首页/分类/相关页面加内链 |
| 全站复用 title/H1 | layout 里固定 title/H1 | 动态按页面生成（description 另按 CTR 看） |
| 页面明显答非所问 | 模块/页面类型与目标任务相反 | 按 Search Intent Match 改内容或拆页 |

缺 meta description **不是** P1。

## P2：中影响问题

| 检查项 | 代码证据 | 典型修复 |
|---|---|---|
| 缺 description（CTR） | 无 meta description | 写利于点击的摘要；**不是已被证明的排名因子** |
| 标题与意图偏离 | 正文在做 A，title 在说 B，或目标词在正文出现但 title 完全不表达该任务 | 先改 title 相关性，再改点击文案 |
| 内容薄 / 无信息增益 | 页面文本很少，或只有和竞品相同的套话 | 补充定义、步骤、场景、FAQ，以及一手数据/独特解释 |
| H2/H3 结构差 | 标题跳级或模块混乱 | 分门别类罗列用户问题和任务步骤 |
| 内链少 | 页面几乎没有内部链接 | 增加上下级和相关页链接（可控制杠杆） |
| 图片缺 alt | `<img>` 无 alt | 为重要图片写描述性 alt |
| 关键词未覆盖 | 目标词不在可见文本中 | 在 title/H1/首段/H2/FAQ 自然覆盖；不要补密度 |
| 关键词堆砌 | 密度异常高或同一短语机械重复 | 改成语义相关词和真实解释。不标「密度太低」 |
| FAQ 缺失 | 长落地页无 FAQ | 补充真实问题和原创回答 |

## P3：增强项

| 检查项 | 代码证据 | 典型修复 |
|---|---|---|
| title/description 不利于点击 | 过短、过长或空泛 | 改为更利于 SERP 点击的表达（CTR，不是排名旋钮） |
| OG/Twitter 不完整 | 缺 og:title/og:image | 增强分享预览 |
| schema 可增强 | 无 JSON-LD | 按页面类型加真实 schema |
| 图片尺寸/性能 | 无 width/height、未压缩 | 使用框架图片组件和压缩。CWV 不作为 P1 |
| robots 未声明 sitemap | robots.txt 无 Sitemap | 补充 sitemap 地址 |

## 页面类型专项

### AdSense 审核专项（游戏站 / 工具站优先）

核心问题：网站是否值得展示广告，还是像自动生成的低质套壳。

P0：

- 站点不可访问、核心页面 4xx/5xx；
- robots/noindex 阻止核心页面抓取或索引；
- 缺 Contact、Privacy Policy、Terms of Service 等审核信任基础；
- 明显侵权、成人、赌博、仇恨、暴力等政策红线；
- sitemap/canonical 指向错误域名，导致审核和收录信号混乱。

P1：

- 游戏页只有 iframe，缺原创介绍、玩法说明、FAQ 和相关内容；
- 工具页只有入口或营销口号，缺使用步骤、示例、限制、FAQ；
- 首页、分类页、核心页正文很薄，只是封面图、卡片或按钮；
- 整站视觉上像通用模板，没有与主打游戏/工具相关的风格；
- 大量页面空白、占位、重复或自动生成痕迹明显。

P2：

- 缺 Blog/Guides/Tutorials 内容区；
- 审核阶段原创文章少于 5 篇；
- 分类页缺文字说明和关键词分组；
- 长尾关键词没有页面映射；
- GSC 中 5-20 名、有展示但低点击的查询没有被优化；
- 内链没有把首页、分类页、游戏/工具页、文章串起来。

P3：

- 视觉 polish 可增强：配色、字体、图片、首屏状态更贴合主题；
- OG/Twitter 预览、favicon、manifest 等品牌信号不完整；
- schema 可增强：WebSite、Organization、BreadcrumbList、Article/BlogPosting、FAQPage；
- 文章 freshness、作者/更新时间、相关内容模块可增强；
- 额外信任信号不足，例如关于团队、更新日志、联系方式、内容来源说明。

### 工具页 / SaaS 落地页

必查模块：

- Hero：主词、价值、工具入口；
- How it works：至少 3 步；
- Features：具体能力；
- Use cases：按场景分组；
- FAQ：真实问题；
- Trust：证言、安全、隐私、品牌；
- Related tools/pages：相关功能内链；
- CTA：底部再次入口。

### 目录站 / 图片站 / Coloring pages 类站点

必查模块：

- 首页 H1 承载主词；
- H2 承载二级词；
- H3 承载三级词；
- 每个 H2/H3 有图片或条目预览；
- 分类页和详情页互相链接；
- 图片 alt 和文件名可读；
- 分页、筛选、标签页 canonical 清晰。

### 线上才能验证（默认 Unknown）

代码审计不要编造这些数字或等级：

- GSC CTR / 点击质量、查询与着陆页是否匹配；
- 任务完成、Return to SERP / pogo-stick（不要用 bounce rate 代替）；
- 品牌词搜索量、线上口碑；
- 外链是否来自受信任、主题相关、有真实访问的页面。

### 博客 / 内容站

必查模块：

- 标题匹配搜索意图（相关性），title/description 利于点击（CTR）；
- 首段快速回答问题；
- 作者、更新时间、引用来源；
- TOC、H2/H3、列表/表格；
- 相关文章和支柱页内链；
- Article/BlogPosting schema；
- 旧内容更新策略。

### 电商 / 产品页

必查模块：

- 产品/分类唯一 title、description、H1；
- 分类页有独特文本，不只是商品网格；
- Faceted navigation 的 canonical/noindex/robots 策略清晰；
- Product schema 只使用真实价格、库存、评分；
- 缺货产品策略明确；
- 面包屑和分类内链清晰。
