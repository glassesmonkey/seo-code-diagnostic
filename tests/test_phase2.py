import json
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "seo_code_audit.py"


@contextmanager
def fixture_server(responses, request_log=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if request_log is not None:
                request_log.append(path)
            status, headers, body = responses.get(
                path,
                (404, {"Content-Type": "text/plain; charset=utf-8"}, "not found"),
            )
            payload = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class RuntimeAuditTestCase(unittest.TestCase):
    def run_audit(self, root: Path, base_url: str, *extra_args: str):
        output_prefix = root.parent / "reports" / "runtime-audit"
        output_prefix.parent.mkdir(exist_ok=True)
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                "--base-url",
                base_url,
                "--out",
                str(output_prefix),
                *extra_args,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        payload = None
        if output_prefix.with_suffix(".json").exists():
            payload = json.loads(output_prefix.with_suffix(".json").read_text(encoding="utf-8"))
        return completed, payload

    def test_runtime_discovers_sitemap_route_and_verifies_it_on_base_url(self):
        html = """<!doctype html>
        <html><head>
          <title>Verified runtime page</title>
          <meta name="description" content="A complete runtime fixture page.">
          <link rel="canonical" href="https://prod.example/ok">
          <script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
        </head><body><main><h1>Verified runtime page</h1><p>Useful page content.</p>
        <a href="/ok">Self link</a></main></body></html>"""
        responses = {
            "/robots.txt": (
                200,
                {"Content-Type": "text/plain; charset=utf-8"},
                "User-agent: *\nAllow: /\nSitemap: https://prod.example/sitemap.xml\n",
            ),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset><url><loc>https://prod.example/ok</loc></url></urlset>",
            ),
            "/ok": (200, {"Content-Type": "text/html; charset=utf-8"}, html),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            root.mkdir()

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["scope"]["mode"], "runtime")
            self.assertEqual(payload["scope"]["base_url"], base_url)
            self.assertEqual(payload["scope"]["domain"], "https://prod.example")
            self.assertEqual(payload["scope"]["provenance"]["mode"], "runtime")
            self.assertIn("started_at", payload["scope"])
            self.assertEqual(payload["coverage"]["target_total"], 1)
            self.assertEqual(payload["coverage"]["verified_total"], 1)
            self.assertEqual(payload["coverage"]["gap_total"], 0)
            self.assertTrue(payload["coverage"]["complete"])
            route = payload["routes"][0]
            self.assertEqual(route["route"], "/ok")
            self.assertEqual(route["route_kind"], "public")
            self.assertEqual(route["index_intent"], "index")
            self.assertEqual(route["indexability"], "indexable")
            self.assertEqual(route["sources"], ["sitemap"])
            self.assertTrue(route["scored"])
            self.assertTrue(route["runtime_reachable"])
            self.assertEqual(route["status_code"], 200)
            self.assertEqual(route["content_type"], "text/html; charset=utf-8")
            self.assertEqual(route["evidence_kind"], "http")
            self.assertEqual(route["coverage_status"], "verified")
            self.assertEqual(route["provenance"]["mode"], "runtime")
            self.assertEqual(payload["coverage"]["confirmed_counts"], {"P0": 0, "P1": 0, "P2": 0, "P3": 0})

    def test_redirect_api_and_admin_routes_are_fetched_without_following_or_on_page_scoring(self):
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, "<urlset></urlset>"),
            "/go": (307, {"Content-Type": "text/plain", "Location": "/landing"}, "redirecting"),
            "/landing": (200, {"Content-Type": "text/html"}, "<title>Should not be followed</title>"),
            "/api/status": (200, {"Content-Type": "application/json"}, '{"ok":true}'),
            "/admin/users": (302, {"Content-Type": "text/plain", "Location": "/sign-in"}, "login"),
            "/sign-in": (200, {"Content-Type": "text/html"}, "<title>Sign in</title>"),
        }
        requests = []
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses, requests) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps(
                    {
                        "routes": {
                            "/go": {"index_intent": "noindex"},
                            "/api/status": {"index_intent": "noindex"},
                            "/admin/users": {"index_intent": "noindex"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(root, base_url, "--routes-file", str(routes_file))

            self.assertEqual(completed.returncode, 0, completed.stderr)
            by_route = {route["route"]: route for route in payload["routes"]}
            self.assertEqual(by_route["/go"]["route_kind"], "redirect")
            self.assertEqual(by_route["/go"]["status_code"], 307)
            self.assertEqual(by_route["/go"]["location"], "/landing")
            self.assertEqual(by_route["/go"]["final_url"], base_url + "/landing")
            self.assertEqual(by_route["/go"]["coverage_status"], "classified")
            self.assertEqual(by_route["/api/status"]["route_kind"], "api")
            self.assertEqual(by_route["/api/status"]["status_code"], 200)
            self.assertEqual(by_route["/api/status"]["coverage_status"], "classified")
            self.assertEqual(by_route["/admin/users"]["route_kind"], "admin")
            self.assertEqual(by_route["/admin/users"]["status_code"], 302)
            self.assertEqual(by_route["/admin/users"]["indexability"], "redirect")
            self.assertNotIn("/landing", requests)
            self.assertNotIn("/sign-in", requests)
            on_page_codes = {"TITLE_MISSING", "MAIN_HEADING_UNCLEAR", "DESCRIPTION_GAP", "CANONICAL_GAP"}
            self.assertFalse(on_page_codes & {finding["code"] for finding in payload["findings"]})
            self.assertTrue(payload["coverage"]["complete"])

    def test_index_intent_conflict_requires_runtime_noindex_and_uses_priority(self):
        def page(path, robots_meta=""):
            robots = f'<meta name="robots" content="{robots_meta}">' if robots_meta else ""
            return (
                "<html><head><title>Indexed target page</title>"
                '<meta name="description" content="Complete target description.">'
                f'<link rel="canonical" href="https://prod.example{path}">{robots}'
                "</head><body><main><h1>Indexed target page</h1><p>Useful content.</p>"
                '<a href="/">Home</a></main></body></html>'
            )

        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, "<urlset></urlset>"),
            "/core-noindex": (200, {"Content-Type": "text/html"}, page("/core-noindex", "noindex, follow")),
            "/normal-noindex": (
                200,
                {"Content-Type": "text/html", "X-Robots-Tag": "noindex"},
                page("/normal-noindex"),
            ),
            "/unknown-noindex": (200, {"Content-Type": "text/html"}, page("/unknown-noindex", "noindex")),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps(
                    {
                        "routes": {
                            "/core-noindex": {"index_intent": "index", "priority": "core"},
                            "/normal-noindex": {"index_intent": "index", "priority": "normal"},
                            "/unknown-noindex": {"index_intent": "unknown", "priority": "core"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
                "--routes-file",
                str(routes_file),
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            conflicts = [finding for finding in payload["findings"] if finding["code"] == "INDEX_INTENT_CONFLICT"]
            self.assertEqual([(item["route"], item["impact"], item["status"]) for item in conflicts], [
                ("/core-noindex", "P0", "Confirmed"),
                ("/normal-noindex", "P1", "Confirmed"),
            ])
            self.assertTrue(all(item["evidence_kind"] == "http" for item in conflicts))
            self.assertTrue(all(item["provenance"]["mode"] == "runtime" for item in conflicts))
            self.assertEqual(payload["coverage"]["confirmed_counts"], {"P0": 1, "P1": 1, "P2": 0, "P3": 0})
            by_route = {route["route"]: route for route in payload["routes"]}
            self.assertEqual(by_route["/unknown-noindex"]["indexability"], "noindex")
            self.assertFalse(any(item["route"] == "/unknown-noindex" and item["status"] == "Confirmed" for item in conflicts))

    def test_runtime_http_and_on_page_findings_follow_rubric_impacts(self):
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, "<urlset></urlset>"),
            "/core-500": (500, {"Content-Type": "text/html"}, "<h1>Server error</h1>"),
            "/missing-fields": (
                200,
                {"Content-Type": "text/html"},
                "<html><head></head><body><main><p>Useful task content.</p><a href='/'>Home</a></main></body></html>",
            ),
            "/multiple-h1": (
                200,
                {"Content-Type": "text/html"},
                "<html><head><title>Clear primary topic</title>"
                '<meta name="description" content="Complete description.">'
                '<link rel="canonical" href="https://prod.example/multiple-h1"></head>'
                "<body><main><h1>Clear primary topic</h1><section><h1>Secondary named section</h1>"
                "<p>Useful task content.</p><a href='/'>Home</a></section></main></body></html>",
            ),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps(
                    {
                        "routes": {
                            "/core-500": {"index_intent": "index", "priority": "core"},
                            "/missing-fields": {"index_intent": "index", "priority": "normal"},
                            "/multiple-h1": {"index_intent": "index", "priority": "normal"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
                "--routes-file",
                str(routes_file),
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            keyed = {(item["route"], item["code"]): item for item in payload["findings"]}
            self.assertEqual(keyed[("/core-500", "HTTP_UNREACHABLE")]["impact"], "P0")
            self.assertEqual(keyed[("/core-500", "HTTP_UNREACHABLE")]["status"], "Confirmed")
            self.assertEqual(keyed[("/missing-fields", "TITLE_MISSING")]["impact"], "P1")
            self.assertEqual(keyed[("/missing-fields", "MAIN_HEADING_UNCLEAR")]["impact"], "P1")
            self.assertEqual(keyed[("/missing-fields", "DESCRIPTION_GAP")]["impact"], "P3")
            self.assertEqual(keyed[("/missing-fields", "CANONICAL_GAP")]["impact"], "P3")
            self.assertNotIn(("/multiple-h1", "MAIN_HEADING_UNCLEAR"), keyed)
            self.assertEqual(payload["coverage"]["confirmed_counts"], {"P0": 1, "P1": 2, "P2": 0, "P3": 2})

    def test_local_blog_sentinel_detects_visible_soft_404_without_raw_script_false_positive(self):
        valid_page = (
            "<html><head><title>Valid article</title>"
            '<meta name="description" content="A valid article description.">'
            '<link rel="canonical" href="https://prod.example/blog/valid"></head>'
            "<body><main><h1>Valid article</h1><p>Useful article content.</p>"
            '<script>const debug = "Post not found";</script><a href="/blog">Blog</a></main></body></html>'
        )
        soft_404_page = (
            "<html><head><title>Post not found</title>"
            '<link rel="canonical" href="https://prod.example/blog/__seo-audit-sentinel__"></head>'
            "<body><main><p>Post not found</p></main></body></html>"
        )
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, "<urlset></urlset>"),
            "/blog/valid": (200, {"Content-Type": "text/html"}, valid_page),
            "/blog/__seo-audit-sentinel__": (200, {"Content-Type": "text/html"}, soft_404_page),
        }
        requests = []
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses, requests) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps({"routes": {"/blog/valid": {"index_intent": "index", "priority": "normal"}}}),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
                "--routes-file",
                str(routes_file),
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("/blog/__seo-audit-sentinel__", requests)
            soft_findings = [item for item in payload["findings"] if item["code"] == "SOFT_404"]
            self.assertEqual(len(soft_findings), 1)
            self.assertEqual(soft_findings[0]["route"], "/blog/__seo-audit-sentinel__")
            self.assertEqual(soft_findings[0]["status"], "Confirmed")
            self.assertEqual(soft_findings[0]["impact"], "P1")
            self.assertFalse(any(item["route"] == "/blog/valid" and item["code"] == "SOFT_404" for item in payload["findings"]))
            sentinel = next(route for route in payload["routes"] if route["route"] == "/blog/__seo-audit-sentinel__")
            self.assertEqual(sentinel["sources"], ["sentinel"])
            self.assertEqual(sentinel["route_kind"], "error")
            self.assertFalse(sentinel["scored"])
            self.assertEqual(sentinel["status_code"], 200)
            self.assertEqual(sentinel["coverage_status"], "classified")

    def test_next_adapter_handles_route_groups_dynamic_patterns_metadata_and_layout_inheritance(self):
        about_page = (
            "<html><head><title>About runtime page</title>"
            '<meta name="description" content="Complete about description.">'
            '<link rel="canonical" href="https://prod.example/about"></head>'
            "<body><main><h1>About runtime page</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
        )
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, "<urlset></urlset>"),
            "/about": (200, {"Content-Type": "text/html"}, about_page),
            "/api/status": (200, {"Content-Type": "application/json"}, '{"ok":true}'),
        }
        requests = []
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses, requests) as base_url:
            root = Path(temp_dir) / "site"
            files = {
                "package.json": '{"dependencies":{"next":"15.0.0","react":"19.0.0"}}',
                "src/app/layout.tsx": "export const metadata={title:'Inherited title',description:'Inherited description'}; export default function Layout({children}){return children}",
                "src/app/(marketing)/about/page.tsx": "export default function Page(){return <main><h1>About</h1></main>}",
                "src/app/[locale]/docs/[...slug]/page.tsx": "export default function Page(){return <main><h1>Docs</h1></main>}",
                "src/app/[locale]/(auth)/sign-in/page.tsx": "export default function Page(){return <main><h1>Sign in</h1></main>}",
                "src/app/robots.ts": "export default function robots(){return {rules:{userAgent:'*',allow:'/'}}}",
                "src/app/sitemap.ts": "export default function sitemap(){return []}",
                "src/app/opengraph-image.tsx": "export default function Image(){return null}",
                "src/app/api/status/route.ts": "export async function GET(){return Response.json({ok:true})}",
            }
            for relative_path, content in files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["scope"]["framework"], "nextjs")
            by_route = {route["route"]: route for route in payload["routes"]}
            self.assertIn("/about", by_route)
            self.assertEqual(by_route["/about"]["sources"], ["framework"])
            self.assertEqual(by_route["/about"]["status_code"], 200)
            self.assertIn("src/app/layout.tsx", by_route["/about"]["metadata_sources"])
            pattern = by_route["/[locale]/docs/[...slug]"]
            self.assertTrue(pattern["is_pattern"])
            self.assertEqual(pattern["coverage_status"], "gap")
            self.assertNotIn("/[locale]/docs/[...slug]", requests)
            self.assertEqual(by_route["/robots.txt"]["route_kind"], "metadata")
            self.assertEqual(by_route["/sitemap.xml"]["route_kind"], "metadata")
            self.assertEqual(by_route["/opengraph-image"]["route_kind"], "metadata")
            self.assertEqual(by_route["/[locale]/sign-in"]["route_kind"], "auth")
            self.assertEqual(by_route["/[locale]/sign-in"]["coverage_status"], "classified")
            self.assertNotIn("/[locale]/sign-in", requests)
            self.assertEqual(by_route["/api/status"]["route_kind"], "api")
            self.assertEqual(by_route["/api/status"]["status_code"], 200)
            self.assertFalse(by_route["/api/status"]["scored"])
            self.assertFalse(payload["coverage"]["complete"])
            self.assertTrue(any(gap["reason"] == "dynamic_pattern_without_concrete_route" for gap in payload["coverage"]["gaps"]))
            self.assertFalse(any(item["route"] == "/[locale]/docs/[...slug]" and item["code"] in {"TITLE_MISSING", "MAIN_HEADING_UNCLEAR"} for item in payload["findings"]))

    def test_next_locale_pattern_is_covered_by_trusted_concrete_route(self):
        page = (
            "<html><head><title>Pricing</title>"
            '<meta name="description" content="Complete pricing description.">'
            '<link rel="canonical" href="https://prod.example/pricing"></head>'
            "<body><main><h1>Pricing</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
        )
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset><url><loc>https://prod.example/pricing</loc></url></urlset>",
            ),
            "/pricing": (200, {"Content-Type": "text/html"}, page),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            files = {
                "package.json": '{"dependencies":{"next":"15.0.0"}}',
                "src/app/[locale]/pricing/page.tsx": "export default function Page(){return <h1>Pricing</h1>}",
            }
            for relative_path, content in files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            by_route = {route["route"]: route for route in payload["routes"]}
            pattern = by_route["/[locale]/pricing"]
            self.assertEqual(pattern["coverage_status"], "classified")
            self.assertEqual(pattern["matched_routes"], ["/pricing"])
            self.assertEqual(by_route["/pricing"]["coverage_status"], "verified")
            self.assertTrue(payload["coverage"]["complete"])

    def test_fumadocs_registry_materializes_pages_posts_and_classifies_invalid_locale(self):
        def page(path, title):
            return (
                f"<html><head><title>{title}</title>"
                f'<meta name="description" content="Complete {title} description.">'
                f'<link rel="canonical" href="https://prod.example{path}"></head>'
                f"<body><main><h1>{title}</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
            )

        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, "<urlset></urlset>"),
            "/about": (200, {"Content-Type": "text/html"}, page("/about", "About")),
            "/blog/first-post": (200, {"Content-Type": "text/html"}, page("/blog/first-post", "First post")),
            "/zh/privacy-policy": (404, {"Content-Type": "text/html"}, "<h1>Not found</h1>"),
            "/blog/__seo-audit-sentinel__": (404, {"Content-Type": "text/html"}, "<h1>Not found</h1>"),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            files = {
                "package.json": '{"dependencies":{"next":"15.0.0"}}',
                "source.config.ts": (
                    "import {defineDocs} from 'fumadocs-mdx/config';"
                    "export const pages=defineDocs({dir:'content/pages'});"
                    "export const posts=defineDocs({dir:'content/posts'});"
                ),
                "src/config/locale/index.ts": "export const locales = ['en']; export const defaultLocale = 'en';",
                "content/pages/about.mdx": "---\ntitle: About\ndescription: About page\n---\n# About",
                "content/pages/privacy-policy.zh.mdx": "---\ntitle: 隐私\n---\n# 隐私",
                "content/posts/first-post.mdx": "---\ntitle: First post\ndescription: First post\n---\n# First post",
                "content/drafts/not-registered.mdx": "---\ntitle: Draft\n---\n# Draft",
            }
            for relative_path, content in files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            by_route = {route["route"]: route for route in payload["routes"]}
            self.assertEqual(by_route["/about"]["sources"], ["registry"])
            self.assertEqual(by_route["/about"]["index_intent"], "unknown")
            self.assertEqual(by_route["/about"]["status_code"], 200)
            self.assertEqual(by_route["/blog/first-post"]["sources"], ["registry"])
            self.assertTrue(by_route["/blog/first-post"]["is_article"])
            self.assertEqual(by_route["/blog/first-post"]["status_code"], 200)
            invalid_locale = by_route["/zh/privacy-policy"]
            self.assertEqual(invalid_locale["route_kind"], "unregistered")
            self.assertEqual(invalid_locale["registry_status"], "invalid_locale")
            self.assertFalse(invalid_locale["scored"])
            self.assertEqual(invalid_locale["status_code"], 404)
            self.assertNotIn("/not-registered", by_route)
            self.assertEqual(payload["coverage"]["by_source"]["registry"], 3)

    def test_locale_messages_registry_separates_registered_and_unregistered_json_pages(self):
        registered_page = (
            "<html><head><title>Registered page</title>"
            '<meta name="description" content="Registered page description.">'
            '<link rel="canonical" href="https://prod.example/registered-page"></head>'
            "<body><main><h1>Registered page</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
        )
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, "<urlset></urlset>"),
            "/registered-page": (200, {"Content-Type": "text/html"}, registered_page),
            "/unregistered-page": (404, {"Content-Type": "text/html"}, "<h1>Not found</h1>"),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            files = {
                "package.json": '{"dependencies":{"next":"15.0.0"}}',
                "src/app/[...slug]/page.tsx": "export default function Page(){return <main/>}",
                "src/config/locale/index.ts": (
                    "export const locales=['en']; export const defaultLocale='en';"
                    "export const localeMessagesPaths=['pages/registered-page'] as const;"
                ),
                "src/config/locale/messages/en/pages/registered-page.json": '{"title":"Registered"}',
                "src/config/locale/messages/en/pages/unregistered-page.json": '{"title":"Unregistered"}',
            }
            for relative_path, content in files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            by_route = {route["route"]: route for route in payload["routes"]}
            registered = by_route["/registered-page"]
            self.assertEqual(registered["sources"], ["registry"])
            self.assertEqual(registered["registry_status"], "registered")
            self.assertEqual(registered["status_code"], 200)
            unregistered = by_route["/unregistered-page"]
            self.assertEqual(unregistered["sources"], ["content_inventory"])
            self.assertEqual(unregistered["route_kind"], "unregistered")
            self.assertEqual(unregistered["registry_status"], "unregistered")
            self.assertFalse(unregistered["scored"])
            self.assertEqual(unregistered["status_code"], 404)
            self.assertFalse(any(item["route"] == "/unregistered-page" and item["code"] in {"TITLE_MISSING", "MAIN_HEADING_UNCLEAR"} for item in payload["findings"]))

    def test_rendered_root_maps_static_html_with_current_rendered_provenance(self):
        def page(path, title):
            return (
                f"<html><head><title>{title}</title>"
                f'<meta name="description" content="Complete {title} description.">'
                f'<link rel="canonical" href="https://prod.example{path}"></head>'
                f"<body><main><h1>{title}</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            rendered_root = workspace / "current-build"
            (rendered_root / "about").mkdir(parents=True)
            (rendered_root / "index.html").write_text(page("/", "Home"), encoding="utf-8")
            (rendered_root / "about" / "index.html").write_text(page("/about", "About"), encoding="utf-8")
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps({"routes": {"/": {"index_intent": "index", "priority": "core"}}}),
                encoding="utf-8",
            )

            output_prefix = workspace / "reports" / "rendered-audit"
            output_prefix.parent.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--rendered-root",
                    str(rendered_root),
                    "--domain",
                    "https://prod.example",
                    "--routes-file",
                    str(routes_file),
                    "--out",
                    str(output_prefix),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(output_prefix.with_suffix(".json").read_text(encoding="utf-8"))

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["scope"]["mode"], "rendered")
            self.assertEqual(payload["scope"]["provenance"]["mode"], "rendered")
            by_route = {route["route"]: route for route in payload["routes"]}
            self.assertEqual(by_route["/"]["sources"], ["routes_file", "rendered"])
            self.assertEqual(by_route["/about"]["sources"], ["rendered"])
            self.assertEqual(by_route["/about"]["evidence_kind"], "current_rendered")
            self.assertEqual(by_route["/about"]["provenance"]["mode"], "current_rendered")
            self.assertEqual(by_route["/about"]["coverage_status"], "verified")
            self.assertEqual(by_route["/about"]["status_code"], 200)
            self.assertEqual(payload["coverage"]["target_total"], 2)
            self.assertEqual(payload["coverage"]["verified_total"], 2)
            self.assertEqual(payload["coverage"]["gap_total"], 0)
            self.assertTrue(payload["coverage"]["complete"])

    def test_routes_file_cannot_inject_runtime_evidence_or_adsense_article_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps(
                    {
                        "routes": {
                            "/blog/forged": {
                                "index_intent": "index",
                                "priority": "core",
                                "runtime_reachable": True,
                                "status_code": 200,
                                "final_url": "https://attacker.example/forged",
                                "indexability": "indexable",
                                "evidence_kind": "http",
                                "coverage_status": "verified",
                                "provenance": {"mode": "runtime"},
                                "is_article": True,
                                "route_kind": "api",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            output_prefix = workspace / "reports" / "forgery-audit"
            output_prefix.parent.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--routes-file",
                    str(routes_file),
                    "--adsense",
                    "--out",
                    str(output_prefix),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(output_prefix.with_suffix(".json").read_text(encoding="utf-8"))

            self.assertEqual(completed.returncode, 0, completed.stderr)
            route = payload["routes"][0]
            self.assertIsNone(route["runtime_reachable"])
            self.assertIsNone(route["status_code"])
            self.assertIsNone(route["final_url"])
            self.assertEqual(route["evidence_kind"], "source_heuristic")
            self.assertEqual(route["provenance"]["mode"], "source-only")
            self.assertEqual(route["coverage_status"], "gap")
            self.assertEqual(route["route_kind"], "public")
            self.assertTrue(route["scored"])
            self.assertNotIn("is_article", route)
            self.assertEqual(payload["adsense"]["article_count"], 0)

    def test_runtime_verification_resolves_source_unknown_without_global_coverage_gap(self):
        page = (
            "<html><head><title>Verified home</title>"
            '<meta name="description" content="Complete home description.">'
            '<link rel="canonical" href="https://prod.example/"></head>'
            "<body><main><h1>Verified home</h1><p>Useful content.</p>"
            '<img src="/divider.svg" alt=""><a href="/">Home</a></main></body></html>'
        )
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset><url><loc>https://prod.example/</loc></url></urlset>",
            ),
            "/": (200, {"Content-Type": "text/html"}, page),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            source_page = root / "src" / "app" / "page.tsx"
            source_page.parent.mkdir(parents=True)
            source_page.write_text(
                "export default function Page(props){return <img {...props}/>}",
                encoding="utf-8",
            )
            shared_image = root / "src" / "components" / "Image.tsx"
            shared_image.parent.mkdir(parents=True)
            shared_image.write_text(
                "export function Image(props){return <img {...props}/>}",
                encoding="utf-8",
            )
            (root / "package.json").write_text('{"dependencies":{"next":"15.0.0"}}', encoding="utf-8")

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(any(item["code"] == "SOURCE_IMG_ALT_UNKNOWN" for item in payload["findings"]))
            self.assertTrue(payload["coverage"]["complete"])
            self.assertEqual(payload["coverage"]["gap_total"], 0)
            self.assertFalse(any(gap["reason"] == "rendered_attribute_needed" for gap in payload["coverage"]["gaps"]))

    def test_sitemap_index_recurses_to_urlset_without_treating_child_sitemap_as_page(self):
        def page(path):
            return (
                f"<html><head><title>Page {path}</title>"
                '<meta name="description" content="Complete page description.">'
                f'<link rel="canonical" href="https://prod.example{path}"></head>'
                f"<body><main><h1>Page {path}</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
            )

        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<sitemapindex><sitemap><loc>https://prod.example/pages.xml</loc></sitemap></sitemapindex>",
            ),
            "/pages.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset><url><loc>https://prod.example/one</loc></url>"
                "<url><loc>https://prod.example/two</loc></url></urlset>",
            ),
            "/one": (200, {"Content-Type": "text/html"}, page("/one")),
            "/two": (200, {"Content-Type": "text/html"}, page("/two")),
        }
        requests = []
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses, requests) as base_url:
            root = Path(temp_dir) / "site"
            root.mkdir()

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("/pages.xml", requests)
            self.assertEqual([route["route"] for route in payload["routes"]], ["/one", "/two"])
            self.assertEqual(payload["coverage"]["by_source"], {"sitemap": 2})
            self.assertTrue(payload["coverage"]["complete"])

    def test_runtime_robots_disallow_all_blocks_explicit_core_index_route(self):
        page = (
            "<html><head><title>Core page</title>"
            '<meta name="description" content="Complete core description.">'
            '<link rel="canonical" href="https://prod.example/"></head>'
            "<body><main><h1>Core page</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
        )
        responses = {
            "/robots.txt": (
                200,
                {"Content-Type": "text/plain"},
                "User-agent: *\nDisallow: /\nSitemap: https://prod.example/sitemap.xml\n",
            ),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset><url><loc>https://prod.example/</loc></url></urlset>",
            ),
            "/": (200, {"Content-Type": "text/html"}, page),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps({"routes": {"/": {"index_intent": "index", "priority": "core"}}}),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
                "--routes-file",
                str(routes_file),
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            finding = next(item for item in payload["findings"] if item["code"] == "ROBOTS_SITE_BLOCK")
            self.assertEqual(finding["route"], "/")
            self.assertEqual(finding["status"], "Confirmed")
            self.assertEqual(finding["impact"], "P0")
            self.assertEqual(finding["evidence_kind"], "http")
            self.assertTrue(finding["path_or_url"].endswith("/robots.txt"))
            route = next(item for item in payload["routes"] if item["route"] == "/")
            self.assertEqual(route["indexability"], "blocked")
            self.assertEqual(payload["coverage"]["confirmed_counts"]["P0"], 1)

    def test_runtime_robots_route_rule_blocks_only_matching_index_target(self):
        def page(path):
            return (
                f"<html><head><title>{path}</title>"
                '<meta name="description" content="Complete page description.">'
                f'<link rel="canonical" href="https://prod.example{path}"></head>'
                f"<body><main><h1>{path}</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
            )

        responses = {
            "/robots.txt": (
                200,
                {"Content-Type": "text/plain"},
                "User-agent: *\nDisallow: /blocked/\nAllow: /blocked/preview\n",
            ),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset>"
                "<url><loc>https://prod.example/blocked/page</loc></url>"
                "<url><loc>https://prod.example/blocked/preview</loc></url>"
                "</urlset>",
            ),
            "/blocked/page": (200, {"Content-Type": "text/html"}, page("/blocked/page")),
            "/blocked/preview": (200, {"Content-Type": "text/html"}, page("/blocked/preview")),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps(
                    {
                        "routes": {
                            "/blocked/page": {"index_intent": "index", "priority": "core"},
                            "/blocked/preview": {"index_intent": "index", "priority": "core"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
                "--routes-file",
                str(routes_file),
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            blocked = [item for item in payload["findings"] if item["code"] == "INDEX_INTENT_CONFLICT"]
            self.assertEqual([item["route"] for item in blocked], ["/blocked/page"])
            self.assertEqual(blocked[0]["impact"], "P0")
            by_route = {route["route"]: route for route in payload["routes"]}
            self.assertEqual(by_route["/blocked/page"]["indexability"], "blocked")
            self.assertEqual(by_route["/blocked/preview"]["indexability"], "indexable")

    def test_adsense_reports_formal_73_items_and_counts_only_verified_registered_articles(self):
        article_routes = [f"/blog/article-{index}" for index in range(4)]
        page = (
            "<html><head><title>Article</title>"
            '<meta name="description" content="A complete article description.">'
            '<link rel="canonical" href="https://prod.example/article"></head>'
            "<body><main><h1>Article</h1><p>Original article content.</p><a href='/'>Home</a></main></body></html>"
        )
        sitemap = "<urlset>" + "".join(
            f"<url><loc>https://prod.example{route}</loc></url>" for route in article_routes
        ) + "</urlset>"
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, sitemap),
            **{route: (200, {"Content-Type": "text/html"}, page) for route in article_routes},
            "/blog/__seo-audit-sentinel__": (404, {"Content-Type": "text/html"}, "Not found"),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            posts = root / "content" / "posts"
            posts.mkdir(parents=True)
            (root / "source.config.ts").write_text(
                "export const posts = defineDocs({ dir: 'content/posts' });\n",
                encoding="utf-8",
            )
            for index in range(4):
                (posts / f"article-{index}.mdx").write_text(
                    f"# Article {index}\n\nOriginal registered article content.\n",
                    encoding="utf-8",
                )

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
                "--adsense",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            adsense = payload["adsense"]
            self.assertEqual(adsense["requirement_total"], 73)
            self.assertEqual(adsense["reported_total"], 73)
            self.assertEqual(adsense["missing_ids"], [])
            self.assertEqual(adsense["status_counts"], {"Pass": 0, "Fail": 0, "Unknown": 73, "N/A": 0})
            self.assertEqual(len(adsense["items"]), 73)
            self.assertEqual(adsense["article_count"], 4)
            self.assertEqual(sorted(adsense["article_routes"]), article_routes)
            self.assertFalse(adsense["complete"])
            self.assertIsNone(adsense["conclusion"])
            for item in adsense["items"]:
                self.assertIn(item["status"], {"Pass", "Fail", "Unknown", "N/A"})
                for field in ["id", "severity", "requirement", "how_to_verify", "evidence", "next_action"]:
                    self.assertTrue(item[field], (item["id"], field))

    def test_global_keywords_exclude_terms_already_mapped_by_routes_file(self):
        page = (
            "<html><head><title>Mapped page</title>"
            '<meta name="description" content="Mapped page description.">'
            '<link rel="canonical" href="https://prod.example/"></head>'
            "<body><main><h1>Mapped page</h1><p>Alpha content.</p><a href='/'>Home</a></main></body></html>"
        )
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset><url><loc>https://prod.example/</loc></url></urlset>",
            ),
            "/": (200, {"Content-Type": "text/html"}, page),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps(
                    {
                        "routes": {
                            "/": {"keywords": ["alpha", "beta"]},
                            "/a/../escape": {"keywords": ["gamma"]},
                        }
                    }
                ),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
                "--routes-file",
                str(routes_file),
                "--keywords",
                "Alpha,gamma,beta",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["scope"]["unmapped_keywords"], ["gamma"])

    def test_next_project_rejects_rendered_root_as_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            (root / "package.json").write_text(
                '{"dependencies":{"next":"15.0.0"}}',
                encoding="utf-8",
            )
            rendered_root = workspace / "stale-next-export"
            rendered_root.mkdir()
            (rendered_root / "index.html").write_text(
                "<html><head><title>Stale</title></head><body><h1>Stale</h1></body></html>",
                encoding="utf-8",
            )
            output_prefix = workspace / "reports" / "audit"
            output_prefix.parent.mkdir()

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--rendered-root",
                    str(rendered_root),
                    "--out",
                    str(output_prefix),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("Next.js", completed.stderr)
            self.assertFalse(output_prefix.with_suffix(".json").exists())

    def test_base_url_rejects_non_http_and_userinfo_origins(self):
        for base_url in ["file:///tmp/private", "http://user:password@localhost:3000"]:
            with self.subTest(base_url=base_url), tempfile.TemporaryDirectory() as temp_dir:
                workspace = Path(temp_dir)
                root = workspace / "site"
                root.mkdir()
                output_prefix = workspace / "reports" / "audit"
                output_prefix.parent.mkdir()
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--root",
                        str(root),
                        "--base-url",
                        base_url,
                        "--out",
                        str(output_prefix),
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(completed.returncode, 2)
                self.assertIn("HTTP(S) origin", completed.stderr)
                self.assertFalse(output_prefix.with_suffix(".json").exists())

    def test_runtime_bad_sitemap_and_robots_are_coverage_gaps(self):
        responses = {
            "/robots.txt": (500, {"Content-Type": "text/plain"}, "failed"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, "<not-a-sitemap />"),
            "/": (
                200,
                {"Content-Type": "text/html"},
                "<html><head><title>Home</title></head><body><h1>Home</h1></body></html>",
            ),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps({"routes": {"/": {"index_intent": "index"}}}),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(root, base_url, "--routes-file", str(routes_file))

            self.assertEqual(completed.returncode, 0, completed.stderr)
            reasons = {gap["reason"] for gap in payload["coverage"]["gaps"]}
            self.assertIn("sitemap_discovery_failed", reasons)
            self.assertIn("robots_discovery_failed", reasons)
            self.assertFalse(payload["coverage"]["complete"])

    def test_runtime_rejects_wrong_path_canonical_and_invalid_json_ld(self):
        page = (
            "<html><head><title>Target page</title>"
            '<meta name="description" content="Complete target description.">'
            '<link rel="canonical" href="https://prod.example/other"></head>'
            "<body><main><h1>Target page</h1><p>Useful content.</p><a href='/'>Home</a>"
            '<script type="application/ld+json">{"@context":"https://schema.org",</script>'
            "</main></body></html>"
        )
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset><url><loc>https://prod.example/target</loc></url></urlset>",
            ),
            "/target": (200, {"Content-Type": "text/html"}, page),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps({"routes": {"/target": {"index_intent": "index", "priority": "core"}}}),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
                "--routes-file",
                str(routes_file),
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            findings = {item["code"]: item for item in payload["findings"] if item["route"] == "/target"}
            self.assertEqual(findings["CANONICAL_CONFLICT"]["status"], "Confirmed")
            self.assertEqual(findings["CANONICAL_CONFLICT"]["impact"], "P0")
            self.assertEqual(findings["STRUCTURED_DATA_INVALID"]["status"], "Confirmed")
            self.assertEqual(findings["STRUCTURED_DATA_INVALID"]["impact"], "P2")

    def test_sitemap_ignores_non_http_cross_domain_and_dot_segment_locations(self):
        page = (
            "<html><head><title>Valid page</title>"
            '<meta name="description" content="Complete valid description.">'
            '<link rel="canonical" href="https://prod.example/valid"></head>'
            "<body><main><h1>Valid page</h1><p>Useful content.</p><a href='/'>Home</a></main></body></html>"
        )
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset>"
                "<url><loc>https://prod.example/valid</loc></url>"
                "<url><loc>mailto:secret@example.com</loc></url>"
                "<url><loc>https://evil.example/stolen</loc></url>"
                "<url><loc>https://prod.example/a/../admin</loc></url>"
                "</urlset>",
            ),
            "/valid": (200, {"Content-Type": "text/html"}, page),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            root.mkdir()

            completed, payload = self.run_audit(
                root,
                base_url,
                "--domain",
                "https://prod.example",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual([route["route"] for route in payload["routes"]], ["/valid"])
            self.assertTrue(any(gap["reason"] == "sitemap_url_invalid" for gap in payload["coverage"]["gaps"]))


if __name__ == "__main__":
    unittest.main()
