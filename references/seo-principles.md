# 中文 SEO 方法论整理

本文件按 **2026 Zyppy Top 10** 写主叙事，供代码审计复用。专家共识 ≠ Google 官方权重。不要机械套模板。本 skill 不替代 GSC/Ahrefs。对照 `zyppy-2026-ranking-factors.md` 与 `SKILL.md` 的 F1–F10。

旧叙事（一个词一个页、密度、TDK、八模块落地页、分门别类、内链、SSR、canonical）已拆进对应因素，不再当章节目录。

## F1. Relevance / Search Intent Match（57.1%）

相关 = 满足搜索者要的结果类型或任务，不是堆关键词。

专家实战（≠ 官方保证）：答非所问 → Fail，技术再好也救不了。十页都匹配意图后，多出来的信息决定胜负——无增量 → Fail，无 SERP → 增益 Unknown。EMD still effective：host 匹配主意图词只作加分观察，品牌域非 EMD 不 Fail，不买垃圾 EMD。

代码里看：

- URL 形态（工具 / 教程 / 对比 / 目录 / 产品）和查询要的形态是否一致。
- title、H1、首屏是否承诺同一件任务（标题相关性）。
- 工具/SaaS 是否具备完成任务所需模块：入口、步骤、能力、场景、有增量的 FAQ、相关页、再次 CTA。这些是意图子项，不是独立「八模块 SEO 宗教」。
- 一页只打一个主意图；冲突就拆页。
- 目标词在可见文本中自然出现即可。密度不是目标，不追求 3%–5%，不报「密度太低」。只抓异常堆砌。
- **EMD / 域名意图匹配**：检查 canonical host 是否精确或高度匹配主意图词（如 `bankstatementconverter.com`）。来源是 Zyppy 2026 专家评论（EMD still unexpectedly effective），≠ Google 官方保证。只当相关性加分观察；已有品牌域不是 EMD 不判 Fail；不要建议买垃圾 EMD。

上线后若有 GSC：先看查询与着陆页任务是否同一形态，再改 F1，而不是先改密度或换域名。

## F2. Backlinks（54.8%）

没有链接表时整项 Unknown。不要从代码发明外链数。

专家实战（≠ 官方保证）：100 条有真人受众的链 > 1000 条没人点的链；最强是高信任域 + 主题相关页。Spam 仍当大负向（即使谷歌口头说会忽略多数）。EM 锚看画像占比，过浓反噬。高质量提及可能连带抬 AI 可见度（Reuters 个例）—标推断，不编倍数。

有表时按质量评，不按数量：

- 信任域名 + 主题相关 + 来源页有真实访客。
- 垃圾链强负向。
- 精确匹配锚文本看它在画像中的占比，不是次数。

「收录稳定后开始做初始外链」应改成：只追求上述三类来源，不做兑换和目录堆量。

## F3. Content Quality（47.6%）

专家实战（≠ 官方保证）：一手数据抬头。AI 让内容变便宜，质量是过滤器；廉价规模 AI → Fail。高质量 AI + 人工深编 + 独特/UGC 可正例。共识太多看不见，增益过大又可能过专家向——找 Goldilocks。

代码里找代理：独特数据、方法、限制、真实 UGC；薄壳和重复模板。不要打质量分。不要伪造 schema 评论。

## F4. Authority & Trust（36.5%）

专家实战（≠ 官方保证）：流行度看被谈论/分享/链接/提及，无数据 Unknown。过专家向可能伤害大众可见度。品牌/信任强时技术和内容差点仍可能撑——但代码里的 P0 仍要修，强度本身 Unknown。

代码只能证明信任模块在不在：About、作者、来源、资质、真实组织信息。

YMYL 承诺型文案会破坏信任，必须改成信息性说明或撤主题。

## F5. Behavior / Click Signals（29.4%）

没有 GSC：行为本身 Unknown。Bounce rate 不用。

专家实战（≠ 官方保证）：Navboost 仍强；应按页面类型建满意度代理。点击差于同 SERP 竞品会有排名天花板（有比较表才 Fail）。Pogo-stick / Return to SERP 才是清晰负向。

代码只评 CTR 文案代理：

- title 点击力（与 F1 相关性分开）。
- meta description：不是已被证明的排名因子；缺了是 P2/P3 CTR，不进 F1。

有 GSC：看展示、点击、CTR、查询是否点到对的任务页；pogo-stick / 回 SERP 为负。

## F6. Brand Signals（27.0%）

专家实战（≠ 官方保证）：Branded search ≈ 新外链（专家说法），无品牌查询数据则 Unknown。Ad spend 几乎无直接作用，最多间接可见度，不要写成排名动作。

品牌词搜索量和外部声誉 Unknown。代码看名称、域名、logo、About、同一实体是否一致。

## F7. User Satisfaction（19.8%）

核心是 task completion。专家实战（≠ 官方保证）：按页面类型建满意度代理；UX 更多通过行为影响排名。工具站首屏能不能做完那件事（真入口，不是营销壳）。真实满意度 Unknown。不要用 bounce。

## F8. Technical SEO Health（17.5%）

Table stakes。专家实战（≠ 官方保证）：商品化——赢不了比赛但能输掉。canonical 指错可立刻伤展示/点击（只写「曾有立即恢复」，不编幅度）。越来越也是机器理解基础设施。Speed/CWV 常被高估：能打开 vs 超时；大电商另说。坏了能摔：robots/noindex、无 HTML、canonical 错、纯 CSR。好了也抬不起平庸内容。CWV 不当 P1。

旧「SSR / canonical / sitemap / robots」整段属于这里：

- 正文必须在初始 HTML 或构建产物里。
- canonical 用绝对 HTTPS、正确域名、每页一个；www/协议/斜杠/参数/别名靠它收口。
- sitemap 只列想被索引的 canonical。
- Next/Nuxt/Astro/SPA 的 head 与渲染方式是 F8 子项。

## F9. Topical Authority（14.3%）

结构代理：支柱 + 集群。专家实战（≠ 官方保证）：看站点是否被关联成某主题专家——结构能证代理，强度 Unknown。同构套话集群不要装成权威。目录站把主题分门别类映射到页面层级（例如 coloring pages → dog → cute dog）。

## F10. Internal Links（11.1%）

专家实战（≠ 官方保证）：好内链 ≈ 很好的外链（量级说法，不编分）。全站可控：决定 equity、重要页、主题连接。首页链二级、二级链三级、下级用清楚锚文本回链。输出必须是来源页 / 锚文本 / 目标页 / 原因。外链质量仍在 F2。

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
