import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "adsense_report_validator.py"
AUDIT_PATH = REPO_ROOT / "scripts" / "seo_code_audit.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("adsense_report_validator_phase4", VALIDATOR_PATH)
AUDIT = load_module("seo_code_audit_phase4", AUDIT_PATH)


def resolve_item(item, status="Pass", *, effort=None):
    resolved = dict(item)
    resolved.update(
        {
            "status": status,
            "evidence": f"Current audit evidence verifies {item['id']}.",
            "evidence_kind": "repo_fact",
            "path_or_url": f"evidence/{item['id'].lower()}.txt",
            "evidence_ref": None,
            "provenance": {"mode": "repo_fact"},
            "next_action": "" if status == "Pass" else f"Fix {item['id']} and verify again.",
            "effort": effort or ("N/A" if status == "Pass" else "M"),
            "applicability_reason": None,
        }
    )
    return resolved


class AssessmentValidatorTestCase(unittest.TestCase):
    def setUp(self):
        self.target = "https://site.example"
        self.template = VALIDATOR.make_assessment_template(self.target)

    def test_registry_and_template_cover_73_unique_ids(self):
        registry = VALIDATOR.load_registry()
        ids = [item["id"] for item in registry]
        self.assertEqual(len(ids), 73)
        self.assertEqual(len(set(ids)), 73)
        self.assertEqual([item["id"] for item in self.template["items"]], ids)
        self.assertEqual(VALIDATOR.validate_assessments(self.template), [])

    def test_missing_duplicate_and_unknown_ids_fail_completeness(self):
        payload = json.loads(json.dumps(self.template))
        payload["items"].pop()
        payload["items"].append(dict(payload["items"][0]))
        payload["items"].append({**payload["items"][0], "id": "ADS-FAKE-99"})
        errors = VALIDATOR.validate_assessments(payload)
        joined = "\n".join(errors)
        self.assertIn("missing requirement ID", joined)
        self.assertIn("duplicate requirement ID", joined)
        self.assertIn("unknown requirement ID", joined)

    def test_pass_and_fail_require_direct_non_placeholder_evidence(self):
        for status in ("Pass", "Fail"):
            with self.subTest(status=status):
                payload = json.loads(json.dumps(self.template))
                payload["items"][0].update(
                    {
                        "status": status,
                        "evidence": "TODO",
                        "evidence_kind": "coverage_gap",
                        "effort": "N/A" if status == "Pass" else "S",
                    }
                )
                errors = VALIDATOR.validate_assessments(payload)
                self.assertTrue(any("direct evidence" in error for error in errors))

    def test_illegal_status_is_rejected(self):
        payload = json.loads(json.dumps(self.template))
        payload["items"][0]["status"] = "Warn"
        errors = VALIDATOR.validate_assessments(payload)
        self.assertTrue(any("invalid status" in error for error in errors))

    def test_unknown_and_na_require_their_specific_explanations(self):
        unknown = json.loads(json.dumps(self.template))
        unknown["items"][0]["next_action"] = ""
        self.assertTrue(any("next_action" in error for error in VALIDATOR.validate_assessments(unknown)))

        not_applicable = json.loads(json.dumps(self.template))
        not_applicable["items"][0].update(
            {
                "status": "N/A",
                "evidence": "This requirement does not apply.",
                "evidence_kind": "not_applicable",
                "provenance": {"mode": "not_applicable"},
                "next_action": "",
                "effort": "N/A",
                "applicability_reason": "",
            }
        )
        self.assertTrue(
            any("applicability_reason" in error for error in VALIDATOR.validate_assessments(not_applicable))
        )

        not_applicable["items"][0]["applicability_reason"] = "The audited site is self-hosted, not a hosted product."
        self.assertEqual(VALIDATOR.validate_assessments(not_applicable), [])

    def test_sensitive_material_is_rejected(self):
        payload = json.loads(json.dumps(self.template))
        payload["items"][0]["evidence"] = "api_key=super-secret-value-123456"
        errors = VALIDATOR.validate_assessments(payload)
        self.assertTrue(any("sensitive material" in error for error in errors))

    def test_target_domain_must_match_expected_domain(self):
        errors = VALIDATOR.validate_assessments(
            self.template,
            expected_domain="https://other.example",
        )
        self.assertTrue(any("target_domain" in error for error in errors))


class AggregationTestCase(unittest.TestCase):
    def setUp(self):
        self.template = VALIDATOR.make_assessment_template("https://site.example")
        self.registry = {item["id"]: item for item in VALIDATOR.load_registry()}

    def items(self):
        return [resolve_item(item) for item in self.template["items"]]

    def test_readiness_has_four_evidence_gated_outcomes(self):
        all_pass = self.items()
        self.assertEqual(VALIDATOR.summarize_items(all_pass, True)["readiness"], "READY")

        high_fail = self.items()
        high_id = next(item["id"] for item in self.registry.values() if item["severity"] == "High")
        index = next(i for i, item in enumerate(high_fail) if item["id"] == high_id)
        high_fail[index] = resolve_item(high_fail[index], "Fail", effort="S")
        self.assertEqual(
            VALIDATOR.summarize_items(high_fail, True)["readiness"],
            "READY_AFTER_FIXES",
        )

        blocker_fail = self.items()
        blocker_id = next(item["id"] for item in self.registry.values() if item["severity"] == "Blocker")
        index = next(i for i, item in enumerate(blocker_fail) if item["id"] == blocker_id)
        blocker_fail[index] = resolve_item(blocker_fail[index], "Fail", effort="L")
        self.assertEqual(VALIDATOR.summarize_items(blocker_fail, True)["readiness"], "NOT_READY")

        self.assertIsNone(VALIDATOR.summarize_items(all_pass, False)["readiness"])
        unresolved = self.items()
        unresolved[0] = self.template["items"][0]
        self.assertIsNone(VALIDATOR.summarize_items(unresolved, True)["readiness"])

    def test_remediation_order_uses_severity_then_effort_then_id(self):
        items = self.items()
        failures = [
            ("ADS-PRIV-01", "L"),
            ("ADS-CONTENT-01", "S"),
            ("ADS-UX-01", "S"),
            ("ADS-CRAWL-06", "M"),
        ]
        for ads_id, effort in failures:
            index = next(i for i, item in enumerate(items) if item["id"] == ads_id)
            items[index] = resolve_item(items[index], "Fail", effort=effort)
        summary = VALIDATOR.summarize_items(items, True)
        self.assertEqual(
            summary["remediation_order"],
            ["ADS-CONTENT-01", "ADS-PRIV-01", "ADS-UX-01", "ADS-CRAWL-06"],
        )


class ScannerAssessmentIntegrationTestCase(unittest.TestCase):
    def test_assessment_input_requires_adsense_and_domain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            root.mkdir()
            assessment_path = workspace / "assessments.json"
            assessment_path.write_text(
                json.dumps(VALIDATOR.make_assessment_template("https://site.example")),
                encoding="utf-8",
            )
            cases = (
                ["--adsense"],
                ["--domain", "https://site.example"],
            )
            for enabled_args in cases:
                with self.subTest(enabled_args=enabled_args):
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(AUDIT_PATH),
                            "--root",
                            str(root),
                            *enabled_args,
                            "--adsense-assessments",
                            str(assessment_path),
                            "--out",
                            str(workspace / "out"),
                        ],
                        cwd=REPO_ROOT,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 2)
                    self.assertIn("requires both --adsense and --domain", completed.stderr)

    def test_stable_hash_ignores_runtime_body_digest_but_includes_assessment_hash(self):
        base = {
            "generated_at": "2026-07-17T00:00:00Z",
            "scope": {
                "started_at": "2026-07-17T00:00:00Z",
                "output_paths": ["first.json"],
                "adsense_assessments": {"mode": "provided", "sha256": "a" * 64},
                "provenance": {"mode": "runtime", "result_hash": "old"},
            },
            "routes": [{"provenance": {"mode": "runtime", "content_hash": "1" * 64}}],
        }
        changed_runtime = json.loads(json.dumps(base))
        changed_runtime["routes"][0]["provenance"]["content_hash"] = "2" * 64
        self.assertEqual(AUDIT.stable_result_hash(base), AUDIT.stable_result_hash(changed_runtime))

        changed_assessment = json.loads(json.dumps(base))
        changed_assessment["scope"]["adsense_assessments"]["sha256"] = "b" * 64
        self.assertNotEqual(AUDIT.stable_result_hash(base), AUDIT.stable_result_hash(changed_assessment))

    def test_assessments_merge_without_path_leak_and_hash_is_stable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "site"
            rendered = workspace / "rendered"
            root.mkdir()
            (root / "src").mkdir()
            rendered.mkdir()
            (rendered / "index.html").write_text(
                "<html><head><title>Home</title><meta name='description' content='Useful page.'>"
                "<link rel='canonical' href='https://site.example/'></head>"
                "<body><main><h1>Home</h1><p>Useful current content.</p></main></body></html>",
                encoding="utf-8",
            )
            assessments = VALIDATOR.make_assessment_template("https://site.example")
            assessments["items"] = [resolve_item(item) for item in assessments["items"]]
            assessment_path = root / "src" / "private-assessments.json"
            assessment_path.write_text(json.dumps(assessments), encoding="utf-8")

            outputs = []
            for name in ("first", "second"):
                out = workspace / name
                self.assertEqual(
                    AUDIT.main(
                        [
                            "--root",
                            str(root),
                            "--domain",
                            "https://site.example",
                            "--rendered-root",
                            str(rendered),
                            "--adsense",
                            "--adsense-assessments",
                            str(assessment_path),
                            "--out",
                            str(out),
                        ]
                    ),
                    0,
                )
                outputs.append(json.loads(out.with_suffix(".json").read_text(encoding="utf-8")))

        first, second = outputs
        self.assertEqual(first["adsense"]["readiness"], "READY")
        self.assertEqual(first["adsense"]["conclusion"], "Pass")
        self.assertEqual(first["adsense"]["remediation_order"], [])
        self.assertEqual(first["scope"]["adsense_assessments"]["mode"], "provided")
        self.assertRegex(first["scope"]["adsense_assessments"]["sha256"], r"^[0-9a-f]{64}$")
        serialized = json.dumps(first, ensure_ascii=False)
        self.assertNotIn(str(assessment_path), serialized)
        self.assertNotIn("private-assessments.json", serialized)
        self.assertNotIn("private-assessments.json", first["scope"]["scanned_paths"])
        self.assertEqual(
            first["scope"]["provenance"]["result_hash"],
            second["scope"]["provenance"]["result_hash"],
        )
        self.assertEqual(VALIDATOR.validate_report(first), [])

    def test_report_validator_rejects_mutated_readiness(self):
        items = [
            resolve_item(item)
            for item in VALIDATOR.make_assessment_template("https://site.example")["items"]
        ]
        summary = VALIDATOR.summarize_items(items, True)
        report = {
            "scope": {"domain": "https://site.example"},
            "coverage": {"complete": True},
            "adsense": {
                "enabled": True,
                "requirement_total": 73,
                "reported_total": 73,
                "missing_ids": [],
                "items": [
                    {**next(row for row in VALIDATOR.load_registry() if row["id"] == item["id"]), **item}
                    for item in items
                ],
                **summary,
            },
        }
        report["adsense"]["readiness"] = "NOT_READY"
        self.assertTrue(any("readiness" in error for error in VALIDATOR.validate_report(report)))


if __name__ == "__main__":
    unittest.main()
