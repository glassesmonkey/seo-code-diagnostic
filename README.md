# SEO Code Diagnostic Skill

一个用于 Codex 的网站代码 SEO 和 AdSense 审核诊断 skill。

它是**代码仓库审计**，不是 Ahrefs / Google Search Console 的替代品。`SKILL.md` 的工作流和报告主表按 [2026 Zyppy Google Ranking Factors Expert Survey](https://signal.zyppy.com/p/google-ranking-factors-expert-survey) 的 Top 10 组织（Relevance → Internal Links）。专家共识 ≠ Google 官方权重。旧 TDK / 密度 / 八模块落地页不再当目录，只作为对应因素的子项。F1 含域名意图匹配 / EMD 观察（专家评论，≠ 官方保证；品牌域非 EMD 不 Fail）。meta description 只挂在 F5 CTR；密度只抓堆砌。没有 GSC/外链表/品牌数据时，F2/F5/F6/F7 等线上信号必须 `Unknown`。

## 安装

把整个 `seo-code-diagnostic/` 文件夹放到以下任意位置：

- 仓库级：`<repo>/.codex/skills/seo-code-diagnostic/`
- 用户级：`~/.codex/skills/seo-code-diagnostic/`

如果从 GitHub 安装，可以直接克隆到用户级 skill 目录：

```bash
git clone https://github.com/glassesmonkey/seo-code-diagnostic.git ~/.codex/skills/seo-code-diagnostic
```

然后在 Codex 中用 `$seo-code-diagnostic` 显式调用，或让 Codex 在 SEO 代码审计任务中自动触发。

## 推荐提示词

```text
Use the $seo-code-diagnostic skill to audit this website codebase.
Target domain: https://example.com
Primary keyword: background remover
Secondary keywords: remove background, transparent background, AI background remover
Please produce a Chinese SEO diagnosis and suggest minimal code fixes.
Also flag YMYL copy risks and internal/prompt/model-thinking copy leaks.
```

AdSense 审核诊断：

```text
Use the $seo-code-diagnostic skill to audit this game/tool site for AdSense approval readiness.
Target domain: https://example.com
Primary keyword: suika game
The site was rejected for low value content. Produce a Chinese AdSense review diagnosis with prioritized fixes.
Cover every ADS-* requirement ID with Pass/Fail/Unknown/N/A, evidence, next action, and a Completeness Check.
```

## 包含内容

- `SKILL.md`：按 F1–F10 组织的诊断流和报告模板。
- `scripts/seo_code_audit.py`：离线静态扫描；Markdown/JSON 主表对齐 Top 10。
- `references/zyppy-2026-ranking-factors.md`：调研摘要 + skill 章节↔因素映射。
- `references/seo-principles.md`：按 Top 10 写的方法论。
- `references/diagnostic-rubric.md`：按 Top 10 重组的严重级别。
- `references/ahrefs-learning-notes.md`：Ahrefs 教程的诊断化笔记（与 Zyppy 冲突时以代码审计规则为准）。
- `references/adsense-requirements.md`：ADS-* 完整清单（独立章节）。
- `references/adsense-review-diagnostic.md`：AdSense 薄壳/low value 经验。
- `agents/openai.yaml`：Codex UI 元信息。

## 静态扫描脚本用法

```bash
python scripts/seo_code_audit.py --root . --out seo-audit
```

带关键词和域名：

```bash
python scripts/seo_code_audit.py \
  --root . \
  --domain "https://example.com" \
  --keywords "background remover,remove background,transparent background" \
  --out seo-audit
```

带 AdSense 审核检查：

```bash
python scripts/seo_code_audit.py \
  --root . \
  --domain "https://example.com" \
  --keywords "suika game,play suika game" \
  --adsense \
  --out seo-audit
```

脚本会生成：

- `seo-audit.json`
- `seo-audit.md`

脚本默认会提示两类文案风险：

- `YMYL_COPY_REVIEW`：健康、财务、安全、法律等 YMYL 主题出现建议、承诺、保证、诊断、收益、治疗等高风险表达。
- `INTERNAL_COPY_LEAK`：内部要求、prompt、模型思考过程、草稿说明、占位文案等不能直接面向用户的文案。

注意：脚本只做静态离线检查，并把能证明的风险映射到相关 ADS-* ID。关键词参数用于覆盖和堆砌检查，不是密度达标工具。完整 SEO / AdSense 判断还需要构建后查看 HTML、线上抓取、Google Search Console、Ahrefs Site Audit、竞品 SERP、AdSense 拒绝原因、账号状态、版权授权、真实流量和关键词数据。没有这些数据时，GSC CTR、品牌查询、外链质量保持 Unknown。完整 AdSense 审核必须按 `references/adsense-requirements.md` 覆盖全部 73 个 ADS-* ID，并做 Completeness Check。
