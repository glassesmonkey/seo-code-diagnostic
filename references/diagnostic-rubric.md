# SEO 代码诊断 Rubric

按 2026 Zyppy Top 10 重组。每一因素先定 `Pass` / `Fail` / `Unknown` / `N/A`，再用 P0–P3 排修复顺序。专家共识 ≠ 官方权重。没有线上数据不要编造。对照 `SKILL.md` 与 `zyppy-2026-ranking-factors.md`。

状态规则：

- `Fail`：代码或用户提供的线上证据已证明问题。
- `Unknown`：需要 GSC / 外链表 / 品牌 / 用户研究，且用户没给。
- `Pass`：该因素在**代码可证范围**内未见问题；hybrid/线上因素没有用户数据时不要标 Pass。
- `N/A`：该因素对站点类型确实不适用（少见）。

## F1 Relevance / Search Intent Match（57.1%）

定义：满足结果类型/任务；含 information gain。meta description 不在本表。

| 检查项 | 挂入的旧项 | 级别 | 代码证据 | 修复 |
|---|---|---|---|---|
| 结果形态错 / 答非所问 | 意图错配 | P1 | 页面类型与查询要的工具/教程/对比/目录相反 | 改内容或拆页 |
| 缺 title | TDK title | P1 | 无 title | 写能表达本页任务的唯一 title |
| title 与任务偏离 | TDK / 关键词覆盖 | P2 | 正文在做 A，title 在说 B | 先改相关性 |
| 缺 H1 / 多 H1 | 语义结构 | P1 | h1 数量 ≠ 1 | 一个主 H1 表达任务 |
| 意图模块残缺 | 落地页八模块 | P2 | 工具页无步骤/场景/有增量的 FAQ | 按任务补模块，不是为了凑八块 |
| 目标词应出现却没有 | 关键词覆盖 | P2 | 可见文本无目标词 | 自然覆盖；不要补密度 |
| 堆砌 | 密度 | P2 | 密度异常高或机械重复 | 改成解释。不报密度低 |
| H2/H3 跳级 | 语义结构 | P2/P3 | 标题跳级 | 按用户问题分层 |
| 域名意图匹配 / EMD | 新子项 | 观察，不单独 Fail | `--domain` 或 canonical host 是否精确/高度匹配主意图词（如 `bankstatementconverter*.*`） | 写入 F1 行。来源：Zyppy 2026 专家评论（EMD still effective），≠ 官方保证。加分观察。品牌域非 EMD **不 Fail**。不要建议购买垃圾 / spammy EMD |

线上：竞品是否已被同一意图覆盖、你的信息增益够不够 → 常 `Unknown`。EMD 贡献本身也不是官方权重。

## F2 Backlinks（54.8%）

默认整项 `Unknown`。代码几乎无证。

用户提供链接表时：

| 检查项 | 级别 | 怎么判 | 动作 |
|---|---|---|---|
| 信任域 + 主题相关 + 来源有访客 | — | 正向 | 保持；不要追求条数 |
| 垃圾/无关/无人读的链 | P1/P2 | 负向 | 停购、拒垃圾、disavow 仅当用户数据支持 |
| 精确匹配锚文本占比 | P2 | 双刃，看画像占比 | 提高品牌/描述性锚，不数次数 |

## F3 Content Quality（47.6%）

| 检查项 | 挂入的旧项 | 级别 | 代码证据 | 修复 |
|---|---|---|---|---|
| 无一手/原创 | 内容薄 | P1/P2 | 只有套话或竞品同构 | 补 Original Research / First-Party Data / 独特限制 |
| 规模化低质 AI / 薄壳 | 薄内容、占位 | P1 | 重复壳、占位、模型痕迹 | 停批量；留人工编审过的页 |
| 关键信息只在图里 | 图片 SEO | P2 | 表格/步骤是图片 | 改成 HTML 文本 |
| 假 schema/评论 | 结构化数据 | P1 | 无真实评价却有 AggregateRating | 删掉伪造 |

准确性/新鲜度的外部验证 → `Unknown`。内部泄露同时记入本因素与横切。

## F4 Authority & Trust（36.5%）

| 检查项 | 级别 | 代码证据 | 修复 |
|---|---|---|---|
| YMYL 承诺/诊断/保证 | P1 | 主题 + 断言同现 | 改信息性说明或撤主题 |
| 无身份/来源 | P2 | 无 About/作者/来源 | 补真实身份，不写假资质 |
| 信任模块可增强 | P3 | 无更新说明 | 按需补充 |

信任强度、外部口碑 → `Unknown`。

## F5 Behavior / Click Signals（29.4%）

无 GSC：线上行为 `Unknown`。代码只处理 CTR 文案。

| 检查项 | 挂入的旧项 | 级别 | 说明 |
|---|---|---|---|
| 缺 meta description | 旧 P1 TDK | **P2** | CTR 杠杆，**不是已被证明的排名因子** |
| title/description 不利于点击 | 旧长度 P3 | P3 | 与 F1 title 相关性分开 |
| 真实 CTR / pogo-stick | — | — | 有 GSC 才评；bounce 不用 |

## F6 Brand Signals（27.0%）

| 检查项 | 级别 | 代码 | 线上 |
|---|---|---|---|
| 名称/域名/logo 实体不一致 | P2 | 可查 | — |
| OG/favicon 不完整 | P3 | 可查 | — |
| 品牌词量、声誉 | — | 无 | `Unknown` |
| 广告花费 | — | 不作为动作 | 几乎无直接排名作用 |

## F7 User Satisfaction（19.8%）

| 检查项 | 挂入的旧项 | 级别 | 代码证据 |
|---|---|---|---|
| 首屏无法完成任务 | 工具/游戏薄壳 | P1 | 无入口、纯 iframe、只有口号 |
| 任务路径含糊 | 落地页模块 | P2 | 有文案无动作 |
| 真实满意度 | — | — | `Unknown`；不用 bounce |

## F8 Technical SEO Health（17.5%）

Table stakes：坏了能摔，好了不抬内容。CWV 不当 P1。

| 检查项 | 挂入的旧项 | 级别 | 代码证据 | 修复 |
|---|---|---|---|---|
| 核心页 noindex | 抓取 | P0 | robots meta noindex | 去掉或按类型条件化 |
| robots 误封全站 | 抓取 | P0 | `Disallow: /` | 生产环境放行 |
| 纯 CSR 无正文 | SSR | P0 | 只有 root + script | SSR/SSG/prerender |
| canonical 错域名/死链 | canonical | P0 | staging/localhost | 生产 HTTPS 绝对 URL |
| 动态页同一 HTML | 渲染 | P0/P1 | 所有 slug 同一 title/正文 | 按数据生成 |
| sitemap/robots 测试域 | 抓取 | P0 | localhost URL | 统一 host |
| 缺 canonical / 多个 canonical / 非绝对 | canonical | P1 | link rel | 每页一个绝对 HTTPS |
| sitemap 缺失或域名错 | sitemap | P1 | 无入口或 host 错 | 只列 canonical |
| 缺 viewport | 移动 | P2 | 无 viewport | 补上 |
| 图片无尺寸、未压缩 | 性能 | P3 | 无 width/height | 组件+压缩；不当增长项 |
| robots 未声明 sitemap | robots | P3 | 无 Sitemap 行 | 补地址 |
| OG 与 canonical 冲突 | head | P3 | og:url ≠ canonical | 对齐 |

框架专项（Next metadata、SPA prerender、Nuxt useHead、构建 HTML）全部是 F8 子项。真实收录、CWV 数字 → `Unknown` 除非用户提供。

## F9 Topical Authority（14.3%）

| 检查项 | 挂入的旧项 | 级别 | 代码证据 |
|---|---|---|---|
| 无支柱+集群 | 关键词层级、分门别类 | P2 | 只有孤立页 |
| 目录站主题未分层 | H2/H3 目录策略 | P2 | 首页不映射二级/三级主题 |
| 权威强度 | — | — | `Unknown`，不打分 |

## F10 Internal Links（11.1%）

| 检查项 | 挂入的旧项 | 级别 | 代码证据 | 修复 |
|---|---|---|---|---|
| 重要页孤儿 | 内链 | P1 | sitemap 有、站内无入口 | 从支柱/分类链入 |
| 内链过少、层级断 | 内链 | P2 | 正文几乎无内链 | 上→下、下→上、相关 |
| 泛锚文本 | 内链 | P3 | click here | 描述目标主题 |

## 横切：YMYL / 内部泄露

默认扫描。YMYL 承诺 → P1，证据同时可挂 F4。内部/prompt/思考过程 → P1，证据同时可挂 F3。

## 页面类型 → 因素映射（不再当主目录）

| 站点类型 | 主要落到 |
|---|---|
| 工具 / SaaS | F1 任务形态 + F7 首屏完成 + F3 一手说明 |
| 目录 / coloring pages | F9 分层 + F1 形态 + F10 分类↔详情 |
| 博客 | F1 意图 + F3 原创/来源 + F9 支柱 |
| 电商 | F1 产品意图 + F8 分面 canonical + F3 独特分类文本 |
| 游戏 / 工具 AdSense | 独立 ADS-* 章；薄壳同时打 F3/F7 |

## AdSense 审核专项（独立，不并入 Top 10 主表）

核心问题：值不值得展示广告，还是低质套壳。完整 73 项见 `adsense-requirements.md`。

P0：不可访问、4xx/5xx、robots/noindex 阻断、缺 Contact/Privacy/Terms、政策红线、canonical/sitemap 错域。

P1：纯 iframe、工具只有入口、核心页很薄、通用模板、批量占位。

P2：缺 Blog/Guides、原创不足 5 篇、分类无说明、长尾无页面、有 GSC 时 5–20 名低点击查询未处理、内链未串起来。

P3：视觉 polish、OG、真实 schema、freshness、额外信任信号。
