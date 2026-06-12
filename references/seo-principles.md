# 中文 SEO 方法论整理

本文件是对中文 SEO 实践经验的结构化整理，供 Codex 做代码审计时复用。不要机械套模板；每次要结合网站类型、关键词和代码实现判断。

## 1. 一个关键词要有一个真正说透的页面

如果想获取某个关键词的自然搜索流量，就要围绕这个关键词做一个对应页面。页面不只是放一个标题，而是要把用户围绕这个词会关心的内容讲清楚。

典型工具落地页模块：

1. 工具名称、核心卖点、工具入口；
2. How it works：具体任务步骤；
3. Features：功能点和差异点；
4. 更细的使用流程或应用场景；
5. FAQ；
6. 用户证言/信任信号；
7. 相关功能/相关关键词链接列表；
8. 再次 CTA 或工具入口。

诊断代码时，不能只看页面是否漂亮，要看源 HTML 中有没有这些可读内容。

## 2. 关键词密度作为辅助，不作为唯一目标

核心关键词密度可参考 3%–5%，不要超过 8%。

但诊断时要避免把页面变成关键词堆砌。更好的做法是：

- 在 title、H1、首段、关键 H2、FAQ、内链 anchor 中自然覆盖主词；
- 用同义词、二级词、三级词、场景词、问题词围绕主词解释；
- 关键词密度过低时优先补充真实内容，而不是重复同一句话。

## 3. HTML 语义结构必须清晰

每个核心页面都需要：

- title；
- meta description；
- canonical；
- 一个 H1；
- 多个有层级的 H2/H3；
- 正文 p / list / table；
- img + alt；
- 必要时 JSON-LD schema。

title 更偏搜索结果和搜索引擎理解；H1 更偏用户进入页面后的主题确认。两者可以相近，但不能混乱或缺失。

## 4. “分门别类罗列”是目录站/工具站/内容站首页的关键策略

首页或支柱页要把主词、二级词、三级词分门别类展示出来。

以 coloring pages 为例：

- H1：coloring pages
- H2：dog coloring pages
  - H3：cute dog coloring pages
  - H3：little dog coloring pages
- H2：cat coloring pages
  - H3：cute cat coloring pages
  - H3：little cat coloring pages
- H2：flower coloring pages
  - H3：red flower coloring pages
  - H3：yellow flower coloring pages

审计时要判断站点是否把关键词层级映射到了页面层级和标题层级，而不是只有孤立页面。

## 5. 内链建设不亚于外链

站内链接应符合层级：

- 首页链接到二级关键词页；
- 二级关键词页链接到三级关键词页；
- 三级关键词页用明确锚文本链接回二级关键词页；
- 二级关键词页链接回首页；
- 所有核心页面自然链接回首页或主支柱页；
- 页面中提到某个关键词时，尽量链接到站内对应页面。

诊断输出要给具体内链建议：来源页、锚文本、目标页、为什么要加。

## 6. 新站优先后端渲染或静态生成

核心 SEO 内容需要直接体现在 HTML 源代码里。不能只靠前端 JS 渲染后才出现。

审计时要做两层检查：

1. 源码或组件里有没有 SEO 内容；
2. 构建后/查看源代码时，title、description、H1、正文、canonical、内链是否真的出现在 HTML 中。

对于纯 SPA 或整页 Client Component，要标为风险，并建议 SSR/SSG/prerender。

## 7. URL 唯一和 canonical 非常重要

一个页面可能可以通过多个 URL 访问，例如：

- www 与裸域名；
- http 与 https；
- trailing slash 与 non-trailing slash；
- 参数 URL；
- 别名 URL；
- 多语言/地区 URL。

每个页面要通过 canonical 告诉搜索引擎规范 URL。canonical 应该：

- 使用绝对 URL；
- 使用正确域名；
- 使用 HTTPS；
- 每页只有一个；
- sitemap 和内链尽量使用 canonical URL。

## 8. 上线后的 SEO 迭代节奏

这部分通常不能只靠代码判断，但报告可以提醒用户：

1. 建站初期先筛词库，优先做容易词，归类后布局到页面；
2. 上线后提交 Google Search Console，先看收录是否稳定增长；
3. 收录稳定后开始做初始外链；
4. 如果反馈好，继续增加页面，布局更多长尾词；
5. 通过 Ahrefs/Semrush 看词库增长；
6. 关注前 20 名关键词，对这些页面做 on-page 优化；
7. 优化后不要频繁改动，观察 1–2 周；
8. 有页面进首页后，总结共性，再复制到下一批页面。
