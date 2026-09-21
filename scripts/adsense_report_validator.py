#!/usr/bin/env python3
"""Validate AdSense assessment inputs and aggregated SEO audit reports.

This validator checks completeness, schema rules, and derived conclusions. It
cannot prove that a human-provided evidence statement is factually true.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "references" / "adsense-requirements.md"
STATUSES = ("Pass", "Fail", "Unknown", "N/A")
EFFORTS = ("S", "M", "L", "Unknown", "N/A")
DIRECT_EVIDENCE_KINDS = {
    "http",
    "current_rendered",
    "repo_fact",
    "owner_confirmation",
    "account_dashboard",
    "analytics",
    "server_or_cdn",
    "legal_review",
    "policy_review",
    "manual_review",
}
REFERENCE_EVIDENCE_KINDS = {
    "owner_confirmation",
    "account_dashboard",
    "analytics",
    "server_or_cdn",
    "legal_review",
    "policy_review",
    "manual_review",
}
EVIDENCE_KINDS = DIRECT_EVIDENCE_KINDS | {"coverage_gap", "not_applicable"}
PLACEHOLDER_RE = re.compile(
    r"(?i)^\s*(?:todo|tbd|fixme|unknown|n/?a|none|null|placeholder|待补|待确认|暂无|未填写)[.!。\s]*$"
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|private[_-]?key|password|secret|token)\s*[:=]\s*[^\s,;]{6,}"
)
SENSITIVE_TOKEN_RE = re.compile(
    r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b|(?i:\bBearer\s+[A-Za-z0-9._~+/=-]{8,})"
)


def normalize_ws(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_target_domain(value: object) -> Optional[str]:
    text = normalize_ws(value).rstrip("/")
    if not text:
        return None
    parsed = urlparse(text)
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        return None
    host = parsed.hostname.lower()
    try:
        parsed_port = parsed.port
    except ValueError:
        return None
    port = f":{parsed_port}" if parsed_port else ""
    return f"{parsed.scheme.lower()}://{host}{port}"


def load_registry(path: Path = REGISTRY_PATH) -> List[Dict[str, str]]:
    """Read the canonical requirement table instead of duplicating its IDs."""
    text = path.read_text(encoding="utf-8")
    formal_start = text.find("## A.")
    formal_end = text.find("## Required Audit Output")
    if formal_start < 0 or formal_end <= formal_start:
        raise ValueError(f"AdSense registry sections are missing: {path}")

    rows: List[Dict[str, str]] = []
    seen = set()
    pattern = re.compile(
        r"^\|\s*(ADS-[A-Z]+-[0-9]{2})\s*\|\s*(Blocker|High|Medium)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
    )
    for line in text[formal_start:formal_end].splitlines():
        match = pattern.match(line)
        if not match:
            continue
        ads_id = match.group(1)
        if ads_id in seen:
            raise ValueError(f"duplicate requirement ID in registry: {ads_id}")
        seen.add(ads_id)
        rows.append(
            {
                "id": ads_id,
                "severity": match.group(2),
                "requirement": normalize_ws(match.group(3)),
                "how_to_verify": normalize_ws(match.group(4)),
            }
        )
    if len(rows) != 73:
        raise ValueError(f"AdSense registry must contain 73 IDs; found {len(rows)}")
    return rows


def make_assessment_template(target_domain: str) -> Dict[str, object]:
    normalized = normalize_target_domain(target_domain)
    if not normalized:
        raise ValueError("target_domain must be an HTTP(S) origin without path or userinfo")
    return {
        "schema_version": 1,
        "target_domain": normalized,
        "items": [
            {
                "id": row["id"],
                "status": "Unknown",
                "evidence": "当前审计没有足以确认该要求的直接证据。",
                "evidence_kind": "coverage_gap",
                "path_or_url": None,
                "evidence_ref": None,
                "provenance": {"mode": "coverage-gap"},
                "next_action": row["how_to_verify"],
                "effort": "Unknown",
                "applicability_reason": None,
            }
            for row in load_registry()
        ],
    }


def _has_sensitive_material(value: object) -> bool:
    if isinstance(value, str):
        return bool(SENSITIVE_ASSIGNMENT_RE.search(value) or SENSITIVE_TOKEN_RE.search(value))
    if isinstance(value, list):
        return any(_has_sensitive_material(item) for item in value)
    if isinstance(value, dict):
        for key, item in value.items():
            if re.fullmatch(
                r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|private[_-]?key|password|secret|token)",
                str(key),
            ) and item is not None and item != "" and item != "[REDACTED]":
                return True
            if _has_sensitive_material(item):
                return True
    return False


def _is_non_placeholder(value: object) -> bool:
    text = normalize_ws(value)
    return bool(text) and not PLACEHOLDER_RE.fullmatch(text)


def _path_is_safe(value: object) -> bool:
    if value is None or value == "":
        return True
    text = normalize_ws(value)
    parsed = urlparse(text)
    if parsed.scheme:
        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    return not Path(text).is_absolute() and ".." not in Path(text).parts


def validate_assessments(
    payload: object,
    expected_domain: Optional[str] = None,
) -> List[str]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["assessment payload must be a JSON object"]
    if _has_sensitive_material(payload):
        errors.append("assessment payload contains sensitive material; use a non-sensitive summary or opaque evidence_ref")
    if payload.get("schema_version") != 1:
        errors.append("assessment schema_version must be 1")

    target = normalize_target_domain(payload.get("target_domain"))
    if not target:
        errors.append("target_domain must be an HTTP(S) origin without path or userinfo")
    expected = normalize_target_domain(expected_domain) if expected_domain else None
    if expected_domain and not expected:
        errors.append("expected target_domain is invalid")
    elif expected and target != expected:
        errors.append(f"target_domain mismatch: expected {expected}, found {target or 'invalid'}")

    items = payload.get("items")
    if not isinstance(items, list):
        return errors + ["items must be an array"]

    registry = load_registry()
    registry_ids = [row["id"] for row in registry]
    registry_set = set(registry_ids)
    ids = [str(item.get("id")) for item in items if isinstance(item, dict)]
    counts = Counter(ids)
    for ads_id in registry_ids:
        if counts.get(ads_id, 0) == 0:
            errors.append(f"missing requirement ID: {ads_id}")
        elif counts[ads_id] > 1:
            errors.append(f"duplicate requirement ID: {ads_id}")
    for ads_id in sorted(set(ids) - registry_set):
        errors.append(f"unknown requirement ID: {ads_id}")

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        ads_id = str(item.get("id") or f"items[{index}]")
        status = item.get("status")
        evidence_kind = item.get("evidence_kind")
        effort = item.get("effort")
        provenance = item.get("provenance")
        provenance_mode = normalize_ws(provenance.get("mode")) if isinstance(provenance, dict) else ""
        if status not in STATUSES:
            errors.append(f"{ads_id}: invalid status {status!r}")
            continue
        if evidence_kind not in EVIDENCE_KINDS:
            errors.append(f"{ads_id}: invalid evidence_kind {evidence_kind!r}")
        if effort not in EFFORTS:
            errors.append(f"{ads_id}: invalid effort {effort!r}")
        if not _path_is_safe(item.get("path_or_url")):
            errors.append(f"{ads_id}: path_or_url must be a public HTTP(S) URL or repository-relative path")

        if status in {"Pass", "Fail"}:
            if (
                not _is_non_placeholder(item.get("evidence"))
                or evidence_kind not in DIRECT_EVIDENCE_KINDS
                or not provenance_mode
            ):
                errors.append(f"{ads_id}: {status} requires direct evidence, a direct evidence_kind, and provenance")
            if evidence_kind in {"http", "current_rendered", "repo_fact"} and not _is_non_placeholder(
                item.get("path_or_url")
            ):
                errors.append(f"{ads_id}: {evidence_kind} direct evidence requires path_or_url")
            if evidence_kind in REFERENCE_EVIDENCE_KINDS and not _is_non_placeholder(item.get("evidence_ref")):
                errors.append(f"{ads_id}: {evidence_kind} direct evidence requires an opaque evidence_ref")
            expected_efforts = {"N/A"} if status == "Pass" else {"S", "M", "L"}
            if effort not in expected_efforts:
                errors.append(f"{ads_id}: {status} requires effort in {sorted(expected_efforts)}")
            if status == "Fail" and not _is_non_placeholder(item.get("next_action")):
                errors.append(f"{ads_id}: Fail requires next_action")
        elif status == "Unknown":
            if evidence_kind != "coverage_gap":
                errors.append(f"{ads_id}: Unknown requires evidence_kind coverage_gap")
            if effort != "Unknown":
                errors.append(f"{ads_id}: Unknown requires effort Unknown")
            if not _is_non_placeholder(item.get("evidence")):
                errors.append(f"{ads_id}: Unknown requires an evidence-gap explanation")
            if not _is_non_placeholder(item.get("next_action")):
                errors.append(f"{ads_id}: Unknown requires next_action")
        else:
            if evidence_kind != "not_applicable":
                errors.append(f"{ads_id}: N/A requires evidence_kind not_applicable")
            if effort != "N/A":
                errors.append(f"{ads_id}: N/A requires effort N/A")
            if not provenance_mode:
                errors.append(f"{ads_id}: N/A requires provenance")
            if not _is_non_placeholder(item.get("applicability_reason")):
                errors.append(f"{ads_id}: N/A requires applicability_reason")
    return errors


def summarize_items(items: Iterable[Dict[str, object]], coverage_complete: bool) -> Dict[str, object]:
    item_list = list(items)
    registry = load_registry()
    registry_ids = [row["id"] for row in registry]
    severity_by_id = {row["id"]: row["severity"] for row in registry}
    ids = [str(item.get("id")) for item in item_list]
    counts = Counter(str(item.get("status")) for item in item_list)
    status_counts = {status: counts.get(status, 0) for status in STATUSES}
    structurally_complete = len(item_list) == len(registry_ids) and Counter(ids) == Counter(registry_ids)
    complete = bool(coverage_complete and structurally_complete and not status_counts["Unknown"])
    failures = [item for item in item_list if item.get("status") == "Fail"]
    if not complete:
        status = "Unknown"
        conclusion = None
        readiness = None
    elif failures:
        status = "Fail"
        conclusion = "Fail"
        readiness = (
            "NOT_READY"
            if any(severity_by_id.get(str(item.get("id"))) == "Blocker" for item in failures)
            else "READY_AFTER_FIXES"
        )
    else:
        status = "Pass"
        conclusion = "Pass"
        readiness = "READY"

    severity_order = {"Blocker": 0, "High": 1, "Medium": 2}
    effort_order = {"S": 0, "M": 1, "L": 2, "Unknown": 3, "N/A": 4}
    remediation_order = [
        str(item.get("id"))
        for item in sorted(
            failures,
            key=lambda item: (
                severity_order.get(severity_by_id.get(str(item.get("id"))), 9),
                effort_order.get(str(item.get("effort")), 9),
                str(item.get("id")),
            ),
        )
    ]
    return {
        "status_counts": status_counts,
        "summary": dict(status_counts),
        "complete": complete,
        "status": status,
        "conclusion": conclusion,
        "readiness": readiness,
        "remediation_order": remediation_order,
    }


def validate_report(report: object) -> List[str]:
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    adsense = report.get("adsense")
    if not isinstance(adsense, dict):
        return ["report.adsense must be an object"]
    if adsense.get("enabled") is not True:
        return []
    scope = report.get("scope")
    coverage = report.get("coverage")
    if not isinstance(scope, dict) or not isinstance(coverage, dict):
        return ["enabled AdSense report requires scope and coverage objects"]

    payload = {
        "schema_version": 1,
        "target_domain": scope.get("domain"),
        "items": adsense.get("items"),
    }
    errors = validate_assessments(payload, expected_domain=scope.get("domain"))
    items = adsense.get("items") if isinstance(adsense.get("items"), list) else []
    registry = load_registry()
    registry_by_id = {row["id"]: row for row in registry}
    for item in items:
        if not isinstance(item, dict) or item.get("id") not in registry_by_id:
            continue
        canonical = registry_by_id[str(item["id"])]
        for field in ("severity", "requirement", "how_to_verify"):
            if item.get(field) != canonical[field]:
                errors.append(f"{item['id']}: report {field} does not match the canonical registry")

    expected = summarize_items(items, coverage.get("complete") is True)
    expected_fields = {
        "requirement_total": len(registry),
        "reported_total": len(items),
        "missing_ids": [row["id"] for row in registry if row["id"] not in {str(item.get('id')) for item in items if isinstance(item, dict)}],
        **expected,
    }
    for field, value in expected_fields.items():
        if adsense.get(field) != value:
            errors.append(f"report.adsense.{field} is not derivable from item details and coverage")
    return errors


def _read_json(path_value: str) -> object:
    return json.loads(Path(path_value).read_text(encoding="utf-8"))


def _print_validation(errors: List[str]) -> int:
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK")
    return 0


def _selftest() -> List[str]:
    errors: List[str] = []
    try:
        template = make_assessment_template("https://example.com")
        errors.extend(validate_assessments(template))
        if len(template["items"]) != 73:
            errors.append("selftest template did not contain 73 items")
        if summarize_items(template["items"], True)["readiness"] is not None:
            errors.append("selftest unresolved template unexpectedly produced readiness")
    except (OSError, ValueError) as exc:
        errors.append(f"selftest failed: {exc}")
    return errors


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AdSense assessment and report completeness.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true", help="List canonical requirement rows as JSON.")
    action.add_argument("--template", action="store_true", help="Print a complete Unknown assessment template.")
    action.add_argument("--check-assessments", metavar="PATH", help="Validate an assessment JSON file.")
    action.add_argument("--check-report", metavar="PATH", help="Validate a final SEO audit JSON report.")
    action.add_argument("--selftest", action="store_true", help="Run built-in integrity checks.")
    parser.add_argument("--target-domain", default="", help="Expected HTTP(S) origin for template or validation.")
    args = parser.parse_args(argv)

    try:
        if args.list:
            print(json.dumps(load_registry(), ensure_ascii=False, indent=2))
            return 0
        if args.template:
            if not args.target_domain:
                parser.error("--template requires --target-domain")
            print(json.dumps(make_assessment_template(args.target_domain), ensure_ascii=False, indent=2))
            return 0
        if args.check_assessments:
            payload = _read_json(args.check_assessments)
            return _print_validation(validate_assessments(payload, args.target_domain or None))
        if args.check_report:
            return _print_validation(validate_report(_read_json(args.check_report)))
        return _print_validation(_selftest())
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
