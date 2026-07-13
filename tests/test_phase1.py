import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "seo_code_audit.py"


class AuditCliTestCase(unittest.TestCase):
    def run_audit(self, root: Path, *extra_args: str):
        output_dir = root.parent / "reports"
        output_dir.mkdir(exist_ok=True)
        output_prefix = output_dir / "audit"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
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

    def test_cli_emits_schema_v2_and_accepts_phase_one_interfaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps({"/": {"index_intent": "Unknown", "priority": "normal"}}),
                encoding="utf-8",
            )
            rendered_root = workspace / "rendered"
            rendered_root.mkdir()

            conflict, conflict_payload = self.run_audit(
                root,
                "--base-url",
                "http://127.0.0.1:3000",
                "--routes-file",
                str(routes_file),
                "--rendered-root",
                str(rendered_root),
            )
            self.assertEqual(conflict.returncode, 2)
            self.assertIsNone(conflict_payload)
            self.assertIn("cannot be used together", conflict.stderr)

            completed, payload = self.run_audit(
                root,
                "--routes-file",
                str(routes_file),
                "--rendered-root",
                str(rendered_root),
                "--exclude",
                "private/**",
                "--exclude",
                "scratch/**",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["schema_version"], 2)
            self.assertEqual(
                {"scope", "coverage", "routes", "findings", "adsense"},
                {key for key in payload if key in {"scope", "coverage", "routes", "findings", "adsense"}},
            )
            self.assertEqual(payload["scope"]["base_url"], "")
            self.assertEqual(payload["scope"]["excludes"], ["private/**", "scratch/**"])
            self.assertFalse(payload["coverage"]["complete"])
            self.assertTrue(payload["coverage"]["gaps"])
            self.assertEqual(
                {"route", "reason", "evidence_needed"},
                {key for key in payload["coverage"]["gaps"][0] if key in {"route", "reason", "evidence_needed"}},
            )

    def test_source_regex_is_candidate_and_confirmed_summary_stays_zero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            page = root / "src" / "app" / "page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text('export default function Page(){return <img src="/hero.png" />}', encoding="utf-8")

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            finding = next(item for item in payload["findings"] if item["code"] == "SOURCE_IMG_WITHOUT_ALT")
            self.assertEqual(finding["status"], "Candidate")
            self.assertEqual(finding["impact"], "P2")
            self.assertEqual(
                {
                    "status",
                    "impact",
                    "route",
                    "route_kind",
                    "index_intent",
                    "indexability",
                    "runtime_reachable",
                    "status_code",
                    "evidence_kind",
                    "path_or_url",
                    "provenance",
                },
                {
                    key
                    for key in finding
                    if key
                    in {
                        "status",
                        "impact",
                        "route",
                        "route_kind",
                        "index_intent",
                        "indexability",
                        "runtime_reachable",
                        "status_code",
                        "evidence_kind",
                        "path_or_url",
                        "provenance",
                    }
                },
            )
            self.assertEqual(payload["summary"]["confirmed_by_impact"]["P2"], 0)

    def test_source_absence_rules_are_unknown_not_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            page = root / "src" / "app" / "page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text(
                "export default function Page(){return <main><h1>Home</h1></main>}",
                encoding="utf-8",
            )

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            by_code = {item["code"]: item for item in payload["findings"]}
            for code in {
                "ROBOTS_MISSING",
                "SITEMAP_MISSING",
                "NO_METADATA_SOURCE_FOUND",
                "NO_CANONICAL_SOURCE_FOUND",
                "NO_SCHEMA_SOURCE_FOUND",
            }:
                self.assertEqual(by_code[code]["status"], "Unknown", code)

    def test_scan_allowlist_hard_excludes_private_and_generated_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            included = root / "src" / "app" / "page.tsx"
            included.parent.mkdir(parents=True)
            included.write_text('export default function Page(){return <img src="/hero.png" />}', encoding="utf-8")

            excluded_files = {
                ".next/server/app/page.html": "<html><body>generated</body></html>",
                ".open-next/server.js": "<img src='/generated.png'>",
                ".source/snapshot.tsx": "<img src='/source.png'>",
                "reports/previous.json": '{"secret":"report"}',
                "docs/seo-plan.md": "internal prompt: do not show to users",
                ".agents/reviewer.md": "internal instructions",
                "AGENTS.md": "system prompt",
                ".env.local": "TOKEN=private-value",
                ".dev.vars": "SECRET=private-value",
                "public/uploads/customer-statement.html": "<title>private statement</title>",
                "logs/audit.log": "private-value",
                "data/site.sqlite": "private-value",
                "src/db/schema.sql": "insert into users values ('private-value');",
            }
            for relative_path, content in excluded_files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            output_prefix = root / "reports" / "audit"
            output_prefix.parent.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--out", str(output_prefix)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(output_prefix.with_suffix(".json").read_text(encoding="utf-8"))

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["scope"]["scanned_paths"], ["src/app/page.tsx"])
            evidence_paths = {str(finding["path_or_url"]) for finding in payload["findings"]}
            self.assertFalse(any("private-value" in json.dumps(finding) for finding in payload["findings"]))
            for excluded_path in excluded_files:
                self.assertNotIn(excluded_path, evidence_paths)

    def test_truncated_source_is_unknown_not_negative_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            page = root / "src" / "app" / "page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text("x" * 700_001, encoding="utf-8")

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            finding = next(item for item in payload["findings"] if item["code"] == "SOURCE_READ_TRUNCATED")
            self.assertEqual(finding["status"], "Unknown")
            self.assertEqual(finding["evidence_kind"], "read_state")
            self.assertEqual(finding["path_or_url"], "src/app/page.tsx")
            self.assertTrue(
                any(gap.get("path_or_url") == "src/app/page.tsx" for gap in payload["coverage"]["gaps"])
            )

    def test_findings_dedupe_by_route_rule_and_content_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            content = 'export default function Page(){return <img src="/hero.png" />}'
            for relative_path in ["src/app/page.tsx", "src/app/(marketing)/page.tsx"]:
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            findings = [item for item in payload["findings"] if item["code"] == "SOURCE_IMG_WITHOUT_ALT"]
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["route"], "/")
            self.assertEqual(
                findings[0]["provenance"]["paths"],
                ["src/app/(marketing)/page.tsx", "src/app/page.tsx"],
            )
            self.assertEqual(findings[0]["provenance"]["mode"], "source-only")
            self.assertRegex(findings[0]["provenance"]["content_hash"], r"^[0-9a-f]{64}$")

    def test_next_src_app_metadata_routes_prevent_missing_robots_and_sitemap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            app = root / "src" / "app"
            app.mkdir(parents=True)
            (app / "robots.ts").write_text(
                "export default function robots(){return {rules:{userAgent:'*',allow:'/'},sitemap:'https://example.com/sitemap.xml'}}",
                encoding="utf-8",
            )
            (app / "sitemap.js").write_text(
                "export default function sitemap(){return [{url:'https://example.com/'}]}",
                encoding="utf-8",
            )

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            codes = {item["code"] for item in payload["findings"]}
            self.assertNotIn("ROBOTS_MISSING", codes)
            self.assertNotIn("SITEMAP_MISSING", codes)
            self.assertEqual(payload["repo_audit"]["robots_found"], ["src/app/robots.ts"])
            self.assertEqual(payload["repo_audit"]["sitemap_found"], ["src/app/sitemap.js"])

    def test_empty_alt_is_valid_and_spread_props_are_unknown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            page = root / "src" / "app" / "page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text(
                'export default function Page(props){return <><img src="/decorative.png" alt=""/><img {...props}/></>}',
                encoding="utf-8",
            )
            html_page = root / "public" / "index.html"
            html_page.parent.mkdir(parents=True)
            html_page.write_text(
                '<html><head><title>Decorative image page</title></head><body><h1>Main</h1><img src="/line.png" alt=""></body></html>',
                encoding="utf-8",
            )

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            codes = [item["code"] for item in payload["findings"]]
            self.assertNotIn("SOURCE_IMG_WITHOUT_ALT", codes)
            self.assertNotIn("IMAGE_ALT_MISSING", codes)
            spread = next(item for item in payload["findings"] if item["code"] == "SOURCE_IMG_ALT_UNKNOWN")
            self.assertEqual(spread["status"], "Unknown")

    def test_use_client_alone_does_not_create_csr_finding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            page = root / "src" / "app" / "chat" / "page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text(
                '"use client"; export default function Chat(){return <main><h1>Chat</h1></main>}',
                encoding="utf-8",
            )

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn("NEXT_PAGE_USE_CLIENT", {item["code"] for item in payload["findings"]})

    def test_copy_review_only_uses_mapped_public_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            fixtures = {
                "source.config.ts": (
                    "import {defineDocs} from 'fumadocs-mdx/config';"
                    "export const posts=defineDocs({dir:'content/posts'});"
                ),
                "src/app/page.tsx": "// internal prompt: do not show to users\nexport default function Page(){return <main>Public copy</main>}",
                "src/app/terms/page.tsx": "export default function Terms(){return <main>This is not legal advice. Never rely on it as legal advice.</main>}",
                "src/lib/prompts.ts": "export const note = 'internal prompt: do not show to users'",
                "content/posts/public-leak.mdx": "# Article\n\nInternal prompt: do not show to users.",
                "content/drafts/private-leak.mdx": "# Draft\n\nInternal prompt: do not show to users.",
                "content/articles/unregistered-leak.mdx": "# Unregistered\n\nInternal prompt: do not show to users.",
            }
            for relative_path, content in fixtures.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            copy_findings = [
                item for item in payload["findings"] if item["code"] in {"INTERNAL_COPY_LEAK", "YMYL_COPY_REVIEW"}
            ]
            self.assertEqual(len(copy_findings), 1)
            self.assertEqual(copy_findings[0]["code"], "INTERNAL_COPY_LEAK")
            self.assertEqual(copy_findings[0]["path_or_url"], "content/posts/public-leak.mdx")
            self.assertEqual(copy_findings[0]["status"], "Candidate")
            self.assertNotIn("content/drafts/private-leak.mdx", json.dumps(payload["findings"]))
            self.assertNotIn("content/articles/unregistered-leak.mdx", payload["scope"]["scanned_paths"])

    def test_symlinked_files_outside_root_never_enter_scope_or_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            source_dir = root / "src" / "app"
            source_dir.mkdir(parents=True)
            external = workspace / "outside.tsx"
            external.write_text(
                "export default function Page(){return <main>Internal prompt: do not show to users</main>}",
                encoding="utf-8",
            )
            (source_dir / "page.tsx").symlink_to(external)

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn("src/app/page.tsx", payload["scope"]["scanned_paths"])
            self.assertNotIn("outside.tsx", json.dumps(payload, ensure_ascii=False))

    def test_routes_file_owns_page_keywords_and_container_key_is_not_a_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            page = root / "public" / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text(
                "<html><head><title>Alpha landing page</title></head><body><h1>Alpha</h1><p>alpha</p></body></html>",
                encoding="utf-8",
            )
            routes_file = workspace / "routes.json"
            routes_file.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "routes": {
                            "/": {
                                "index_intent": "Index",
                                "priority": "core",
                                "keywords": ["alpha"],
                                "intent_source": "fixture",
                            },
                            "/target": {
                                "index_intent": "Unknown",
                                "priority": "normal",
                                "keywords": ["beta"],
                                "intent_source": "fixture",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            completed, payload = self.run_audit(
                root,
                "--routes-file",
                str(routes_file),
                "--keywords",
                "global-missing,another-unmapped",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual([entry["route"] for entry in payload["routes"]], ["/", "/target"])
            self.assertNotIn("routes", {entry["route"] for entry in payload["routes"]})
            self.assertEqual(payload["scope"]["unmapped_keywords"], ["global-missing", "another-unmapped"])
            evidence = json.dumps(payload["findings"], ensure_ascii=False)
            self.assertNotIn("global-missing", evidence)
            self.assertNotIn("another-unmapped", evidence)
            self.assertNotIn("KEYWORD_DENSITY_HIGH", {item["code"] for item in payload["findings"]})

    def test_routes_file_accepts_direct_map_and_list_compatibility_shapes(self):
        variants = [
            ({"/direct": {"index_intent": "Index"}}, ["/direct"]),
            ([{"route": "/listed", "index_intent": "Unknown"}], ["/listed"]),
        ]
        for routes_payload, expected_routes in variants:
            with self.subTest(routes_payload=routes_payload), tempfile.TemporaryDirectory() as temp_dir:
                workspace = Path(temp_dir)
                root = workspace / "site"
                root.mkdir()
                routes_file = workspace / "routes.json"
                routes_file.write_text(json.dumps(routes_payload), encoding="utf-8")

                completed, payload = self.run_audit(root, "--routes-file", str(routes_file))

                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual([entry["route"] for entry in payload["routes"]], expected_routes)

    def test_unparseable_routes_file_becomes_unknown_coverage_gap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            routes_file = workspace / "routes.json"
            routes_file.write_text('{"routes": ', encoding="utf-8")

            completed, payload = self.run_audit(root, "--routes-file", str(routes_file))

            self.assertEqual(completed.returncode, 0, completed.stderr)
            finding = next(item for item in payload["findings"] if item["code"] == "ROUTES_FILE_UNREADABLE")
            self.assertEqual(finding["status"], "Unknown")
            self.assertEqual(finding["evidence_kind"], "parse_state")
            self.assertEqual(finding["path_or_url"], str(routes_file.resolve()))
            self.assertTrue(
                any(gap.get("path_or_url") == str(routes_file.resolve()) for gap in payload["coverage"]["gaps"])
            )

    def test_adsense_without_verified_urls_has_73_unknown_items_and_zero_articles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            for index in range(8):
                article = root / "content" / "posts" / f"article-{index}.mdx"
                article.parent.mkdir(parents=True, exist_ok=True)
                article.write_text(f"# Article {index}\n\nOriginal content.", encoding="utf-8")

            completed, payload = self.run_audit(root, "--adsense")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            adsense = payload["adsense"]
            self.assertTrue(adsense["enabled"])
            self.assertEqual(len(adsense["items"]), 73)
            self.assertEqual({item["status"] for item in adsense["items"]}, {"Unknown"})
            self.assertEqual(adsense["article_count"], 0)
            self.assertFalse(adsense["complete"])
            self.assertIsNone(adsense["conclusion"])
            serialized = json.dumps(adsense, ensure_ascii=False)
            self.assertNotIn('"warn"', serialized)
            self.assertNotIn('"pass"', serialized)
            self.assertNotIn("Ready", serialized)

    def test_env_files_are_invisible_and_secret_like_evidence_is_redacted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            root.mkdir()
            env_secret = "env-secret-1234567890"
            public_secret = "public-secret-1234567890"
            (root / ".env.development.local").write_text(f"API_KEY={env_secret}\n", encoding="utf-8")
            (root / "source.config.ts").write_text(
                "import {defineDocs} from 'fumadocs-mdx/config';"
                "export const posts=defineDocs({dir:'content/posts'});",
                encoding="utf-8",
            )
            post = root / "content" / "posts" / "bad-copy.mdx"
            post.parent.mkdir(parents=True)
            post.write_text(
                f"# Draft\n\nInternal prompt: API_KEY={public_secret} do not show to users.",
                encoding="utf-8",
            )

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            serialized = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn(".env.development.local", serialized)
            self.assertNotIn(env_secret, serialized)
            self.assertNotIn(public_secret, serialized)
            self.assertIn("[REDACTED]", serialized)

    def test_markdown_uses_confirmed_counts_and_coverage_gap_conclusion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            root.mkdir()

            completed, payload = self.run_audit(root)
            markdown_path = root.parent / "reports" / "audit.md"
            markdown = markdown_path.read_text(encoding="utf-8")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["summary"]["confirmed_by_impact"]["P1"], 0)
            self.assertIn("覆盖不完整", markdown)
            self.assertIn("Confirmed P0-P2", markdown)
            self.assertNotIn("未发现脚本可识别的明显 SEO 问题", markdown)
            self.assertNotIn("有 1 个 P1 高影响问题", markdown)

    def test_default_output_is_outside_root_and_second_run_is_stable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            page = root / "src" / "app" / "page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text('export default function Page(){return <img src="/hero.png" />}', encoding="utf-8")
            command = [sys.executable, str(SCRIPT), "--root", str(root)]

            first = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
            output_path = root.parent / "site-seo-audit.json"
            first_payload = json.loads(output_path.read_text(encoding="utf-8"))
            second = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
            second_payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertFalse(output_path.is_relative_to(root))
            self.assertEqual(first_payload["scope"]["scanned_paths"], ["src/app/page.tsx"])
            self.assertRegex(first_payload["scope"]["provenance"]["result_hash"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                first_payload["scope"]["provenance"]["result_hash"],
                second_payload["scope"]["provenance"]["result_hash"],
            )

    def test_truncated_html_is_unknown_and_does_not_create_missing_element_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            page = root / "public" / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text("x" * 700_001, encoding="utf-8")

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            findings = {item["code"]: item for item in payload["findings"]}
            self.assertEqual(findings["HTML_READ_TRUNCATED"]["status"], "Unknown")
            self.assertEqual(findings["HTML_READ_TRUNCATED"]["evidence_kind"], "read_state")
            self.assertFalse(
                {"TITLE_MISSING", "MAIN_HEADING_UNCLEAR", "DESCRIPTION_GAP", "CANONICAL_GAP"}
                & findings.keys()
            )

    def test_multiple_h1_alone_does_not_create_a_heading_finding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "site"
            page = root / "public" / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text(
                "<html><head><title>Clear page title</title></head>"
                "<body><main><h1>Primary task</h1><section><h1>Supporting section</h1></section></main></body></html>",
                encoding="utf-8",
            )

            completed, payload = self.run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn(
                "MAIN_HEADING_AMBIGUOUS",
                {item["code"] for item in payload["findings"]},
            )


if __name__ == "__main__":
    unittest.main()
