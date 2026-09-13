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
| Relevance | 57.1% | 内容匹配并满足搜索意图 | 代码可推断：页面类型、任务模块、title/H1/正文是否答在点上 |
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

打开 `SKILL.md` 的「标准工作流 / 必查项」应直接是 F1–F10，而不是旧 TDK 目录。下表是硬映射。

| 因素 | SKILL.md | seo-principles.md | diagnostic-rubric.md | 脚本报告章节 | 旧检查挂到哪里 |
|---|---|---|---|---|---|
| F1 Relevance 57.1% | `#### F1. Relevance / Search Intent Match` | 同名章 | 同名表 | Top 10 主表 + F1 分项 | title 相关性、H1、意图模块、关键词覆盖、堆砌（非密度目标） |
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

