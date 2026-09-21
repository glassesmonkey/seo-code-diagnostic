import importlib.util
import json
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
SPEC = importlib.util.spec_from_file_location("seo_code_audit_phase3", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


@contextmanager
def fixture_server(responses):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
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


def public_resolver(host, port, *args, **kwargs):
    return [(2, 1, 6, "", ("93.184.216.34", port))]


def private_resolver(host, port, *args, **kwargs):
    return [(2, 1, 6, "", ("10.0.0.7", port))]


def external_result(
    url,
    html="<html><body><p>No reverse link.</p></body></html>",
    *,
    final_url=None,
    status=200,
    content_type="text/html; charset=utf-8",
    truncated=False,
    error=None,
):
    return AUDIT.ExternalHTTPResult(
        requested_url=url,
        final_url=final_url or url,
        status_code=status,
        content_type=content_type,
        text=html,
        truncated=truncated,
        error=error,
        checked_urls=[url],
        content_hash=AUDIT.sha256_text(html) if not error else None,
    )


def page_evidence(route, links, *, title="Page", h1=None, total_links=None):
    return {
        "route": route,
        "source_url": "https://site.example" + (route if route != "/" else "/"),
        "title": title,
        "h1": h1 or [title],
        "index_intent": "index",
        "indexability": "indexable",
        "total_crawlable_links": total_links if total_links is not None else len(links),
        "external_links": [
            {
                "target_url": target,
                "target_host": urlsplit(target).hostname,
                "anchor_text": anchor,
                "rel": rel,
                "zone": zone,
                "qualified": bool({"nofollow", "sponsored", "ugc"} & set(rel)),
                "source_route": route,
                "source_url": "https://site.example" + (route if route != "/" else "/"),
            }
            for target, anchor, rel, zone in links
        ],
    }


class AnchorAndSafetyTestCase(unittest.TestCase):
    def test_anchor_text_rel_zone_and_protocol_relative_href_are_bounded(self):
        parser = AUDIT.parse_runtime_html(
            "<body><nav><a href='//peer.example/path' rel='nofollow, sponsored'>"
            "Peer <span>Site</span></a><p>After link</p></nav>"
            "<main><a href='https://other.example/'>Other</a></main></body>"
        )

        self.assertEqual(parser.links[0]["href"], "//peer.example/path")
        self.assertEqual(parser.links[0]["text"], "Peer Site")
        self.assertEqual(parser.links[0]["rel"], "nofollow, sponsored")
        self.assertEqual(parser.links[0]["zone"], "nav")
        self.assertNotIn("After link", parser.links[0]["text"])
        self.assertEqual(parser.links[1]["text"], "Other")
        self.assertEqual(parser.links[1]["zone"], "main")

        evidence = AUDIT.extract_page_link_evidence(
            parser,
            "https://site.example/source",
            "/source",
            "https://site.example",
        )
        self.assertEqual(evidence["external_links"][0]["target_url"], "https://peer.example/path")
        self.assertEqual(evidence["external_links"][0]["rel"], ["nofollow", "sponsored"])
        self.assertTrue(evidence["external_links"][0]["qualified"])

    def test_public_url_validation_rejects_private_userinfo_and_ip_literals(self):
        normalized, error = AUDIT.validate_public_http_url(
            "https://public.example/path#fragment",
            resolver=public_resolver,
        )
        self.assertEqual(normalized, "https://public.example/path")
        self.assertIsNone(error)

        blocked = [
            ("http://127.0.0.1/", public_resolver),
            ("http://[::1]/", public_resolver),
            ("https://user:pass@public.example/", public_resolver),
            ("https://public.example:8443/", public_resolver),
            ("https://private.example/", private_resolver),
        ]
        for url, resolver in blocked:
            with self.subTest(url=url):
                normalized, error = AUDIT.validate_public_http_url(url, resolver=resolver)
                self.assertIsNone(normalized)
                self.assertIsNotNone(error)

    def test_public_fetch_checks_each_redirect_before_requesting_it(self):
        requested = []

        def malicious_redirect(url):
            requested.append(url)
            return AUDIT.HTTPResult(
                url,
                302,
                {"location": "http://127.0.0.1/admin"},
                b"",
                "",
                False,
                None,
                "http://127.0.0.1/admin",
                "http://127.0.0.1/admin",
                "text/html",
            )

        result = AUDIT.fetch_public_http(
            "https://public.example/start",
            resolver=public_resolver,
            request_once=malicious_redirect,
        )
        self.assertEqual(requested, ["https://public.example/start"])
        self.assertEqual(result.error, "redirect_ip_literal_forbidden")


class ReciprocalAnalysisTestCase(unittest.TestCase):
    def test_target_and_homepage_reverse_links_are_observed_without_flagging_one_pair(self):
        pages = [
            page_evidence(
                "/source",
                [("https://peer.example/deep", "Peer", [], "main")],
            )
        ]

        def fetcher(url):
            if url == "https://peer.example/":
                return external_result(url, "<footer><a href='https://site.example/'>Source</a></footer>")
            return external_result(url)

        analysis, findings = AUDIT.analyze_reciprocal_links(
            pages,
            "https://site.example",
            fetcher=fetcher,
        )

        self.assertEqual(analysis["status"], "complete")
        self.assertEqual(analysis["reciprocal_domain_total"], 1)
        self.assertEqual(analysis["targets"][0]["reverse_status"], "reverse_link_observed")
        self.assertEqual(analysis["targets"][0]["reverse_links"][0]["zone"], "footer")
        self.assertEqual(findings, [])

    def test_missing_non_html_truncated_and_failed_pages_remain_scoped_gaps(self):
        pages = [
            page_evidence(
                "/source",
                [
                    ("https://missing.example/a", "Missing", [], "main"),
                    ("https://binary.example/a", "Binary", [], "main"),
                    ("https://large.example/a", "Large", [], "main"),
                    ("https://failed.example/a", "Failed", [], "main"),
                ],
            )
        ]

        def fetcher(url):
            host = urlsplit(url).hostname
            if host == "binary.example":
                return external_result(url, content_type="application/pdf")
            if host == "large.example":
                return external_result(url, truncated=True)
            if host == "failed.example":
                return external_result(url, error="TimeoutError", status=None)
            return external_result(url)

        analysis, findings = AUDIT.analyze_reciprocal_links(
            pages,
            "https://site.example",
            fetcher=fetcher,
        )

        self.assertEqual(analysis["status"], "partial")
        reasons = {gap["reason"] for gap in analysis["gaps"]}
        self.assertIn("external_non_html", reasons)
        self.assertIn("external_body_truncated", reasons)
        self.assertIn("external_request_failed", reasons)
        missing = next(item for item in analysis["targets"] if item["target_host"] == "missing.example")
        self.assertEqual(missing["reverse_status"], "not_observed_on_checked_pages")
        self.assertEqual(findings, [])

    def test_three_sitewide_footer_follow_pairs_generate_one_confirmed_p2(self):
        links = [
            (f"https://peer{i}.example/", f"Peer {i}", [], "footer")
            for i in range(1, 4)
        ]
        pages = [page_evidence(f"/page-{i}", links) for i in range(1, 7)]

        def fetcher(url):
            return external_result(url, "<footer><a href='https://site.example/'>Source site</a></footer>")

        analysis, findings = AUDIT.analyze_reciprocal_links(
            pages,
            "https://site.example",
            fetcher=fetcher,
        )

        self.assertEqual(analysis["reciprocal_domain_total"], 3)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["code"], "RECIPROCAL_LINK_NETWORK_PATTERN")
        self.assertEqual(finding["status"], "Confirmed")
        self.assertEqual(finding["impact"], "P2")
        self.assertIsNone(finding["route"])
        self.assertEqual(len(finding["affected_hosts"]), 3)
        self.assertEqual(len(finding["affected_routes"]), 6)

    def test_partner_page_pattern_requires_three_unqualified_reverse_pairs(self):
        links = [
            (f"https://partner{i}.example/", f"Partner {i}", [], "main")
            for i in range(1, 6)
        ]
        pages = [page_evidence("/partners", links, title="Link Partners", total_links=6)]

        def fetcher(url):
            host = urlsplit(url).hostname
            index = int(host.removeprefix("partner").split(".", 1)[0])
            if index <= 3:
                return external_result(url, "<a href='https://site.example/'>Source</a>")
            return external_result(url)

        analysis, findings = AUDIT.analyze_reciprocal_links(
            pages,
            "https://site.example",
            fetcher=fetcher,
        )

        self.assertEqual(analysis["reciprocal_domain_total"], 3)
        self.assertEqual(len(findings), 1)
        self.assertIn("partner_page", findings[0]["provenance"]["signals"])

    def test_qualified_reverse_links_and_single_pairs_never_generate_p2(self):
        pages = [
            page_evidence(
                "/source",
                [("https://peer.example/", "Peer", [], "footer")],
            )
        ]

        def fetcher(url):
            return external_result(
                url,
                "<footer><a rel='sponsored' href='https://site.example/'>Source</a></footer>",
            )

        analysis, findings = AUDIT.analyze_reciprocal_links(
            pages,
            "https://site.example",
            fetcher=fetcher,
        )

        self.assertEqual(analysis["reciprocal_domain_total"], 1)
        self.assertFalse(analysis["targets"][0]["reverse_follow"])
        self.assertEqual(findings, [])

    def test_domain_budget_is_deterministic_and_marks_partial(self):
        links = [
            (f"https://host{i:02d}.example/page", f"Host {i}", [], "main")
            for i in range(21)
        ]
        pages = [page_evidence("/source", links)]

        analysis, findings = AUDIT.analyze_reciprocal_links(
            pages,
            "https://site.example",
            fetcher=lambda url: external_result(url),
        )

        self.assertEqual(analysis["status"], "partial")
        self.assertEqual(analysis["candidate_domain_total"], 21)
        self.assertEqual(analysis["selected_domain_total"], 20)
        self.assertEqual(analysis["skipped_domain_total"], 1)
        selected = [item["target_host"] for item in analysis["targets"]]
        self.assertEqual(selected, [f"host{i:02d}.example" for i in range(20)])
        self.assertEqual(findings, [])

    def test_final_hosts_are_deduplicated(self):
        pages = [
            page_evidence(
                "/source",
                [
                    ("https://go-one.example/a", "One", [], "main"),
                    ("https://go-two.example/b", "Two", [], "main"),
                ],
            )
        ]

        def fetcher(url):
            if urlsplit(url).hostname.startswith("go-"):
                return external_result(url, final_url="https://peer.example/final")
            return external_result(url)

        analysis, findings = AUDIT.analyze_reciprocal_links(
            pages,
            "https://site.example",
            fetcher=fetcher,
        )

        self.assertEqual(len(analysis["targets"]), 1)
        self.assertEqual(analysis["targets"][0]["target_host"], "peer.example")
        self.assertEqual(findings, [])


class ReciprocalReportTestCase(unittest.TestCase):
    def test_runtime_default_writes_link_analysis_without_polluting_route_coverage(self):
        sitemap = "<urlset>" + "".join(
            f"<url><loc>https://site.example/page-{i}</loc></url>" for i in range(1, 4)
        ) + "</urlset>"
        footer = "".join(
            f"<a href='https://peer{i}.example/'>Peer {i}</a>" for i in range(1, 4)
        )

        def page(index):
            return (
                f"<html><head><title>Page {index}</title>"
                "<meta name='description' content='Complete fixture description.'>"
                f"<link rel='canonical' href='https://site.example/page-{index}'></head>"
                f"<body><main><h1>Page {index}</h1><p>Useful content.</p></main>"
                f"<footer>{footer}</footer></body></html>"
            )

        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (200, {"Content-Type": "application/xml"}, sitemap),
            **{
                f"/page-{i}": (200, {"Content-Type": "text/html; charset=utf-8"}, page(i))
                for i in range(1, 4)
            },
        }

        def fetcher(url):
            return external_result(url, "<footer><a href='https://site.example/'>Source</a></footer>")

        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            root.mkdir()
            first_out = Path(temp_dir) / "first"
            second_out = Path(temp_dir) / "second"
            args = [
                "--root",
                str(root),
                "--domain",
                "https://site.example",
                "--base-url",
                base_url,
            ]

            self.assertEqual(AUDIT.main([*args, "--out", str(first_out)], reciprocal_fetcher=fetcher), 0)
            self.assertEqual(AUDIT.main([*args, "--out", str(second_out)], reciprocal_fetcher=fetcher), 0)
            first = json.loads(first_out.with_suffix(".json").read_text(encoding="utf-8"))
            second = json.loads(second_out.with_suffix(".json").read_text(encoding="utf-8"))
            markdown = first_out.with_suffix(".md").read_text(encoding="utf-8")

        self.assertTrue(first["coverage"]["complete"])
        self.assertEqual(first["coverage"]["gap_total"], 0)
        self.assertEqual(first["link_analysis"]["status"], "complete")
        self.assertEqual(first["link_analysis"]["reciprocal_domain_total"], 3)
        self.assertEqual(first["coverage"]["confirmed_counts"]["P2"], 1)
        self.assertIn("## 互链验证", markdown)
        self.assertEqual(
            first["scope"]["provenance"]["result_hash"],
            second["scope"]["provenance"]["result_hash"],
        )

    def test_off_and_missing_domain_keep_fixed_not_run_object(self):
        responses = {
            "/robots.txt": (200, {"Content-Type": "text/plain"}, "User-agent: *\nAllow: /\n"),
            "/sitemap.xml": (
                200,
                {"Content-Type": "application/xml"},
                "<urlset><url><loc>https://site.example/</loc></url></urlset>",
            ),
            "/": (
                200,
                {"Content-Type": "text/html"},
                "<html><head><title>Home</title></head><body><main><h1>Home</h1></main></body></html>",
            ),
        }
        with tempfile.TemporaryDirectory() as temp_dir, fixture_server(responses) as base_url:
            root = Path(temp_dir) / "site"
            root.mkdir()
            off_out = Path(temp_dir) / "off"
            missing_out = Path(temp_dir) / "missing"
            self.assertEqual(
                AUDIT.main(
                    [
                        "--root",
                        str(root),
                        "--domain",
                        "https://site.example",
                        "--base-url",
                        base_url,
                        "--reciprocal-links",
                        "off",
                        "--out",
                        str(off_out),
                    ]
                ),
                0,
            )
            self.assertEqual(
                AUDIT.main(
                    ["--root", str(root), "--base-url", base_url, "--out", str(missing_out)]
                ),
                0,
            )
            off = json.loads(off_out.with_suffix(".json").read_text(encoding="utf-8"))
            missing = json.loads(missing_out.with_suffix(".json").read_text(encoding="utf-8"))

        self.assertEqual(off["link_analysis"]["status"], "not_run")
        self.assertEqual(off["link_analysis"]["reason"], "disabled")
        self.assertEqual(missing["link_analysis"]["status"], "not_run")
        self.assertEqual(missing["link_analysis"]["reason"], "domain_required")


if __name__ == "__main__":
    unittest.main()
