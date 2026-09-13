# 中文 SEO 方法论整理

本文件按 **2026 Zyppy Top 10** 写主叙事，供代码审计复用。专家共识 ≠ Google 官方权重。不要机械套模板。本 skill 不替代 GSC/Ahrefs。对照 `zyppy-2026-ranking-factors.md` 与 `SKILL.md` 的 F1–F10。

旧叙事（一个词一个页、密度、TDK、八模块落地页、分门别类、内链、SSR、canonical）已拆进对应因素，不再当章节目录。

## F1. Relevance / Search Intent Match（57.1%）

相关 = 满足搜索者要的结果类型或任务，不是堆关键词。技术完美但答非所问，救不了。

很多页都已匹配意图时，比的是 information gain：一手数据、独特方法、竞品没写的限制或反例。

代码里看：

- URL 形态（工具 / 教程 / 对比 / 目录 / 产品）和查询要的形态是否一致。
- title、H1、首屏是否承诺同一件任务（标题相关性）。
- 工具/SaaS 是否具备完成任务所需模块：入口、步骤、能力、场景、有增量的 FAQ、相关页、再次 CTA。这些是意图子项，不是独立「八模块 SEO 宗教」。
- 一页只打一个主意图；冲突就拆页。
- 目标词在可见文本中自然出现即可。密度不是目标，不追求 3%–5%，不报「密度太低」。只抓异常堆砌。

上线后若有 GSC：先看查询与着陆页任务是否同一形态，再改 F1，而不是先改密度。

## F2. Backlinks（54.8%）

没有链接表时整项 Unknown。不要从代码发明外链数。

有表时按质量评，不按数量：

- 信任域名 + 主题相关 + 来源页有真实访客。
- 垃圾链强负向。
- 精确匹配锚文本看它在画像中的占比，不是次数。

「收录稳定后开始做初始外链」应改成：只追求上述三类来源，不做兑换和目录堆量。

## F3. Content Quality（47.6%）

优先 Original Research / First-Party Data。规模化低质 AI 为负。人工编审过的 AI + 独特内容/UGC 可以接受。

代码里找代理：独特数据、方法、限制、真实 UGC；薄壳和重复模板。不要打质量分。不要伪造 schema 评论。

## F4. Authority & Trust（36.5%）

代码只能证明信任模块在不在：About、作者、来源、资质、真实组织信息。信任强度 Unknown。

YMYL 承诺型文案会破坏信任，必须改成信息性说明或撤主题。

## F5. Behavior / Click Signals（29.4%）

没有 GSC：行为本身 Unknown。Bounce rate 不用。

代码只评 CTR 文案代理：

- title 点击力（与 F1 相关性分开）。
- meta description：不是已被证明的排名因子；缺了是 P2/P3 CTR，不进 F1。

有 GSC：看展示、点击、CTR、查询是否点到对的任务页；pogo-stick / 回 SERP 为负。

## F6. Brand Signals（27.0%）

品牌词搜索量和外部声誉 Unknown。代码看名称、域名、logo、About、同一实体是否一致。广告花费几乎无直接排名作用，不要写成主动作。

## F7. User Satisfaction（19.8%）

核心是 task completion。工具站：首屏能不能做完那件事（真入口，不是营销壳）。

真实满意度 Unknown。代码只判断任务路径是否存在且可走完。

## F8. Technical SEO Health（17.5%）

Table stakes。坏了能摔：robots/noindex、无 HTML、canonical 错、纯 CSR。好了也抬不起平庸内容。CWV 常被高估，不当 P1。

旧「SSR / canonical / sitemap / robots」整段属于这里：

- 正文必须在初始 HTML 或构建产物里。
- canonical 用绝对 HTTPS、正确域名、每页一个；www/协议/斜杠/参数/别名靠它收口。
- sitemap 只列想被索引的 canonical。
- Next/Nuxt/Astro/SPA 的 head 与渲染方式是 F8 子项。

## F9. Topical Authority（14.3%）

结构代理：支柱 + 集群。目录站把主题分门别类映射到页面层级和标题层级（例如 coloring pages → dog → cute dog），这是 F9，不是独立「首页策略章」。权威强度 Unknown，不打分。

## F10. Internal Links（11.1%）

可控杠杆。首页链二级、二级链三级、下级用清楚锚文本回链、提到某主题就链到对应页。输出必须是来源页 / 锚文本 / 目标页 / 原因。外链质量仍在 F2，不要和内链混成「链接数量」。

## 横切

- YMYL 与内部/prompt/模型痕迹：默认检查，证据可挂 F3/F4。
- AdSense：独立清单，见 `adsense-requirements.md`。

## 上线后节奏（仍按因素，不是旧 8 步清单）

1. F1：按意图形态布页，不按密度。
2. F8：提交 GSC，先保证能被抓到；这是桌面筹码。
3. F5/F7：有数据再看点击质量和任务是否完成。
4. F2：只要信任 + 相关 + 有读者的链接。
5. F3/F9/F10：有信息增益的新页 + 集群 + 内链。
6. 不要编造 Ahrefs 词库增长或外链数字。
