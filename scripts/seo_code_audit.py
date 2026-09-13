#!/usr/bin/env python3
"""
Static SEO Code Audit helper for Codex.

This script performs a deterministic, offline scan of a website codebase.
It does not crawl the public web and does not replace a full browser render,
Ahrefs Site Audit, Google Search Console, or PageSpeed Insights.

Reports are organized by the 2026 Zyppy Top 10 ranking factors (F1-F10).
Keyword density is a stuffing heuristic only: never treat 3%-5% (or an 8%
cap) as an optimization target, and never flag "density too low".
Missing meta description is a CTR lever (P2) under F5, not a ranking F1 item.

Outputs:
  - <out>.json: structured findings
  - <out>.md: readable Chinese audit summary

Example:
  python scripts/seo_code_audit.py --root . --domain https://example.com \
    --keywords "background remover,remove background" --out seo-audit

AdSense approval-readiness checks:
  python scripts/seo_code_audit.py --root . --domain https://example.com \
    --keywords "suika game,play suika game" --adsense --out seo-audit
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".next/cache",
    ".nuxt",
    ".turbo",
    ".vercel",
    ".netlify",
    ".cache",
    "coverage",
    "vendor",
    "__pycache__",
}

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    ".next/cache",
    ".nuxt",
    ".turbo",
    ".vercel",
    ".netlify",
    "coverage",
    "__pycache__",
}

HTML_EXTS = {".html", ".htm"}
SOURCE_EXTS = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro", ".md", ".mdx"}
TEXT_EXTS = HTML_EXTS | SOURCE_EXTS | {".json", ".xml", ".txt", ".config", ".mjs", ".cjs"}
COPY_REVIEW_SOURCE_EXTS = {".jsx", ".tsx", ".vue", ".svelte", ".astro", ".md", ".mdx"}
MAX_READ_BYTES = 700_000

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
# Stuffing heuristic only. Not an optimization target or "healthy" ceiling.
STUFFING_DENSITY_PERCENT = 8.0

# 2026 Zyppy Top 10. mode: code = can Pass from repo; online = always Unknown
# without user data; hybrid = Fail if code issues else Unknown (never Pass).
RANKING_FACTORS: List[Dict[str, str]] = [
    {"id": "F1", "name": "Relevance / Search Intent Match", "share": "57.1%", "mode": "code"},
    {"id": "F2", "name": "Backlinks", "share": "54.8%", "mode": "online"},
    {"id": "F3", "name": "Content Quality", "share": "47.6%", "mode": "code"},
    {"id": "F4", "name": "Authority & Trust", "share": "36.5%", "mode": "hybrid"},
    {"id": "F5", "name": "Behavior / Click Signals", "share": "29.4%", "mode": "hybrid"},
    {"id": "F6", "name": "Brand Signals", "share": "27.0%", "mode": "hybrid"},
    {"id": "F7", "name": "User Satisfaction", "share": "19.8%", "mode": "hybrid"},
    {"id": "F8", "name": "Technical SEO Health", "share": "17.5%", "mode": "code"},
    {"id": "F9", "name": "Topical Authority", "share": "14.3%", "mode": "hybrid"},
    {"id": "F10", "name": "Internal Links", "share": "11.1%", "mode": "code"},
]

ISSUE_TO_FACTOR = {
    "MISSING_TITLE": "F1",
    "TITLE_INTENT_GAP": "F1",
    "MISSING_H1": "F1",
    "MULTIPLE_H1": "F1",
    "HEADING_SKIP": "F1",
    "KEYWORD_NOT_FOUND": "F1",
    "KEYWORD_DENSITY_HIGH": "F1",
    "FAQ_MODULE_ABSENT": "F1",
    "THIN_CONTENT": "F3",
    "INTERNAL_COPY_LEAK": "F3",
    "YMYL_COPY_REVIEW": "F4",
    "MISSING_DESCRIPTION": "F5",
    "DESCRIPTION_LENGTH": "F5",
    "TITLE_LENGTH": "F5",
    "NOINDEX": "F8",
    "ROBOTS_MISSING": "F8",
    "ROBOTS_DISALLOW_ALL": "F8",
    "ROBOTS_NO_SITEMAP": "F8",
    "SITEMAP_MISSING": "F8",
    "SITEMAP_EMPTY": "F8",
    "SITEMAP_DOMAIN_MISMATCH": "F8",
    "MISSING_CANONICAL": "F8",
    "MULTIPLE_CANONICAL": "F8",
    "CANONICAL_NOT_ABSOLUTE": "F8",
    "CANONICAL_DOMAIN_MISMATCH": "F8",
    "CANONICAL_NOT_HTTPS": "F8",
    "CSR_OR_THIN_HTML_RISK": "F8",
    "MISSING_VIEWPORT": "F8",
    "NEXT_PAGE_USE_CLIENT": "F8",
    "NO_METADATA_SOURCE_FOUND": "F8",
    "NO_CANONICAL_SOURCE_FOUND": "F8",
    "NO_SCHEMA_SOURCE_FOUND": "F8",
    "OG_URL_CANONICAL_MISMATCH": "F8",
    "META_KEYWORDS_PRESENT": "F8",
    "IMAGE_DIMENSIONS_MISSING": "F8",
    "IMAGE_ALT_MISSING": "F3",
    "SOURCE_IMG_WITHOUT_ALT": "F3",
    "LOW_INTERNAL_LINKS": "F10",
}

FACTOR_ONLINE = {
    "F1": "竞品 SERP / 真实意图满足度常 Unknown。EMD 是专家观察，≠ 官方保证",
    "F2": "信任域、主题相关、真实访客、垃圾链、EM 锚占比；无链接表则 Unknown",
    "F3": "外部准确性/新鲜度 Unknown；不打质量分",
    "F4": "信任强度 / 外部口碑 Unknown",
    "F5": "无 GSC 则 CTR/pogo-stick Unknown；bounce 不用",
    "F6": "品牌词量/声誉 Unknown；广告花费几乎无直接作用",
    "F7": "真实任务完成/满意度 Unknown",
    "F8": "真实收录/CWV 常 Unknown；table stakes，不是增长解锁",
    "F9": "主题权威强度 Unknown；结构只是代理",
    "F10": "不计算内链权重分",
}

FACTOR_DEFAULT_ACTION = {
    "F1": "按结果形态/任务改 title、H1 和正文；记录域名意图匹配/EMD 观察。不要补密度，不要买垃圾 EMD。",
    "F2": "没有链接表就保持 Unknown；有表则评信任域+主题+真实访客，不追求数量。",
    "F3": "补一手/原创信息；停掉规模化低质 AI 薄壳。",
    "F4": "补真实身份/来源；YMYL 改成信息性说明。强度保持 Unknown。",
    "F5": "description 按 CTR 处理，不是排名 P1。有 GSC 再评点击质量。",
    "F6": "对齐名称/域名/组织实体。不要把广告花费当排名动作。",
    "F7": "让工具/游戏首屏能完成任务。满意度无数据则 Unknown。",
    "F8": "先修会摔的抓取/SSR/canonical/sitemap。修好不会抬起平庸内容。",
    "F9": "用支柱+集群做结构代理，不打权威分。",
    "F10": "补具体来源页→锚文本→目标页，避免重要页孤儿。",
}


@dataclass
class Issue:
    severity: str
    code: str
    file: str
    evidence: str
    recommendation: str


class SEOHTMLParser(HTMLParser):
    """Small stdlib HTML parser for SEO-relevant signals."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: List[str] = []
        self.in_title = False
        self.title_parts: List[str] = []
        self.current_heading: Optional[Dict[str, object]] = None
        self.headings: List[Dict[str, object]] = []
        self.meta: Dict[str, str] = {}
        self.meta_props: Dict[str, str] = {}
        self.canonicals: List[str] = []
        self.links: List[Dict[str, str]] = []
        self.images: List[Dict[str, str]] = []
        self.iframes: List[Dict[str, str]] = []
        self.scripts: List[Dict[str, str]] = []
        self.text_parts: List[str] = []
        self.json_ld_count = 0
        self._script_type_stack: List[str] = []

    def _attrs(self, attrs: List[Tuple[str, Optional[str]]]) -> Dict[str, str]:
        return {k.lower(): (v or "") for k, v in attrs}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr = self._attrs(attrs)
        self.stack.append(tag)

        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = attr.get("name", "").lower().strip()
            prop = attr.get("property", "").lower().strip()
            content = attr.get("content", "").strip()
            if name:
                self.meta[name] = content
            if prop:
                self.meta_props[prop] = content
        elif tag == "link":
            rel = attr.get("rel", "").lower()
            href = attr.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonicals.append(href)
        elif re.fullmatch(r"h[1-6]", tag):
            self.current_heading = {"level": int(tag[1]), "text": ""}
        elif tag == "a":
            self.links.append({"href": attr.get("href", ""), "text": ""})
        elif tag == "img":
            self.images.append(
                {
                    "src": attr.get("src", ""),
                    "alt": attr.get("alt", ""),
                    "width": attr.get("width", ""),
                    "height": attr.get("height", ""),
                    "loading": attr.get("loading", ""),
                }
            )
        elif tag == "iframe":
            self.iframes.append({"src": attr.get("src", ""), "title": attr.get("title", "")})
        elif tag == "script":
            stype = attr.get("type", "").lower()
            self._script_type_stack.append(stype)
            if "ld+json" in stype:
                self.json_ld_count += 1
            self.scripts.append({"src": attr.get("src", ""), "type": stype})

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif re.fullmatch(r"h[1-6]", tag) and self.current_heading:
            text = normalize_ws(str(self.current_heading.get("text", "")))
            self.current_heading["text"] = text
            self.headings.append(self.current_heading)
            self.current_heading = None
        elif tag == "script" and self._script_type_stack:
            self._script_type_stack.pop()

        # Pop from the right until the matching tag if the markup is imperfect.
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data: str) -> None:
        if not data or not data.strip():
            return
        if self.in_title:
            self.title_parts.append(data)
        if self.current_heading is not None:
            self.current_heading["text"] = str(self.current_heading.get("text", "")) + data
        if self.links:
            # This is approximate: enough to make anchor text visible in the JSON.
            self.links[-1]["text"] = normalize_ws(self.links[-1].get("text", "") + " " + data)

        hidden_context = {"head", "title", "script", "style", "svg", "canvas", "template"}
        if any(tag in hidden_context for tag in self.stack):
            return
        self.text_parts.append(data)

    @property
    def title(self) -> str:
        return normalize_ws(" ".join(self.title_parts))

    @property
    def text(self) -> str:
        return normalize_ws(" ".join(self.text_parts))


# ---------- helpers ----------


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def safe_read(path: Path) -> str:
    data = path.read_bytes()[:MAX_READ_BYTES]
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def should_skip(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    for part in rel_parts:
        if part in EXCLUDED_PARTS:
            return True
    return False


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        # Mutate dirnames so os.walk does not descend into excluded dirs.
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES and d not in EXCLUDED_PARTS]
        if should_skip(current, root):
            continue
        for filename in filenames:
            path = current / filename
            if should_skip(path, root):
                continue
            if path.is_file():
                yield path


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def is_absolute_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_domain(domain: Optional[str]) -> Optional[str]:
    if not domain:
        return None
    domain = domain.strip().rstrip("/")
    if not domain:
        return None
    if not re.match(r"^https?://", domain):
        domain = "https://" + domain
    return domain.rstrip("/")


def token_count(text: str) -> int:
    # English words/numbers + individual CJK chars as rough searchable units.
    return len(re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", text))


def compact_intent(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (text or "").lower())


def registrable_label(host: str) -> str:
    host = (host or "").lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in host.split(".") if p]
    two_level = {"co", "com", "net", "org", "ac", "gov", "edu"}
    if len(parts) >= 3 and parts[-2] in two_level:
        return parts[-3]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] if parts else ""


def emd_match_level(label: str, host: str, keyword: str) -> str:
    """exact | high | none. Observation only; never a Fail reason by itself."""
    ks = compact_intent(keyword)
    sl = compact_intent(label)
    hs = compact_intent(host)
    if not ks:
        return "unknown"
    if sl and sl == ks:
        return "exact"
    if sl and (ks in sl or sl in ks):
        return "high"
    if hs and ks in hs:
        return "high"
    tokens = [t for t in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", (keyword or "").lower()) if len(t) > 1]
    if tokens and sl and all(compact_intent(t) in sl for t in tokens):
        return "high"
    return "none"


def looks_spammy_emd_host(host: str, keyword: str) -> bool:
    if not host:
        return False
    if host.count("-") < 3:
        return False
    compact_host = compact_intent(host)
    if keyword and compact_intent(keyword) and compact_intent(keyword) in compact_host:
        return True
    tokens = [t for t in re.findall(r"[a-z0-9]+", (keyword or "").lower()) if len(t) > 2]
    return bool(tokens) and all(t in compact_host for t in tokens)


def collect_candidate_hosts(domain: Optional[str], html_pages: List[Dict[str, object]]) -> List[str]:
    hosts: List[str] = []
    seen = set()

    def add(host: str) -> None:
        host = (host or "").lower().split(":")[0].strip()
        if host.startswith("www."):
            host = host[4:]
        if host and host not in seen:
            seen.add(host)
            hosts.append(host)

    if domain:
        add(urlparse(domain).netloc)
    for page in html_pages:
        canonical = str(page.get("canonical") or "")
        if is_absolute_http_url(canonical):
            add(urlparse(canonical).netloc)
    return hosts


def assess_emd_observation(
    domain: Optional[str], keywords: List[str], html_pages: List[Dict[str, object]]
) -> Dict[str, object]:
    """F1 sub-item: domain-intent / EMD observation. Never Fail a brand domain for not being EMD."""
    hosts = collect_candidate_hosts(domain, html_pages)
    primary = keywords[0] if keywords else ""
    host = hosts[0] if hosts else ""
    label = registrable_label(host) if host else ""
    spammy = looks_spammy_emd_host(host, primary)
    source = "来源：Zyppy 2026 专家评论（EMD still unexpectedly effective），≠ Google 官方保证"

    if not host:
        summary = "域名意图匹配/EMD：Unknown（无 --domain 也无 canonical host）"
        level = "unknown"
    elif not primary:
        summary = f"域名意图匹配/EMD：已记录 host `{host}`，未提供主意图词，无法判断是否 EMD"
        level = "no_keyword"
    else:
        level = emd_match_level(label, host, primary)
        if level == "exact":
            summary = f"域名意图匹配/EMD：精确匹配 `{host}` ≈ `{primary}`（相关性加分观察）"
        elif level == "high":
            summary = f"域名意图匹配/EMD：高度匹配 `{host}` ~ `{primary}`（相关性加分观察）"
        else:
            summary = f"域名意图匹配/EMD：非 EMD（`{host}`）。已有品牌域不因此判 Fail"
        if spammy:
            summary += "；host 连字符很多，像 spammy EMD，不要建议购买这类域"

    return {
        "level": level,
        "host": host,
        "label": label,
        "keyword": primary,
        "spammy_looking": spammy,
        "summary": summary,
        "note": f"{source}。只作加分观察；不要为了 SEO 买垃圾 EMD。",
    }


def keyword_density(text: str, keyword: str) -> Dict[str, object]:
    """Count keyword occurrences. density_percent is only for stuffing detection."""
    text_norm = normalize_ws(text).lower()
    keyword_norm = normalize_ws(keyword).lower()
    if not text_norm or not keyword_norm:
        return {"keyword": keyword, "count": 0, "density_percent": 0.0}
    count = len(re.findall(re.escape(keyword_norm), text_norm))
    kw_units = max(token_count(keyword_norm), 1)
    total_units = max(token_count(text_norm), 1)
    density = (count * kw_units / total_units) * 100
    return {"keyword": keyword, "count": count, "density_percent": round(density, 2)}


def escape_md(value: object) -> str:
    s = str(value if value is not None else "")
    s = normalize_ws(s)
    s = s.replace("|", "\\|")
    if len(s) > 180:
        s = s[:177] + "..."
    return s


def add_issue(issues: List[Issue], severity: str, code: str, file: str, evidence: str, recommendation: str) -> None:
    issues.append(Issue(severity, code, file, normalize_ws(evidence), normalize_ws(recommendation)))


def add_adsense_check(
    checks: List[Dict[str, object]],
    severity: str,
    item: str,
    status: str,
    evidence: str,
    recommendation: str,
    ids: Optional[List[str]] = None,
) -> None:
    checks.append(
        {
            "ids": ids or [],
            "severity": severity,
            "item": normalize_ws(item),
            "status": status,
            "evidence": normalize_ws(evidence),
            "recommendation": normalize_ws(recommendation),
        }
    )


def format_ads_ids(ids: object) -> str:
    if not ids:
        return ""
    if isinstance(ids, list):
        return ", ".join(str(x) for x in ids)
    return str(ids)


YMYL_TOPIC_PATTERNS = [
    r"\b(diabetes|cancer|depression|anxiety|blood pressure|heart disease|medical|medicine|medication|health)\b",
    r"\b(loan|mortgage|debt|credit card|investment|investing|stock|tax|insurance|retirement)\b",
    r"\b(legal|lawsuit|immigration|divorce|contract|bankruptcy|attorney|lawyer)\b",
    r"\b(emergency|dangerous|personal safety|public safety|security risk)\b",
    r"(糖尿病|癌症|抑郁|焦虑|血压|心脏病|医疗|药物|健康|治疗)",
    r"(贷款|债务|信用卡|投资|股票|税务|保险|退休|理财)",
    r"(法律|律师|诉讼|移民|离婚|合同|破产)",
    r"(安全|紧急|危险|事故|风险)",
    r"(糖尿病|がん|癌|うつ|血圧|心臓病|医療|薬|健康|治療)",
    r"(投資|ローン|借金|税金|保険|退職)",
    r"(法律|弁護士|訴訟|離婚|移民|契約)",
    r"(安全|緊急|危険|事故|リスク)",
    r"\b(diabetes|krebs|depression|blutdruck|herzkrankheit|medizin|medikament|gesundheit|behandlung)\b",
    r"\b(kredit|darlehen|schulden|investition|aktien|steuer|versicherung|rente|rendite)\b",
    r"\b(recht|anwalt|klage|scheidung|einwanderung|vertrag|insolvenz)\b",
    r"\b(sicherheit|notfall|gefährlich|unfall|risiko)\b",
]

YMYL_CLAIM_PATTERNS = [
    r"\b(guaranteed?|cures?|cure|treats?|diagnose|prevents?|you should|must|always|never|risk-free|make money|profit|invest now|medical advice|legal advice)\b",
    r"(保证|必定|一定|根治|治愈|治疗|诊断|预防|你应该|必须|无风险|保本|稳赚|赚钱|立刻投资|医疗建议|法律建议)",
    r"(保証|必ず|絶対|治す|治療|診断|予防|すべき|必須|リスクなし|儲かる|今すぐ投資|医療助言|法的助言)",
    r"\b(garantiert|heilen|heilung|behandeln|diagnose|verhindern|sie sollten|müssen|immer|niemals|risikofrei|gewinn|geld verdienen|investieren|medizinischer rat|rechtsberatung)\b",
]

INTERNAL_COPY_PATTERNS = [
    r"(内部要求|内部说明|内部备注|模型思考|思考过程|提示词|系统提示|开发者提示|不要直接面向用户|面向用户文案|待人工改写|占位文案)",
    r"\b(internal requirements?|internal notes?|internal instructions?|model reasoning|chain of thought|thought process|system prompt|developer prompt|prompt draft|draft copy|placeholder copy|for internal use|not for users?|do not show to users?|as an ai language model)\b",
    r"(内部要件|内部メモ|内部指示|モデルの思考|思考過程|システムプロンプト|開発者プロンプト|プロンプト|ユーザーに表示しない|下書き|プレースホルダー)",
    r"\b(interne anforderungen|interner hinweis|interne notiz|interne anweisung|denkprozess|gedankengang|system-?prompt|entwickler-?prompt|nicht für nutzer|nicht anzeigen|platzhaltertext|entwurf)\b",
]


def matches_any(patterns: List[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def copy_review_snippets(text: str) -> Iterable[str]:
    for part in re.split(r"(?<=[.!?。！？；;])\s+|\n+", text):
        snippet = normalize_ws(part)
        if not snippet:
            continue
        if len(snippet) <= 420:
            yield snippet
            continue
        for start in range(0, len(snippet), 360):
            window = normalize_ws(snippet[start : start + 420])
            if window:
                yield window


def audit_copy_text(text: str, file_rel: str, confidence: str) -> List[Issue]:
    issues: List[Issue] = []
    found_ymyl = False
    found_internal = False
    for snippet in copy_review_snippets(text):
        if not found_ymyl and matches_any(YMYL_TOPIC_PATTERNS, snippet) and matches_any(YMYL_CLAIM_PATTERNS, snippet):
            add_issue(
                issues,
                "P1",
                "YMYL_COPY_REVIEW",
                file_rel,
                f"{confidence}命中 YMYL 风险文案：{snippet}",
                "人工审稿：如果这是用户可见文案，避免给健康/财务/法律/安全承诺或建议；改成信息性说明，补充来源/资质/免责声明，或移除该主题。",
            )
            found_ymyl = True
        if not found_internal and matches_any(INTERNAL_COPY_PATTERNS, snippet):
            add_issue(
                issues,
                "P1",
                "INTERNAL_COPY_LEAK",
                file_rel,
                f"{confidence}命中内部/模型痕迹：{snippet}",
                "把内部要求、prompt/模型思考或草稿说明改成真实用户语言；如果只是开发注释，确认不会渲染到页面。",
            )
            found_internal = True
        if found_ymyl and found_internal:
            break
    return issues


def rel_posix(path: Path, root: Path) -> str:
    return rel(path, root).replace(os.sep, "/")


def path_contains_token(value: str, tokens: List[str]) -> bool:
    value_l = value.lower().replace("_", "-")
    return any(token in value_l for token in tokens)


def find_likely_pages(all_files: List[Path], root: Path, tokens: List[str]) -> List[str]:
    matches: List[str] = []
    for path in all_files:
        if path.suffix.lower() not in TEXT_EXTS:
            continue
        file_rel = rel_posix(path, root).lower()
        if path_contains_token(file_rel, tokens):
            matches.append(rel_posix(path, root))
    return sorted(set(matches))


def find_likely_article_files(all_files: List[Path], root: Path) -> List[str]:
    article_dirs = {
        "blog",
        "blogs",
        "post",
        "posts",
        "article",
        "articles",
        "guide",
        "guides",
        "news",
        "content",
        "tutorial",
        "tutorials",
    }
    article_exts = {".md", ".mdx", ".html", ".htm", ".astro", ".svelte", ".vue", ".tsx", ".jsx"}
    skip_names = {"index", "layout", "template", "component", "components"}
    matches: List[str] = []
    for path in all_files:
        if path.suffix.lower() not in article_exts:
            continue
        file_rel = rel_posix(path, root)
        parts = [part.lower() for part in file_rel.split("/")]
        if not any(part in article_dirs for part in parts):
            continue
        if path.stem.lower() in skip_names:
            continue
        matches.append(file_rel)
    return sorted(set(matches))


def is_adsense_core_page(file_rel: str) -> bool:
    path = file_rel.lower().replace("\\", "/")
    name = Path(path).name
    if name in {"index.html", "index.htm"}:
        return True
    core_markers = ["/game", "/games", "/tool", "/tools", "/category", "/categories", "/play", "/apps"]
    return any(marker in path for marker in core_markers)


# ---------- project detection ----------


def detect_project(root: Path, all_files: List[Path]) -> Dict[str, object]:
    package_path = root / "package.json"
    package = {}
    stack = []
    scripts = {}
    if package_path.exists():
        try:
            package = json.loads(safe_read(package_path))
            deps = {}
            deps.update(package.get("dependencies") or {})
            deps.update(package.get("devDependencies") or {})
            scripts = package.get("scripts") or {}
            dep_names = set(deps.keys())
            if "next" in dep_names:
                stack.append("Next.js")
            if "nuxt" in dep_names or "@nuxt/kit" in dep_names:
                stack.append("Nuxt")
            if "astro" in dep_names:
                stack.append("Astro")
            if "gatsby" in dep_names:
                stack.append("Gatsby")
            if "@sveltejs/kit" in dep_names:
                stack.append("SvelteKit")
            if "react" in dep_names and "Next.js" not in stack and "Gatsby" not in stack:
                stack.append("React")
            if "vue" in dep_names and "Nuxt" not in stack:
                stack.append("Vue")
            if "vite" in dep_names and not any(s in stack for s in ["Next.js", "Nuxt", "Astro", "SvelteKit"]):
                stack.append("Vite")
        except Exception as exc:  # pragma: no cover - defensive
            package = {"error": str(exc)}

    config_hits = []
    important_names = {
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
        "nuxt.config.js",
        "nuxt.config.ts",
        "astro.config.mjs",
        "astro.config.ts",
        "vite.config.js",
        "vite.config.ts",
        "gatsby-config.js",
        "svelte.config.js",
        "remix.config.js",
    }
    for path in all_files:
        if path.name in important_names:
            config_hits.append(rel(path, root))

    route_dirs = []
    for candidate in ["app", "pages", "src/pages", "src/routes", "routes", "content", "posts", "public", "dist", "build"]:
        if (root / candidate).exists():
            route_dirs.append(candidate)

    seo_files = []
    for candidate in [
        "robots.txt",
        "public/robots.txt",
        "sitemap.xml",
        "public/sitemap.xml",
        "app/robots.ts",
        "app/robots.js",
        "app/sitemap.ts",
        "app/sitemap.js",
        "src/app/robots.ts",
        "src/app/sitemap.ts",
    ]:
        if (root / candidate).exists():
            seo_files.append(candidate)

    return {
        "stack": stack or ["Unknown/static or server-rendered app"],
        "package_scripts": scripts,
        "config_files": config_hits,
        "route_dirs": route_dirs,
        "seo_files": seo_files,
    }


# ---------- HTML audit ----------


def parse_html(path: Path) -> SEOHTMLParser:
    parser = SEOHTMLParser()
    try:
        parser.feed(safe_read(path))
    except Exception:
        # HTMLParser is forgiving, but keep going if weird input appears.
        pass
    return parser


def classify_links(links: List[Dict[str, str]], domain: Optional[str]) -> Tuple[int, int, int]:
    internal = external = empty = 0
    host = urlparse(domain).netloc if domain else ""
    for link in links:
        href = (link.get("href") or "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:"):
            empty += 1
        elif href.startswith("/"):
            internal += 1
        elif href.startswith("http://") or href.startswith("https://"):
            if host and urlparse(href).netloc == host:
                internal += 1
            else:
                external += 1
        else:
            internal += 1
    return internal, external, empty


def audit_html_file(path: Path, root: Path, domain: Optional[str], keywords: List[str]) -> Dict[str, object]:
    parser = parse_html(path)
    file_rel = rel(path, root)
    issues: List[Issue] = []
    text = parser.text
    words = token_count(text)
    text_chars = len(text)
    title = parser.title
    description = parser.meta.get("description", "")
    robots = parser.meta.get("robots", "")
    viewport = parser.meta.get("viewport", "")
    h1s = [h for h in parser.headings if h.get("level") == 1]
    internal_links, external_links, empty_links = classify_links(parser.links, domain)
    missing_alt = [img for img in parser.images if not normalize_ws(img.get("alt", ""))]
    missing_dims = [img for img in parser.images if not img.get("width") or not img.get("height")]
    script_count = len(parser.scripts)
    canonical = parser.canonicals[0] if parser.canonicals else ""
    og_url = parser.meta_props.get("og:url", "")

    if re.search(r"\bnoindex\b", robots, flags=re.I):
        add_issue(issues, "P0", "NOINDEX", file_rel, f"robots meta = {robots}", "确认该页面是否真的不需要收录；核心 SEO 页面不要设置 noindex。")

    if not title:
        add_issue(issues, "P1", "MISSING_TITLE", file_rel, "未找到 <title>", "为每个可索引页面设置唯一 title，先匹配主搜索意图/任务，再考虑 SERP 点击文案。")
    elif len(title) < 15 or len(title) > 70:
        add_issue(issues, "P3", "TITLE_LENGTH", file_rel, f"title 长度 {len(title)}: {title}", "这是 CTR/展示问题：检查标题是否过短、过长或会在搜索结果中被截断。相关性另看 title 是否表达本页任务。")

    if not description:
        add_issue(
            issues,
            "P2",
            "MISSING_DESCRIPTION",
            file_rel,
            "未找到 meta description（CTR 杠杆，不是已被证明的排名因子）",
            "建议补充能说明价值并促进点击的 meta description。专家共识认为它对排名几乎没有/没有影响；按 P2/P3 CTR 处理，不要当成排名 P1。",
        )
    elif len(description) < 50 or len(description) > 170:
        add_issue(issues, "P3", "DESCRIPTION_LENGTH", file_rel, f"description 长度 {len(description)}", "CTR 文案问题：检查描述是否过短、过长或缺少具体收益。不是排名因子。")

    if parser.meta.get("keywords"):
        add_issue(issues, "P3", "META_KEYWORDS_PRESENT", file_rel, "发现 meta keywords", "通常不需要维护 meta keywords；优先优化 title、description、正文和内链。")

    if not viewport:
        add_issue(issues, "P2", "MISSING_VIEWPORT", file_rel, "未找到 viewport meta", "补充移动端 viewport，确保移动优先体验。")

    if len(parser.canonicals) == 0:
        add_issue(issues, "P1", "MISSING_CANONICAL", file_rel, "未找到 rel=canonical", "为核心可索引页面添加自引用 canonical，使用绝对 HTTPS URL。")
    elif len(parser.canonicals) > 1:
        add_issue(issues, "P1", "MULTIPLE_CANONICAL", file_rel, f"发现 {len(parser.canonicals)} 个 canonical", "每页只保留一个 canonical，避免搜索引擎忽略冲突信号。")
    else:
        if not is_absolute_http_url(canonical):
            add_issue(issues, "P1", "CANONICAL_NOT_ABSOLUTE", file_rel, canonical, "canonical 应使用完整绝对 URL，例如 https://example.com/path。")
        if domain and is_absolute_http_url(canonical):
            canonical_host = urlparse(canonical).netloc.lower()
            domain_host = urlparse(domain).netloc.lower()
            if canonical_host != domain_host:
                add_issue(issues, "P1", "CANONICAL_DOMAIN_MISMATCH", file_rel, canonical, f"确认 canonical 域名应统一为 {domain_host}。")
            if urlparse(canonical).scheme != "https":
                add_issue(issues, "P2", "CANONICAL_NOT_HTTPS", file_rel, canonical, "正式站点优先使用 HTTPS canonical。")

    if og_url and canonical and og_url.rstrip("/") != canonical.rstrip("/"):
        add_issue(issues, "P3", "OG_URL_CANONICAL_MISMATCH", file_rel, f"og:url={og_url}; canonical={canonical}", "通常让 og:url 与 canonical 保持一致，避免分享 URL 与规范 URL 冲突。")

    if len(h1s) == 0:
        add_issue(issues, "P1", "MISSING_H1", file_rel, "未找到 H1", "每个页面应有一个 H1，直接表达页面主主题/主关键词。")
    elif len(h1s) > 1:
        add_issue(issues, "P1", "MULTIPLE_H1", file_rel, f"发现 {len(h1s)} 个 H1: {[h.get('text') for h in h1s[:5]]}", "通常每页保留一个主 H1，其余模块用 H2/H3。")

    levels = [int(h.get("level", 0)) for h in parser.headings]
    for prev, cur in zip(levels, levels[1:]):
        if cur - prev > 1:
            add_issue(issues, "P2", "HEADING_SKIP", file_rel, f"标题层级从 H{prev} 跳到 H{cur}", "调整 H2/H3 层级，使内容结构更清晰。")
            break

    if text_chars < 600 and script_count >= 5:
        add_issue(issues, "P0", "CSR_OR_THIN_HTML_RISK", file_rel, f"可见文本约 {text_chars} 字符，script {script_count} 个", "核心 SEO 页面需要在初始 HTML/SSR/SSG 中输出主要文案，避免纯前端渲染导致爬虫难以读取。")
    elif text_chars < 900:
        add_issue(issues, "P2", "THIN_CONTENT", file_rel, f"可见文本约 {text_chars} 字符", "检查页面是否充分覆盖搜索意图；核心落地页应补充步骤、功能、场景、FAQ、信任信号和相关链接。")

    issues.extend(audit_copy_text(text, file_rel, "高置信可见文本"))

    if parser.images:
        missing_alt_ratio = len(missing_alt) / max(len(parser.images), 1)
        if missing_alt:
            add_issue(issues, "P2", "IMAGE_ALT_MISSING", file_rel, f"{len(missing_alt)}/{len(parser.images)} 张图片缺少 alt", "为重要图片添加简洁描述性 alt；装饰图可用空 alt。")
        if missing_dims and len(missing_dims) / max(len(parser.images), 1) > 0.4:
            add_issue(issues, "P3", "IMAGE_DIMENSIONS_MISSING", file_rel, f"{len(missing_dims)}/{len(parser.images)} 张图片缺少 width/height", "为图片设置尺寸或使用框架图片组件，降低布局偏移风险。")

    if internal_links < 2 and text_chars > 600:
        add_issue(issues, "P2", "LOW_INTERNAL_LINKS", file_rel, f"内部链接约 {internal_links} 个", "为核心页面补充到上级、下级和相关页面的上下文内链。")

    lower_headings = " ".join(str(h.get("text", "")).lower() for h in parser.headings)
    if text_chars > 1000 and not re.search(r"faq|frequently asked|常见问题|questions|问答", lower_headings, flags=re.I):
        add_issue(issues, "P3", "FAQ_MODULE_ABSENT", file_rel, "未发现明显 FAQ 标题", "如果页面承载关键词流量，可补充真实 FAQ，回答搜索者的常见问题。")

    if title and keywords:
        title_l = title.lower()
        body_l = text.lower()
        present_in_body = [kw for kw in keywords if normalize_ws(kw).lower() in body_l]
        if present_in_body and not any(normalize_ws(kw).lower() in title_l for kw in present_in_body):
            add_issue(
                issues,
                "P2",
                "TITLE_INTENT_GAP",
                file_rel,
                f"正文覆盖了 {present_in_body[:3]}，但 title 未表达这些意图：{title}",
                "先改 title 相关性，使它匹配本页任务；点击吸引力另算 CTR，不要为了密度改 title。",
            )

    densities = [keyword_density(text, kw) for kw in keywords]
    for density in densities:
        kw = str(density["keyword"])
        pct = float(density["density_percent"])
        count = int(density["count"])
        if count == 0:
            add_issue(issues, "P2", "KEYWORD_NOT_FOUND", file_rel, f"关键词 `{kw}` 在可见文本中未出现", "确认该关键词是否应映射到此页面；如果是，按意图补充自然表达，不要用密度目标硬塞词。")
        elif pct > STUFFING_DENSITY_PERCENT:
            add_issue(issues, "P2", "KEYWORD_DENSITY_HIGH", file_rel, f"`{kw}` 密度约 {pct}%（堆砌启发式，不是优化上限）", "降低机械重复，改用同义词、实体、示例和相关问题解释主词。不要把密度压到某个百分比区间当目标。")

    return {
        "file": file_rel,
        "title": title,
        "description": description,
        "canonical": canonical,
        "robots": robots,
        "h1_count": len(h1s),
        "h1": [h.get("text", "") for h in h1s],
        "heading_counts": dict(Counter(int(h.get("level", 0)) for h in parser.headings)),
        "text_chars": text_chars,
        "word_units": words,
        "image_count": len(parser.images),
        "images_missing_alt": len(missing_alt),
        "iframe_count": len(parser.iframes),
        "internal_links": internal_links,
        "external_links": external_links,
        "empty_or_special_links": empty_links,
        "script_count": script_count,
        "json_ld_count": parser.json_ld_count,
        "keyword_density": densities,
        "issues": [asdict(issue) for issue in issues],
    }


# ---------- source audit ----------


def audit_source_files(root: Path, source_files: List[Path]) -> Dict[str, object]:
    findings: List[Issue] = []
    summary = {
        "files_scanned": len(source_files),
        "metadata_files": [],
        "canonical_mentions": [],
        "h1_mentions": [],
        "json_ld_mentions": [],
        "client_page_risks": [],
        "img_without_alt_suspects": [],
        "route_files": [],
    }

    route_like_re = re.compile(r"(^|/)(app|pages|routes|src/pages|src/routes)/.*(page|index|\[|\.astro|\.svelte|\.vue)", re.I)
    img_tag_re = re.compile(r"<img\b([^>]*?)>", re.I | re.S)

    for path in source_files:
        file_rel = rel(path, root)
        try:
            content = safe_read(path)
        except Exception:
            continue
        content_l = content.lower()
        if route_like_re.search(file_rel.replace(os.sep, "/")):
            summary["route_files"].append(file_rel)

        if re.search(r"export\s+(const\s+metadata|async\s+function\s+generateMetadata|function\s+generateMetadata)|<Head\b|<title\b|useHead\(|svelte:head|set:html", content):
            summary["metadata_files"].append(file_rel)
        if "canonical" in content_l or "rel=\"canonical\"" in content_l or "rel='canonical'" in content_l:
            summary["canonical_mentions"].append(file_rel)
        if re.search(r"<h1\b", content, flags=re.I):
            summary["h1_mentions"].append(file_rel)
        if "application/ld+json" in content_l or "schema.org" in content_l:
            summary["json_ld_mentions"].append(file_rel)

        # Next App Router risk: a page component marked use client often means core content may render client-side.
        if re.search(r"^[\s;]*(?:'use client'|\"use client\")", content, flags=re.M):
            if re.search(r"(^|/)(app|src/app)/.*page\.(tsx|jsx|ts|js)$", file_rel.replace(os.sep, "/")):
                summary["client_page_risks"].append(file_rel)
                add_issue(
                    findings,
                    "P2",
                    "NEXT_PAGE_USE_CLIENT",
                    file_rel,
                    "App Router page 文件包含 'use client'",
                    "确认核心 SEO 文案是否仍由服务器输出；必要时把交互组件下沉，页面主体保留为 Server Component。",
                )

        for match in img_tag_re.finditer(content):
            attrs = match.group(1)
            if "alt=" not in attrs.lower():
                summary["img_without_alt_suspects"].append(file_rel)
                add_issue(
                    findings,
                    "P2",
                    "SOURCE_IMG_WITHOUT_ALT",
                    file_rel,
                    "源码中发现疑似 <img> 未设置 alt",
                    "为重要图片添加描述性 alt；装饰图使用 alt=\"\"。",
                )
                break

        if path.suffix.lower() in COPY_REVIEW_SOURCE_EXTS:
            findings.extend(audit_copy_text(content, file_rel, "中置信源码/内容"))

    # Repo-level hints.
    if summary["route_files"] and not summary["metadata_files"]:
        add_issue(
            findings,
            "P1",
            "NO_METADATA_SOURCE_FOUND",
            "repo",
            "未在路由/源码中发现明显 title/meta/metadata 设置",
            "检查是否有统一 SEO 组件；动态页面应生成唯一 title 和 canonical。description 按 CTR 补充，不当成排名 P1。",
        )
    if summary["route_files"] and not summary["canonical_mentions"]:
        add_issue(
            findings,
            "P1",
            "NO_CANONICAL_SOURCE_FOUND",
            "repo",
            "未在源码中发现 canonical 相关实现",
            "为核心页面统一实现 canonical，动态路由应使用绝对 URL。",
        )
    if summary["route_files"] and not summary["json_ld_mentions"]:
        add_issue(
            findings,
            "P3",
            "NO_SCHEMA_SOURCE_FOUND",
            "repo",
            "未发现 JSON-LD/schema.org 相关实现",
            "根据页面类型考虑 Organization、WebSite、BreadcrumbList、Article、SoftwareApplication、FAQPage 等结构化数据。",
        )

    return {"summary": summary, "issues": [asdict(issue) for issue in findings]}


# ---------- robots/sitemap audit ----------


def audit_repo_files(root: Path, all_files: List[Path], domain: Optional[str]) -> Dict[str, object]:
    issues: List[Issue] = []
    files_by_rel = {rel(path, root): path for path in all_files}

    robots_candidates = ["robots.txt", "public/robots.txt", "static/robots.txt"]
    robots_found = [name for name in robots_candidates if name in files_by_rel]
    if not robots_found:
        add_issue(issues, "P2", "ROBOTS_MISSING", "repo", "未发现 robots.txt", "添加 robots.txt，明确允许核心页面抓取并声明 sitemap 地址。")
    else:
        for name in robots_found:
            content = safe_read(files_by_rel[name])
            if re.search(r"User-agent:\s*\*\s*\n\s*Disallow:\s*/\s*(?:\n|$)", content, flags=re.I):
                add_issue(issues, "P0", "ROBOTS_DISALLOW_ALL", name, "User-agent: * / Disallow: /", "确认是否误封全站；上线生产站通常不应阻止所有搜索引擎抓取。")
            if "sitemap:" not in content.lower():
                add_issue(issues, "P3", "ROBOTS_NO_SITEMAP", name, "robots.txt 未声明 Sitemap", "在 robots.txt 中补充 Sitemap: https://example.com/sitemap.xml。")

    sitemap_candidates = ["sitemap.xml", "public/sitemap.xml", "static/sitemap.xml", "app/sitemap.ts", "app/sitemap.js", "src/app/sitemap.ts"]
    sitemap_found = [name for name in sitemap_candidates if name in files_by_rel]
    if not sitemap_found:
        add_issue(issues, "P1", "SITEMAP_MISSING", "repo", "未发现 sitemap 文件或生成入口", "添加 sitemap，列出希望被索引的 canonical URL。")
    else:
        for name in sitemap_found:
            if name.endswith(".xml"):
                content = safe_read(files_by_rel[name])
                urls = re.findall(r"<loc>(.*?)</loc>", content, flags=re.I | re.S)
                if not urls:
                    add_issue(issues, "P2", "SITEMAP_EMPTY", name, "未解析到 <loc>", "检查 sitemap 是否有效。")
                elif domain:
                    host = urlparse(domain).netloc.lower()
                    mismatches = [u.strip() for u in urls if is_absolute_http_url(u.strip()) and urlparse(u.strip()).netloc.lower() != host]
                    if mismatches:
                        add_issue(issues, "P1", "SITEMAP_DOMAIN_MISMATCH", name, mismatches[0], f"sitemap URL 应统一为 canonical 域名 {host}。")

    return {"robots_found": robots_found, "sitemap_found": sitemap_found, "issues": [asdict(issue) for issue in issues]}


# ---------- reporting ----------


def collect_issues(result: Dict[str, object]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    for page in result.get("html_pages", []):
        issues.extend(page.get("issues", []))
    issues.extend(result.get("source_audit", {}).get("issues", []))
    issues.extend(result.get("repo_audit", {}).get("issues", []))
    for issue in issues:
        issue["factor"] = ISSUE_TO_FACTOR.get(str(issue.get("code", "")), "")
    issues.sort(key=lambda x: (SEVERITY_ORDER.get(x.get("severity", "P3"), 9), x.get("file", ""), x.get("code", "")))
    return issues


def build_factor_summary(result: Dict[str, object]) -> List[Dict[str, object]]:
    issues = collect_issues(result)
    by_factor: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for issue in issues:
        fid = str(issue.get("factor") or "")
        if fid:
            by_factor[fid].append(issue)

    has_html = bool(result.get("html_pages"))
    rows: List[Dict[str, object]] = []
    for spec in RANKING_FACTORS:
        fid = spec["id"]
        factor_issues = by_factor.get(fid, [])
        mode = spec["mode"]
        if factor_issues:
            status = "Fail"
            preview = "; ".join(
                f"{item.get('severity')} {item.get('code')} @ {item.get('file')}" for item in factor_issues[:4]
            )
            if len(factor_issues) > 4:
                preview += f" …共 {len(factor_issues)} 条"
            action = str(factor_issues[0].get("recommendation") or FACTOR_DEFAULT_ACTION[fid])
        elif mode == "code":
            if fid in {"F1", "F3", "F10"} and not has_html:
                status = "Unknown"
                preview = "没有可解析的 HTML 页面，无法从代码证明该因素"
            else:
                status = "Pass"
                preview = "静态扫描未见该因素的代码问题；不是线上排名证明"
            action = FACTOR_DEFAULT_ACTION[fid]
        else:
            status = "Unknown"
            preview = "代码无法证明该因素的线上强度；禁止编造指标"
            action = FACTOR_DEFAULT_ACTION[fid]
        if fid == "F1":
            emd = result.get("emd_observation") or {}
            emd_summary = str(emd.get("summary") or "").strip()
            if emd_summary:
                preview = f"{emd_summary}。{preview}" if preview else emd_summary
        rows.append(
            {
                "id": fid,
                "name": spec["name"],
                "share": spec["share"],
                "mode": mode,
                "status": status,
                "evidence": preview,
                "online_signal": FACTOR_ONLINE[fid],
                "action": action,
                "issue_count": len(factor_issues),
                **({"emd_level": (result.get("emd_observation") or {}).get("level")} if fid == "F1" else {}),
            }
        )
    return rows


def audit_adsense_readiness(result: Dict[str, object], root: Path, all_files: List[Path]) -> Dict[str, object]:
    checks: List[Dict[str, str]] = []
    html_pages = result.get("html_pages", [])
    seo_issues = collect_issues(result)
    issue_codes = {str(issue.get("code", "")) for issue in seo_issues}

    required_page_specs = [
        ("About 页面", ["about", "about-us", "about_us"], "P0", ["ADS-UX-05", "ADS-PUB-05"], "说明网站是谁维护、解决什么问题，让审核者看到真实站点身份。"),
        ("Contact 页面", ["contact", "contact-us", "contact_us"], "P0", ["ADS-UX-05", "ADS-PUB-05"], "提供可联系邮箱或表单；AdSense 审核通常需要基本联系入口。"),
        ("Privacy Policy 页面", ["privacy", "privacy-policy", "privacy_policy"], "P0", ["ADS-UX-05", "ADS-PRIV-01", "ADS-PRIV-02"], "补齐隐私政策，并让内容匹配实际 cookies、广告、统计和表单收集行为。"),
        ("Terms 页面", ["terms", "terms-of-service", "terms_of_service", "tos"], "P0", ["ADS-UX-05"], "补齐使用条款，说明内容、游戏/工具使用边界和免责声明。"),
    ]
    required_pages: Dict[str, List[str]] = {}
    for label, tokens, severity, ids, recommendation in required_page_specs:
        matches = find_likely_pages(all_files, root, tokens)
        required_pages[label] = matches
        if matches:
            add_adsense_check(checks, severity, label, "pass", f"发现候选文件：{', '.join(matches[:5])}", "确认页面在导航或页脚中可访问，且内容不是空模板。", ids)
        else:
            add_adsense_check(checks, severity, label, "fail", "未发现明显候选文件", recommendation, ids)

    article_files = find_likely_article_files(all_files, root)
    if len(article_files) >= 5:
        add_adsense_check(checks, "P2", "Blog / 内容区", "pass", f"发现约 {len(article_files)} 个候选内容文件", "审核阶段继续保持原创、相关、可索引，避免空壳文章。", ["ADS-CONTENT-01", "ADS-CONTENT-03", "ADS-CRAWL-07"])
    elif article_files:
        add_adsense_check(checks, "P2", "Blog / 内容区", "warn", f"只发现约 {len(article_files)} 个候选内容文件", "审核前建议准备 5-10 篇围绕游戏/工具主题的原创攻略、教程、推荐或问题解答。", ["ADS-CONTENT-01", "ADS-CONTENT-03", "ADS-CRAWL-07"])
    else:
        add_adsense_check(checks, "P2", "Blog / 内容区", "fail", "未发现明显 blog/posts/articles/guides 内容目录", "增加 Blog 或 Guides 区域，先发布 5-10 篇与主关键词和长尾词相关的原创文章。", ["ADS-CONTENT-01", "ADS-CONTENT-03", "ADS-CRAWL-07"])

    iframe_risk_pages = [
        page
        for page in html_pages
        if int(page.get("iframe_count", 0) or 0) > 0 and int(page.get("text_chars", 0) or 0) < 1200
    ]
    if iframe_risk_pages:
        preview = ", ".join(str(page.get("file", "")) for page in iframe_risk_pages[:8])
        add_adsense_check(checks, "P1", "游戏/工具页不是纯 iframe 壳", "fail", f"{len(iframe_risk_pages)} 个页面 iframe 较重且正文少：{preview}", "每个游戏/工具页补原创介绍、玩法/使用步骤、FAQ、相关内容和站内链接，不能只嵌入 iframe。", ["ADS-CONTENT-02", "ADS-CONTENT-03", "ADS-PROG-06", "ADS-PUB-11"])
    else:
        add_adsense_check(checks, "P1", "游戏/工具页不是纯 iframe 壳", "pass", "未在静态 HTML 中发现 iframe-heavy thin page", "仍需人工打开核心页确认首屏不是通用模板或纯嵌入壳。", ["ADS-CONTENT-02", "ADS-CONTENT-03", "ADS-PROG-06", "ADS-PUB-11"])

    thin_core_pages = [
        page
        for page in html_pages
        if is_adsense_core_page(str(page.get("file", ""))) and int(page.get("text_chars", 0) or 0) < 900
    ]
    if thin_core_pages:
        preview = ", ".join(f"{page.get('file')}({page.get('text_chars', 0)} chars)" for page in thin_core_pages[:8])
        add_adsense_check(checks, "P1", "首页/分类/核心页内容厚度", "fail", preview, "首页、分类页、游戏页和工具页要有可读正文、模块说明、FAQ 和相关入口；宁可页面少，也要每页扎实。", ["ADS-CONTENT-01", "ADS-CONTENT-03", "ADS-CONTENT-04", "ADS-PUB-11"])
    else:
        add_adsense_check(checks, "P1", "首页/分类/核心页内容厚度", "pass", "未发现明显核心 HTML 页面正文过薄", "如果项目是 SSR/SSG 框架，还需构建后查看源代码确认核心文案真实输出。", ["ADS-CONTENT-01", "ADS-CONTENT-03", "ADS-CONTENT-04", "ADS-PUB-11"])

    if "MISSING_VIEWPORT" in issue_codes:
        add_adsense_check(checks, "P2", "移动端基础适配", "fail", "SEO 检查发现 MISSING_VIEWPORT", "补充 viewport，并在手机视口确认游戏/工具、导航、内容和潜在广告位不会遮挡。", ["ADS-UX-01", "ADS-PUB-10", "ADS-REST-08"])
    else:
        add_adsense_check(checks, "P2", "移动端基础适配", "pass", "未发现 viewport 缺失问题", "仍需人工检查移动端布局和广告位预留。", ["ADS-UX-01", "ADS-PUB-10", "ADS-REST-08"])

    blocking_codes = sorted(issue_codes & {"NOINDEX", "ROBOTS_DISALLOW_ALL", "SITEMAP_MISSING", "CANONICAL_DOMAIN_MISMATCH"})
    if blocking_codes:
        add_adsense_check(checks, "P0", "抓取/索引基础", "fail", f"发现阻断或高风险 SEO 问题：{', '.join(blocking_codes)}", "AdSense 审核前先修复抓取、索引、sitemap 和 canonical 基础问题。", ["ADS-CRAWL-01", "ADS-CRAWL-02", "ADS-CRAWL-07"])
    else:
        add_adsense_check(checks, "P0", "抓取/索引基础", "pass", "未发现 noindex、robots 全站误封、sitemap 缺失或 canonical 错域名", "上线后仍需用 Google Search Console 验证真实收录。", ["ADS-CRAWL-01", "ADS-CRAWL-02", "ADS-CRAWL-07"])

    manual_checks = [
        {
            "ids": ["ADS-CONTENT-01", "ADS-UX-02"],
            "item": "视觉差异化",
            "why": "审核者第一眼会判断这是认真维护的网站，还是批量模板。",
            "how": "参考主打游戏/工具的配色、字体、素材和页面氛围，避免一眼通用模板。",
        },
        {
            "ids": ["ADS-CONTENT-01", "ADS-CRAWL-07"],
            "item": "真实流量与索引",
            "why": "社区经验显示，近年的 low value content 经常和无人访问、无人搜索命中相关。",
            "how": "提供 GSC 已收录页面、点击/展示、自然搜索趋势和核心页访问数据。",
        },
        {
            "ids": ["ADS-CONTENT-01", "ADS-CONTENT-03"],
            "item": "GSC 5-20 名查询",
            "why": "这些词已经被 Google 认为相关，通常比从 50 名以外冲首页更容易。",
            "how": "找 impressions 有量、排名 5-20、点击低的查询，补专门页面或优化对应段落。",
        },
        {
            "ids": ["ADS-PUB-01", "ADS-PUB-02", "ADS-PUB-03", "ADS-PUB-08", "ADS-REST-01", "ADS-REST-06"],
            "item": "版权与政策风险",
            "why": "侵权游戏、成人、赌博、仇恨/暴力等内容可能直接导致拒绝甚至封号。",
            "how": "人工确认游戏授权、素材来源、用户生成内容和站内外链接是否符合政策。",
        },
    ]

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    p0_fail_count = sum(1 for check in checks if check["status"] == "fail" and check["severity"] == "P0")
    p1_fail_count = sum(1 for check in checks if check["status"] == "fail" and check["severity"] == "P1")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    if p0_fail_count:
        conclusion = "AdSense 审核高风险：先补齐政策/信任页面和抓取索引基础，再提交审核。"
    elif p1_fail_count:
        conclusion = "AdSense 审核中高风险：当前更像薄内容或游戏/工具壳，需要先补原创内容和页面价值。"
    elif warn_count:
        conclusion = "AdSense 审核有通过基础，但内容厚度、Blog 或人工信号还需要补强。"
    else:
        conclusion = "静态检查未发现明显 AdSense 审核阻断项，但仍需人工确认视觉、流量、索引和版权政策。"

    low_value_likely_causes = [
        "核心页只有游戏 iframe、工具入口或营销文案，缺少原创解释、玩法/教程、FAQ 和相关内链。",
        "首页、分类页和详情页没有形成关键词到页面的长尾覆盖，只是堆卡片或封面图。",
        "缺少 Blog/Guides 内容区，Google 缺少可收录、可理解、可判断价值的原创页面。",
        "页面存在但无人访问或 GSC 中几乎没有收录/展示，容易被判断为没有用户价值。",
    ]
    manual_data_needed = [
        "AdSense 后台拒绝原因原文或截图",
        "Google Search Console 已收录页面数量和未收录原因",
        "GSC 查询列表，尤其是排名 5-20 且展示不低的词",
        "近 28/90 天自然流量、展示、点击和核心页面访问数据",
        "游戏/工具素材和内容版权来源说明",
    ]
    static_ads_ids = sorted({ads_id for check in checks for ads_id in check.get("ids", [])})

    return {
        "enabled": True,
        "conclusion": conclusion,
        "checks": checks,
        "manual_checks": manual_checks,
        "low_value_likely_causes": low_value_likely_causes,
        "manual_data_needed": manual_data_needed,
        "required_pages": required_pages,
        "article_count": len(article_files),
        "article_files": article_files[:50],
        "iframe_risk_pages": [page.get("file", "") for page in iframe_risk_pages[:50]],
        "thin_core_pages": [page.get("file", "") for page in thin_core_pages[:50]],
        "summary": {"fail": fail_count, "warn": warn_count, "p0_fail": p0_fail_count, "p1_fail": p1_fail_count, "static_ads_ids_evidenced": static_ads_ids},
    }


def write_adsense_markdown(lines: List[str], adsense: Dict[str, object]) -> None:
    lines.append("## AdSense 审核诊断")
    lines.append(str(adsense.get("conclusion", "")))
    lines.append("")
    lines.append("静态脚本只输出可从本地代码/静态 HTML 证明的 ADS-* 证据；完整 AdSense 审核仍需按 `references/adsense-requirements.md` 覆盖全部 73 个 ID，并把无法证明的项标为 Unknown 或 N/A。")
    lines.append("")
    lines.append("### 审核清单")
    lines.append("| ADS ID | 优先级 | 检查项 | 状态 | 证据 | 建议 |")
    lines.append("|---|---|---|---|---|---|")
    for check in adsense.get("checks", []):
        lines.append(
            f"| {escape_md(format_ads_ids(check.get('ids')))} | {escape_md(check.get('severity'))} | {escape_md(check.get('item'))} | {escape_md(check.get('status'))} | {escape_md(check.get('evidence'))} | {escape_md(check.get('recommendation'))} |"
        )
    lines.append("")

    low_value_causes = adsense.get("low_value_likely_causes", [])
    if low_value_causes:
        lines.append("### Low value content 常见原因")
        for cause in low_value_causes:
            lines.append(f"- {escape_md(cause)}")
        lines.append("")

    manual_checks = adsense.get("manual_checks", [])
    if manual_checks:
        lines.append("### 必须人工确认")
        lines.append("| ADS ID | 项目 | 为什么重要 | 怎么确认 |")
        lines.append("|---|---|---|---|")
        for check in manual_checks:
            lines.append(f"| {escape_md(format_ads_ids(check.get('ids')))} | {escape_md(check.get('item'))} | {escape_md(check.get('why'))} | {escape_md(check.get('how'))} |")
        lines.append("")

    manual_data = adsense.get("manual_data_needed", [])
    if manual_data:
        lines.append("### 建议补充的数据")
        for item in manual_data:
            lines.append(f"- {escape_md(item)}")
        lines.append("")


def write_markdown(result: Dict[str, object], output_path: Path) -> None:
    issues = collect_issues(result)
    counts = Counter(issue.get("severity", "P3") for issue in issues)
    html_pages = result.get("html_pages", [])
    project = result.get("project", {})
    factors = result.get("factor_summary") or build_factor_summary(result)

    lines: List[str] = []
    lines.append("# SEO 代码静态诊断报告")
    lines.append("")
    lines.append("主骨架是 2026 Zyppy Top 10。专家共识 ≠ Google 官方权重。本报告是代码审计，不是 GSC/Ahrefs 替代品。")
    lines.append("")
    lines.append(f"生成时间：{result.get('generated_at')}  ")
    lines.append(f"扫描根目录：`{escape_md(result.get('root'))}`  ")
    if result.get("domain"):
        lines.append(f"目标域名：`{escape_md(result.get('domain'))}`  ")
    if result.get("keywords"):
        lines.append(f"目标关键词：`{escape_md(', '.join(result.get('keywords', [])))}`  ")
    lines.append("")

    fail_ids = [str(row.get("id")) for row in factors if row.get("status") == "Fail"]
    unknown_ids = [str(row.get("id")) for row in factors if row.get("status") == "Unknown"]
    lines.append("## 一句话结论")
    if counts.get("P0"):
        lines.append(f"F8 出现 P0 table-stakes 阻断（{counts.get('P0')}）。坏的技术会摔；修好也不会抬起平庸内容。因素 Fail：{', '.join(fail_ids) or '无'}。")
    elif fail_ids:
        lines.append(f"因素 Fail：{', '.join(fail_ids)}。Unknown（需线上数据）：{', '.join(unknown_ids) or '无'}。缺 description 只进 F5，不是 F1 排名项。")
    else:
        lines.append(f"代码可证因素未见 Fail。线上因素保持 Unknown：{', '.join(unknown_ids) or '无'}。禁止编造 CTR/外链/品牌数字。")
    lines.append("")

    lines.append("## 项目识别")
    lines.append(f"- 技术栈：{escape_md(', '.join(project.get('stack', [])))}")
    if project.get("route_dirs"):
        lines.append(f"- 路由/内容目录：`{escape_md(', '.join(project.get('route_dirs', [])))}`")
    if project.get("seo_files"):
        lines.append(f"- SEO 文件：`{escape_md(', '.join(project.get('seo_files', [])))}`")
    if project.get("config_files"):
        lines.append(f"- 配置文件：`{escape_md(', '.join(project.get('config_files', [])))}`")
    lines.append("")

    lines.append("## Top 10 排名因素")
    lines.append("| 因素 | Top3% | 状态 | 代码证据 | 线上信号 | 动作 |")
    lines.append("|---|---:|---|---|---|---|")
    for row in factors:
        label = f"{row.get('id')} {row.get('name')}"
        lines.append(
            f"| {escape_md(label)} | {escape_md(row.get('share'))} | {escape_md(row.get('status'))} | {escape_md(row.get('evidence'))} | {escape_md(row.get('online_signal'))} | {escape_md(row.get('action'))} |"
        )
    lines.append("")
    lines.append("状态：`Pass` 只表示代码可证范围内未见问题；`Unknown` 表示需要 GSC/外链表/品牌数据且未提供；`Fail` 表示已有代码或用户证据。hybrid 因素没有代码问题也不会标 Pass。")
    lines.append("")

    lines.append("## F1–F10 分项证据")
    issues_by_factor: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for issue in issues:
        if issue.get("factor"):
            issues_by_factor[str(issue.get("factor"))].append(issue)
    for row in factors:
        fid = str(row.get("id"))
        lines.append(f"### {fid} {row.get('name')}（{row.get('share')}）")
        lines.append(f"- 状态：`{row.get('status')}`")
        lines.append(f"- 线上：{row.get('online_signal')}")
        factor_issues = issues_by_factor.get(fid, [])
        if factor_issues:
            lines.append("")
            lines.append("| 优先级 | 代码 | 文件 | 证据 | 建议 |")
            lines.append("|---|---|---|---|---|")
            for issue in factor_issues[:40]:
                lines.append(
                    f"| {escape_md(issue.get('severity'))} | {escape_md(issue.get('code'))} | `{escape_md(issue.get('file'))}` | {escape_md(issue.get('evidence'))} | {escape_md(issue.get('recommendation'))} |"
                )
        else:
            lines.append(f"- 代码证据：{row.get('evidence')}")
        if fid == "F1":
            emd = result.get("emd_observation") or {}
            if emd:
                lines.append(f"- 域名意图匹配/EMD：{emd.get('summary')}")
                lines.append(f"- {emd.get('note')}")
        lines.append("")

    copy_issues = [i for i in issues if i.get("code") in {"YMYL_COPY_REVIEW", "INTERNAL_COPY_LEAK"}]
    if copy_issues:
        lines.append("## 文案风险（YMYL / 内部泄露）")
        lines.append("横切项；YMYL 同时记入 F4，内部泄露同时记入 F3。")
        lines.append("")
        lines.append("| 优先级 | 代码 | 文件 | 证据 | 建议 |")
        lines.append("|---|---|---|---|---|")
        for issue in copy_issues:
            lines.append(
                f"| {escape_md(issue.get('severity'))} | {escape_md(issue.get('code'))} | `{escape_md(issue.get('file'))}` | {escape_md(issue.get('evidence'))} | {escape_md(issue.get('recommendation'))} |"
            )
        lines.append("")

    unmapped = [i for i in issues if not i.get("factor")]
    if unmapped:
        lines.append("## 未映射问题")
        lines.append("| 优先级 | 代码 | 文件 | 证据 | 建议 |")
        lines.append("|---|---|---|---|---|")
        for issue in unmapped[:40]:
            lines.append(
                f"| {escape_md(issue.get('severity'))} | {escape_md(issue.get('code'))} | `{escape_md(issue.get('file'))}` | {escape_md(issue.get('evidence'))} | {escape_md(issue.get('recommendation'))} |"
            )
        lines.append("")

    if html_pages:
        lines.append("## 页面取证摘要")
        lines.append("| 文件 | Title | H1 | 文本字符 | 图片/缺 alt | 内链 | Canonical |")
        lines.append("|---|---|---|---:|---:|---:|---|")
        for page in html_pages[:80]:
            h1 = "; ".join(str(x) for x in page.get("h1", []))
            img = f"{page.get('image_count', 0)}/{page.get('images_missing_alt', 0)}"
            lines.append(
                f"| `{escape_md(page.get('file'))}` | {escape_md(page.get('title'))} | {escape_md(h1)} | {page.get('text_chars', 0)} | {img} | {page.get('internal_links', 0)} | {escape_md(page.get('canonical'))} |"
            )
        lines.append("")

    emd = result.get("emd_observation") or {}
    if emd:
        lines.append("## F1 子项：域名意图匹配 / EMD")
        lines.append(f"- 级别：`{escape_md(emd.get('level'))}`")
        lines.append(f"- host：`{escape_md(emd.get('host') or '（无）')}`；可注册标签：`{escape_md(emd.get('label') or '（无）')}`")
        lines.append(f"- 主意图词：`{escape_md(emd.get('keyword') or '（未提供）')}`")
        lines.append(f"- 观察：{escape_md(emd.get('summary'))}")
        lines.append(f"- {escape_md(emd.get('note'))}")
        lines.append("- 口径：加分观察；品牌域不是 EMD 不判 Fail；不要建议购买垃圾/spammy EMD。")
        lines.append("")

    if result.get("keywords") and html_pages:
        lines.append("## F1 子项：关键词覆盖与堆砌")
        lines.append("密度不是优化目标，也不存在 3%–5% 或 8% 达标区间。只在目标词未出现或异常堆砌时报警，不报密度低。")
        lines.append("")
        lines.append("| 文件 | 关键词 | 出现次数 | 估算密度（仅供堆砌判断） |")
        lines.append("|---|---|---:|---:|")
        for page in html_pages[:80]:
            for kd in page.get("keyword_density", []):
                lines.append(
                    f"| `{escape_md(page.get('file'))}` | {escape_md(kd.get('keyword'))} | {kd.get('count', 0)} | {kd.get('density_percent', 0)}% |"
                )
        lines.append("")

    source_summary = result.get("source_audit", {}).get("summary", {})
    if source_summary:
        lines.append("## F8 子项：源码技术信号")
        lines.append(f"- 扫描源码文件：{source_summary.get('files_scanned', 0)}")
        for key, label in [
            ("route_files", "疑似路由文件"),
            ("metadata_files", "含 metadata/head 的文件"),
            ("canonical_mentions", "提到 canonical 的文件"),
            ("h1_mentions", "包含 H1 的文件"),
            ("json_ld_mentions", "包含 JSON-LD/schema 的文件"),
            ("client_page_risks", "Next page `use client` 风险文件"),
            ("img_without_alt_suspects", "疑似图片缺 alt 文件"),
        ]:
            values = source_summary.get(key, [])
            if values:
                preview = ", ".join(values[:12])
                suffix = " ..." if len(values) > 12 else ""
                lines.append(f"- {label}：`{escape_md(preview + suffix)}`")
        lines.append("")

    if result.get("adsense_audit"):
        write_adsense_markdown(lines, result.get("adsense_audit", {}))

    lines.append("## 建议下一步")
    lines.append("1. F8 table stakes：先修会摔的抓取/SSR/canonical/sitemap。")
    lines.append("2. F1：每个 URL 满足哪一种结果类型/任务；很多页都匹配时补 F3 信息增益。")
    lines.append("3. F7：工具/游戏首屏必须能完成任务。")
    lines.append("4. F10：具体内链，不谈权重分。")
    lines.append("5. F5：title/description 只当 CTR；缺 description 不是 F1/P1。")
    lines.append("6. F2/F4/F6/F9 的线上强度保持 Unknown，除非用户提供外链表、GSC 或品牌数据。")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ---------- main ----------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline static SEO code audit helper.")
    parser.add_argument("--root", default=".", help="Repository/site root to scan.")
    parser.add_argument("--domain", default="", help="Canonical production domain, e.g. https://example.com")
    parser.add_argument("--keywords", default="", help="Comma-separated target keywords for coverage and stuffing checks (not a density target).")
    parser.add_argument("--adsense", action="store_true", help="Add AdSense approval-readiness checks for game/tool/content sites.")
    parser.add_argument("--out", default="seo-audit", help="Output prefix, without extension.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"Root directory not found: {root}", file=sys.stderr)
        return 2

    domain = normalize_domain(args.domain)
    keywords = [normalize_ws(x) for x in args.keywords.split(",") if normalize_ws(x)]

    all_files = [p for p in iter_files(root)]
    html_files = [p for p in all_files if p.suffix.lower() in HTML_EXTS]
    source_files = [p for p in all_files if p.suffix.lower() in SOURCE_EXTS]

    project = detect_project(root, all_files)
    html_pages = [audit_html_file(path, root, domain, keywords) for path in html_files]
    source_audit = audit_source_files(root, source_files)
    repo_audit = audit_repo_files(root, all_files, domain)

    result: Dict[str, object] = {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "root": str(root),
        "domain": domain,
        "keywords": keywords,
        "project": project,
        "file_counts": {
            "all_files": len(all_files),
            "html_files": len(html_files),
            "source_files": len(source_files),
        },
        "html_pages": html_pages,
        "source_audit": source_audit,
        "repo_audit": repo_audit,
    }
    if args.adsense:
        result["adsense_audit"] = audit_adsense_readiness(result, root, all_files)
    result["emd_observation"] = assess_emd_observation(domain, keywords, html_pages)
    result["factor_summary"] = build_factor_summary(result)

    out_prefix = Path(args.out)
    if not out_prefix.is_absolute():
        out_prefix = Path.cwd() / out_prefix
    json_path = out_prefix.with_suffix(".json")
    md_path = out_prefix.with_suffix(".md")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(result, md_path)

    issues = collect_issues(result)
    counts = Counter(issue.get("severity", "P3") for issue in issues)
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print("Issues:", ", ".join(f"{sev}={counts.get(sev, 0)}" for sev in ["P0", "P1", "P2", "P3"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
