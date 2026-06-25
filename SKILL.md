---
name: seo-code-diagnostic
description: "Audit a website codebase for SEO and AdSense approval readiness: on-page SEO, technical SEO, crawlability, SSR/prerendering, TDK, headings, canonical URLs, internal links, image SEO, sitemap/robots, structured data, keyword-to-page content gaps, AdSense review rejection, low value content, policy readiness, full ADS-* checklist audits with Pass/Fail/Unknown/N/A, game/tool site thin-shell risks, and Chinese diagnosis/code fix plans."
---

# SEO Code Diagnostic Skill

## 什么时候使用

当用户要求你“根据网站代码做 SEO 诊断”“检查某个站点/落地页/Next.js/React/Vue/Astro/Nuxt 项目的 SEO”“优化 TDK、H1、canonical、内链、sitemap、robots、SSR、图片 alt、结构化数据、关键词落地页”等任务时，使用本 skill。

当用户提到 AdSense 审核、AdSense review、反复被拒、low value content、policy issue、游戏站/工具站套壳、iframe 游戏页、站点是否值得投放广告等问题时，也使用本 skill，并启用 AdSense 审核诊断分支。

这个 skill 面向代码仓库审计，不是 Ahrefs/Semrush 的线上排名或外链替代品。除非用户提供了关键词量级、排名、Ahrefs/Google Search Console 数据或生产 URL，否则不要编造搜索量、排名、外链数量、流量变化或竞争难度。

## 核心判断原则

SEO 的第一性原理：搜索引擎和 AI crawler 需要先能访问页面，再能理解页面，再能判断页面是否比竞品更好地满足搜索意图。

审计时始终围绕四件事判断：

1. **能不能抓到**：robots、noindex、HTTP 状态、sitemap、内部链接、页面是否依赖纯前端渲染。
2. **能不能读懂**：title、description、canonical、H1/H2/H3、正文、图片 alt、结构化数据、语义化 HTML。
3. **是否讲透关键词**：一个核心关键词对应一个明确页面；页面要覆盖用户围绕这个词会关心的主要问题，而不是机械重复关键词。
4. **站内权重如何流动**：首页、分类页、子分类页、详情页之间要有清晰层级和上下级内链；重要页面要有上下文内链指向。

## 输入处理

优先收集或推断这些信息：

- 目标域名或预期 canonical host，例如 `https://example.com`。
- 首页主关键词、每个核心页面的目标关键词、二级/三级关键词。
- 页面类型：工具页、SaaS 落地页、博客、目录站、电商、作品集、本地服务页等。
- 技术栈：Next.js、React/Vite、Nuxt/Vue、Astro、SvelteKit、Gatsby、WordPress、Rails、Laravel 等。
- 是否允许运行构建命令、测试命令或只做静态代码审计。
- 如果是 AdSense 审核：收集拒绝原因原文/截图、AdSense 后台提示、目标站点类型、是否游戏/工具 iframe、GSC 收录页面、GSC 查询、近 28/90 天流量、是否有游戏/素材授权和政策敏感内容。

如果用户没有提供关键词，先从域名、路由、页面标题、README、产品文案中推断候选关键词，并在报告中标注“待确认”。不要因为缺关键词就停止审计；先做技术和结构层面的诊断。

## 标准工作流

### 1. 识别项目和页面入口

检查：

- `package.json`、锁文件、framework config：`next.config.*`、`nuxt.config.*`、`astro.config.*`、`vite.config.*`、`gatsby-config.*` 等。
- 路由目录：`app/`、`pages/`、`src/pages/`、`src/routes/`、`routes/`、`content/`、`posts/`、`public/`、`dist/`、`build/`。
- SEO 相关文件：`robots.txt`、`sitemap.xml`、`sitemap.ts`、`robots.ts`、`manifest.json`、`middleware.*`、redirect config、schema/JSON-LD 组件。
- 头部元信息来源：Next metadata API、`next/head`、Nuxt `useHead`、VueUse/head、React Helmet、Astro frontmatter/layout、SvelteKit `svelte:head`、模板 `<head>`。

### 2. 运行静态审计脚本

如环境允许，在仓库根目录运行：

```bash
python /path/to/seo-code-diagnostic/scripts/seo_code_audit.py --root . --out seo-audit
```

如果有目标域名和关键词：

```bash
python /path/to/seo-code-diagnostic/scripts/seo_code_audit.py \
  --root . \
  --domain "https://example.com" \
  --keywords "main keyword,secondary keyword" \
  --out seo-audit
```

脚本会生成 `seo-audit.json` 和 `seo-audit.md`。把脚本结果当作证据，不要把它当作完整结论；你还需要人工检查框架层面的 SSR/SSG、动态 metadata、页面组件复用、内链策略和内容缺口。

如果用户要求 AdSense 审核诊断，添加 `--adsense`：

```bash
python /path/to/seo-code-diagnostic/scripts/seo_code_audit.py \
  --root . \
  --domain "https://example.com" \
  --keywords "main keyword,secondary keyword" \
  --adsense \
  --out seo-audit
```

`--adsense` 只做代码能证明的静态风险检查，并把静态证据映射到相关 ADS-* ID，例如必备页面、Blog/内容区、iframe 薄壳、核心页面内容厚度、移动端 viewport、抓取/索引基础。它不是完整 AdSense 结论；视觉差异化、真实流量、GSC 排名 5-20 的查询、Google 收录、版权授权、账号状态和政策敏感内容必须人工确认。

### 3. 必查项

#### 抓取与索引

- 页面是否在初始 HTML 或构建产物中包含主要文本，而不是全靠浏览器执行 JS 后才出现。
- 重要页面是否有唯一可访问 URL，是否返回 200，是否被 `robots.txt` 或 `<meta name="robots" content="noindex">` 阻止。
- 是否有 sitemap，并且 sitemap 只列出希望被索引的 canonical URL。
- 是否有 robots.txt，且没有误封核心页面、静态资源或所有 crawler。
- 是否存在明显 CSR-only 风险：HTML 只有 `#root`/`#__next` 和大量脚本，几乎没有正文。

#### TDK 与 head

- 每个可索引页面有唯一、准确、吸引点击的 `<title>`。
- 每个核心页面有有用的 `meta description`；不要依赖关键词堆叠。
- 一般不需要 `meta keywords`；发现时可建议删除或不维护。
- 每个核心页面有唯一 canonical，canonical 用绝对 URL、HTTPS、正确域名，并且每页只出现一次。
- `og:url` 与 canonical 不冲突；Open Graph/Twitter meta 对分享有价值，但优先级低于 title/description/canonical。

#### 页面语义结构

- 每个页面一个 H1；H1 直接表达主关键词或主搜索意图。
- H2/H3 分门别类罗列相关问题、场景、功能、步骤、用例、FAQ，不要跳级混乱。
- 正文放在真实 HTML 文本中；关键解释不要只写在图片、canvas、SVG 或客户端状态里。
- 页面包含足够上下文：定义、使用步骤、核心功能、差异点、示例、FAQ、信任证明、相关页面链接和转化入口。

#### 落地页内容模块

对工具页或 SaaS 关键词落地页，参考这个顺序检查缺口：

1. 工具名称、核心价值、主关键词和工具入口。
2. How it works：围绕主用户任务解释步骤。
3. Features：具体能力，不是空泛形容词。
4. 示例/场景/用例：解释不同搜索意图。
5. FAQ：回答真实问题，答案要有信息增益。
6. 用户证言、评分、案例、品牌/安全/隐私信任信号。
7. 相关功能/相关关键词页面链接列表。
8. 页面尾部再次给工具入口或 CTA。

#### 关键词与内容覆盖

- 首页主关键词、二级关键词、三级关键词要有页面映射：主词通常用首页或支柱页；二级词用一级子目录；三级词用二级子目录或详情页。
- 关键词密度只作为辅助信号：经验参考范围是 3%–5%，不要超过 8%；但不要为了密度牺牲自然表达。低于目标时优先补充同义词、实体、场景、FAQ 和相关问题，而不是硬塞词。
- 一个页面不要同时竞争多个完全不同的搜索意图；必要时拆页。
- 用语义相关词围绕主词解释，例如 “remove background” 页面可自然覆盖 upload image、transparent background、PNG、AI background remover、photo editor、erase background、download result 等。

#### 内链建设

- 首页链接到核心二级/三级关键词页面。
- 二级关键词页面链接回首页，并链接到它下面的三级页面。
- 三级页面用精确或自然锚文本链接回二级页面；所有核心页面都能自然链接回首页或支柱页。
- 发现页面提到某个目标词但没链接到对应页面时，建议加上下文内链。
- 避免孤儿页、只在 sitemap 出现但站内没有入口的页面。
- 内链 anchor 要描述目标页主题，不要泛用 “click here”“learn more”。

#### 图片 SEO

- 所有重要图片有简洁、描述性的 alt。
- 图片文件名尽量描述内容，不用随机 `IMG_1234.jpg`。
- 大图要压缩、设置宽高、合理懒加载；首屏 LCP 图片不要过度 lazy-load。
- 关键表格和信息不要只做成图片；搜索引擎和 AI 系统需要可读 HTML 文本。

#### 结构化数据与 AI 可见性

根据页面类型检查 JSON-LD：

- 通用：`Organization`、`WebSite`、`BreadcrumbList`。
- 工具/SaaS：`SoftwareApplication`、`Product`、`AggregateRating`（只有真实评分时）。
- 内容页：`Article`、`BlogPosting`、作者信息、更新时间。
- FAQ：只有页面真实展示 FAQ 时再加 `FAQPage`。

优先写清楚页面内容，不要用 schema 掩盖薄内容。

### 4. AdSense 审核诊断分支

AdSense 审核的第一性问题：这个网站是否值得展示广告。对游戏站和工具站，审核风险通常不是“少一个 meta 标签”，而是网站看起来像认真维护的内容站，还是自动生成的低质套壳。

当用户说 AdSense 被拒、low value content、policy、反复 review 失败、是否可以申请 AdSense、复审是否 ready、或要求完整 AdSense 审核时，必须加载：

- `references/adsense-requirements.md`：官方来源驱动的 ADS-* 完整检查表、状态规则和输出协议。
- `references/adsense-review-diagnostic.md`：游戏站/工具站、low value content、薄壳和长尾内容经验判断。

AdSense 审核不是只查当前看起来可疑的项目。必须逐项覆盖 `adsense-requirements.md` 的全部 73 个 ADS-* ID。每个 ID 只能标记 `Pass`、`Fail`、`Unknown` 或 `N/A`：

- `Pass`：必须有代码、线上抓取、后台、GSC/GA、用户确认或其他明确证据。
- `Fail`：必须给出页面/文件/证据、精确修复动作和验收标准。
- `Unknown`：用于必须依赖 AdSense 后台、站长确认、服务器/CDN 配置、GSC/GA、版权授权、法律/隐私判断或更大样本抓取的项目；必须说明缺什么证据。
- `N/A`：只在该要求确实不适用于当前站点类型/变现模式时使用，并说明原因。

先按这个顺序检查：

1. **视觉差异化**：网站不能一眼像通用模板。游戏站优先参考主打游戏的配色、字体、素材和氛围；工具站要有清晰品牌感和真实产品感。
2. **不是纯 iframe/工具壳**：纯 iframe 不是内容。每个游戏/工具页至少要有原创介绍、玩法/使用步骤、FAQ、相关游戏/工具和上下文内链。
3. **内容厚度**：首页、分类页、游戏页、工具页都要有可读正文，不能只有卡片、封面图、按钮或营销口号。
4. **Blog/Guides 区域**：审核阶段建议准备 5-10 篇相关原创文章，例如玩法攻略、技巧、推荐、教程、问题解答、行业资讯。
5. **必备页面**：About、Contact、Privacy Policy、Terms of Service 要齐全，并从导航或页脚可访问。
6. **政策红线**：人工确认是否有侵权游戏/素材、成人、赌博、仇恨、暴力等高风险内容。
7. **长尾词机会**：不要浪费长尾词。结合 GSC 找排名 5-20、展示不低但点击少的查询，优先做页面或补内容。

输出时不要承诺“改完一定通过 AdSense”。要区分静态证据、线上证据、后台/账号证据和人工确认项，并说明还需要用户提供 AdSense 拒绝截图、GSC 收录、GSC 查询、流量、账号状态和授权信息。最终 AdSense 决策只能是 `Ready`、`Ready after fixes` 或 `Not ready`，并且必须在报告最后做 Completeness Check：

- `Requirement IDs in reference: 73`
- `Requirement IDs in report: <count>`
- `Missing IDs: none` 或列出缺失 ID

### 5. 框架专项判断

#### Next.js

检查 `app/` 或 `pages/`：

- App Router 优先使用 `metadata`、`generateMetadata`、`alternates.canonical`、`robots`、`openGraph`。
- 关键页面不要整页 `use client` 后才生成核心文案；Server Component 或 SSG/SSR 更稳。
- 动态路由要有 `generateStaticParams` 或可靠 SSR，并为每个动态页面生成唯一 title、description、canonical。
- `app/sitemap.ts`、`app/robots.ts` 或 `public/sitemap.xml`、`public/robots.txt` 要覆盖可索引页面。

#### React/Vite SPA

默认警惕 CSR-only。若核心业务靠自然搜索，建议：

- 改为 Next.js/Astro/Nuxt/SvelteKit 等 SSR/SSG；或
- 增加 prerender/SSG 构建；或
- 至少确保每个可索引 URL 有真实 HTML、唯一 title/description/canonical。

#### Nuxt/Vue

检查 SSR 是否开启，`useHead`/`definePageMeta` 是否为每页生成唯一 head，动态路由是否有 server-rendered 内容和 canonical。

#### Astro/SvelteKit/Gatsby

检查构建产物 HTML；确认页面文本、head、canonical、JSON-LD 在静态 HTML 中可见。

### 6. 严重级别

- **P0 阻断型**：noindex/robots 误封、重要页面无法生成 HTML、核心页面 4xx/5xx、canonical 指向错误域名或死链、纯 CSR 导致几乎无可读内容。
- **P1 高影响**：缺 title/description/H1/canonical、多个 H1、动态页复用同一 TDK、重要页面孤儿、sitemap 缺核心 URL、结构严重混乱。
- **P2 中影响**：内容薄、搜索意图覆盖不足、内链层级不清、图片 alt 缺失、FAQ/相关页模块缺失、关键词页面映射不清。
- **P3 优化项**：标题过长/过短、OG/Twitter 不完整、schema 可增强、图片文件名可优化、段落可读性改进。

AdSense 分支中：

- **P0**：政策/版权红线、站点不可访问、noindex/robots 阻断、缺 Contact/Privacy/Terms 等审核信任基础。
- **P1**：纯 iframe 壳、核心页很薄、没有原创价值、首页/游戏页/工具页像批量模板。
- **P2**：缺 Blog/Guides 内容集群、原创文章不足 5 篇、分类/首页文字弱、长尾词没有页面映射。
- **P3**：视觉 polish、OG/social preview、schema、文章 freshness、额外信任信号。

### 7. 输出格式

用中文输出。先给结论，再给证据。不要只给泛泛建议。

推荐结构：

```markdown
# SEO 代码诊断报告

## 一句话结论

## 优先级总览
| 优先级 | 数量 | 主要问题 |

## P0/P1 必修复问题
| 优先级 | 页面/文件 | 证据 | 为什么影响 SEO | 建议修复 | 代码位置 |

## 关键词与页面映射
| 关键词 | 搜索意图 | 建议 URL | 当前页面 | 缺口 | 建议动作 |

## 页面结构与内容缺口
| 页面 | H1 | H2/H3 覆盖 | 缺失模块 | 建议补充 |

## 内链结构建议
| 来源页 | 锚文本 | 目标页 | 原因 |

## 技术 SEO 检查
- robots / sitemap / canonical / SSR / schema / image / performance

## AdSense 审核诊断（如果用户要求）
| ADS ID | 优先级 | 状态 | 证据 | 建议 |

## AdSense 完整检查表（如果用户要求 AdSense 审核）
| ADS ID | Severity | Status | Evidence | Next action |

## Completeness Check（如果用户要求 AdSense 审核）
- Requirement IDs in reference: 73
- Requirement IDs in report: ...
- Missing IDs: ...

## Low value content 可能原因（如果用户要求）
- ...

## 需要用户补充的数据（如果用户要求）
- AdSense 拒绝原因 / GSC 收录 / GSC 查询 / 流量 / 授权信息

## 可执行修复清单
1. ...
2. ...

## 验证方式
- 本地 build/test 命令
- 查看源代码要能看到 title、description、H1、正文、canonical
- 提交 Google Search Console 后观察收录与前 20 名关键词变化
```

如果用户要求直接改代码，先列出最小修复方案，然后执行修改。修改后运行可用的 lint/build/test，并说明哪些验证已完成、哪些需要线上数据或 GSC/Ahrefs 才能验证。

## 不要做

- 不要承诺“改完一定上首页”。
- 不要伪造 Ahrefs、GSC、GA、排名、搜索量、外链数据。
- 不要为了关键词密度把文案改成机械重复。
- 不要把所有页面 canonical 到首页。
- 不要给不存在的评分、评论、奖项、案例加结构化数据。
- 不要只检查 React 组件是否有 `<h1>`，还要确认构建后的 HTML 或 SSR 输出是否可见。
- 不要承诺 AdSense 一定通过；只能给通过概率相关的风险诊断和整改建议。
- 不要把视觉原创性、真实流量、GSC 收录、版权授权和政策判断伪装成代码静态检查结论。
