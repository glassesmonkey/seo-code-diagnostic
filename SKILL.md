---
name: seo-code-diagnostic
description: "Audit a website codebase against the 2026 Zyppy Top 10 ranking factors (Relevance/Intent, Backlinks, Content Quality, Authority, Behavior/CTR, Brand, Satisfaction, Technical table stakes, Topical Authority, Internal Links), plus AdSense ADS-* completeness, YMYL/internal-copy leaks, and Chinese diagnosis. Codebase audit only: do not invent GSC/Ahrefs/backlink/CTR metrics. Meta description is a CTR lever, not a proven ranking factor. Keyword density flags stuffing only."
---

# SEO Code Diagnostic Skill

诊断主骨架是 **2026 Zyppy Top 10**（Cyrus/Dawn Shepard，131 位 SEO，2026-09-09）。专家共识 ≠ Google 官方权重。本 skill 是代码仓库审计，不是 Ahrefs / GSC 替代品。

旧的「抓取 / TDK / H1 / 密度 / 落地页八模块」**不再当主目录**。它们拆进对应因素下当子项。meta description 不进排名主线，只挂在 F5 CTR。

对照：`references/zyppy-2026-ranking-factors.md`（含专家实战 → Pass/Fail/Unknown 动作表）。读者应同时看到 Top 10 骨架和可执行的专家检查点。

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

每一项都写：**定义（调查）**、**专家实战要点**、**代码能查**、**必须 Unknown**、**严重级别**。状态只能是 `Pass` / `Fail` / `Unknown` / `N/A`。专家实战是调查观察，**≠ Google 官方保证**；要写成查什么、何时 Pass/Fail/Unknown，不要只堆金句。不要发明分数。

#### F1. Relevance / Search Intent Match（57.1%）

**定义（调查）**：内容相关 = 匹配并满足搜索意图。Search Intent Match 是单项第 1：页面是否满足搜索者想要的**结果类型或任务**，超出关键词和语义相近。

**专家实战要点**（调查观察，≠ 官方保证）：

- **答非所问救不了**：技术、标题层级、URL 再干净，结果形态错了仍 `Fail`（P1）。先问「用户要工具/答案/对比/目录中的哪一种」，再看代码。
- **Information gain**：用户或 SERP 显示已有多页覆盖同一任务时，查本页有没有别人没有的一手数据、限制、方法。只有同构套话 → `Fail`（P2）；说不清竞品差 → 信息增益 `Unknown`。
- **EMD still effective**：检查 host 是否精确/高度匹配主意图词。匹配 = 加分观察，不单独 `Pass` 整项。品牌域非 EMD **不** `Fail`。不建议买垃圾 EMD。

**代码仓库能查**：

- 结果形态：这个 URL 是工具、教程、对比、目录还是产品页？和目标查询要的形态是否一致。
- title / H1 是否表达本页任务（标题**相关性**，不是点击文案）。
- 可见正文是否在完成该任务。工具/SaaS 子项：入口、How it works、能力、场景、能增加信息增益的 FAQ、相关页、再次 CTA。目录站子项：H1/H2/H3 是否按任务/主题分层，而不是为了堆词。
- 一个 URL 是否同时抢多个完全不同的意图（该拆页）。
- 目标词是否在可见文本中自然出现。**密度不是目标**；不追求 3%–5%，也不把 8% 当达标线。只在异常高时标堆砌。不要报「密度太低」。
- **域名意图匹配 / EMD**：看 `--domain` 或 canonical host 的可注册标签是否精确或高度匹配主意图词（如 `bankstatementconverter*.*` 对 “bank statement converter”）。写入 Relevance 行，作为相关性**加分观察**。

**必须 Unknown**：真实用户打开后是否觉得「就是我要的那种结果」；竞品 SERP 上的信息增益比较（除非用户提供 SERP/竞品）。EMD 的真实排名贡献也不是官方权重，只能当观察。

**严重级别**：页面明显答非所问或结果形态错 → P1。意图模块残缺、title 与任务偏离、目标词应出现却完全没有、堆砌 → P2。标题层级抛光 → P3。缺 title → P1（无法表达意图）。**缺 meta description 不进本因素。** 域名不是 EMD **不判 Fail**；已有品牌域保持 Pass/Fail 只由内容与意图决定。不要建议为了 SEO 去买垃圾 / spammy EMD。连字符堆词域名只标注风险观察，不写成「快去买 EMD」。

#### F2. Backlinks（54.8%）

**定义（调查）**：外链仍是 Top 3。高分主要是：高度受信任域名、主题相关页面、来源页有真实访客。

**专家实战要点**（调查观察，≠ 官方保证）：

- **100 条有真人受众的链 > 1000 条没人点的链**：有链接表时按「来源页像不像有读者」评，不按条数。无表 → 整项 `Unknown`。禁止编造外链数。
- **高信任域 + 主题相关页最强**：Pass 线索 = 该主题里被信任的来源，且来源页谈同一主题。目录/兑换/脚注农场 → `Fail`。
- **Spam 仍是大负向**：即使 Google 口头说会忽略多数垃圾链，专家仍把它当强负向。有表且垃圾占主导 → `Fail`（P1/P2）。不要写「Google 会自动忽略所以不用管」。
- **EM 锚文本看画像占比，不是条数**：精确匹配过多 → 风险观察/`Fail`（P2）。变量是占比，不要数「还差几条精确锚」。
- **高质量提及可能连带抬 AI 可见度**（调查里 Reuters 被提及后 ChatGPT 可见度上升的个例）：只标**推断**。用户没给 AI 引荐/提及数据 → `Unknown`，不编倍数。

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

**定义（调查）**：原创、准确、新鲜。不要打「质量分」。

**专家实战要点**（调查观察，≠ 官方保证）：

- **Original Research / First-Party Data 抬头**：核心页能指出自己的数据、实验、操作限制或独特样本 → 质量代理偏正。全是泛百科套话 → `Fail`（P2/P1）。
- **AI 让内容变便宜，质量是过滤器**：廉价规模 AI（重复壳、可替换词、无增量）→ `Fail`。不要输出「AI 质量分」。
- **高质量 AI + 人工深编 + 独特/UGC 可正例**：有编审痕迹、独特模块或真实 UGC 时，不要仅因「像 AI 写的」判 Fail。
- **Goldilocks**：共识复述过多会看不见；信息增益大到只对专家说话也可能伤害大众可见度。查页面是「完成普通搜索者的任务」还是「只写给同行」。过专家向且无入门路径 → P2 观察（与 F4/F6 一起写）。两侧都缺证据 → `Unknown`。

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

**专家实战要点**（调查观察，≠ 官方保证；与 F6 一起读）：

- **流行度 / 被谈论、分享、链接、提及**：代码只能看是否具备被信任的身份模块。外部有多「被谈论」无数据 → `Unknown`。
- **过专家向可能伤害大众可见度**：YMYL/教程页只有同行黑话、没有普通用户能完成的任务说明 → P2 观察，并回看 F1/F3。
- **品牌/信任很强时，技术和内容差点仍可能撑住**：这是线上推断。代码里 F8 `Fail` 仍要修（会摔）；不要写成「品牌强所以 P0 可以不修」。品牌强度本身 `Unknown`。

**代码仓库能查**：About、作者、来源、资质、更新说明、真实 Organization/Person schema、不造假的证言。YMYL 主题出现承诺/诊断/保证时，作为信任破坏项（详见横切）。

**必须 Unknown**：站点/品牌被 Google 有多信任、E-E-A-T 分数、外部口碑强度。

**严重级别**：YMYL 承诺型可见文案 → P1。完全没有身份/来源模块 → P2。信任模块可增强 → P3。强度本身保持 Unknown。

#### F5. Behavior / Click Signals（29.4%）

**定义（调查）**：用户如何挑选结果、如何与页面互动。满意度/任务完成见 F7。

**专家实战要点**（调查观察，≠ 官方保证）：

- **Navboost 仍强**：无 GSC → 整项线上行为 `Unknown`，不要 Pass。有 GSC 才比点击质量。
- **点击差于同 SERP 竞品会有排名天花板**：用户提供「同查询下你的 CTR vs 同类位置」时，明显偏低 → `Fail`（先改 F1 形态和 F5 点击文案）。没比较表 → `Unknown`。
- **Bounce rate 是烂代理**：报告里禁止用 bounce 当满意度或 Pass/Fail 依据。
- **Pogo-stick / Return to SERP 才是清晰负向**：有用户研究或明确回 SERP 证据才 `Fail`；否则 `Unknown`。
- **按页面类型建满意度代理**（与 F7 共用）：工具看任务是否完成，文章看是否答完问题。代码只建代理，不冒充 Navboost 分数。

**代码仓库能查（只是 CTR 文案代理，不是行为本身）**：

- title 是否利于 SERP 点击（长度、具体收益）。这与 F1 的 title **相关性**分开。
- meta description：专家普遍认为对**排名几乎没有/没有影响**，仍可能影响 CTR。按 **P2/P3 CTR 杠杆**，写明「不是已被证明的排名因子」。不要放进 F1 排名主线。

**必须 Unknown**：没有 GSC 时，整项线上行为（真实 CTR、pogo-stick、Navboost）= `Unknown`。有 GSC 才评：展示、点击、CTR、查询与着陆页是否匹配。不要用 bounce rate 当满意度。

**严重级别**：缺 description → P2（CTR，不是排名 P1）。title/description 过长过短或空泛 → P3。没有 GSC 不要给行为项 Pass。

#### F6. Brand Signals（27.0%）

**定义（调查）**：成为一个被人搜索、信任、访问的品牌/实体。

**专家实战要点**（调查观察，≠ 官方保证；与 F4 一起读）：

- **Branded search ≈ 新外链**（专家说法）：有品牌查询/GSC 品牌词数据才评。无数据 → `Unknown`，不编品牌词量。
- **被搜索、谈论、分享、提及**：外部流行度无数据保持 `Unknown`。代码只查实体是否一致、是否像可被提及的品牌而不是空壳。
- **Ad spend 几乎无直接作用**：最多间接可见度。不要把「加大广告」写成排名修复。广告不是 Fail/Pass 条件。

**代码仓库能查**：名称/logo/域名是否同一实体；About、`sameAs`、组织信息是否一致；favicon/OG 是否像一个品牌而不是空壳。

**必须 Unknown**：品牌词搜索量、外部提及、声誉。不要把「多投广告」写成排名动作。

**严重级别**：实体在代码里自相矛盾 → P2。OG/favicon 不完整 → P3。品牌强度默认 Unknown。

#### F7. User Satisfaction（19.8%）

**定义（调查）**：满意度或 **task completion** 是最终结果。

**专家实战要点**（调查观察，≠ 官方保证）：

- **Task completion 最高**：工具/游戏站首屏能不能做完那件事。无入口、纯 iframe、只有口号 → `Fail`（P1）。路径存在且可走完 → 代码侧可 Pass 代理；真实满意度仍 `Unknown`。
- **按页面类型做满意度代理**：工具=做成了；文章=问题答完；电商=能完成选品/下单信息。不要用 bounce。
- **UX 更多通过行为影响排名**（调查 UX 节，并入本因素 + F8）：布局妨碍完成任务 → 记 F7 `Fail`。没有行为数据时，不把「好看」写成排名 Pass。

**代码仓库能查**：工具/游戏入口是否真实存在、是否被 iframe 壳挡住、步骤是否通向可完成的动作、CTA 是否指向能用的功能。这是「任务是否可能完成」的代理。

**必须 Unknown**：真实满意度、回访、任务完成率、pogo-stick。不要用 bounce 代替。

**严重级别**：工具/游戏页无法完成任务（纯 iframe、无入口、坏流程）→ P1。任务路径含糊 → P2。真实满意度保持 Unknown。

#### F8. Technical SEO Health（17.5%）

**定义（调查）**：抓取与索引是其他因素的地基。

**专家实战要点**（调查观察，≠ 官方保证）：

- **商品化：赢不了比赛但能输掉**：F8 `Pass` 不等于会排名。P0/P1 抓取问题仍是 `Fail`（会摔）。不要把「技术分很高」写成增长解锁。
- **canonical 指错可立刻伤展示/点击**：指到 staging、首页、不相关 URL → `Fail`（P0/P1）。专家提过修对后展示/点击曾较快恢复——只写「曾有立即恢复的案例」，**不要编 +60% 或任何数字**。
- **越来越也是机器理解基础设施**：正文在初始 HTML、真实 schema、语义结构，是给爬虫/机器读的，不只是「给谷歌打分」。
- **UX / Speed / CWV 常被高估**（调查 UX 节并入）：能打开 vs 超时才是硬问题（超时/CSR 无正文 → `Fail`）。CWV 数字不当 P1。大电商另说：用户若提供「超大图导致关键模板数秒才可用」的证据，可作 P2 观察，仍不编实验室分数。

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

**专家实战要点**（调查观察，≠ 官方保证）：

- **关联到某主题的专家身份**：代码用支柱+集群当结构代理。只有孤立薄页 → `Fail`（P2）。主题下真实可见度/提及 → `Unknown`，不打权威分。
- **和 F3 信息增益、F10 主题连接一起看**：集群页若全是同构套话，结构在也不要给 F9 Pass 装成权威。

**代码仓库能查（结构代理，不是分数）**：是否有支柱页 + 集群；主词/二级/三级是否落到首页/分类/详情；目录站是否「分门别类」而不是孤立薄页。

**必须 Unknown**：该主题下的真实权威/可见度。

**严重级别**：只有孤立页、没有主题层级 → P2。结构代理可增强 → P3。不要输出「主题权威分」。

#### F10. Internal Links（11.1%）

**定义（调查）**：内链与信息架构。

**专家实战要点**（调查观察，≠ 官方保证）：

- **好内链 ≈ 很好的外链**（专家量级说法）：用来提高内链优先级，**不要**编「一条内链 = 一条外链」的分数。重要页孤儿 → `Fail`（P1）。
- **全站可控：决定 equity、重要页、主题连接**：查哪些钱页/任务页被导航和正文链到，主题是否互相指。只在 sitemap 出现 → `Fail`。输出必须是来源页 / 锚文本 / 目标页 / 原因。

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
| F1 Relevance / Search Intent Match | 57.1% | Pass/Fail/Unknown/N/A | 结果形态/title/H1；**域名意图匹配 / EMD 观察** | 竞品/SERP 信息增益常 Unknown | 非 EMD 不 Fail；不买垃圾 EMD |
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
（每项：专家实战要点对照、证据、Unknown、修复。金句要落到动作，不单引原话。）

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
- 不要建议为了 SEO 去买垃圾 / spammy EMD；不要因为品牌域不是 EMD 而把 F1 判 Fail。
- 不要只复述专家金句；每条实战观察都要落到查什么和 Pass/Fail/Unknown。不要把专家百分比写成 Google 官方权重。
