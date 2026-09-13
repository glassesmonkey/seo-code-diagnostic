# SEO Code Diagnostic Skill

一个用于 Codex 的网站代码 SEO 和 AdSense 审核诊断 skill。

它是**代码仓库审计**，不是 Ahrefs / Google Search Console 的替代品。判断框架对齐 [2026 Zyppy Google Ranking Factors Expert Survey](https://signal.zyppy.com/p/google-ranking-factors-expert-survey)（Cyrus/Dawn Shepard，131 位 SEO，2026-09）：专家共识 ≠ Google 官方权重。技术 SEO 是 table stakes；meta description 按 CTR 杠杆，不是排名 P1；关键词密度只用于发现堆砌，不作为 3%–5% 优化目标，也不因为「密度太低」报警。没有用户提供的 GSC/Ahrefs 数据时，行为、品牌、外链质量必须标 Unknown，禁止编造指标。

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

- `SKILL.md`：Codex 主要工作流和诊断规则。
- `scripts/seo_code_audit.py`：离线静态扫描脚本，输出 JSON/Markdown。
- `references/zyppy-2026-ranking-factors.md`：2026 Zyppy 专家调研摘要，以及哪些信号能从代码证明、必须标 Unknown。
- `references/ahrefs-learning-notes.md`：Ahrefs 官方教程的诊断化学习笔记。
- `references/adsense-requirements.md`：AdSense 官方来源驱动的 ADS-* 完整审核清单、状态规则和输出协议。
- `references/adsense-review-diagnostic.md`：AdSense 审核、low value content 和游戏/工具站薄壳风险诊断。
- `references/seo-principles.md`：中文 SEO 方法论和诊断原则的结构化整理。
- `references/diagnostic-rubric.md`：P0–P3 诊断标准。
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
