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
import sys
from collections import Counter
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
    resolved = path.resolve()
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
        dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDED_DIR_NAMES and d.lower() not in EXCLUDED_PARTS]
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


def adsense_requirement_ids() -> List[str]:
    reference_path = Path(__file__).resolve().parents[1] / "references" / "adsense-requirements.md"
    try:
        text = reference_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    return sorted(set(re.findall(r"ADS-[A-Z]+-[0-9]{2}", text)))


def build_adsense_contract(enabled: bool, routes: List[Dict[str, object]]) -> Dict[str, object]:
    if not enabled:
        return {
            "enabled": False,
            "status": "N/A",
            "items": [],
            "article_count": 0,
            "complete": False,
            "conclusion": None,
            "summary": {"Pass": 0, "Fail": 0, "Unknown": 0, "N/A": 0},
        }

    ids = adsense_requirement_ids()
    items = [
        {
            "id": ads_id,
            "status": "Unknown",
            "evidence_kind": "coverage_gap",
            "path_or_url": None,
            "provenance": {"mode": "coverage-gap"},
        }
        for ads_id in ids
    ]
    verified_article_routes = [
        str(route.get("route"))
        for route in routes
        if route.get("runtime_reachable") is True
        and route.get("status_code") == 200
        and re.match(r"^/(?:blog|articles?|guides?)/[^/]+", str(route.get("route") or ""))
    ]
    counts = Counter(item["status"] for item in items)
    complete = bool(items) and all(item["status"] in {"Pass", "Fail", "N/A"} for item in items)
    return {
        "enabled": True,
        "status": "Unknown" if not complete else ("Fail" if counts.get("Fail") else "Pass"),
        "items": items,
        "article_count": len(verified_article_routes),
        "article_routes": verified_article_routes,
        "complete": complete,
        "conclusion": None if not complete else ("Fail" if counts.get("Fail") else "Pass"),
        "summary": {status: counts.get(status, 0) for status in ["Pass", "Fail", "Unknown", "N/A"]},
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
        add_issue(issues, "P1", "MISSING_TITLE", file_rel, "未找到 <title>", "为每个可索引页面设置唯一 title，包含主搜索意图并吸引点击。")
    elif len(title) < 15 or len(title) > 70:
        add_issue(issues, "P3", "TITLE_LENGTH", file_rel, f"title 长度 {len(title)}: {title}", "检查标题是否过短、过长或会在搜索结果中被截断。")

    if not description:
        add_issue(issues, "P3", "MISSING_DESCRIPTION", file_rel, "未找到 meta description", "先确认页面类型与搜索摘要表现，再判断是否值得补充 description。")
    elif len(description) < 50 or len(description) > 170:
        add_issue(issues, "P3", "DESCRIPTION_LENGTH", file_rel, f"description 长度 {len(description)}", "检查描述是否过短、过长或缺少具体收益。")

    if parser.meta.get("keywords"):
        add_issue(issues, "P3", "META_KEYWORDS_PRESENT", file_rel, "发现 meta keywords", "通常不需要维护 meta keywords；优先优化 title、description、正文和内链。")

    if not viewport:
        add_issue(issues, "P2", "MISSING_VIEWPORT", file_rel, "未找到 viewport meta", "补充移动端 viewport，确保移动优先体验。")

    if len(parser.canonicals) == 0:
        add_issue(issues, "P3", "MISSING_CANONICAL", file_rel, "未找到 rel=canonical", "结合重复 URL、索引意图与其他规范化信号判断是否需要 canonical。")
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
        add_issue(issues, "P3", "MAIN_HEADING_AMBIGUOUS", file_rel, f"发现 {len(h1s)} 个 H1: {[h.get('text') for h in h1s[:5]]}", "仅当多个同等显著标题让页面主标题不清时调整层级。")

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
    data = dict(value) if isinstance(value, dict) else {}
    raw_keywords = data.get("keywords", [])
    if isinstance(raw_keywords, str):
        route_keywords = [normalize_ws(item) for item in raw_keywords.split(",") if normalize_ws(item)]
    elif isinstance(raw_keywords, list):
        route_keywords = [normalize_ws(str(item)) for item in raw_keywords if normalize_ws(str(item))]
    else:
        route_keywords = []
    return {
        "route": route,
        "index_intent": data.get("index_intent", "Unknown"),
        "priority": data.get("priority", "normal"),
        "keywords": route_keywords,
        "intent_source": data.get("intent_source", "routes-file"),
        **{key: item for key, item in data.items() if key not in {"route", "index_intent", "priority", "keywords", "intent_source"}},
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
    return {
        "status": "Unknown" if read_unknown or parse_unknown or static_unknown else "Candidate",
        "impact": issue.get("severity", "P3"),
        "code": issue.get("code", "UNKNOWN_RULE"),
        "route": route,
        "route_kind": "page" if route else "repository",
        "index_intent": "Unknown",
        "indexability": "Unknown",
        "runtime_reachable": None,
        "status_code": None,
        "evidence_kind": "read_state" if read_unknown else ("parse_state" if parse_unknown else "source_heuristic"),
        "path_or_url": path,
        "provenance": "source-only",
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
        digest = content_hash(candidate_path) if candidate_path.is_file() else None
        key = (
            finding.get("route"),
            finding.get("code"),
            digest if digest else path_value,
        )
        if key not in deduped:
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
                f"- 73 项证据完整：{'是' if adsense.get('complete') else '否'}",
                "",
                "| ADS ID | 状态 | 证据类型 |",
                "|---|---|---|",
            ]
        )
        for item in adsense.get("items", []):
            lines.append(
                f"| {escape_md(item.get('id'))} | {escape_md(item.get('status'))} | "
                f"{escape_md(item.get('evidence_kind'))} |"
            )
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


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

    all_files = [p for p in iter_files(root, args.exclude, [json_path, md_path])]
    html_files = [p for p in all_files if p.suffix.lower() in HTML_EXTS]
    source_files = [p for p in all_files if p.suffix.lower() in SOURCE_EXTS]
    route_entries, routes_file_error = load_routes_file(args.routes_file)
    routes_by_path = {str(entry["route"]): entry for entry in route_entries}

    project = detect_project(root, all_files)
    html_pages = []
    for path in html_files:
        page_route = html_source_route(path, root)
        mapped_keywords = list(routes_by_path.get(page_route, {}).get("keywords", []))
        page = audit_html_file(path, root, domain, mapped_keywords)
        page["route"] = page_route
        html_pages.append(page)
    source_audit = audit_source_files(root, source_files)
    repo_audit = audit_repo_files(root, all_files, domain)

    result: Dict[str, object] = {
        "schema_version": 2,
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
        "scope": {
            "root": str(root),
            "domain": domain,
            "base_url": args.base_url.rstrip("/"),
            "routes_file": str(Path(args.routes_file).resolve()) if args.routes_file else None,
            "rendered_root": str(Path(args.rendered_root).resolve()) if args.rendered_root else None,
            "excludes": list(args.exclude),
            "scanned_paths": sorted(rel_posix(path, root) for path in all_files),
            "unmapped_keywords": keywords,
            "routes_file_error": routes_file_error,
        },
        "coverage": {
            "complete": False,
            "target_routes": len(route_entries),
            "verified_routes": 0,
            "gaps": [
                coverage_gap(
                    str(entry.get("route")),
                    "runtime_not_verified",
                    "HTTP response from --base-url or a current-run rendered artifact",
                )
                for entry in route_entries
            ]
            or [
                coverage_gap(
                    None,
                    "no_target_routes",
                    "A sitemap, routes-file, or framework route inventory",
                )
            ],
        },
        "routes": route_entries,
        "findings": [],
        "adsense": build_adsense_contract(bool(args.adsense), route_entries),
    }
    legacy_issues = collect_issues(result)
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
    result["findings"] = dedupe_findings([finding_from_issue(issue) for issue in legacy_issues], root)
    for page in result["html_pages"]:
        page.pop("issues", None)
    result["source_audit"].pop("issues", None)
    result["repo_audit"].pop("issues", None)
    existing_gap_keys = {
        (gap.get("route"), gap.get("reason"), gap.get("path_or_url")) for gap in result["coverage"]["gaps"]
    }
    for finding in result["findings"]:
        if finding.get("status") != "Unknown" or not finding.get("path_or_url"):
            continue
        reason = {
            "ROUTES_FILE_UNREADABLE": "routes_file_unreadable",
            "SOURCE_READ_TRUNCATED": "source_read_truncated",
            "SOURCE_READ_FAILED": "source_read_failed",
            "HTML_READ_TRUNCATED": "html_read_truncated",
            "HTML_READ_FAILED": "html_read_failed",
            "HTML_PARSE_FAILED": "html_parse_failed",
            "SOURCE_IMG_ALT_UNKNOWN": "rendered_attribute_needed",
        }.get(str(finding.get("code")), "evidence_unknown")
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
            result["coverage"]["gaps"].append(gap)
            existing_gap_keys.add(key)
    confirmed_counts = Counter(
        finding["impact"] for finding in result["findings"] if finding.get("status") == "Confirmed"
    )
    result["summary"] = {
        "confirmed_by_impact": {impact: confirmed_counts.get(impact, 0) for impact in ["P0", "P1", "P2", "P3"]},
        "finding_statuses": dict(Counter(finding["status"] for finding in result["findings"])),
    }
    result = redact_report_value(result)
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
