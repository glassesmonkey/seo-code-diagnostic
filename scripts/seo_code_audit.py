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
MAX_READ_BYTES = 700_000

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


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


def add_issue(issues: List[Issue], severity: str, code: str, file: str, evidence: str, recommendation: str) -> None:
    issues.append(Issue(severity, code, file, normalize_ws(evidence), normalize_ws(recommendation)))


def add_adsense_check(
    checks: List[Dict[str, str]],
    severity: str,
    item: str,
    status: str,
    evidence: str,
    recommendation: str,
) -> None:
    checks.append(
        {
            "severity": severity,
            "item": normalize_ws(item),
            "status": status,
            "evidence": normalize_ws(evidence),
            "recommendation": normalize_ws(recommendation),
        }
    )


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
        add_issue(issues, "P1", "MISSING_TITLE", file_rel, "未找到 <title>", "为每个可索引页面设置唯一 title，包含主搜索意图并吸引点击。")
    elif len(title) < 15 or len(title) > 70:
        add_issue(issues, "P3", "TITLE_LENGTH", file_rel, f"title 长度 {len(title)}: {title}", "检查标题是否过短、过长或会在搜索结果中被截断。")

    if not description:
        add_issue(issues, "P1", "MISSING_DESCRIPTION", file_rel, "未找到 meta description", "为核心页面添加能扩展 title、说明价值点并促进点击的 meta description。")
    elif len(description) < 50 or len(description) > 170:
        add_issue(issues, "P3", "DESCRIPTION_LENGTH", file_rel, f"description 长度 {len(description)}", "检查描述是否过短、过长或缺少具体收益。")

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
        pct = float(density["density_percent"])
        count = int(density["count"])
        if count == 0:
            add_issue(issues, "P2", "KEYWORD_NOT_FOUND", file_rel, f"关键词 `{kw}` 在可见文本中未出现", "确认该关键词是否应映射到此页面；如果是，补充自然表达和相关语义内容。")
        elif pct > 8:
            add_issue(issues, "P2", "KEYWORD_DENSITY_HIGH", file_rel, f"`{kw}` 密度约 {pct}%", "降低机械重复，改用同义词、实体、示例和相关问题解释主词。")
        elif 0 < pct < 1 and text_chars > 900:
            add_issue(issues, "P3", "KEYWORD_DENSITY_LOW", file_rel, f"`{kw}` 密度约 {pct}%", "如果该页目标就是这个关键词，可在 H1/H2/首段/FAQ/内链锚文本中更自然地覆盖。")

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
    issues.sort(key=lambda x: (SEVERITY_ORDER.get(x.get("severity", "P3"), 9), x.get("file", ""), x.get("code", "")))
    return issues


def audit_adsense_readiness(result: Dict[str, object], root: Path, all_files: List[Path]) -> Dict[str, object]:
    checks: List[Dict[str, str]] = []
    html_pages = result.get("html_pages", [])
    seo_issues = collect_issues(result)
    issue_codes = {str(issue.get("code", "")) for issue in seo_issues}

    required_page_specs = [
        ("About 页面", ["about", "about-us", "about_us"], "P0", "说明网站是谁维护、解决什么问题，让审核者看到真实站点身份。"),
        ("Contact 页面", ["contact", "contact-us", "contact_us"], "P0", "提供可联系邮箱或表单；AdSense 审核通常需要基本联系入口。"),
        ("Privacy Policy 页面", ["privacy", "privacy-policy", "privacy_policy"], "P0", "补齐隐私政策，并让内容匹配实际 cookies、广告、统计和表单收集行为。"),
        ("Terms 页面", ["terms", "terms-of-service", "terms_of_service", "tos"], "P0", "补齐使用条款，说明内容、游戏/工具使用边界和免责声明。"),
    ]
    required_pages: Dict[str, List[str]] = {}
    for label, tokens, severity, recommendation in required_page_specs:
        matches = find_likely_pages(all_files, root, tokens)
        required_pages[label] = matches
        if matches:
            add_adsense_check(checks, severity, label, "pass", f"发现候选文件：{', '.join(matches[:5])}", "确认页面在导航或页脚中可访问。")
        else:
            add_adsense_check(checks, severity, label, "fail", "未发现明显候选文件", recommendation)

    article_files = find_likely_article_files(all_files, root)
    if len(article_files) >= 5:
        add_adsense_check(checks, "P2", "Blog / 内容区", "pass", f"发现约 {len(article_files)} 个候选内容文件", "审核阶段继续保持原创、相关、可索引，避免空壳文章。")
    elif article_files:
        add_adsense_check(checks, "P2", "Blog / 内容区", "warn", f"只发现约 {len(article_files)} 个候选内容文件", "审核前建议准备 5-10 篇围绕游戏/工具主题的原创攻略、教程、推荐或问题解答。")
    else:
        add_adsense_check(checks, "P2", "Blog / 内容区", "fail", "未发现明显 blog/posts/articles/guides 内容目录", "增加 Blog 或 Guides 区域，先发布 5-10 篇与主关键词和长尾词相关的原创文章。")

    iframe_risk_pages = [
        page
        for page in html_pages
        if int(page.get("iframe_count", 0) or 0) > 0 and int(page.get("text_chars", 0) or 0) < 1200
    ]
    if iframe_risk_pages:
        preview = ", ".join(str(page.get("file", "")) for page in iframe_risk_pages[:8])
        add_adsense_check(checks, "P1", "游戏/工具页不是纯 iframe 壳", "fail", f"{len(iframe_risk_pages)} 个页面 iframe 较重且正文少：{preview}", "每个游戏/工具页补原创介绍、玩法/使用步骤、FAQ、相关内容和站内链接，不能只嵌入 iframe。")
    else:
        add_adsense_check(checks, "P1", "游戏/工具页不是纯 iframe 壳", "pass", "未在静态 HTML 中发现 iframe-heavy thin page", "仍需人工打开核心页确认首屏不是通用模板或纯嵌入壳。")

    thin_core_pages = [
        page
        for page in html_pages
        if is_adsense_core_page(str(page.get("file", ""))) and int(page.get("text_chars", 0) or 0) < 900
    ]
    if thin_core_pages:
        preview = ", ".join(f"{page.get('file')}({page.get('text_chars', 0)} chars)" for page in thin_core_pages[:8])
        add_adsense_check(checks, "P1", "首页/分类/核心页内容厚度", "fail", preview, "首页、分类页、游戏页和工具页要有可读正文、模块说明、FAQ 和相关入口；宁可页面少，也要每页扎实。")
    else:
        add_adsense_check(checks, "P1", "首页/分类/核心页内容厚度", "pass", "未发现明显核心 HTML 页面正文过薄", "如果项目是 SSR/SSG 框架，还需构建后查看源代码确认核心文案真实输出。")

    if "MISSING_VIEWPORT" in issue_codes:
        add_adsense_check(checks, "P2", "移动端基础适配", "fail", "SEO 检查发现 MISSING_VIEWPORT", "补充 viewport，并在手机视口确认游戏/工具、导航、内容和潜在广告位不会遮挡。")
    else:
        add_adsense_check(checks, "P2", "移动端基础适配", "pass", "未发现 viewport 缺失问题", "仍需人工检查移动端布局和广告位预留。")

    blocking_codes = sorted(issue_codes & {"NOINDEX", "ROBOTS_DISALLOW_ALL", "SITEMAP_MISSING", "CANONICAL_DOMAIN_MISMATCH"})
    if blocking_codes:
        add_adsense_check(checks, "P0", "抓取/索引基础", "fail", f"发现阻断或高风险 SEO 问题：{', '.join(blocking_codes)}", "AdSense 审核前先修复抓取、索引、sitemap 和 canonical 基础问题。")
    else:
        add_adsense_check(checks, "P0", "抓取/索引基础", "pass", "未发现 noindex、robots 全站误封、sitemap 缺失或 canonical 错域名", "上线后仍需用 Google Search Console 验证真实收录。")

    manual_checks = [
        {
            "item": "视觉差异化",
            "why": "审核者第一眼会判断这是认真维护的网站，还是批量模板。",
            "how": "参考主打游戏/工具的配色、字体、素材和页面氛围，避免一眼通用模板。",
        },
        {
            "item": "真实流量与索引",
            "why": "社区经验显示，近年的 low value content 经常和无人访问、无人搜索命中相关。",
            "how": "提供 GSC 已收录页面、点击/展示、自然搜索趋势和核心页访问数据。",
        },
        {
            "item": "GSC 5-20 名查询",
            "why": "这些词已经被 Google 认为相关，通常比从 50 名以外冲首页更容易。",
            "how": "找 impressions 有量、排名 5-20、点击低的查询，补专门页面或优化对应段落。",
        },
        {
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
        "summary": {"fail": fail_count, "warn": warn_count, "p0_fail": p0_fail_count, "p1_fail": p1_fail_count},
    }


def write_adsense_markdown(lines: List[str], adsense: Dict[str, object]) -> None:
    lines.append("## AdSense 审核诊断")
    lines.append(str(adsense.get("conclusion", "")))
    lines.append("")
    lines.append("### 审核清单")
    lines.append("| 优先级 | 检查项 | 状态 | 证据 | 建议 |")
    lines.append("|---|---|---|---|---|")
    for check in adsense.get("checks", []):
        lines.append(
            f"| {escape_md(check.get('severity'))} | {escape_md(check.get('item'))} | {escape_md(check.get('status'))} | {escape_md(check.get('evidence'))} | {escape_md(check.get('recommendation'))} |"
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
        lines.append("| 项目 | 为什么重要 | 怎么确认 |")
        lines.append("|---|---|---|")
        for check in manual_checks:
            lines.append(f"| {escape_md(check.get('item'))} | {escape_md(check.get('why'))} | {escape_md(check.get('how'))} |")
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

    lines: List[str] = []
    lines.append("# SEO 代码静态诊断报告")
    lines.append("")
    lines.append(f"生成时间：{result.get('generated_at')}  ")
    lines.append(f"扫描根目录：`{escape_md(result.get('root'))}`  ")
    if result.get("domain"):
        lines.append(f"目标域名：`{escape_md(result.get('domain'))}`  ")
    if result.get("keywords"):
        lines.append(f"目标关键词：`{escape_md(', '.join(result.get('keywords', [])))}`  ")
    lines.append("")

    lines.append("## 一句话结论")
    if counts.get("P0"):
        lines.append(f"发现 {counts.get('P0')} 个 P0 阻断型问题，优先检查抓取/索引/渲染/canonical。")
    elif counts.get("P1"):
        lines.append(f"未发现 P0，但有 {counts.get('P1')} 个 P1 高影响问题，优先修复 TDK、H1、canonical、sitemap 或 metadata。")
    elif issues:
        lines.append("未发现明显阻断型问题，主要优化空间在内容覆盖、内链、图片和结构化数据。")
    else:
        lines.append("未发现脚本可识别的明显 SEO 问题；仍建议人工检查搜索意图、竞品内容差距和线上抓取结果。")
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

    lines.append("## 优先级总览")
    lines.append("| 优先级 | 数量 | 含义 |")
    lines.append("|---|---:|---|")
    meaning = {
        "P0": "阻断抓取、索引或核心 HTML 可见性的风险",
        "P1": "高影响 on-page/technical SEO 问题",
        "P2": "内容、内链、语义、图片等中影响问题",
        "P3": "增强项和细节优化",
    }
    for sev in ["P0", "P1", "P2", "P3"]:
        lines.append(f"| {sev} | {counts.get(sev, 0)} | {meaning[sev]} |")
    lines.append("")

    if issues:
        lines.append("## 发现的问题")
        lines.append("| 优先级 | 代码 | 文件 | 证据 | 建议 |")
        lines.append("|---|---|---|---|---|")
        for issue in issues[:120]:
            lines.append(
                f"| {escape_md(issue.get('severity'))} | {escape_md(issue.get('code'))} | `{escape_md(issue.get('file'))}` | {escape_md(issue.get('evidence'))} | {escape_md(issue.get('recommendation'))} |"
            )
        if len(issues) > 120:
            lines.append(f"\n仅展示前 120 条，完整结果见 JSON，共 {len(issues)} 条。")
        lines.append("")

    if html_pages:
        lines.append("## HTML 页面摘要")
        lines.append("| 文件 | Title | H1 | 文本字符 | 图片/缺 alt | 内链 | Canonical |")
        lines.append("|---|---|---|---:|---:|---:|---|")
        for page in html_pages[:80]:
            h1 = "; ".join(str(x) for x in page.get("h1", []))
            img = f"{page.get('image_count', 0)}/{page.get('images_missing_alt', 0)}"
            lines.append(
                f"| `{escape_md(page.get('file'))}` | {escape_md(page.get('title'))} | {escape_md(h1)} | {page.get('text_chars', 0)} | {img} | {page.get('internal_links', 0)} | {escape_md(page.get('canonical'))} |"
            )
        lines.append("")

    if result.get("keywords") and html_pages:
        lines.append("## 关键词密度辅助检查")
        lines.append("关键词密度不是目标本身，只用来发现“完全没覆盖”或“机械堆砌”。")
        lines.append("")
        lines.append("| 文件 | 关键词 | 出现次数 | 估算密度 |")
        lines.append("|---|---|---:|---:|")
        for page in html_pages[:80]:
            for kd in page.get("keyword_density", []):
                lines.append(
                    f"| `{escape_md(page.get('file'))}` | {escape_md(kd.get('keyword'))} | {kd.get('count', 0)} | {kd.get('density_percent', 0)}% |"
                )
        lines.append("")

    source_summary = result.get("source_audit", {}).get("summary", {})
    if source_summary:
        lines.append("## 源码 SEO 信号")
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
    lines.append("1. 先修 P0/P1：抓取、索引、SSR/SSG、title、description、H1、canonical、sitemap。")
    lines.append("2. 再做关键词-页面映射：确认首页、二级目录、三级目录、详情页分别承载哪些词。")
    lines.append("3. 对核心落地页补齐模块：工具入口、How it works、Features、场景、FAQ、证言、相关链接、CTA。")
    lines.append("4. 加强内链：上级页链接下级页，下级页用明确锚文本链接回上级页，所有核心页自然链接到首页或支柱页。")
    lines.append("5. 构建后查看网页源代码，确认核心文案、TDK、H1/H2/H3、canonical、JSON-LD 都在 HTML 中可见。")
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
