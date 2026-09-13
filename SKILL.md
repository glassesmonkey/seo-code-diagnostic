---
name: seo-code-diagnostic
description: "Audit a website codebase against the 2026 Zyppy Top 10 ranking factors (Relevance/Intent, Backlinks, Content Quality, Authority, Behavior/CTR, Brand, Satisfaction, Technical table stakes, Topical Authority, Internal Links), plus AdSense ADS-* completeness, YMYL/internal-copy leaks, and Chinese diagnosis. Codebase audit only: do not invent GSC/Ahrefs/backlink/CTR metrics. Meta description is a CTR lever, not a proven ranking factor. Keyword density flags stuffing only."
---

# SEO Code Diagnostic Skill

诊断主骨架是 **2026 Zyppy Top 10**（Cyrus/Dawn Shepard，131 位 SEO，2026-09-09）。专家共识 ≠ Google 官方权重。本 skill 是代码仓库审计，不是 Ahrefs / GSC 替代品。

旧的「抓取 / TDK / H1 / 密度 / 落地页八模块」**不再当主目录**。它们拆进对应因素下当子项。meta description 不进排名主线，只挂在 F5 CTR。

对照：`references/zyppy-2026-ranking-factors.md`。

## 什么时候使用

当用户要求网站代码 SEO 诊断、落地页/框架项目 SEO、或按排名因素查意图/内容/内链/技术底座时，使用本 skill。

当用户提到 AdSense 审核、low value content、游戏站/工具站套壳时，也使用本 skill，并启用**独立的** AdSense 分支。

没有用户提供的搜索量、排名、Ahrefs、GSC、外链表或品牌数据时，禁止编造这些数字。对应因素标 `Unknown`。

## 输入处理

优先收集或推断：

- 目标域名 / canonical host。
- 每个核心 URL 要满足的**结果类型或任务**（工具、教程、对比、目录、产品），以及候选关键词。
- 页面类型与技术栈。
- 是否允许构建，或只做静态审计。
- 若有：GSC、外链表、品牌查询、AdSense 拒绝原因。

没有关键词也能先做 F8 / F10 和可见结构。没有 GSC / 外链表 / 品牌数据时，F2、F5、F6、F7 的线上部分必须 `Unknown`。

## 标准工作流

### 1. 识别项目和页面入口

- `package.json`、框架 config：`next.config.*`、`nuxt.config.*`、`astro.config.*`、`vite.config.*` 等。
- 路由/内容：`app/`、`pages/`、`src/pages/`、`src/routes/`、`routes/`、`content/`、`posts/`、`public/`、`dist/`、`build/`。
- 抓取入口：`robots.txt`、`sitemap.xml`/`sitemap.ts`、`robots.ts`、middleware、redirect。
- Head 来源：Next `metadata`/`generateMetadata`、`next/head`、Nuxt `useHead`、React Helmet、Astro/SvelteKit head、模板 `<head>`。

这些只是取证入口，不是诊断目录。取证后按下面 Top 10 逐项写状态。

### 2. 运行静态审计脚本

```bash
python /path/to/seo-code-diagnostic/scripts/seo_code_audit.py --root . --out seo-audit
```

有域名和关键词时加 `--domain`、`--keywords`。AdSense 审核加 `--adsense`。

脚本输出按 F1–F10 因素表组织。它是证据，不是完整结论。人工必须补：意图是否答在点上、一手信息是否存在、框架 SSR、以及所有线上信号。

`--adsense` 只映射代码能证明的 ADS-* 风险，不是 73 项齐全结论。

### 3. 必查项：按 Top 10 因素诊断

每一项都写：**定义（调查）**、**代码能查**、**必须 Unknown**、**严重级别**。状态只能是 `Pass` / `Fail` / `Unknown` / `N/A`。不要发明分数。

#### F1. Relevance / Search Intent Match（57.1%）

**定义（调查）**：内容相关 = 匹配并满足搜索意图。Search Intent Match 是单项第 1：页面是否满足搜索者想要的**结果类型或任务**，超出关键词和语义相近。技术完美但答非所问，救不了。当很多页都已匹配意图并覆盖同一范围时，看 **information gain**（有没有别人没有的东西）。

**代码仓库能查**：

- 结果形态：这个 URL 是工具、教程、对比、目录还是产品页？和目标查询要的形态是否一致。
- title / H1 是否表达本页任务（标题**相关性**，不是点击文案）。
- 可见正文是否在完成该任务。工具/SaaS 子项：入口、How it works、能力、场景、能增加信息增益的 FAQ、相关页、再次 CTA。目录站子项：H1/H2/H3 是否按任务/主题分层，而不是为了堆词。
- 一个 URL 是否同时抢多个完全不同的意图（该拆页）。
- 目标词是否在可见文本中自然出现。**密度不是目标**；不追求 3%–5%，也不把 8% 当达标线。只在异常高时标堆砌。不要报「密度太低」。

**必须 Unknown**：真实用户打开后是否觉得「就是我要的那种结果」；竞品 SERP 上的信息增益比较（除非用户提供 SERP/竞品）。

**严重级别**：页面明显答非所问或结果形态错 → P1。意图模块残缺、title 与任务偏离、目标词应出现却完全没有、堆砌 → P2。标题层级抛光 → P3。缺 title → P1（无法表达意图）。**缺 meta description 不进本因素。**

#### F2. Backlinks（54.8%）

**定义（调查）**：外链仍是 Top 3。高分主要是：高度受信任域名、主题相关页面、来源页有真实访客。「一百个有真实读者的链接，胜过一千个没人点的链接。」垃圾链是最强负向之一。精确匹配锚文本双刃：变量是它在锚文本画像中的**占比**，不是次数。

**代码仓库能查**：几乎不能证明外链质量。最多看页脚/合作模块是否露出明显垃圾友链，那只是站内线索，不是外链画像。

**必须 Unknown（默认）**：DR/外链数、引用域、流量、锚文本占比。禁止编造。

**用户提供链接表时怎么评**（有表才从 Unknown 往 Pass/Fail 走）：

| 看 | 正向 | 负向 |
|---|---|---|
| 来源域名 | 该主题里被信任的媒体、文档、大学、工具、行业站点 | 批量目录、兑换、脚注农场、无关站 |
| 来源页 | 与你主题相关，且像有真实读者 | 无人读的列表页、隐藏链、全站页脚 |
| 锚文本 | 描述性、品牌、部分匹配为主 | 精确匹配占比过高 |
| 数量 | 不作为目标 | 用数量代替质量 |

**严重级别**：无链接表 → 整项 `Unknown`，不要写 P0。有表且垃圾/无关占主导 → P1/P2。不要给「需要 50 条外链」这类数量处方。

#### F3. Content Quality（47.6%）

**定义（调查）**：原创、准确、新鲜。Original Research / First-Party Data 靠前。规模化、几乎不增值的 AI 为负。高质量 AI + 人工编审 + 站点已有独特内容/UGC，专家里有人认为可以。不要打「质量分」。

**代码仓库能查**：

- 是否有一手数据、方法、限制、反例、独特示例、真实 UGC；还是和模板站同一套套话。
- 薄页：只有卡片、按钮、iframe、营销形容词。
- 规模化低质 AI 痕迹：近乎重复的页面壳、占位、内部/模型痕迹（与横切的内部泄露一起报）。
- 图片关键信息是否只在图里（搜索引擎读不到）。
- 结构化数据是否与真实内容一致；禁止伪造评分/评论/奖项。

**必须 Unknown**：准确性和新鲜度的外部验证；「AI 质量分」。

**严重级别**：核心页没有原创价值、批量薄壳 → P1。薄、无一手信息、FAQ 没有增量 → P2。可读性抛光 → P3。

#### F4. Authority & Trust（36.5%）

**定义（调查）**：Google 对网站、创作者或品牌/业务的信任。

**代码仓库能查**：About、作者、来源、资质、更新说明、真实 Organization/Person schema、不造假的证言。YMYL 主题出现承诺/诊断/保证时，作为信任破坏项（详见横切）。

**必须 Unknown**：站点/品牌被 Google 有多信任、E-E-A-T 分数、外部口碑强度。

**严重级别**：YMYL 承诺型可见文案 → P1。完全没有身份/来源模块 → P2。信任模块可增强 → P3。强度本身保持 Unknown。

#### F5. Behavior / Click Signals（29.4%）

**定义（调查）**：用户如何挑选结果、如何与页面互动。Google 在看用户。满意度/任务完成见 F7；这里管点击与回 SERP。Return to SERP / pogo-stick 为负。Bounce rate 是差代理。

**代码仓库能查（只是 CTR 文案代理，不是行为本身）**：

- title 是否利于 SERP 点击（长度、具体收益）。这与 F1 的 title **相关性**分开。
- meta description：专家普遍认为对**排名几乎没有/没有影响**，仍可能影响 CTR。按 **P2/P3 CTR 杠杆**，写明「不是已被证明的排名因子」。不要放进 F1 排名主线。

**必须 Unknown**：没有 GSC 时，整项线上行为（真实 CTR、pogo-stick、Navboost）= `Unknown`。有 GSC 才评：展示、点击、CTR、查询与着陆页是否匹配。不要用 bounce rate 当满意度。

**严重级别**：缺 description → P2（CTR，不是排名 P1）。title/description 过长过短或空泛 → P3。没有 GSC 不要给行为项 Pass。

#### F6. Brand Signals（27.0%）

**定义（调查）**：成为一个被人搜索、信任、访问的品牌/实体。线上声誉和品牌词搜索量重要。广告花费几乎无直接作用，最多间接提高可见度。

**代码仓库能查**：名称/logo/域名是否同一实体；About、`sameAs`、组织信息是否一致；favicon/OG 是否像一个品牌而不是空壳。

**必须 Unknown**：品牌词搜索量、外部提及、声誉。不要把「多投广告」写成排名动作。

**严重级别**：实体在代码里自相矛盾 → P2。OG/favicon 不完整 → P3。品牌强度默认 Unknown。

#### F7. User Satisfaction（19.8%）

**定义（调查）**：满意度或 **task completion** 是最终结果。工具站要问：用户能否在首屏完成任务（打开就能用，而不是只读营销）？

**代码仓库能查**：工具/游戏入口是否真实存在、是否被 iframe 壳挡住、步骤是否通向可完成的动作、CTA 是否指向能用的功能。这是「任务是否可能完成」的代理。

**必须 Unknown**：真实满意度、回访、任务完成率、pogo-stick。不要用 bounce 代替。

**严重级别**：工具/游戏页无法完成任务（纯 iframe、无入口、坏流程）→ P1。任务路径含糊 → P2。真实满意度保持 Unknown。

#### F8. Technical SEO Health（17.5%）

**定义（调查）**：抓取与索引是其他因素的地基。多数专家说是 **table stakes**：坏的技术 SEO 会让你输掉；好的技术 SEO 不会把平庸内容抬上去。CWV/速度争议大、常被高估。

**代码仓库能查**（旧「抓取/索引/canonical/SSR」整段挂在这里）：

- robots / noindex / sitemap / 唯一可访问 URL。
- 初始 HTML 或构建产物里是否有正文（纯 CSR 只有 `#root` + script → 会摔）。
- canonical：绝对 URL、HTTPS、正确域名、每页一个；sitemap/内链用 canonical。
- 框架子项：Next `metadata`/`generateMetadata`、不要整页 `use client` 才出文案；SPA 要 SSR/SSG/prerender；Nuxt/Astro/SvelteKit 的 head 与构建 HTML。
- 图片尺寸/压缩、viewport：体验与抓取辅助，不是增长开关。
- schema 作为机器理解基础设施；有真实内容再加。

**必须 Unknown**：真实收录、CWV 实验室/实操数字（除非用户提供）。不要把 CWV 写成 P1 增长项。

**严重级别**：noindex/robots 误封、核心页无 HTML、4xx/5xx、canonical 错域名/死链、纯 CSR 无可读正文 → P0。缺 canonical、sitemap 缺核心 URL、动态页同一 HTML → P1。viewport、robots 未声明 sitemap → P2/P3。修好 F8 不等于内容会排上去。

#### F9. Topical Authority（14.3%）

**定义（调查）**：品牌/站点是否被当成某主题的专家。

**代码仓库能查（结构代理，不是分数）**：是否有支柱页 + 集群；主词/二级/三级是否落到首页/分类/详情；目录站是否「分门别类」而不是孤立薄页。

**必须 Unknown**：该主题下的真实权威/可见度。

**严重级别**：只有孤立页、没有主题层级 → P2。结构代理可增强 → P3。不要输出「主题权威分」。

#### F10. Internal Links（11.1%）

**定义（调查）**：内链与信息架构。专家认为这是站点可端到端控制的杠杆：决定哪些页积累权重、哪些页被看成重要、主题如何连接。一条好内链可以被看成接近一条很好的外链。

**代码仓库能查**：

- 首页 → 二级 → 三级，以及回链。
- 孤儿页、只在 sitemap 出现的页。
- 提到目标主题却不链到对应页。
- 锚文本描述目标主题，不用 “click here”。

**必须 Unknown**：内链「权重分」。给具体「来源页 / 锚文本 / 目标页 / 原因」。

**严重级别**：重要页孤儿 → P1。内链过少、层级断 → P2。锚文本抛光 → P3。

### 4. 横切检查：YMYL 与内部泄露

这两项不是 Top 10 里的独立名次，但默认要做；可同时记在 F3/F4 证据里。

- **YMYL**：不是禁词。健康/财务/安全/法律等主题出现建议、承诺、保证、诊断、收益、治疗时，标高风险并要求人工审稿。改成信息性说明，补来源/资质/免责，或撤主题。
- **内部/模型痕迹**：内部要求、prompt、思考过程、草稿、占位、面向执行者的句子，不能出现在用户页面。改成用户能做什么、看到什么、得到什么。
- 脚本 `YMYL_COPY_REVIEW` / `INTERNAL_COPY_LEAK` 是启发式。可见 HTML 置信度高；源码命中要确认是否渲染到页面。

### 5. AdSense 审核诊断分支（独立章节）

AdSense 不并入 Top 10 主表。第一问：这个网站是否值得展示广告。

当用户说 AdSense 被拒、low value、policy、反复失败、是否可申请时，加载：

- `references/adsense-requirements.md`：73 个 ADS-*，状态 `Pass` / `Fail` / `Unknown` / `N/A`。
- `references/adsense-review-diagnostic.md`：游戏/工具站、薄壳、low value。

必须覆盖全部 73 个 ID。`Pass` 要有证据；`Fail` 要有修复和验收；`Unknown` 说明缺什么；`N/A` 说明为何不适用。

先看：视觉差异化；不是纯 iframe/工具壳；内容厚度；Blog/Guides；About/Contact/Privacy/Terms；政策红线；GSC 里 5–20 名、有展示低点击的查询（有 GSC 才做）。

不要承诺一定通过。决策只能是 `Ready` / `Ready after fixes` / `Not ready`，并做 Completeness Check（reference 73 / report count / missing IDs）。

### 6. 输出格式

用中文。先结论，再证据。主表必须是 Top 10 一行一项。

```markdown
# SEO 代码诊断报告

## 一句话结论

## Top 10 排名因素
| 因素 | Top3% | 状态 | 代码证据 | 线上信号 | 动作 |
|---|---:|---|---|---|---|
| F1 Relevance / Search Intent Match | 57.1% | Pass/Fail/Unknown/N/A | … | 竞品/SERP 信息增益常 Unknown | … |
| F2 Backlinks | 54.8% | 默认 Unknown | 无链接表则写「无」 | 信任域/主题/真实访客/垃圾链/EM 锚占比 | 有表才评，不追求数量 |
| F3 Content Quality | 47.6% | … | 一手/原创 vs 薄/规模 AI | 外部准确性 Unknown | … |
| F4 Authority & Trust | 36.5% | … | About/作者/来源 | 信任强度 Unknown | … |
| F5 Behavior / Click | 29.4% | 无 GSC 则 Unknown | title CTR；description 仅 CTR | GSC CTR/pogo；bounce 不用 | 缺 description=P2 CTR，非排名 P1 |
| F6 Brand Signals | 27.0% | … | 实体一致性 | 品牌词/口碑 Unknown；广告花费几乎无直接作用 | … |
| F7 User Satisfaction | 19.8% | … | 首屏能否完成任务 | 满意度 Unknown | … |
| F8 Technical SEO Health | 17.5% | … | 抓取/SSR/canonical/sitemap | 收录/CWV 常 Unknown | table stakes，不是增长解锁 |
| F9 Topical Authority | 14.3% | … | 支柱+集群结构代理 | 权威强度 Unknown | 不打分 |
| F10 Internal Links | 11.1% | … | 层级/孤儿/锚文本 | — | 具体来源→目标 |

## F1–F10 分项证据
（每项：定义一句话、证据、Unknown 说明、修复）

## 文案风险（YMYL / 内部泄露）
| 优先级 | 页面/文件 | 风险类型 | 原文证据 | 改写方向 |

## AdSense（仅当用户要求；独立于 Top 10）
| ADS ID | Severity | Status | Evidence | Next action |
Completeness Check: 73 / <count> / missing

## 可执行修复清单
按因素顺序，不按旧 TDK 清单。

## 验证
- 本地 build；查看源代码中的 title/H1/正文/canonical。
- description 按 CTR 验收，不按排名验收。
- 有 GSC/外链表/品牌数据再验证 F2/F5/F6/F7；否则保持 Unknown。
```

如果用户要求改代码：先按因素列出最小修复，再改。跑可用的 lint/build/test。写清哪些已验证、哪些仍 Unknown。

## 不要做

- 不要承诺改完一定上首页。
- 不要伪造 Ahrefs、GSC、GA、排名、搜索量、CTR、品牌词量、外链数量或权威分。
- 不要把 3%–5%（或 8% 上限）密度当目标；不要因为密度低报警。
- 不要把缺 meta description 写成 F1/P1 排名问题。
- 不要把 F8 / CWV 写成增长解锁。
- 不要把「多做外链」当主处方。
- 不要把 YMYL 写成未经证明的医疗/金融/法律/安全承诺。
- 不要把内部要求、prompt、思考过程暴露给用户。
- 不要把所有页面 canonical 到首页。
- 不要给不存在的评分、评论、奖项加 schema。
- 不要只看组件里有没有 `<h1>`，要看构建后 HTML。
- 不要承诺 AdSense 一定通过。
- 不要把旧 TDK checklist 当成报告主目录。
