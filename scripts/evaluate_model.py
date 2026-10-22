"""Opt-in semantic checks against a genuine configured model; never a CI fixture."""

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", action="store_true", help="Use the loopback-only free CPU model")
    parser.add_argument("--wait-ready", type=int, default=0, help="Wait 0-300s for llama.cpp /health")
    parser.add_argument("--report", type=Path, default=Path("reports/local/model-evaluation.json"))
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if args.local:
        os.environ.update(
            LLM_BASE_URL="http://localhost:18089/v1",
            LLM_MODEL="patternforge-local",
            LLM_API_KEY="local-loopback-placeholder",
            LLM_JSON_SCHEMA="1",
        )
    import django

    django.setup()
    import regex
    from core.errors import PipelineError
    from core.services.plans import request_plan, validate_java_pattern, validate_plan
    from django.conf import settings

    if (
        not settings.LLM_MODEL
        or "fixture" in settings.LLM_MODEL.lower()
        or "://fixtures:" in settings.LLM_BASE_URL
    ):
        raise SystemExit("A configured genuine model is required; deterministic CI fixtures are rejected.")
    if not 0 <= args.wait_ready <= 300:
        parser.error("--wait-ready must be between 0 and 300")
    if args.wait_ready:
        import httpx

        deadline = time.monotonic() + args.wait_ready
        health_url = settings.LLM_BASE_URL.removesuffix("/v1") + "/health"
        while True:
            try:
                if httpx.get(health_url, timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() >= deadline:
                raise SystemExit("The genuine model did not become ready before the deadline.")
            time.sleep(1)

    # Escaped source literals decode to the original Chinese prompts during inference.
    cases = [
        (
            "regex_replace",
            "Find email addresses",
            "Contact a.b+tag@example.technology today",
            "a.b+tag@example.technology",
            ["Text"],
        ),
        (
            "regex_replace",
            "\u8bc6\u522b\u6587\u672c\u4e2d\u7684\u7535\u5b50\u90ae\u7bb1\u5730\u5740",
            "\u7528\u6237 hello@example.com",
            "hello@example.com",
            ["Text"],
        ),
        ("regex_replace", "Match runs of decimal digits", "Order AB123X", "123", ["Text"]),
        (
            "regex_extract",
            "Extract the email address from the text",
            "Write to team@example.org now",
            "team@example.org",
            ["Text"],
        ),
        (
            "normalize",
            "Trim ends, collapse repeated whitespace and convert to lowercase",
            "  ALICE   SMITH  ",
            "alice smith",
            ["Text"],
        ),
        (
            "normalize",
            "Make all letters uppercase and trim surrounding whitespace",
            "  Alice  ",
            "ALICE",
            ["Text"],
        ),
        # A custom identifier has no universal format; do not infer it from a private cell.
        ("regex_extract", "Extract order IDs", "Order ORD-0 shipped", None, ["Description"]),
        (
            "regex_extract",
            "Extract order IDs beginning with ORD- followed by digits",
            "Order ORD-0 shipped",
            "ORD-0",
            ["Description"],
        ),
        (
            "regex_extract",
            "\u63d0\u53d6\u4ee5 INV- \u5f00\u5934\u3001\u540e\u9762\u7d27\u8ddf"
            "\u4e00\u4f4d\u6216\u591a\u4f4d\u6570\u5b57\u7684\u53d1\u7968\u7f16\u53f7",
            "Invoice INV-42 sent",
            "INV-42",
            ["Description"],
        ),
        ("normalize", "Trim, collapse whitespace, lowercase names", "  USER   0  ", "user 0", ["Name"]),
    ]
    results = []
    for operation, prompt, sample, expected, columns in cases:
        start = time.monotonic()
        entry = {"operation": operation, "instruction": prompt}
        expects_refusal = expected is None
        if expects_refusal:
            entry["expected_error"] = "RULE_NEEDS_CLARIFICATION"
        try:
            plan = validate_plan(
                request_plan({"operation": operation, "prompt": prompt, "target_columns": columns}),
                operation,
            )
            validate_java_pattern(plan)
            if operation == "normalize":
                actual = sample
                for step in plan["steps"]:
                    actual = {
                        "trim": lambda: actual.strip(),
                        "collapse_whitespace": lambda: regex.sub(r"\s+", " ", actual),
                        "lowercase": lambda: actual.lower(),
                        "uppercase": lambda: actual.upper(),
                    }[step]()
            else:
                match = regex.search(plan["pattern"], sample, timeout=0.05)
                actual = match.group(plan["group"]) if match else None
            entry.update(
                passed=not expects_refusal and actual == expected, plan=plan, expected=expected, actual=actual
            )
            if expected == "ORD-0":
                # Reuse this one genuine plan across distinct lengths and counterexamples.
                checks = []
                for text, wanted in [
                    ("Order ORD-9 shipped", "ORD-9"),
                    ("Order ORD-123456 shipped", "ORD-123456"),
                    ("Order PO-123 shipped", None),
                    ("No order here", None),
                ]:
                    match = regex.search(plan["pattern"], text, timeout=0.05)
                    result = match.group(plan["group"]) if match else None
                    checks.append(
                        {"sample": text, "expected": wanted, "actual": result, "passed": result == wanted}
                    )
                entry["additional_checks"] = checks
                entry["passed"] = entry["passed"] and all(check["passed"] for check in checks)
        except PipelineError as exc:
            entry.update(
                passed=expects_refusal and exc.code == "RULE_NEEDS_CLARIFICATION", error_code=exc.code
            )
        entry["seconds"] = round(time.monotonic() - start, 3)
        results.append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    report = {
        "genuine_model": True,
        "model": settings.LLM_MODEL,
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "passed": sum(item["passed"] for item in results),
        "total": len(results),
        "cases": results,
        "limitations": "Small fixed semantic sample; not a general model-quality guarantee or real-AWS run.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Genuine model checks: {report['passed']}/{report['total']}. Report: {args.report}")
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
