# 2026 Zyppy Google Ranking Factors Expert Survey

本文件把 Zyppy 专家调研翻译成 **seo-code-diagnostic 的判断边界**。它校准优先级和措辞，不把专家投票变成可计算的排名权重。

## 来源与边界

- **文章**：Cyrus Shepard & Dawn Shepard, “2026 Google Ranking Factors Expert Survey”
- **URL**：https://signal.zyppy.com/p/google-ranking-factors-expert-survey
- **日期**：2026-09-09
- **样本**：131 位 SEO；每位评估 100+ 个潜在因子（+3 到 -3），并回答开放题「最重要的三个 Google 排名因子」
- **数据量**：文中称 13,665 个排名因子数据点

**专家共识 ≠ Google 官方权重。** 本 skill 仍然是代码仓库审计，不是 Ahrefs / Semrush / Google Search Console 的替代品。没有用户提供的线上数据时，对应信号必须标 `Unknown`，禁止编造搜索量、排名、CTR、外链数量、品牌词量或「权威分」。

## Top 10（开放题「Top 3」入选比例）

| 因子 | Top 3 入选 | 调研原意（摘要） | 本 skill 怎么用 |
|---|---:|---|---|
| Relevance | 57.1% | 内容匹配并满足搜索意图 | 代码可推断：页面类型、任务模块、title/H1/正文；**域名意图匹配 / EMD 观察**（加分，品牌域非 EMD 不 Fail） |
| Backlinks | 54.8% | 来自受信任、主题相关、有真实访问的页面的链接 | 无数据 = `Unknown`；不追求链接数量 |
| Content Quality | 47.6% | 原创、准确、新鲜；一手数据 | 代码可推断：是否有原创/一手/独特解释；批量低质 AI 标风险 |
| Authority & Trust | 36.5% | Google 对站点/创作者/品牌的信任 | 代码只能看信任模块是否存在；强度 = `Unknown` |
| Behavior / Click | 29.4% | 用户如何点结果、如何与页面互动 | 无 GSC = `Unknown` |
| Brand | 27.0% | 被人搜索、信任、回访的品牌/实体 | 品牌词量/口碑 = `Unknown` |
| User Satisfaction | 19.8% | 满意度或任务完成 | 无行为数据 = `Unknown` |
| Technical SEO | 17.5% | 抓取与索引是其他因子的地基 | **Table stakes**：差会输，好也抬不起平庸内容 |
| Topical Authority | 14.3% | 品牌/站点是否被当成某主题专家 | 结构集群是代理，不是分数 |
| Internal Links | 11.1% | 站内连接与信息架构 | 代码可证明；可端到端控制的杠杆 |

## 必须融合进诊断的子要点

### 1. Search Intent Match 是相关性第 1

调研定义：页面是否满足搜索者想要的**结果类型或任务**，而不只是关键词或语义相近。

- 技术完美但答非所问，救不了排名。
- **信息增益**：当很多页面都已匹配意图并覆盖同一范围时，差别在于有没有别人没有的东西。
- 代码侧：对照页面类型（工具/教程/对比/目录）和模块（步骤、示例、FAQ、数据），判断是否在完成该任务。不要用关键词密度代替意图匹配。
- **EMD（Exact Match Domain）**：专家评论写到 EMD 仍然 unexpectedly effective（同一竞争词上，EMD 可比主品牌域更省力）。本 skill 把它挂在 F1：检查 canonical host / 域名是否精确或高度匹配主意图词（如 `bankstatementconverter*.*`）。只作相关性加分观察，**≠ Google 官方保证**。不要建议为了 SEO 去买垃圾 / spammy EMD；已有品牌域不因「不是 EMD」判 Fail。报告 Top 10 的 Relevance 行必须写出「域名意图匹配 / EMD 观察」。

### 2. Meta description 不是排名 P1

专家普遍认为 meta description 对排名几乎没有 / 没有影响。它仍可能影响 SERP CTR。

- 缺 description → **P2/P3 CTR 杠杆**
- 明确写：**不是已被证明的排名因子**
- 不要因为缺 description 把它写成 P1「排名关键项」

### 3. 外链看质量，不看数量

调研里评分很高的是：

- 来自高度受信任域名的链接
- 来自主题相关页面的链接
- 来自「真有访问」的页面的链接（「一百个有真实读者的链接，胜过一千个没人点的链接」）

同时：

- 垃圾链被评为最强负向之一（即便 Google 声称会忽略大部分垃圾链）
- 精确匹配锚文本两边都有刀：到一定比例有帮助，超过则伤；变量是它在锚文本画像中的**占比**，不是原始次数

代码审计**不得**编造外链指标。用户没给 Ahrefs/GSC/链接表时，整段标 `Unknown`。

### 4. 内容质量：一手数据；低质规模化 AI 为负

- **Original Research / First-Party Data** 排在内容质量前列。
- 规模化、几乎不增值的 AI 内容：负向。
- 高质量 AI + 严格人工编辑 + 站点已有独特内容/UGC：专家里有人认为可以。
- 代码侧找代理：独特数据、方法、示例、限制说明、真实 UGC；不要给「AI 内容质量分」。

### 5. 品牌：口碑与品牌词；广告花费几乎无直接作用

- 重要的是线上声誉/信任，以及有多少人用品牌名搜索你。
- Google 广告花费：勉强偏正，且多被认为是间接（提高可见度），不是直接排名开关。
- 代码侧只能检查 About、作者、来源、评价等信任模块是否存在且真实。

### 6. 用户信号：任务完成最高；pogo-stick 为负；跳出率是差代理

- **Satisfaction / Task Completion** 在用户信号里最高。
- **Return to SERP / pogo-stick** 为负向。
- Bounce rate 不是好指标。
- 没有 GSC 或用户研究时标 `Unknown`。报告里可以提醒：看点击质量、查询与着陆页是否匹配，不要用 bounce 当满意度。

### 7. 技术 SEO 是 table stakes

- 抓取和索引是其他因子的地基。
- 大多数受访者把它说成桌面筹码：**坏的技术 SEO 会让你输掉；好的技术 SEO 不会把平庸内容抬上去。**
- Core Web Vitals / 速度：争议大，常被高估。能加载通常就够；本 skill 不把 CWV 当 P1 增长项。
- 本 skill 仍把 robots/noindex/canonical/sitemap/纯 CSR 无正文保持为 **P0/P1 阻断或高影响**——那是「会输」的那一侧，不是增长解锁。

### 8. 内链是可控制的强杠杆

专家强调：内链决定哪些页积累权重、Google 把哪些页读成重要、主题如何在站内连接。执行得好时，一条好内链可以被看成接近一条很好的外链。代码审计必须给出具体「来源页 / 锚文本 / 目标页 / 原因」。

## 专家实战要点 → 诊断动作

调查正文里的专家观察必须写进 skill，不能只留 Top 10 百分比。以下全部是**专家实战 / 调查**，≠ Google 官方保证。诊断时写成查什么、何时 `Pass` / `Fail` / `Unknown`。

### Relevance（F1）

| 专家观察 | 查什么 | 状态 |
|---|---|---|
| 技术完美但答非所问救不了 | 结果形态 vs 查询要的任务 | 形态错 → `Fail`；对得上再看模块 |
| 十页都匹配后，多出来的信息决定胜负 | 本页是否有竞品没有的一手/限制/方法 | 无增量 → `Fail`；无 SERP → 增益 `Unknown` |
| EMD still unexpectedly effective | canonical host 是否精确/高度匹配主意图词 | 加分观察；品牌域非 EMD **不** `Fail`；不买垃圾 EMD |

### Backlinks（F2）

| 专家观察 | 查什么 | 状态 |
|---|---|---|
| 100 条有真人受众 > 1000 条没人点 | 来源页是否像有真实读者 | 无链接表 → `Unknown`；不按条数 Pass |
| 高信任域 + 主题相关页最强 | 来源域名信任度 + 来源页主题 | 有表且符合可偏正；农场/兑换 → `Fail` |
| Spam 仍是大负向（即使谷歌口头说会忽略多数） | 垃圾/隐藏/页脚农场占比 | 主导 → `Fail` |
| EM 锚文本看画像占比，过浓反噬 | 精确匹配锚占比，不是条数 | 过浓 → `Fail`/P2 |
| 高质量提及或抬 AI 可见度（Reuters 个例） | 用户是否提供提及/AI 引荐 | 只标推断；无数据 → `Unknown`；不编倍数 |

### Content Quality（F3）

| 专家观察 | 查什么 | 状态 |
|---|---|---|
| Original Research / First-Party Data 抬头 | 是否有自己的数据、实验、限制 | 无 → `Fail` 代理 |
| AI 让内容变便宜，质量是过滤器；廉价规模 AI 负向 | 重复壳、可替换词、无增量 | 是 → `Fail` |
| 高质量 AI + 人工深编 + 独特/UGC 可正例 | 编审痕迹、UGC、独特模块 | 有则不要只因「像 AI」Fail |
| 共识太多看不见；增益过大可能过冲（Goldilocks） | 是复述还是只写给同行 | 两端极端 → P2 观察；缺竞品 → `Unknown` |

### Authority & Brand（F4 / F6）

| 专家观察 | 查什么 | 状态 |
|---|---|---|
| 流行度：被谈论、分享、链接、提及 | 外部提及/分享 | 无数据 → `Unknown` |
| 过专家向可能伤害大众可见度 | 普通用户能否完成任务 | 只有同行黑话 → P2，回看 F1/F3 |
| 品牌信号强时技术/内容可差点仍能撑 | 品牌查询/口碑 | 强度 `Unknown`；**不**用来放过 F8 P0 |
| Branded search ≈ 新外链（专家说法） | GSC 品牌词 | 无数据 → `Unknown` |
| Ad spend 几乎无直接作用，最多间接可见度 | — | 不作为 Pass/Fail 或修复动作 |

### User / Behavior（F5 / F7）

| 专家观察 | 查什么 | 状态 |
|---|---|---|
| Navboost 仍强；按页面类型建满意度代理 | 工具做成了？文章答完了？ | 无 GSC/研究 → 线上 `Unknown` |
| Bounce rate 烂代理 | — | 禁止当 Pass/Fail |
| Pogo-stick / Return to SERP 清晰负向 | 是否有回 SERP 证据 | 有 → `Fail`；无 → `Unknown` |
| 点击差于同 SERP 竞品会有排名天花板 | 同类位置 CTR 比较 | 有表且明显落后 → `Fail`；无表 → `Unknown` |
| Task completion 最高 | 首屏能否完成任务 | 无入口/纯 iframe → `Fail` |

### Technical + UX（F8，UX 并入）

| 专家观察 | 查什么 | 状态 |
|---|---|---|
| 商品化：赢不了比赛但能输掉 | 抓取/SSR/canonical 会不会摔 | P0/P1 → `Fail`；Pass ≠ 会赢 |
| canonical 指错可立刻伤展示点击 | canonical 是否指错页/错域 | `Fail`；只写「曾有立即恢复」，不编幅度 |
| 越来越也是机器理解基础设施 | 初始 HTML 正文、真实 schema | 无正文 → `Fail` |
| UX 更多通过行为影响排名 | 布局是否挡任务 | 挡任务 → 记 F7 |
| Speed/CWV 常被高估；能打开 vs 超时；大电商另说 | 打得开？CSR 空壳？超时？ | 打不开/空壳 → `Fail`；CWV 不当 P1 |

### Internal links（F10）

| 专家观察 | 查什么 | 状态 |
|---|---|---|
| 好内链 ≈ 很好的外链（量级说法） | 重要页是否有上下文内链 | 提高优先级；不编等价分数 |
| 全站可控：equity、重要页、主题连接 | 导航/正文谁链向钱页；孤儿 | 孤儿 → `Fail`；写出源→锚→目标 |

### 9. Title 拆成两件事

| 检查 | 问什么 | 优先级 |
|---|---|---|
| 标题相关性 | title 是否表达本页要满足的意图/任务 | 按 on-page 相关性，通常 P1（缺失）或 P2（错配） |
| 标题/描述点击 | title 与 description 是否在 SERP 上说清价值、吸引点击 | CTR 杠杆，P2/P3；description 不按排名 P1 |

## 三层证据规则（禁止发明指标）

| 层 | 例子 | 报告写法 |
|---|---|---|
| 代码能证明 | noindex、缺 title/H1/canonical、sitemap、CSR 无正文、内链层级、可见文本厚度 | 给文件、摘录、修复 |
| 代码可推断 | 意图模块缺口、薄内容、缺一手信息、标题与任务错配、批量 AI 套话 | 写代理证据；不要打「质量分」 |
| 必须线上验证 | GSC CTR、品牌查询、外链质量、任务完成、pogo-stick、主题权威强度 | 默认 `Unknown`；列出缺什么数据 |

## 本 skill 明确不再采用的旧口径

- 把关键词密度 3%–5%（上限 8%）当成诊断或优化目标。
- 因为「密度太低」而报警或要求补密度。
- 把缺 meta description 写成 P1 排名关键项。
- 把技术 SEO / CWV 写成增长解锁。
- 把「多做外链」写成上线后主路径；应写成信任 + 主题相关 + 真实读者。

密度只保留一个用途：异常高时提示堆砌。覆盖缺失用「目标词未出现 / 意图未覆盖」，不用「密度偏低」。

## Skill 章节 ↔ 因素一一映射

打开 `SKILL.md` 的「标准工作流 / 必查项」应直接是 F1–F10，每项含 **专家实战要点**（可执行，不是金句墙）。下表是硬映射。

| 因素 | SKILL.md | seo-principles.md | diagnostic-rubric.md | 脚本报告章节 | 旧检查挂到哪里 |
|---|---|---|---|---|---|
| F1 Relevance 57.1% | `#### F1` + 专家实战（答非所问/增益/EMD） | 同名章 + 实战 | 同名表 + 实战动作 | Top 10 主表必须含「域名意图匹配 / EMD 观察」+ F1 分项 | title 相关性、H1、意图模块、关键词覆盖、堆砌、**EMD** |
| F2 Backlinks 54.8% | `#### F2. Backlinks` | 同名章 | 同名表 | 主表默认 Unknown | 外链；有链接表才评信任/主题/真实访客/垃圾/EM 锚 |
| F3 Content Quality 47.6% | `#### F3. Content Quality` | 同名章 | 同名表 | 主表 + 薄内容/一手代理 | 薄页、一手数据、规模 AI、假 schema |
| F4 Authority & Trust 36.5% | `#### F4. Authority & Trust` | 同名章 | 同名表 | 主表 | About/作者/来源；YMYL 承诺 |
| F5 Behavior / Click 29.4% | `#### F5. Behavior / Click Signals` | 同名章 | 同名表 | 主表；无 GSC=Unknown | title CTR、**meta description 只挂这里** |
| F6 Brand Signals 27.0% | `#### F6. Brand Signals` | 同名章 | 同名表 | 主表 | 实体一致性；广告花费不作为动作 |
| F7 User Satisfaction 19.8% | `#### F7. User Satisfaction` | 同名章 | 同名表 | 主表 | 工具首屏能否完成任务 |
| F8 Technical 17.5% | `#### F8. Technical SEO Health` | 同名章 | 同名表 | 主表 | 抓取、SSR/CSR、canonical、sitemap、框架 head、CWV 不当 P1 |
| F9 Topical Authority 14.3% | `#### F9. Topical Authority` | 同名章 | 同名表 | 主表 | 支柱+集群、目录站分门别类 |
| F10 Internal Links 11.1% | `#### F10. Internal Links` | 同名章 | 同名表 | 主表 | 层级、孤儿、锚文本 |
| 横切 | `### 4. 横切检查` | 文末横切 | 文末横切 | 文案风险节 | YMYL、内部泄露 |
| AdSense | `### 5. AdSense…（独立章节）` | 点到 ADS 文件 | 独立专项 | AdSense 节 | 全部 ADS-*，不并入主表 |

输出主表必须是上面 10 行，状态为 `Pass` / `Fail` / `Unknown` / `N/A`。

