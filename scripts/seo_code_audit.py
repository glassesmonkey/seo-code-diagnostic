#!/usr/bin/env python3
"""
Static SEO Code Audit helper for Codex.

This script performs a deterministic, offline scan of a website codebase.
It does not crawl the public web and does not replace a full browser render,
Ahrefs Site Audit, Google Search Console, or PageSpeed Insights.

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
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".next",
    ".open-next",
    ".source",
    ".nuxt",
    ".turbo",
    ".vercel",
    ".netlify",
    ".cache",
    "coverage",
    "vendor",
    "__pycache__",
    ".agents",
    ".agent",
    ".claude",
    ".codex",
    "reports",
    "report",
    "output",
    "outputs",
    "dist",
    "build",
    "logs",
    "log",
    "uploads",
    "upload",
    "database",
    "databases",
    "data",
    "db",
    "migrations",
}

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    ".next",
    ".open-next",
    ".source",
    ".nuxt",
    ".turbo",
    ".vercel",
    ".netlify",
    "coverage",
    "__pycache__",
    ".agents",
    ".agent",
    ".claude",
    ".codex",
    "reports",
    "report",
    "output",
    "outputs",
    "dist",
    "build",
    "logs",
    "log",
    "uploads",
    "upload",
    "database",
    "databases",
    "data",
    "db",
    "migrations",
}

ALLOWED_TOP_LEVEL_DIRS = {
    "src",
    "app",
    "pages",
    "routes",
    "content",
    "posts",
    "components",
    "public",
    "static",
}

ALLOWED_ROOT_FILES = {
    "package.json",
    "robots.txt",
    "sitemap.xml",
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
    "source.config.ts",
    "source.config.js",
    "source.config.mjs",
}

PRIVATE_FILE_SUFFIXES = {
    ".bak",
    ".db",
    ".dump",
    ".jsonl",
    ".log",
    ".ndjson",
    ".parquet",
    ".sql",
    ".sqlite",
    ".sqlite3",
}

HTML_EXTS = {".html", ".htm"}
SOURCE_EXTS = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro", ".md", ".mdx"}
TEXT_EXTS = HTML_EXTS | SOURCE_EXTS | {".json", ".xml", ".txt", ".config", ".mjs", ".cjs"}
COPY_REVIEW_SOURCE_EXTS = {".jsx", ".tsx", ".vue", ".svelte", ".astro", ".md", ".mdx"}
MAX_READ_BYTES = 700_000
MAX_HTTP_BYTES = 2_000_000
HTTP_TIMEOUT_SECONDS = 8

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


@dataclass
class Issue:
    severity: str
    code: str
    file: str
    evidence: str
    recommendation: str


@dataclass
class ReadState:
    text: str
    truncated: bool
    error: Optional[str] = None


@dataclass
class HTTPResult:
    requested_url: str
    status_code: Optional[int]
    headers: Dict[str, str]
    body: bytes
    text: str
    truncated: bool
    error: Optional[str]
    location: Optional[str]
    final_url: Optional[str]
    content_type: Optional[str]


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
        self._script_data_stack: List[Optional[List[str]]] = []
        self.json_ld_blocks: List[str] = []

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
                    "alt_present": "1" if "alt" in attr else "",
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
                self._script_data_stack.append([])
            else:
                self._script_data_stack.append(None)
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
            script_data = self._script_data_stack.pop() if self._script_data_stack else None
            if script_data is not None:
                self.json_ld_blocks.append("".join(script_data).strip())

        # Pop from the right until the matching tag if the markup is imperfect.
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data: str) -> None:
        if not data or not data.strip():
            return
        if self._script_data_stack and self._script_data_stack[-1] is not None:
            self._script_data_stack[-1].append(data)
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


def read_text_state(path: Path) -> ReadState:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return ReadState(text="", truncated=False, error=type(exc).__name__)
    truncated = len(data) > MAX_READ_BYTES
    data = data[:MAX_READ_BYTES]
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return ReadState(text=data.decode(enc), truncated=truncated)
        except UnicodeDecodeError:
            continue
    return ReadState(text=data.decode("utf-8", errors="ignore"), truncated=truncated)


def safe_read(path: Path) -> str:
    state = read_text_state(path)
    if state.error:
        raise OSError(state.error)
    return state.text


def should_skip(path: Path, root: Path, exclude_patterns: Iterable[str] = (), output_paths: Iterable[Path] = ()) -> bool:
    if path.is_symlink():
        return True
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    for part in rel_parts:
        if part.lower() in EXCLUDED_PARTS:
            return True
    name_lower = path.name.lower()
    if name_lower == "agents.md" or name_lower == ".dev.vars" or name_lower.startswith(".env"):
        return True
    if path.suffix.lower() in PRIVATE_FILE_SUFFIXES:
        return True
    rel_value = "/".join(rel_parts)
    if any(fnmatch.fnmatch(rel_value, pattern) or Path(rel_value).match(pattern) for pattern in exclude_patterns):
        return True
    try:
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return True
    if any(resolved == output.resolve() for output in output_paths):
        return True
    return False


def is_allowlisted(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    if not parts:
        return False
    if len(parts) == 1:
        return parts[0].lower() in ALLOWED_ROOT_FILES or (
            path.suffix.lower() in HTML_EXTS and path.stem.lower() == "index"
        )
    return parts[0].lower() in ALLOWED_TOP_LEVEL_DIRS


def iter_files(
    root: Path,
    exclude_patterns: Iterable[str] = (),
    output_paths: Iterable[Path] = (),
) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        # Mutate dirnames so os.walk does not descend into excluded dirs.
        dirnames[:] = [
            d
            for d in dirnames
            if d.lower() not in EXCLUDED_DIR_NAMES
            and d.lower() not in EXCLUDED_PARTS
            and not (current / d).is_symlink()
        ]
        if should_skip(current, root, exclude_patterns, output_paths):
            continue
        for filename in filenames:
            path = current / filename
            if should_skip(path, root, exclude_patterns, output_paths):
                continue
            if path.is_file() and is_allowlisted(path, root):
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


def keyword_density(text: str, keyword: str) -> Dict[str, object]:
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


SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|private[_-]?key|password|secret|token)\b\s*[:=]\s*)(?:[\"']?)([^\s,;\"'<>}\]]+)"
)
SECRET_TOKEN_RE = re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b")
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
SENSITIVE_REPORT_KEY_RE = re.compile(
    r"(?i)^(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|private[_-]?key|password|secret|token)$"
)


def redact_sensitive_text(value: str) -> str:
    value = SECRET_ASSIGNMENT_RE.sub(lambda match: match.group(1) + "[REDACTED]", value)
    value = SECRET_TOKEN_RE.sub("[REDACTED]", value)
    value = BEARER_RE.sub("Bearer [REDACTED]", value)
    return value


def redact_report_value(value: object, key: Optional[str] = None) -> object:
    if key and SENSITIVE_REPORT_KEY_RE.match(key) and value is not None:
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, list):
        return [redact_report_value(item) for item in value]
    if isinstance(value, dict):
        return {item_key: redact_report_value(item_value, str(item_key)) for item_key, item_value in value.items()}
    return value


def add_issue(issues: List[Issue], severity: str, code: str, file: str, evidence: str, recommendation: str) -> None:
    issues.append(Issue(severity, code, file, normalize_ws(evidence), normalize_ws(recommendation)))


def adsense_requirements() -> List[Dict[str, str]]:
    reference_path = Path(__file__).resolve().parents[1] / "references" / "adsense-requirements.md"
    try:
        text = reference_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    formal_start = text.find("## A.")
    formal_end = text.find("## Required Audit Output")
    if formal_start < 0 or formal_end <= formal_start:
        return []
    requirements: List[Dict[str, str]] = []
    seen: set = set()
    for line in text[formal_start:formal_end].splitlines():
        match = re.match(
            r"^\|\s*(ADS-[A-Z]+-[0-9]{2})\s*\|\s*(Blocker|High|Medium)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$",
            line,
        )
        if not match or match.group(1) in seen:
            continue
        seen.add(match.group(1))
        requirements.append(
            {
                "id": match.group(1),
                "severity": match.group(2),
                "requirement": normalize_ws(match.group(3)),
                "how_to_verify": normalize_ws(match.group(4)),
            }
        )
    return requirements


def adsense_requirement_ids() -> List[str]:
    return [item["id"] for item in adsense_requirements()]


def build_adsense_contract(
    enabled: bool,
    routes: List[Dict[str, object]],
    coverage: Dict[str, object],
) -> Dict[str, object]:
    requirements = adsense_requirements()
    requirement_ids = [item["id"] for item in requirements]
    empty_counts = {status: 0 for status in ["Pass", "Fail", "Unknown", "N/A"]}
    if not enabled:
        return {
            "enabled": False,
            "status": "N/A",
            "requirement_total": len(requirements),
            "reported_total": 0,
            "missing_ids": [],
            "status_counts": empty_counts,
            "items": [],
            "article_count": 0,
            "article_routes": [],
            "complete": False,
            "conclusion": None,
            "summary": empty_counts,
        }

    items = [
        {
            **requirement,
            "status": "Unknown",
            "evidence": "当前审计没有足以确认该要求的直接证据。",
            "next_action": requirement["how_to_verify"],
            "evidence_kind": "coverage_gap",
            "path_or_url": None,
            "provenance": {"mode": "coverage-gap"},
        }
        for requirement in requirements
    ]
    verified_article_routes = [
        str(route.get("route"))
        for route in routes
        if route.get("is_article") is True
        and route.get("registry_status") == "registered"
        and "registry" in route.get("sources", [])
        and route.get("runtime_reachable") is True
        and route.get("status_code") == 200
        and route.get("coverage_status") == "verified"
        and route.get("evidence_kind") in {"http", "current_rendered"}
    ]
    counts = Counter(item["status"] for item in items)
    reported_ids = {str(item.get("id")) for item in items}
    missing_ids = [ads_id for ads_id in requirement_ids if ads_id not in reported_ids]
    status_counts = {status: counts.get(status, 0) for status in ["Pass", "Fail", "Unknown", "N/A"]}
    complete = bool(
        requirements
        and coverage.get("complete") is True
        and len(items) == len(requirements)
        and not missing_ids
        and all(item["status"] in {"Pass", "Fail", "N/A"} for item in items)
    )
    return {
        "enabled": True,
        "status": "Unknown" if not complete else ("Fail" if counts.get("Fail") else "Pass"),
        "requirement_total": len(requirements),
        "reported_total": len(items),
        "missing_ids": missing_ids,
        "status_counts": status_counts,
        "items": items,
        "article_count": len(verified_article_routes),
        "article_routes": sorted(verified_article_routes),
        "complete": complete,
        "conclusion": None if not complete else ("Fail" if counts.get("Fail") else "Pass"),
        "summary": status_counts,
    }


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


def visible_copy_source(text: str, suffix: str) -> str:
    if suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro"}:
        text = re.sub(r"\{?\s*/\*.*?\*/\s*\}?", " ", text, flags=re.S)
        text = re.sub(r"(^|\s)//[^\n]*", r"\1", text)
    if suffix.lower() in {".md", ".mdx"}:
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return text


def mapped_public_route(file_rel: str) -> Optional[str]:
    route = source_route(file_rel)
    if route:
        return route
    value = file_rel.replace("\\", "/")
    match = re.search(r"(?:^|/)content/(?:posts?|articles?|blog)/(.+?)\.(?:md|mdx|html?)$", value, flags=re.I)
    if match:
        return "/blog/" + match.group(1).strip("/")
    match = re.search(r"(?:^|/)posts/(.+?)\.(?:md|mdx|html?)$", value, flags=re.I)
    if match:
        return "/blog/" + match.group(1).strip("/")
    return None


def legal_policy_route(route: Optional[str]) -> bool:
    return bool(route and re.search(r"(?:^|/)(?:terms|privacy|legal|disclaimer)(?:/|$)", route, flags=re.I))


def rel_posix(path: Path, root: Path) -> str:
    return rel(path, root).replace(os.sep, "/")


def is_user_content_file(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    return bool(
        parts
        and parts[0].lower() in {"content", "posts"}
        and path.suffix.lower() in {".md", ".mdx", ".html", ".htm", ".json"}
    )


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
        "src/app/robots.js",
        "src/app/robots.tsx",
        "src/app/robots.jsx",
        "src/app/sitemap.ts",
        "src/app/sitemap.js",
        "src/app/sitemap.tsx",
        "src/app/sitemap.jsx",
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


def parse_html(path: Path) -> Tuple[SEOHTMLParser, ReadState, Optional[str]]:
    parser = SEOHTMLParser()
    read_state = read_text_state(path)
    if read_state.error:
        return parser, read_state, None
    try:
        parser.feed(read_state.text)
    except Exception as exc:
        return parser, read_state, type(exc).__name__
    return parser, read_state, None


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
    parser, read_state, parse_error = parse_html(path)
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
    missing_alt = [img for img in parser.images if not img.get("alt_present")]
    missing_dims = [img for img in parser.images if not img.get("width") or not img.get("height")]
    script_count = len(parser.scripts)
    canonical = parser.canonicals[0] if parser.canonicals else ""
    og_url = parser.meta_props.get("og:url", "")

    page_result: Dict[str, object] = {
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
        "keyword_density": [],
        "issues": [],
    }

    if read_state.error or read_state.truncated or parse_error:
        if read_state.error:
            code = "HTML_READ_FAILED"
            evidence = f"读取失败：{read_state.error}"
            recommendation = "修复读取权限后重新扫描；当前不能依据空解析结果判断页面缺失元素。"
        elif read_state.truncated:
            code = "HTML_READ_TRUNCATED"
            evidence = f"文件超过 {MAX_READ_BYTES} bytes，HTML 读取被截断"
            recommendation = "提供可完整读取的本轮 HTML 后重新扫描；当前不能依据部分内容判断页面缺失元素。"
        else:
            code = "HTML_PARSE_FAILED"
            evidence = f"HTML 解析失败：{parse_error}"
            recommendation = "修复或重新生成 HTML 后扫描；当前不能依据解析失败判断页面缺失元素。"
        add_issue(issues, "P3", code, file_rel, evidence, recommendation)
        page_result["issues"] = [asdict(issue) for issue in issues]
        return page_result

    if re.search(r"\bnoindex\b", robots, flags=re.I):
        add_issue(issues, "P3", "NOINDEX_SOURCE_SIGNAL", file_rel, f"robots meta = {robots}", "先确认页面索引意图与运行时 robots；只有目标页冲突才升级。")

    if not title:
        add_issue(issues, "P1", "TITLE_MISSING", file_rel, "未找到 <title>", "为每个可索引页面设置唯一 title，包含主搜索意图并吸引点击。")
    elif len(title) < 15 or len(title) > 70:
        add_issue(issues, "P3", "TITLE_LENGTH", file_rel, f"title 长度 {len(title)}: {title}", "检查标题是否过短、过长或会在搜索结果中被截断。")

    if not description:
        add_issue(issues, "P3", "DESCRIPTION_GAP", file_rel, "未找到 meta description", "先确认页面类型与搜索摘要表现，再判断是否值得补充 description。")
    elif len(description) < 50 or len(description) > 170:
        add_issue(issues, "P3", "DESCRIPTION_LENGTH", file_rel, f"description 长度 {len(description)}", "检查描述是否过短、过长或缺少具体收益。")

    if parser.meta.get("keywords"):
        add_issue(issues, "P3", "META_KEYWORDS_PRESENT", file_rel, "发现 meta keywords", "通常不需要维护 meta keywords；优先优化 title、description、正文和内链。")

    if not viewport:
        add_issue(issues, "P2", "MISSING_VIEWPORT", file_rel, "未找到 viewport meta", "补充移动端 viewport，确保移动优先体验。")

    if len(parser.canonicals) == 0:
        add_issue(issues, "P3", "CANONICAL_GAP", file_rel, "未找到 rel=canonical", "结合重复 URL、索引意图与其他规范化信号判断是否需要 canonical。")
    elif len(parser.canonicals) > 1:
        add_issue(issues, "P1", "CANONICAL_CONFLICT", file_rel, f"发现 {len(parser.canonicals)} 个 canonical", "每页只保留一个 canonical，避免搜索引擎忽略冲突信号。")
    else:
        if not is_absolute_http_url(canonical):
            add_issue(issues, "P1", "CANONICAL_NOT_ABSOLUTE", file_rel, canonical, "canonical 应使用完整绝对 URL，例如 https://example.com/path。")
        if domain and is_absolute_http_url(canonical):
            canonical_host = urlparse(canonical).netloc.lower()
            domain_host = urlparse(domain).netloc.lower()
            if canonical_host != domain_host:
                add_issue(issues, "P1", "CANONICAL_CONFLICT", file_rel, canonical, f"确认 canonical 域名应统一为 {domain_host}。")
            if urlparse(canonical).scheme != "https":
                add_issue(issues, "P2", "CANONICAL_NOT_HTTPS", file_rel, canonical, "正式站点优先使用 HTTPS canonical。")

    if og_url and canonical and og_url.rstrip("/") != canonical.rstrip("/"):
        add_issue(issues, "P3", "OG_URL_CANONICAL_MISMATCH", file_rel, f"og:url={og_url}; canonical={canonical}", "通常让 og:url 与 canonical 保持一致，避免分享 URL 与规范 URL 冲突。")

    if len(h1s) == 0:
        add_issue(issues, "P1", "MAIN_HEADING_UNCLEAR", file_rel, "未找到 H1", "每个页面应有一个能直接表达主任务的清晰标题。")

    levels = [int(h.get("level", 0)) for h in parser.headings]
    for prev, cur in zip(levels, levels[1:]):
        if cur - prev > 1:
            add_issue(issues, "P2", "HEADING_SKIP", file_rel, f"标题层级从 H{prev} 跳到 H{cur}", "调整 H2/H3 层级，使内容结构更清晰。")
            break

    if text_chars < 600 and script_count >= 5:
        add_issue(issues, "P2", "RENDERED_TEXT_COVERAGE_CANDIDATE", file_rel, f"可见文本约 {text_chars} 字符，script {script_count} 个", "通过本轮运行时 HTML 验证主要文案是否实际输出；脚本数量本身不能证明 CSR-only。")
    elif text_chars < 900:
        add_issue(issues, "P3", "CONTENT_DEPTH_REVIEW", file_rel, f"可见文本约 {text_chars} 字符", "结合页面类型与搜索意图人工判断内容是否足够；固定字符数不是薄内容结论。")

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

    densities = [keyword_density(text, kw) for kw in keywords]
    for density in densities:
        kw = str(density["keyword"])
        count = int(density["count"])
        if count == 0:
            add_issue(issues, "P2", "KEYWORD_NOT_FOUND", file_rel, f"关键词 `{kw}` 在可见文本中未出现", "确认该关键词是否应映射到此页面；如果是，补充自然表达和相关语义内容。")

    page_result["keyword_density"] = densities
    page_result["issues"] = [asdict(issue) for issue in issues]
    return page_result


# ---------- source audit ----------


def audit_source_files(root: Path, source_files: List[Path]) -> Dict[str, object]:
    findings: List[Issue] = []
    summary = {
        "files_scanned": len(source_files),
        "metadata_files": [],
        "canonical_mentions": [],
        "h1_mentions": [],
        "json_ld_mentions": [],
        "client_component_pages": [],
        "img_without_alt_suspects": [],
        "route_files": [],
    }

    route_like_re = re.compile(r"(^|/)(app|pages|routes|src/pages|src/routes)/.*(page|index|\[|\.astro|\.svelte|\.vue)", re.I)
    img_tag_re = re.compile(r"<img\b([^>]*?)>", re.I | re.S)

    for path in source_files:
        file_rel = rel(path, root)
        read_state = read_text_state(path)
        if read_state.error:
            add_issue(
                findings,
                "P3",
                "SOURCE_READ_FAILED",
                file_rel,
                f"读取失败：{read_state.error}",
                "修复读取权限或编码后重新扫描；当前不能依据未命中下结论。",
            )
            continue
        content = read_state.text
        if read_state.truncated:
            add_issue(
                findings,
                "P3",
                "SOURCE_READ_TRUNCATED",
                file_rel,
                f"文件超过 {MAX_READ_BYTES} bytes，扫描内容被截断",
                "缩小文件或提供可完整读取的公开页面来源后重新扫描。",
            )
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

        # `use client` is a component boundary, not proof that initial HTML is absent.
        if re.search(r"^[\s;]*(?:'use client'|\"use client\")", content, flags=re.M):
            if re.search(r"(^|/)(app|src/app)/.*page\.(tsx|jsx|ts|js)$", file_rel.replace(os.sep, "/")):
                summary["client_component_pages"].append(file_rel)

        for match in img_tag_re.finditer(content):
            attrs = match.group(1)
            if re.search(r"\balt\s*=", attrs, flags=re.I):
                continue
            if re.search(r"\{\s*\.\.\.", attrs):
                add_issue(
                    findings,
                    "P3",
                    "SOURCE_IMG_ALT_UNKNOWN",
                    file_rel,
                    "源码 <img> 使用 spread props，无法静态确认 alt 属性",
                    "通过渲染后的 HTML 或组件调用点验证 alt；当前不能判定缺失。",
                )
            else:
                summary["img_without_alt_suspects"].append(file_rel)
                add_issue(
                    findings,
                    "P2",
                    "SOURCE_IMG_WITHOUT_ALT",
                    file_rel,
                    "源码中发现疑似 <img> 未设置 alt",
                    "为重要图片添加描述性 alt；装饰图使用 alt=\"\"。",
                )

        public_route = mapped_public_route(file_rel)
        if path.suffix.lower() in COPY_REVIEW_SOURCE_EXTS and public_route:
            copy_findings = audit_copy_text(
                visible_copy_source(content, path.suffix),
                file_rel,
                "中置信公开源码/内容",
            )
            if legal_policy_route(public_route):
                copy_findings = [issue for issue in copy_findings if issue.code != "YMYL_COPY_REVIEW"]
            findings.extend(copy_findings)

    # Repo-level hints.
    if summary["route_files"] and not summary["metadata_files"]:
        add_issue(
            findings,
            "P1",
            "NO_METADATA_SOURCE_FOUND",
            "repo",
            "未在路由/源码中发现明显 title/meta/metadata 设置",
            "检查是否有统一 SEO 组件；动态页面应生成唯一 title、description、canonical。",
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

    robots_candidates = [
        "robots.txt",
        "public/robots.txt",
        "static/robots.txt",
        "app/robots.ts",
        "app/robots.js",
        "app/robots.tsx",
        "app/robots.jsx",
        "src/app/robots.ts",
        "src/app/robots.js",
        "src/app/robots.tsx",
        "src/app/robots.jsx",
    ]
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

    sitemap_candidates = [
        "sitemap.xml",
        "public/sitemap.xml",
        "static/sitemap.xml",
        "app/sitemap.ts",
        "app/sitemap.js",
        "app/sitemap.tsx",
        "app/sitemap.jsx",
        "src/app/sitemap.ts",
        "src/app/sitemap.js",
        "src/app/sitemap.tsx",
        "src/app/sitemap.jsx",
    ]
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
    issues.sort(key=lambda x: (SEVERITY_ORDER.get(x.get("severity", "P3"), 9), x.get("file", ""), x.get("code", "")))
    return issues


def source_route(file_path: str) -> Optional[str]:
    """Map simple public page files to a route without claiming runtime reachability."""
    value = file_path.replace("\\", "/")
    match = re.search(r"(?:^|/)(?:src/)?app/(.*?)/?page\.(?:js|jsx|ts|tsx)$", value, flags=re.I)
    if match:
        parts = [part for part in match.group(1).split("/") if part and not (part.startswith("(") and part.endswith(")"))]
        return "/" + "/".join(parts) if parts else "/"
    match = re.search(r"(?:^|/)(?:src/)?pages/(.*)\.(?:js|jsx|ts|tsx)$", value, flags=re.I)
    if match:
        route = re.sub(r"(?:^|/)index$", "", match.group(1)).strip("/")
        return "/" + route if route else "/"
    return None


def html_source_route(path: Path, root: Path) -> Optional[str]:
    value = rel_posix(path, root)
    for prefix in ("public/", "static/"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    if value.lower() in {"index.html", "index.htm"}:
        return "/"
    value = re.sub(r"/index\.html?$", "", value, flags=re.I)
    value = re.sub(r"\.html?$", "", value, flags=re.I)
    return "/" + value.strip("/") if value else "/"


def normalize_route_entry(route: object, value: object) -> Optional[Dict[str, object]]:
    if not isinstance(route, str) or not route.startswith("/"):
        return None
    normalized_route = normalize_route_path(route)
    if not normalized_route:
        return None
    data = dict(value) if isinstance(value, dict) else {}
    raw_keywords = data.get("keywords", [])
    if isinstance(raw_keywords, str):
        route_keywords = [normalize_ws(item) for item in raw_keywords.split(",") if normalize_ws(item)]
    elif isinstance(raw_keywords, list):
        route_keywords = [normalize_ws(str(item)) for item in raw_keywords if normalize_ws(str(item))]
    else:
        route_keywords = []
    return {
        "route": normalized_route,
        "index_intent": normalize_index_intent(data.get("index_intent")),
        "priority": normalize_priority(data.get("priority")),
        "keywords": route_keywords,
        "intent_source": data.get("intent_source", "routes-file"),
    }


def load_routes_file(path_value: str) -> Tuple[List[Dict[str, object]], Optional[str]]:
    if not path_value:
        return [], None
    path = Path(path_value)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [], type(exc).__name__

    container: object = payload
    if isinstance(payload, dict) and "routes" in payload:
        container = payload.get("routes")

    entries: List[Dict[str, object]] = []
    if isinstance(container, dict):
        for route, value in container.items():
            entry = normalize_route_entry(route, value)
            if entry:
                entries.append(entry)
    elif isinstance(container, list):
        for value in container:
            if not isinstance(value, dict):
                continue
            entry = normalize_route_entry(value.get("route"), value)
            if entry:
                entries.append(entry)
    else:
        return [], "InvalidRouteContainer"
    return entries, None


def finding_from_issue(issue: Dict[str, str]) -> Dict[str, object]:
    path = str(issue.get("file", "repo"))
    route = mapped_public_route(path)
    code = str(issue.get("code", ""))
    read_unknown = code.startswith("SOURCE_READ_") or code.startswith("HTML_READ_")
    parse_unknown = code == "ROUTES_FILE_UNREADABLE" or code == "HTML_PARSE_FAILED"
    static_unknown = code == "SOURCE_IMG_ALT_UNKNOWN"
    absence_unknown = code in {
        "ROBOTS_MISSING",
        "SITEMAP_MISSING",
        "NO_METADATA_SOURCE_FOUND",
        "NO_CANONICAL_SOURCE_FOUND",
        "NO_SCHEMA_SOURCE_FOUND",
    }
    return {
        "status": "Unknown" if read_unknown or parse_unknown or static_unknown or absence_unknown else "Candidate",
        "impact": issue.get("severity", "P3"),
        "code": issue.get("code", "UNKNOWN_RULE"),
        "route": route,
        "route_kind": "public" if route else "unknown",
        "index_intent": "unknown",
        "indexability": "unknown",
        "runtime_reachable": None,
        "status_code": None,
        "evidence_kind": "read_state" if read_unknown else ("parse_state" if parse_unknown else "source_heuristic"),
        "path_or_url": path,
        "provenance": {"mode": "source-only"},
        "evidence": issue.get("evidence", ""),
        "recommendation": issue.get("recommendation", ""),
    }


def content_hash(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(128 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def dedupe_findings(findings: List[Dict[str, object]], root: Path) -> List[Dict[str, object]]:
    deduped: Dict[Tuple[object, object, object], Dict[str, object]] = {}
    for finding in findings:
        path_value = str(finding.get("path_or_url") or "")
        candidate_path = root / path_value
        existing_provenance = finding.get("provenance") if isinstance(finding.get("provenance"), dict) else {}
        digest = existing_provenance.get("content_hash") or (
            content_hash(candidate_path) if candidate_path.is_file() else None
        )
        key = (
            finding.get("route"),
            finding.get("code"),
            digest if digest else path_value,
        )
        if key not in deduped:
            if existing_provenance.get("mode") and existing_provenance.get("mode") != "source-only":
                provenance = dict(existing_provenance)
                provenance.setdefault("content_hash", digest)
                provenance.setdefault("paths", [path_value] if path_value else [])
                finding["provenance"] = provenance
            else:
                finding["provenance"] = {
                    "mode": "source-only",
                    "kind": finding.get("evidence_kind"),
                    "content_hash": digest,
                    "paths": [path_value] if path_value else [],
                }
            deduped[key] = finding
            continue
        provenance = deduped[key]["provenance"]
        paths = provenance.get("paths", [])
        if path_value and path_value not in paths:
            paths.append(path_value)
            paths.sort()
    return sorted(
        deduped.values(),
        key=lambda item: (
            SEVERITY_ORDER.get(str(item.get("impact", "P3")), 9),
            str(item.get("route") or ""),
            str(item.get("code") or ""),
            str(item.get("path_or_url") or ""),
        ),
    )


def coverage_gap(
    route: Optional[str],
    reason: str,
    evidence_needed: str,
    path_or_url: Optional[str] = None,
) -> Dict[str, object]:
    gap: Dict[str, object] = {
        "route": route,
        "reason": reason,
        "evidence_needed": evidence_needed,
    }
    if path_or_url:
        gap["path_or_url"] = path_or_url
    return gap


SOURCE_ORDER = {
    "routes_file": 0,
    "sitemap": 1,
    "registry": 2,
    "framework": 3,
    "content_inventory": 4,
    "rendered": 5,
    "sentinel": 6,
}


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def normalize_index_intent(value: object) -> str:
    normalized = normalize_ws(str(value or "unknown")).lower().replace("_", "")
    if normalized in {"index", "indexable"}:
        return "index"
    if normalized in {"noindex", "nonindex", "nonindexable"}:
        return "noindex"
    return "unknown"


def normalize_priority(value: object) -> str:
    normalized = normalize_ws(str(value or "normal")).lower()
    if normalized in {"core", "normal", "low", "supporting", "excluded", "sentinel"}:
        return normalized
    return "normal"


def normalize_route_path(value: object) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if any(ord(char) < 32 for char in raw) or "\\" in raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        path = parsed.path
    else:
        path = raw.split("?", 1)[0].split("#", 1)[0]
    if any(part in {".", ".."} for part in path.split("/")):
        return None
    if not path.startswith("/"):
        path = "/" + path
    path = re.sub(r"/{2,}", "/", path)
    if path != "/":
        path = path.rstrip("/")
    return path or "/"


def classify_route_kind(route: str) -> str:
    path = route.lower()
    path = re.sub(r"^/(?:\[locale\]|[a-z]{2}(?:-[a-z]{2})?)(?=/|$)", "", path) or "/"
    if re.match(r"^/(?:api|rpc|webhooks?)(?:/|$)", path):
        return "api"
    if re.match(
        r"^/(?:sign-in|sign-up|signin|signup|login|register|auth|oauth|verify-email|forgot-password|reset-password|no-permission)(?:/|$)",
        path,
    ):
        return "auth"
    if re.match(r"^/(?:admin|dashboard|account|settings|activity)(?:/|$)", path):
        return "admin"
    if re.match(r"^/(?:404|500|error|not-found)(?:/|$)", path):
        return "error"
    if path in {"/robots.txt", "/sitemap.xml", "/manifest.json", "/manifest.webmanifest", "/ads.txt"}:
        return "metadata"
    return "public"


def new_route_record(route: str) -> Dict[str, object]:
    kind = classify_route_kind(route)
    scored = kind == "public"
    return {
        "route": route,
        "route_kind": kind,
        "index_intent": "unknown",
        "intent_source": "unknown",
        "priority": "normal",
        "keywords": [],
        "sources": [],
        "scored": scored,
        "not_scored_reason": None if scored else f"route_kind:{kind}",
        "runtime_reachable": None,
        "status_code": None,
        "location": None,
        "final_url": None,
        "content_type": None,
        "indexability": "unknown",
        "evidence_kind": "source_heuristic",
        "path_or_url": route,
        "provenance": {"mode": "source-only"},
        "coverage_status": "gap" if scored else "classified",
        "is_pattern": bool(re.search(r"\[[^]]+\]", route)),
    }


def merge_route(
    route_map: Dict[str, Dict[str, object]],
    route_value: object,
    source: str,
    data: Optional[Dict[str, object]] = None,
) -> Optional[Dict[str, object]]:
    route = normalize_route_path(route_value)
    if not route:
        return None
    record = route_map.setdefault(route, new_route_record(route))
    sources = set(record.get("sources", []))
    sources.add(source)
    record["sources"] = sorted(sources, key=lambda item: (SOURCE_ORDER.get(item, 99), item))
    data = data or {}
    if source == "routes_file":
        record["index_intent"] = normalize_index_intent(data.get("index_intent"))
        record["intent_source"] = str(data.get("intent_source") or "routes-file")
        record["priority"] = normalize_priority(data.get("priority"))
        record["keywords"] = list(data.get("keywords") or [])
    elif record.get("index_intent") == "unknown" and source == "sitemap":
        record["index_intent"] = "index"
        record["intent_source"] = source
    if source != "routes_file" and data.get("route_kind") in {
        "public", "metadata", "api", "auth", "admin", "error", "redirect", "unregistered", "unknown"
    }:
        record["route_kind"] = data["route_kind"]
    if data.get("is_pattern") is not None:
        record["is_pattern"] = bool(data.get("is_pattern"))
    if data.get("path"):
        paths = set(record.get("source_paths", []))
        paths.add(str(data["path"]))
        record["source_paths"] = sorted(paths)
    if data.get("metadata_sources"):
        metadata_sources = set(record.get("metadata_sources", []))
        metadata_sources.update(str(item) for item in data.get("metadata_sources", []))
        record["metadata_sources"] = sorted(metadata_sources)
    if source != "routes_file":
        for key in ["registry_collection", "registry_status", "is_article", "locale", "sentinel_kind", "rendered_path"]:
            if key in data:
                record[key] = data[key]
    kind = str(record.get("route_kind") or "unknown")
    record["scored"] = kind == "public" and not record.get("is_pattern")
    record["not_scored_reason"] = None if record["scored"] else (
        "dynamic_pattern_without_concrete_route" if record.get("is_pattern") else f"route_kind:{kind}"
    )
    record["coverage_status"] = (
        "gap"
        if record["scored"] or (record.get("is_pattern") and kind == "public")
        else "classified"
    )
    return record


def dynamic_pattern_regex(pattern: str) -> re.Pattern:
    segments = [segment for segment in pattern.strip("/").split("/") if segment]
    pieces = ["^"]
    for index, segment in enumerate(segments):
        if index == 0 and segment == "[locale]":
            pieces.append(r"(?:/[A-Za-z]{2}(?:-[A-Za-z]{2})?)?")
        elif re.fullmatch(r"\[\[\.\.\.[^]]+\]\]", segment):
            pieces.append(r"(?:/[^/]+(?:/[^/]+)*)?")
        elif re.fullmatch(r"\[\.\.\.[^]]+\]", segment):
            pieces.append(r"/[^/]+(?:/[^/]+)*")
        elif re.fullmatch(r"\[[^]]+\]", segment):
            pieces.append(r"/[^/]+")
        else:
            pieces.append("/" + re.escape(segment))
    pieces.append(r"/?$")
    return re.compile("".join(pieces))


def resolve_dynamic_patterns(route_map: Dict[str, Dict[str, object]]) -> None:
    concrete_routes = [
        str(record.get("route"))
        for record in route_map.values()
        if not record.get("is_pattern")
        and record.get("route_kind") == "public"
        and set(record.get("sources", [])) & {"sitemap", "routes_file", "registry"}
    ]
    for record in route_map.values():
        if not record.get("is_pattern") or record.get("route_kind") != "public":
            continue
        matcher = dynamic_pattern_regex(str(record.get("route") or ""))
        matches = sorted(route for route in concrete_routes if matcher.fullmatch(route))
        if not matches:
            continue
        record["matched_routes"] = matches
        record["coverage_status"] = "classified"
        record["not_scored_reason"] = "dynamic_pattern_covered_by_concrete_routes"


def decode_http_body(data: bytes, content_type: Optional[str]) -> str:
    charset = "utf-8"
    if content_type:
        match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type, flags=re.I)
        if match:
            charset = match.group(1)
    try:
        return data.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return data.decode("utf-8", errors="replace")


def fetch_http(url: str) -> HTTPResult:
    request = Request(url, headers={"User-Agent": "seo-code-diagnostic/2", "Accept": "text/html,application/xml,text/plain,*/*"})
    opener = build_opener(NoRedirectHandler())
    response = None
    try:
        response = opener.open(request, timeout=HTTP_TIMEOUT_SECONDS)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError, OSError) as exc:
        return HTTPResult(url, None, {}, b"", "", False, type(exc).__name__, None, None, None)

    try:
        status = int(response.getcode())
        headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
        data = response.read(MAX_HTTP_BYTES + 1)
        truncated = len(data) > MAX_HTTP_BYTES
        data = data[:MAX_HTTP_BYTES]
        content_type = headers.get("content-type")
        location = headers.get("location")
        final_url = urljoin(url, location) if location and 300 <= status < 400 else response.geturl()
        return HTTPResult(
            url,
            status,
            headers,
            data,
            decode_http_body(data, content_type),
            truncated,
            None,
            location,
            final_url,
            content_type,
        )
    except (OSError, ValueError) as exc:
        return HTTPResult(url, None, {}, b"", "", False, type(exc).__name__, None, None, None)
    finally:
        if response is not None:
            response.close()


def runtime_url(base_url: str, route: str) -> str:
    return base_url.rstrip("/") + (route if route.startswith("/") else "/" + route)


def discover_sitemap(
    base_url: str,
    domain: Optional[str] = None,
) -> Tuple[List[str], HTTPResult, List[Dict[str, object]]]:
    primary = fetch_http(runtime_url(base_url, "/sitemap.xml"))
    routes: List[str] = []
    gaps: List[Dict[str, object]] = []
    visited: set = set()
    expected_host = (urlparse(domain).hostname or "").lower() if domain else ""

    def sitemap_path(value: str) -> Optional[str]:
        parsed = urlparse(value)
        route = normalize_route_path(value)
        if not route or parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        if expected_host and (parsed.hostname or "").lower() != expected_host:
            return None
        return route

    def visit(result: HTTPResult, depth: int) -> None:
        if result.requested_url in visited:
            return
        visited.add(result.requested_url)
        if len(visited) > 20 or depth > 3:
            gaps.append(
                coverage_gap(None, "sitemap_recursion_limit", "At most 20 sitemap documents and 3 nested levels", result.requested_url)
            )
            return
        if result.status_code != 200 or result.truncated or result.error:
            gaps.append(
                coverage_gap(None, "sitemap_discovery_failed", "A complete parseable current sitemap", result.requested_url)
            )
            return
        try:
            xml_root = ET.fromstring(result.text)
        except ET.ParseError:
            gaps.append(
                coverage_gap(None, "sitemap_discovery_failed", "A parseable XML sitemap", result.requested_url)
            )
            return
        root_kind = xml_root.tag.rsplit("}", 1)[-1].lower()
        loc_values = [
            normalize_ws(str(element.text or ""))
            for element in xml_root.iter()
            if element.tag.rsplit("}", 1)[-1].lower() == "loc" and normalize_ws(str(element.text or ""))
        ]
        if root_kind == "sitemapindex":
            for loc in loc_values:
                child_path = sitemap_path(loc)
                if not child_path:
                    gaps.append(
                        coverage_gap(None, "sitemap_url_invalid", "A same-domain HTTP sitemap URL without dot segments or userinfo", result.requested_url)
                    )
                    continue
                visit(fetch_http(runtime_url(base_url, child_path)), depth + 1)
            return
        if root_kind != "urlset":
            gaps.append(
                coverage_gap(None, "sitemap_discovery_failed", "A sitemapindex or urlset XML root", result.requested_url)
            )
            return
        for loc in loc_values:
            route = sitemap_path(loc)
            if route and route not in routes:
                routes.append(route)
            elif not route:
                gaps.append(
                    coverage_gap(None, "sitemap_url_invalid", "A same-domain HTTP page URL without dot segments or userinfo", result.requested_url)
                )

    visit(primary, 0)
    return routes, primary, gaps


def parse_runtime_html(text: str) -> SEOHTMLParser:
    parser = SEOHTMLParser()
    parser.feed(text)
    parser.close()
    return parser


def response_provenance(result: HTTPResult, mode: str) -> Dict[str, object]:
    return {
        "mode": mode,
        "content_hash": hashlib.sha256(result.body).hexdigest() if result.body else None,
    }


def robots_disallows_all(result: Optional[HTTPResult]) -> bool:
    if not result or result.error or result.truncated or result.status_code != 200:
        return False

    groups: List[Tuple[List[str], List[Tuple[str, str]]]] = []
    agents: List[str] = []
    directives: List[Tuple[str, str]] = []
    for raw_line in result.text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        value = value.lower()
        if field == "user-agent":
            if directives:
                groups.append((agents, directives))
                agents = []
                directives = []
            agents.append(value)
        elif agents and field in {"allow", "disallow"}:
            directives.append((field, value))
    if agents:
        groups.append((agents, directives))

    for group_agents, group_directives in groups:
        if "*" not in group_agents:
            continue
        disallows_root = any(field == "disallow" and value == "/" for field, value in group_directives)
        has_allowance = any(field == "allow" and value.startswith("/") for field, value in group_directives)
        if disallows_root and not has_allowance:
            return True
    return False


def robots_blocks_route(result: Optional[HTTPResult], route: str) -> bool:
    if not result or result.error or result.truncated or result.status_code != 200:
        return False
    agents: List[str] = []
    directives: List[Tuple[str, str]] = []
    groups: List[Tuple[List[str], List[Tuple[str, str]]]] = []
    for raw_line in result.text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if directives:
                groups.append((agents, directives))
                agents = []
                directives = []
            agents.append(value.lower())
        elif agents and field in {"allow", "disallow"}:
            directives.append((field, value))
    if agents:
        groups.append((agents, directives))

    matches: List[Tuple[int, int, str]] = []
    for group_agents, group_directives in groups:
        if "*" not in group_agents:
            continue
        for field, value in group_directives:
            if not value:
                continue
            anchored = value.endswith("$")
            raw_pattern = value[:-1] if anchored else value
            regex = "^" + re.escape(raw_pattern).replace(r"\*", ".*")
            if anchored:
                regex += "$"
            if not re.search(regex, route):
                continue
            specificity = len(raw_pattern.replace("*", ""))
            allow_tiebreak = 1 if field == "allow" else 0
            matches.append((specificity, allow_tiebreak, field))
    if not matches:
        return False
    return max(matches)[2] == "disallow"


def runtime_finding(
    record: Dict[str, object],
    result: HTTPResult,
    code: str,
    impact: str,
    evidence: str,
    recommendation: str,
    status: str = "Confirmed",
) -> Dict[str, object]:
    return {
        "code": code,
        "status": status,
        "impact": impact,
        "route": record.get("route"),
        "route_kind": record.get("route_kind", "unknown"),
        "index_intent": record.get("index_intent", "unknown"),
        "indexability": record.get("indexability", "unknown"),
        "runtime_reachable": record.get("runtime_reachable"),
        "status_code": record.get("status_code"),
        "evidence_kind": record.get("evidence_kind", "http"),
        "path_or_url": result.requested_url,
        "provenance": dict(record.get("provenance") or {"mode": "runtime"}),
        "evidence": normalize_ws(evidence),
        "recommendation": normalize_ws(recommendation),
    }


def verify_runtime_route(
    record: Dict[str, object],
    base_url: str,
    domain: Optional[str],
    provided_result: Optional[HTTPResult] = None,
    evidence_kind: str = "http",
    provenance_mode: str = "runtime",
) -> Tuple[List[Dict[str, object]], Optional[Dict[str, object]]]:
    route = str(record["route"])
    if record.get("is_pattern"):
        if record.get("route_kind") != "public" or record.get("matched_routes"):
            record["coverage_status"] = "classified"
            return [], None
        record["coverage_status"] = "gap"
        return [], coverage_gap(route, "dynamic_pattern_without_concrete_route", "A concrete URL from sitemap, routes-file, registry, or generateStaticParams", route)

    result = provided_result or fetch_http(runtime_url(base_url, route))
    record.update(
        {
            "runtime_reachable": result.status_code is not None,
            "status_code": result.status_code,
            "location": result.location,
            "final_url": result.final_url,
            "content_type": result.content_type,
            "evidence_kind": evidence_kind if result.status_code is not None else "read_state",
            "path_or_url": result.requested_url,
            "provenance": response_provenance(result, provenance_mode),
        }
    )
    if result.error or result.status_code is None:
        record["runtime_reachable"] = False
        record["coverage_status"] = "gap"
        return [], coverage_gap(route, "http_request_failed", "A successful current-run HTTP response", result.requested_url)
    if result.truncated:
        record["coverage_status"] = "gap"
        return [], coverage_gap(route, "http_body_truncated", "A complete current-run HTTP response", result.requested_url)
    if 300 <= result.status_code < 400:
        if record.get("route_kind") == "public":
            record["route_kind"] = "redirect"
        record["scored"] = False
        record["not_scored_reason"] = "runtime_redirect"
        record["indexability"] = "redirect"
        record["coverage_status"] = "classified"
        return [], None
    if result.status_code >= 400:
        record["indexability"] = "error"
        record["coverage_status"] = "verified" if record.get("scored") else "classified"
        if not record.get("scored"):
            return [], None
        if record.get("index_intent") == "index":
            impact = "P0" if record.get("priority") == "core" else "P1"
            return [
                runtime_finding(
                    record,
                    result,
                    "HTTP_UNREACHABLE",
                    impact,
                    f"目标页当前返回 HTTP {result.status_code}",
                    "修复目标路由，使其稳定返回完成主要任务的 200 HTML；若页面不应公开，更新显式索引意图。",
                )
            ], None
        return [
            runtime_finding(
                record,
                result,
                "HTTP_UNREACHABLE",
                "P2",
                f"当前返回 HTTP {result.status_code}，但索引意图未知",
                "确认该路由是否应公开索引，再决定修复响应或把它分类为非评分路由。",
                status="Unknown",
            )
        ], None
    if record.get("sentinel_kind") == "soft_404":
        record["route_kind"] = "error"
        record["scored"] = False
        record["not_scored_reason"] = "soft_404_sentinel"
        record["coverage_status"] = "classified"
        if not result.content_type or "html" not in result.content_type.lower():
            record["indexability"] = "unknown"
            return [], None
        sentinel_parser = parse_runtime_html(result.text)
        sentinel_robots = " ".join(
            value
            for value in [sentinel_parser.meta.get("robots", ""), result.headers.get("x-robots-tag", "")]
            if value
        )
        record["indexability"] = "noindex" if re.search(r"\bnoindex\b", sentinel_robots, flags=re.I) else "indexable"
        visible_text = normalize_ws(sentinel_parser.text)
        visible_h1 = [
            heading for heading in sentinel_parser.headings
            if heading.get("level") == 1 and normalize_ws(str(heading.get("text", "")))
        ]
        record["signals"] = {
            "title": sentinel_parser.title,
            "h1": [heading.get("text", "") for heading in visible_h1],
            "text_chars": len(visible_text),
            "robots": sentinel_robots,
        }
        if not visible_h1 and re.search(r"\b(?:post|page|article|content)\s+not\s+found\b|^not\s+found$", visible_text, flags=re.I):
            return [
                runtime_finding(
                    record,
                    result,
                    "SOFT_404",
                    "P1",
                    "明显不存在的 blog slug 返回 200，且可见页面呈现 not found 占位内容",
                    "对不存在实体返回真实 404/410 或明确跳转，不要输出可索引的 200 占位页。",
                )
            ], None
        return [], None
    if not record.get("scored"):
        header_robots = result.headers.get("x-robots-tag", "")
        record["indexability"] = "noindex" if re.search(r"\bnoindex\b", header_robots, flags=re.I) else "unknown"
        record["coverage_status"] = "classified"
        return [], None
    if not result.content_type or "html" not in result.content_type.lower():
        record["coverage_status"] = "verified"
        record["indexability"] = "unknown"
        status = "Confirmed" if record.get("index_intent") == "index" else "Unknown"
        return [
            runtime_finding(
                record,
                result,
                "RENDERED_CONTENT_MISSING",
                "P1" if status == "Confirmed" else "P2",
                f"公开页面返回 Content-Type {result.content_type or 'missing'}，没有可评分 HTML",
                "让公开目标路由返回包含页面主内容的 HTML，或将数据端点正确分类为 API。",
                status=status,
            )
        ], None

    html_parser = parse_runtime_html(result.text)
    robots = " ".join(
        value for value in [html_parser.meta.get("robots", ""), result.headers.get("x-robots-tag", "")] if value
    )
    record["indexability"] = "noindex" if re.search(r"\bnoindex\b", robots, flags=re.I) else "indexable"
    record["coverage_status"] = "verified"
    record["signals"] = {
        "title": html_parser.title,
        "description": html_parser.meta.get("description", ""),
        "canonical": html_parser.canonicals[0] if html_parser.canonicals else "",
        "h1": [heading.get("text", "") for heading in html_parser.headings if heading.get("level") == 1],
        "text_chars": len(html_parser.text),
        "internal_link_count": classify_links(html_parser.links, domain)[0],
        "json_ld_count": html_parser.json_ld_count,
        "robots": robots,
    }
    findings: List[Dict[str, object]] = []
    if record.get("index_intent") == "index" and record.get("indexability") == "noindex":
        impact = "P0" if record.get("priority") == "core" else "P1"
        findings.append(
            runtime_finding(
                record,
                result,
                "INDEX_INTENT_CONFLICT",
                impact,
                f"目标页意图为 index，但当前响应 robots 信号为 {robots}",
                "移除目标页 noindex，或把显式 index intent 改为 noindex 并从 sitemap/公开入口移除。",
            )
        )
    intent_status = "Confirmed" if record.get("index_intent") == "index" else "Unknown"
    if not html_parser.title:
        findings.append(
            runtime_finding(
                record,
                result,
                "TITLE_MISSING",
                "P1" if intent_status == "Confirmed" else "P3",
                "当前 HTML 没有可用 title",
                "为该目标页输出能明确表达页面任务的 title。",
                status=intent_status,
            )
        )
    h1s = [heading for heading in html_parser.headings if heading.get("level") == 1 and normalize_ws(str(heading.get("text", "")))]
    if not h1s:
        findings.append(
            runtime_finding(
                record,
                result,
                "MAIN_HEADING_UNCLEAR",
                "P1" if intent_status == "Confirmed" else "P3",
                "当前 HTML 没有可识别的主 H1",
                "输出一个清晰表达页面主任务的可见主标题。",
                status=intent_status,
            )
        )
    description = html_parser.meta.get("description", "")
    if not description:
        findings.append(
            runtime_finding(
                record,
                result,
                "DESCRIPTION_GAP",
                "P3",
                "当前 HTML 没有 meta description",
                "结合页面搜索意图补充准确摘要；此项本身不作为索引阻断。",
                status=intent_status,
            )
        )
    canonical = html_parser.canonicals[0] if html_parser.canonicals else ""
    if not canonical:
        findings.append(
            runtime_finding(
                record,
                result,
                "CANONICAL_GAP",
                "P3",
                "当前 HTML 没有 canonical；尚无重复 URL 证据",
                "如该页存在重复 URL，再补充一致的规范化信号；否则仅作为增强项。",
                status=intent_status,
            )
        )
    elif domain and is_absolute_http_url(canonical):
        canonical_host = urlparse(canonical).netloc.lower()
        domain_host = urlparse(domain).netloc.lower()
        canonical_route = normalize_route_path(canonical)
        route_conflict = canonical_route is not None and canonical_route != normalize_route_path(route)
        if canonical_host != domain_host or (intent_status == "Confirmed" and route_conflict):
            conflict = (
                f"canonical 主机 {canonical_host} 与生产域名 {domain_host} 不一致"
                if canonical_host != domain_host
                else f"显式 index 路由 {route} 的 canonical 指向 {canonical_route}"
            )
            findings.append(
                runtime_finding(
                    record,
                    result,
                    "CANONICAL_CONFLICT",
                    "P0" if record.get("priority") == "core" and intent_status == "Confirmed" else "P1",
                    conflict,
                    "把 canonical 指向该页面的正确生产规范 URL，并核对重复 URL 信号。",
                    status=intent_status,
                )
            )
    invalid_json_ld = 0
    for block in html_parser.json_ld_blocks:
        try:
            json.loads(block)
        except (json.JSONDecodeError, TypeError):
            invalid_json_ld += 1
    record["signals"]["json_ld_invalid_count"] = invalid_json_ld
    if invalid_json_ld:
        findings.append(
            runtime_finding(
                record,
                result,
                "STRUCTURED_DATA_INVALID",
                "P2",
                f"当前 HTML 有 {invalid_json_ld} 个无法解析的 JSON-LD 块",
                "修复 JSON-LD 语法，并确认结构化数据与页面可见事实一致。",
                status=intent_status,
            )
        )
    if not html_parser.text:
        findings.append(
            runtime_finding(
                record,
                result,
                "RENDERED_CONTENT_MISSING",
                "P1" if intent_status == "Confirmed" else "P3",
                "当前 HTML 没有可见正文",
                "在初始 HTML 中输出完成页面主要任务所需的可见内容。",
                status=intent_status,
            )
        )
    if any(not image.get("alt_present") for image in html_parser.images):
        findings.append(
            runtime_finding(
                record,
                result,
                "IMAGE_ALT_MISSING",
                "P2",
                "当前 HTML 存在没有 alt 属性的图片",
                "为信息图片添加描述性 alt；装饰图使用合法的 alt=\"\"。",
                status=intent_status,
            )
        )
    return findings, None


def source_commit(root: Path) -> Optional[str]:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", value) else None


def framework_slug(project: Dict[str, object]) -> str:
    stack = [str(item).lower() for item in project.get("stack", [])]
    for label, slug in [
        ("next.js", "nextjs"),
        ("nuxt", "nuxt"),
        ("astro", "astro"),
        ("sveltekit", "sveltekit"),
        ("gatsby", "gatsby"),
        ("vite", "vite"),
        ("react", "react"),
    ]:
        if any(label in item for item in stack):
            return slug
    return "unknown"


NEXT_PAGE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".md", ".mdx"}


def next_url_segments(segments: List[str]) -> Optional[List[str]]:
    output: List[str] = []
    for segment in segments:
        if not segment:
            continue
        if segment.startswith("_"):
            return None
        if segment.startswith("@"):
            continue
        if re.fullmatch(r"\([^)]*\)", segment):
            continue
        interception = re.match(r"^\((?:\.{1,3})\)(.*)$", segment)
        if interception:
            segment = interception.group(1)
            if not segment:
                continue
        output.append(segment)
    return output


def next_route_from_segments(segments: List[str]) -> Optional[str]:
    normalized = next_url_segments(segments)
    if normalized is None:
        return None
    return "/" + "/".join(normalized) if normalized else "/"


def next_layout_metadata_sources(page_path: Path, app_root: Path, root: Path) -> List[str]:
    sources: List[str] = []
    current = page_path.parent
    while current == app_root or app_root in current.parents:
        for suffix in [".ts", ".tsx", ".js", ".jsx"]:
            layout = current / f"layout{suffix}"
            if not layout.is_file():
                continue
            state = read_text_state(layout)
            if state.error or state.truncated:
                continue
            if re.search(r"\b(?:metadata|generateMetadata)\b|<title\b|<meta\b", state.text, flags=re.I):
                sources.append(rel_posix(layout, root))
        if current == app_root:
            break
        current = current.parent
    return sorted(set(sources))


def discover_next_routes(root: Path, all_files: List[Path]) -> List[Dict[str, object]]:
    candidates: List[Dict[str, object]] = []
    for path in all_files:
        relative = rel_posix(path, root)
        parts = relative.split("/")
        app_index = None
        if parts and parts[0] == "app":
            app_index = 0
        elif len(parts) > 1 and parts[:2] == ["src", "app"]:
            app_index = 1
        if app_index is not None:
            app_root = root.joinpath(*parts[: app_index + 1])
            filename = parts[-1]
            stem = Path(filename).stem
            suffix = Path(filename).suffix.lower()
            segments = parts[app_index + 1 : -1]
            route = next_route_from_segments(segments)
            if route is None:
                continue
            data: Optional[Dict[str, object]] = None
            if stem == "page" and suffix in NEXT_PAGE_EXTENSIONS:
                data = {
                    "route": route,
                    "route_kind": classify_route_kind(route),
                    "path": relative,
                    "metadata_sources": next_layout_metadata_sources(path, app_root, root),
                }
            elif stem in {
                "robots",
                "sitemap",
                "manifest",
                "opengraph-image",
                "twitter-image",
                "icon",
                "apple-icon",
            } and suffix in NEXT_PAGE_EXTENSIONS:
                endpoint = {
                    "robots": "robots.txt",
                    "sitemap": "sitemap.xml",
                    "manifest": "manifest.webmanifest",
                    "opengraph-image": "opengraph-image",
                    "twitter-image": "twitter-image",
                    "icon": "icon",
                    "apple-icon": "apple-icon",
                }[stem]
                data = {
                    "route": (route.rstrip("/") + "/" + endpoint) if route != "/" else "/" + endpoint,
                    "route_kind": "metadata",
                    "path": relative,
                    "metadata_sources": [],
                }
            elif stem == "route" and suffix in NEXT_PAGE_EXTENSIONS:
                kind = classify_route_kind(route)
                data = {
                    "route": route,
                    "route_kind": kind if kind != "public" else "unknown",
                    "path": relative,
                    "metadata_sources": [],
                }
            if data:
                data["is_pattern"] = bool(re.search(r"\[[^]]+\]", str(data["route"])))
                candidates.append(data)
            continue

        pages_index = None
        if parts and parts[0] == "pages":
            pages_index = 0
        elif len(parts) > 1 and parts[:2] == ["src", "pages"]:
            pages_index = 1
        if pages_index is None or path.suffix.lower() not in NEXT_PAGE_EXTENSIONS:
            continue
        route_parts = parts[pages_index + 1 :]
        filename_stem = Path(route_parts[-1]).stem
        if filename_stem in {"_app", "_document", "_error"}:
            continue
        route_parts[-1] = filename_stem
        if filename_stem == "index":
            route_parts = route_parts[:-1]
        route = next_route_from_segments(route_parts)
        if route is None:
            continue
        kind = classify_route_kind(route)
        if filename_stem in {"404", "500"}:
            kind = "error"
        candidates.append(
            {
                "route": route,
                "route_kind": kind,
                "path": relative,
                "metadata_sources": [],
                "is_pattern": bool(re.search(r"\[[^]]+\]", route)),
            }
        )
    return candidates


def discover_supported_locales(all_files: List[Path]) -> Tuple[Optional[set], Optional[str]]:
    locale_sets: List[set] = []
    defaults: List[str] = []
    for path in all_files:
        relative = str(path).lower().replace("\\", "/")
        if "locale" not in relative and "i18n" not in relative:
            continue
        if path.suffix.lower() not in SOURCE_EXTS | {".mjs", ".cjs"}:
            continue
        state = read_text_state(path)
        if state.error or state.truncated:
            continue
        for match in re.finditer(r"\blocales\b\s*(?::[^=]+)?=\s*\[([^\]]{0,500})\]", state.text, flags=re.S):
            values = set(re.findall(r"['\"]([A-Za-z]{2}(?:-[A-Za-z]{2})?)['\"]", match.group(1)))
            if values:
                locale_sets.append(values)
        for match in re.finditer(r"\bdefaultLocale\b\s*(?::[^=]+)?=\s*['\"]([A-Za-z]{2}(?:-[A-Za-z]{2})?)['\"]", state.text):
            defaults.append(match.group(1))
    supported = set.intersection(*locale_sets) if locale_sets else None
    default = defaults[0] if defaults else (sorted(supported)[0] if supported else None)
    return supported, default


def discover_fumadocs_registry(root: Path, all_files: List[Path]) -> List[Dict[str, object]]:
    collection_dirs: List[str] = []
    for path in all_files:
        if not re.fullmatch(r"source\.config\.(?:ts|js|mjs)", path.name, flags=re.I):
            continue
        state = read_text_state(path)
        if state.error or state.truncated:
            continue
        collection_dirs.extend(
            match.group(1).strip("/")
            for match in re.finditer(
                r"defineDocs\s*\(\s*\{[^{}]{0,1000}?\bdir\s*:\s*['\"]([^'\"]+)['\"]",
                state.text,
                flags=re.S,
            )
        )
    supported_locales, default_locale = discover_supported_locales(all_files)
    candidates: List[Dict[str, object]] = []
    for collection_dir in sorted(set(collection_dirs)):
        collection_path = root / collection_dir
        collection_name = Path(collection_dir).name.lower()
        base_path = {"posts": "/blog", "pages": "", "docs": "/docs", "logs": "/logs"}.get(
            collection_name,
            "/" + collection_name,
        )
        for path in all_files:
            try:
                relative_content = path.relative_to(collection_path)
            except ValueError:
                continue
            if path.suffix.lower() not in {".md", ".mdx"}:
                continue
            content_parts = list(relative_content.parts)
            filename = Path(content_parts[-1])
            stem = filename.stem
            locale = None
            locale_match = re.match(r"^(.*)\.([A-Za-z]{2}(?:-[A-Za-z]{2})?)$", stem)
            if locale_match:
                stem = locale_match.group(1)
                locale = locale_match.group(2)
            content_parts[-1] = stem
            if content_parts[-1].lower() == "index":
                content_parts = content_parts[:-1]
            slug = "/".join(part for part in content_parts if part)
            route = (base_path.rstrip("/") + ("/" + slug if slug else "")) or "/"
            invalid_locale = bool(locale and (supported_locales is None or locale not in supported_locales))
            if locale and locale != default_locale:
                route = "/" + locale + (route if route != "/" else "")
            candidates.append(
                {
                    "route": route,
                    "route_kind": "unregistered" if invalid_locale else "public",
                    "path": rel_posix(path, root),
                    "is_pattern": False,
                    "registry_collection": collection_name,
                    "registry_status": "invalid_locale" if invalid_locale else "registered",
                    "is_article": collection_name == "posts" and not invalid_locale,
                    "locale": locale or default_locale,
                }
            )
    return candidates


def discover_locale_message_registry(root: Path, all_files: List[Path]) -> List[Dict[str, object]]:
    registered_paths: set = set()
    for path in all_files:
        relative = rel_posix(path, root).lower()
        if "locale" not in relative and "i18n" not in relative:
            continue
        if path.suffix.lower() not in SOURCE_EXTS | {".mjs", ".cjs"}:
            continue
        state = read_text_state(path)
        if state.error or state.truncated:
            continue
        for match in re.finditer(
            r"\blocaleMessagesPaths\b\s*(?::[^=]+)?=\s*\[([^\]]{0,20000})\]",
            state.text,
            flags=re.S,
        ):
            registered_paths.update(
                value.strip("/")
                for value in re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
                if value.strip("/").startswith("pages/")
            )

    supported_locales, default_locale = discover_supported_locales(all_files)
    candidates: List[Dict[str, object]] = []
    pattern = re.compile(r"(?:^|/)locale/messages/([^/]+)/pages/(.+)\.json$", flags=re.I)
    for path in all_files:
        relative = rel_posix(path, root)
        match = pattern.search(relative)
        if not match:
            continue
        locale = match.group(1)
        content_path = "pages/" + match.group(2).strip("/")
        is_registered = content_path in registered_paths
        invalid_locale = bool(supported_locales is not None and locale not in supported_locales)
        route = "/" + content_path[len("pages/") :]
        if locale != default_locale:
            route = "/" + locale + route
        candidates.append(
            {
                "route": route,
                "route_kind": "public" if is_registered and not invalid_locale else "unregistered",
                "path": relative,
                "is_pattern": False,
                "registry_collection": "locale_messages_pages",
                "registry_status": (
                    "registered" if is_registered and not invalid_locale else (
                        "invalid_locale" if invalid_locale else "unregistered"
                    )
                ),
                "is_article": False,
                "locale": locale,
                "source": "registry" if is_registered and not invalid_locale else "content_inventory",
            }
        )
    return candidates


def discover_rendered_routes(rendered_root: Path) -> List[Dict[str, object]]:
    if not rendered_root.is_dir() or rendered_root.is_symlink():
        return []
    root_resolved = rendered_root.resolve()
    candidates: List[Dict[str, object]] = []
    for dirpath, dirnames, filenames in os.walk(rendered_root):
        current = Path(dirpath)
        dirnames[:] = [
            name for name in dirnames
            if not (current / name).is_symlink()
            and (current / name).resolve().is_relative_to(root_resolved)
        ]
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() not in HTML_EXTS or path.is_symlink():
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(root_resolved)
            except (OSError, ValueError):
                continue
            candidates.append(
                {
                    "route": html_source_route(path, rendered_root),
                    "route_kind": "public",
                    "path": rel_posix(path, rendered_root),
                    "rendered_path": rel_posix(path, rendered_root),
                    "is_pattern": False,
                }
            )
    return sorted(candidates, key=lambda item: (str(item["route"]), str(item["path"])))


def rendered_http_result(path: Path, safe_path: str, route: str, domain: Optional[str]) -> HTTPResult:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return HTTPResult(safe_path, None, {}, b"", "", False, type(exc).__name__, None, None, "text/html")
    truncated = len(data) > MAX_HTTP_BYTES
    data = data[:MAX_HTTP_BYTES]
    final_url = domain.rstrip("/") + route if domain else route
    return HTTPResult(
        safe_path,
        200,
        {"content-type": "text/html; charset=utf-8"},
        data,
        decode_http_body(data, "text/html; charset=utf-8"),
        truncated,
        None,
        None,
        final_url,
        "text/html; charset=utf-8",
    )


def coverage_contract(
    routes: List[Dict[str, object]],
    findings: List[Dict[str, object]],
    gaps: List[Dict[str, object]],
) -> Dict[str, object]:
    confirmed = Counter(
        str(finding.get("impact")) for finding in findings if finding.get("status") == "Confirmed"
    )
    by_source = Counter()
    by_kind = Counter()
    for route in routes:
        by_kind[str(route.get("route_kind") or "unknown")] += 1
        for source in route.get("sources", []):
            by_source[str(source)] += 1
    verified = sum(1 for route in routes if route.get("scored") and route.get("coverage_status") == "verified")
    complete = bool(routes) and not gaps and all(
        route.get("coverage_status") in {"verified", "classified"} for route in routes
    )
    counts = {impact: confirmed.get(impact, 0) for impact in ["P0", "P1", "P2", "P3"]}
    return {
        "target_total": len(routes),
        "verified_total": verified,
        "gap_total": len(gaps),
        "complete": complete,
        "by_source": dict(sorted(by_source.items())),
        "by_route_kind": dict(sorted(by_kind.items())),
        "gaps": gaps,
        "confirmed_counts": counts,
        # Compatibility aliases retained for schema-v1 consumers during migration.
        "target_routes": len(routes),
        "verified_routes": verified,
    }


def write_markdown(result: Dict[str, object], output_path: Path) -> None:
    findings = list(result.get("findings", []))
    coverage = dict(result.get("coverage", {}))
    scope = dict(result.get("scope", {}))
    confirmed_counts = dict(result.get("summary", {}).get("confirmed_by_impact", {}))

    lines: List[str] = [
        "# SEO Code Diagnostic 报告（schema v2）",
        "",
        f"生成时间：{escape_md(result.get('generated_at'))}  ",
        f"扫描根目录：`{escape_md(scope.get('root'))}`  ",
    ]
    if scope.get("domain"):
        lines.append(f"目标域名：`{escape_md(scope.get('domain'))}`  ")
    if scope.get("base_url"):
        lines.append(f"验证地址：`{escape_md(scope.get('base_url'))}`  ")
    lines.extend(["", "## 结论"])

    confirmed_p0_p2 = sum(int(confirmed_counts.get(impact, 0) or 0) for impact in ["P0", "P1", "P2"])
    if not coverage.get("complete"):
        lines.append(
            f"覆盖不完整；当前仅确认 Confirmed P0-P2 = {confirmed_p0_p2}，不能据此给出全站清洁结论。"
        )
    elif confirmed_p0_p2:
        lines.append(f"Confirmed P0-P2 = {confirmed_p0_p2}；按影响级别处理下表中的已确认问题。")
    else:
        lines.append("目标路由覆盖完整，Confirmed P0-P2 = 0。")
    lines.extend(
        [
            "",
            "## Evidence gate 汇总",
            "| 影响 | Confirmed 数量 |",
            "|---|---:|",
        ]
    )
    for impact in ["P0", "P1", "P2", "P3"]:
        lines.append(f"| {impact} | {int(confirmed_counts.get(impact, 0) or 0)} |")
    lines.append("")

    gaps = list(coverage.get("gaps", []))
    lines.extend(
        [
            "## Coverage",
            f"- 目标路由：{int(coverage.get('target_routes', 0) or 0)}",
            f"- 已验证路由：{int(coverage.get('verified_routes', 0) or 0)}",
            f"- 完整：{'是' if coverage.get('complete') else '否'}",
            "",
        ]
    )
    if gaps:
        lines.extend(["| 路由 | 缺口原因 | 需要的证据 | 路径/URL |", "|---|---|---|---|"])
        for gap in gaps:
            lines.append(
                f"| {escape_md(gap.get('route'))} | {escape_md(gap.get('reason'))} | "
                f"{escape_md(gap.get('evidence_needed'))} | {escape_md(gap.get('path_or_url'))} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Findings",
            "| 状态 | 影响 | 规则 | 路由 | 证据类型 | 路径/URL | 证据 |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for finding in findings:
        lines.append(
            f"| {escape_md(finding.get('status'))} | {escape_md(finding.get('impact'))} | "
            f"{escape_md(finding.get('code'))} | {escape_md(finding.get('route'))} | "
            f"{escape_md(finding.get('evidence_kind'))} | {escape_md(finding.get('path_or_url'))} | "
            f"{escape_md(finding.get('evidence'))} |"
        )
    if not findings:
        lines.append("| Unknown | - | NO_EVIDENCE |  | coverage_gap |  | 尚无足够证据。 |")
    lines.append("")

    unmapped_keywords = list(scope.get("unmapped_keywords", []))
    if unmapped_keywords:
        lines.extend(
            [
                "## 未映射关键词",
                "这些词只作为待映射清单，不应用到每个页面：",
                "",
                *[f"- {escape_md(keyword)}" for keyword in unmapped_keywords],
                "",
            ]
        )

    adsense = dict(result.get("adsense", {}))
    if adsense.get("enabled"):
        lines.extend(
            [
                "## AdSense",
                f"- 状态：{escape_md(adsense.get('status'))}",
                f"- 已验证文章路由：{int(adsense.get('article_count', 0) or 0)}",
                f"- 检查项：{int(adsense.get('reported_total', 0) or 0)}/{int(adsense.get('requirement_total', 0) or 0)}",
                f"- 证据完整：{'是' if adsense.get('complete') else '否'}",
                "",
                "| ADS ID | Severity | Status | Evidence | Next action |",
                "|---|---|---|---|---|",
            ]
        )
        for item in adsense.get("items", []):
            lines.append(
                f"| {escape_md(item.get('id'))} | {escape_md(item.get('severity'))} | "
                f"{escape_md(item.get('status'))} | {escape_md(item.get('evidence'))} | "
                f"{escape_md(item.get('next_action'))} |"
            )
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def stable_result_hash(result: Dict[str, object]) -> str:
    comparable = json.loads(json.dumps(result, ensure_ascii=False))
    comparable.pop("generated_at", None)
    scope = comparable.get("scope")
    if isinstance(scope, dict):
        scope.pop("started_at", None)
        provenance = scope.get("provenance")
        if isinstance(provenance, dict):
            provenance.pop("result_hash", None)
    encoded = json.dumps(comparable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# ---------- main ----------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline static SEO code audit helper.")
    parser.add_argument("--root", default=".", help="Repository/site root to scan.")
    parser.add_argument("--domain", default="", help="Canonical production domain, e.g. https://example.com")
    parser.add_argument("--keywords", default="", help="Comma-separated target keywords for density checks.")
    parser.add_argument("--adsense", action="store_true", help="Add AdSense approval-readiness checks for game/tool/content sites.")
    parser.add_argument("--out", default="seo-audit", help="Output prefix, without extension.")
    parser.add_argument("--base-url", default="", help="Local or remote HTTP origin reserved for URL-level verification.")
    parser.add_argument("--routes-file", default="", help="JSON route intent mapping.")
    parser.add_argument("--rendered-root", default="", help="Static output produced by the current audit run.")
    parser.add_argument("--exclude", action="append", default=[], help="Additional root-relative glob to exclude; repeatable.")
    args = parser.parse_args(argv)
    if args.base_url and args.rendered_root:
        parser.error("--base-url and --rendered-root cannot be used together")
    if args.base_url:
        parsed_base_url = urlparse(args.base_url)
        if (
            parsed_base_url.scheme.lower() not in {"http", "https"}
            or not parsed_base_url.hostname
            or parsed_base_url.username is not None
            or parsed_base_url.password is not None
        ):
            parser.error("--base-url must be an HTTP(S) origin without userinfo")

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"Root directory not found: {root}", file=sys.stderr)
        return 2

    domain = normalize_domain(args.domain)
    keywords = [normalize_ws(x) for x in args.keywords.split(",") if normalize_ws(x)]

    out_prefix = Path(args.out)
    if not out_prefix.is_absolute():
        if args.out == "seo-audit":
            out_prefix = root.parent / f"{root.name}-seo-audit"
        else:
            out_prefix = Path.cwd() / out_prefix
    json_path = out_prefix.with_suffix(".json")
    md_path = out_prefix.with_suffix(".md")
    json_path.parent.mkdir(parents=True, exist_ok=True)

    started_at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    base_url = args.base_url.rstrip("/")
    runtime_enabled = bool(base_url)
    rendered_root = Path(args.rendered_root).resolve() if args.rendered_root else None
    inventory_files = [p for p in iter_files(root, args.exclude, [json_path, md_path])]
    fumadocs_candidates = discover_fumadocs_registry(root, inventory_files)
    locale_message_candidates = discover_locale_message_registry(root, inventory_files)
    registered_content_paths = {
        str(candidate.get("path"))
        for candidate in fumadocs_candidates
        if candidate.get("registry_status") == "registered" and candidate.get("path")
    }
    all_files = [
        path
        for path in inventory_files
        if not is_user_content_file(path, root)
        or rel_posix(path, root) in registered_content_paths
    ]
    html_files = [p for p in all_files if p.suffix.lower() in HTML_EXTS]
    source_files = [p for p in all_files if p.suffix.lower() in SOURCE_EXTS]
    route_entries, routes_file_error = load_routes_file(args.routes_file)
    routes_by_path = {str(entry["route"]): entry for entry in route_entries}
    mapped_keyword_keys = {
        str(keyword).casefold()
        for entry in route_entries
        for keyword in entry.get("keywords", [])
    }
    unmapped_keywords = [keyword for keyword in keywords if keyword.casefold() not in mapped_keyword_keys]

    project = detect_project(root, all_files)
    if rendered_root and framework_slug(project) == "nextjs":
        parser.error("Next.js projects must use a fresh build plus --base-url; --rendered-root is for static frameworks")
    html_pages = []
    for path in html_files:
        page_route = html_source_route(path, root)
        mapped_keywords = list(routes_by_path.get(page_route, {}).get("keywords", []))
        page = audit_html_file(path, root, domain, mapped_keywords)
        page["route"] = page_route
        html_pages.append(page)
    source_audit = audit_source_files(root, source_files)
    repo_audit = audit_repo_files(root, all_files, domain)

    route_map: Dict[str, Dict[str, object]] = {}
    for entry in route_entries:
        merge_route(route_map, entry.get("route"), "routes_file", entry)
    if framework_slug(project) == "nextjs":
        for candidate in discover_next_routes(root, all_files):
            merge_route(route_map, candidate.get("route"), "framework", candidate)
    for candidate in fumadocs_candidates:
        merge_route(route_map, candidate.get("route"), "registry", candidate)
    for candidate in locale_message_candidates:
        merge_route(route_map, candidate.get("route"), str(candidate.get("source")), candidate)
    if rendered_root:
        for candidate in discover_rendered_routes(rendered_root):
            merge_route(route_map, candidate.get("route"), "rendered", candidate)

    sitemap_result: Optional[HTTPResult] = None
    robots_result: Optional[HTTPResult] = None
    sitemap_gaps: List[Dict[str, object]] = []
    if runtime_enabled:
        sitemap_routes, sitemap_result, sitemap_gaps = discover_sitemap(base_url, domain)
        for route in sitemap_routes:
            merge_route(route_map, route, "sitemap")
        robots_result = fetch_http(runtime_url(base_url, "/robots.txt"))
        if (
            robots_result.error
            or robots_result.truncated
            or robots_result.status_code != 200
        ):
            sitemap_gaps.append(
                coverage_gap(
                    None,
                    "robots_discovery_failed",
                    "A complete current robots.txt response with HTTP 200",
                    robots_result.requested_url,
                )
            )
        local_host = (urlparse(base_url).hostname or "").lower()
        has_blog_entity = any(
            path.startswith("/blog/")
            and path != "/blog/__seo-audit-sentinel__"
            and not re.search(r"\[[^]]+\]", path)
            for path in route_map
        )
        if local_host in {"127.0.0.1", "localhost", "::1"} and has_blog_entity:
            sentinel = merge_route(route_map, "/blog/__seo-audit-sentinel__", "sentinel")
            if sentinel:
                sentinel.update(
                    {
                        "route_kind": "error",
                        "index_intent": "noindex",
                        "intent_source": "soft-404-sentinel",
                        "priority": "sentinel",
                        "scored": False,
                        "not_scored_reason": "soft_404_sentinel",
                        "coverage_status": "classified",
                        "sentinel_kind": "soft_404",
                    }
                )

    resolve_dynamic_patterns(route_map)
    routes = [route_map[key] for key in sorted(route_map)]
    runtime_findings: List[Dict[str, object]] = []
    gaps: List[Dict[str, object]] = list(sitemap_gaps)
    if runtime_enabled:
        for route in routes:
            route_findings, gap = verify_runtime_route(route, base_url, domain)
            runtime_findings.extend(route_findings)
            if gap:
                gaps.append(gap)
        site_blocked = robots_disallows_all(robots_result)
        if site_blocked:
            for route in routes:
                if (
                    route.get("scored")
                    and route.get("index_intent") == "index"
                    and route.get("coverage_status") == "verified"
                ):
                    route["indexability"] = "blocked"
                    impact = "P0" if route.get("priority") == "core" else "P1"
                    finding = runtime_finding(
                        route,
                        robots_result,
                        "ROBOTS_SITE_BLOCK",
                        impact,
                        "robots.txt 的 User-agent: * 组使用 Disallow: / 阻止目标页抓取",
                        "移除全站阻断，或将明确不应索引的页面从 index intent 与 sitemap 中移除。",
                    )
                    finding["provenance"] = response_provenance(robots_result, "runtime")
                    runtime_findings.append(finding)
        else:
            existing_intent_conflicts = {
                str(finding.get("route"))
                for finding in runtime_findings
                if finding.get("code") == "INDEX_INTENT_CONFLICT"
            }
            for route in routes:
                route_path = str(route.get("route") or "")
                if (
                    route_path in existing_intent_conflicts
                    or not route.get("scored")
                    or route.get("index_intent") != "index"
                    or route.get("coverage_status") != "verified"
                    or not robots_blocks_route(robots_result, route_path)
                ):
                    continue
                route["indexability"] = "blocked"
                impact = "P0" if route.get("priority") == "core" else "P1"
                finding = runtime_finding(
                    route,
                    robots_result,
                    "INDEX_INTENT_CONFLICT",
                    impact,
                    f"robots.txt 的 User-agent: * 规则阻止抓取目标路由 {route_path}",
                    "调整 robots Allow/Disallow 规则，或把该路由的显式 index intent 改为 noindex。",
                )
                finding["provenance"] = response_provenance(robots_result, "runtime")
                runtime_findings.append(finding)
    elif rendered_root:
        for route in routes:
            rendered_path = route.get("rendered_path")
            if rendered_path:
                path = rendered_root / str(rendered_path)
                response = rendered_http_result(path, str(rendered_path), str(route.get("route")), domain)
                route_findings, gap = verify_runtime_route(
                    route,
                    "",
                    domain,
                    provided_result=response,
                    evidence_kind="current_rendered",
                    provenance_mode="current_rendered",
                )
                runtime_findings.extend(route_findings)
                if gap:
                    gaps.append(gap)
            elif route.get("scored"):
                gaps.append(
                    coverage_gap(
                        str(route.get("route")),
                        "current_rendered_missing",
                        "A mapped HTML file in --rendered-root",
                    )
                )
    else:
        for route in routes:
            if route.get("is_pattern"):
                gaps.append(
                    coverage_gap(
                        str(route.get("route")),
                        "dynamic_pattern_without_concrete_route",
                        "A concrete URL from sitemap, routes-file, registry, or generateStaticParams",
                    )
                )
            elif route.get("scored"):
                gaps.append(
                    coverage_gap(
                        str(route.get("route")),
                        "runtime_not_verified",
                        "HTTP response from --base-url or a current-run rendered artifact",
                    )
                )

    debug_result: Dict[str, object] = {
        "html_pages": html_pages,
        "source_audit": source_audit,
        "repo_audit": repo_audit,
    }
    legacy_issues = collect_issues(debug_result)
    if sitemap_result and sitemap_result.status_code == 200 and not sitemap_result.error:
        legacy_issues = [issue for issue in legacy_issues if issue.get("code") not in {"SITEMAP_MISSING", "SITEMAP_EMPTY"}]
    if robots_result and robots_result.status_code == 200 and not robots_result.error:
        legacy_issues = [issue for issue in legacy_issues if issue.get("code") != "ROBOTS_MISSING"]
    if routes_file_error and args.routes_file:
        legacy_issues.append(
            asdict(
                Issue(
                    "P3",
                    "ROUTES_FILE_UNREADABLE",
                    str(Path(args.routes_file).resolve()),
                    f"routes-file 无法解析：{routes_file_error}",
                    "修复 JSON 或路由容器后重新扫描；当前路由覆盖未知。",
                )
            )
        )
    findings = dedupe_findings([finding_from_issue(issue) for issue in legacy_issues] + runtime_findings, root)
    for page in html_pages:
        page.pop("issues", None)
    source_audit.pop("issues", None)
    repo_audit.pop("issues", None)
    if not routes:
        gaps.append(
            coverage_gap(
                None,
                "no_target_routes",
                "A sitemap, routes-file, framework route inventory, or registered content",
            )
        )
    existing_gap_keys = {(gap.get("route"), gap.get("reason"), gap.get("path_or_url")) for gap in gaps}
    for finding in findings:
        if finding.get("status") != "Unknown" or not finding.get("path_or_url"):
            continue
        finding_code = str(finding.get("code"))
        mapped_route = finding.get("route")
        verified_route = route_map.get(str(mapped_route)) if mapped_route else None
        if verified_route and verified_route.get("coverage_status") == "verified" and verified_route.get("evidence_kind") in {
            "http",
            "current_rendered",
        }:
            continue
        if finding_code in {
            "ROBOTS_MISSING",
            "SITEMAP_MISSING",
            "NO_METADATA_SOURCE_FOUND",
            "NO_CANONICAL_SOURCE_FOUND",
            "NO_SCHEMA_SOURCE_FOUND",
        }:
            continue
        if not mapped_route and finding_code in {
            "SOURCE_READ_TRUNCATED",
            "SOURCE_READ_FAILED",
            "SOURCE_IMG_ALT_UNKNOWN",
        }:
            continue
        reason = {
            "ROUTES_FILE_UNREADABLE": "routes_file_unreadable",
            "SOURCE_READ_TRUNCATED": "source_read_truncated",
            "SOURCE_READ_FAILED": "source_read_failed",
            "HTML_READ_TRUNCATED": "html_read_truncated",
            "HTML_READ_FAILED": "html_read_failed",
            "HTML_PARSE_FAILED": "html_parse_failed",
            "SOURCE_IMG_ALT_UNKNOWN": "rendered_attribute_needed",
        }.get(finding_code, "evidence_unknown")
        needed = {
            "routes_file_unreadable": "A readable JSON routes-file",
            "source_read_truncated": "A complete readable source file",
            "source_read_failed": "A readable source file",
            "html_read_truncated": "A complete current-run HTML document",
            "html_read_failed": "A readable current-run HTML document",
            "html_parse_failed": "A parseable current-run HTML document",
            "rendered_attribute_needed": "Rendered HTML for the mapped route",
        }.get(reason, "Additional runtime or source evidence")
        gap = coverage_gap(
            finding.get("route"),
            reason,
            needed,
            str(finding.get("path_or_url")),
        )
        key = (gap.get("route"), gap.get("reason"), gap.get("path_or_url"))
        if key not in existing_gap_keys:
            gaps.append(gap)
            existing_gap_keys.add(key)

    coverage = coverage_contract(routes, findings, gaps)
    commit = source_commit(root)
    mode = "runtime" if runtime_enabled else ("rendered" if args.rendered_root else "source-only")
    result: Dict[str, object] = {
        "schema_version": 2,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
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
        "scope": {
            "root": str(root),
            "domain": domain,
            "base_url": base_url,
            "rendered_root": str(rendered_root) if rendered_root else None,
            "framework": framework_slug(project),
            "mode": mode,
            "source_commit": commit,
            "started_at": started_at,
            "route_sources": coverage["by_source"],
            "routes_file": str(Path(args.routes_file).resolve()) if args.routes_file else None,
            "routes_file_error": routes_file_error,
            "excludes": list(args.exclude),
            "output_paths": [str(json_path), str(md_path)],
            "scanned_paths": sorted(rel_posix(path, root) for path in all_files),
            "unmapped_keywords": unmapped_keywords,
            "provenance": {"mode": mode, "source_commit": commit},
        },
        "coverage": coverage,
        "routes": routes,
        "findings": findings,
        "adsense": build_adsense_contract(bool(args.adsense), routes, coverage),
        "summary": {
            "confirmed_by_impact": coverage["confirmed_counts"],
            "finding_statuses": dict(Counter(finding["status"] for finding in findings)),
        },
    }
    result = redact_report_value(result)
    result["scope"]["provenance"]["result_hash"] = stable_result_hash(result)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(result, md_path)

    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    confirmed = result["summary"]["confirmed_by_impact"]
    print("Confirmed:", ", ".join(f"{impact}={confirmed.get(impact, 0)}" for impact in ["P0", "P1", "P2", "P3"]))
    print("Finding statuses:", json.dumps(result["summary"]["finding_statuses"], ensure_ascii=False, sort_keys=True))
    if not result["coverage"]["complete"]:
        print(f"Coverage incomplete: {len(result['coverage']['gaps'])} gap(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
