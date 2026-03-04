#!/usr/bin/env python3
"""
LegacyLens Eval Runner
======================
Runs the full eval suite and generates a scored report.

Usage:
    python tests/evals/run_evals.py                  # all evals
    python tests/evals/run_evals.py --fast            # offline evals only (no API keys needed)
    python tests/evals/run_evals.py --category graph  # single category
    python tests/evals/run_evals.py --verbose         # pytest verbose output
"""

import subprocess
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CATEGORIES = {
    "chunker":   {"file": "test_chunker_evals.py",   "label": "Chunker Quality",      "needs_api": False},
    "graph":     {"file": "test_graph_evals.py",      "label": "Graph Integrity",      "needs_api": False},
    "api":       {"file": "test_api_evals.py",        "label": "API Contracts",         "needs_api": False},
    "retrieval": {"file": "test_retrieval_evals.py",  "label": "Retrieval Quality",    "needs_api": True},
    "e2e":       {"file": "test_e2e_evals.py",        "label": "E2E Generation",       "needs_api": True},
}


def run_category(name: str, info: dict, verbose: bool = False) -> dict:
    test_path = Path(__file__).parent / info["file"]
    cmd = [
        sys.executable, "-m", "pytest", str(test_path),
        "--tb=short", "-q", "--no-header",
        f"--junitxml={PROJECT_ROOT / 'tests' / 'evals' / f'results_{name}.xml'}",
    ]
    if verbose:
        cmd.append("-v")

    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    elapsed = time.time() - t0

    output = result.stdout + result.stderr
    passed = output.count(" PASSED") + output.count(" passed")
    failed = output.count(" FAILED") + output.count(" failed")
    skipped = output.count(" SKIPPED") + output.count(" skipped")
    errors = output.count(" ERROR") + output.count(" error")

    # Parse summary line like "5 passed, 1 failed, 2 skipped"
    for line in output.strip().split("\n"):
        line = line.strip()
        if "passed" in line or "failed" in line:
            import re
            m_p = re.search(r"(\d+) passed", line)
            m_f = re.search(r"(\d+) failed", line)
            m_s = re.search(r"(\d+) skipped", line)
            m_e = re.search(r"(\d+) error", line)
            if m_p: passed = int(m_p.group(1))
            if m_f: failed = int(m_f.group(1))
            if m_s: skipped = int(m_s.group(1))
            if m_e: errors = int(m_e.group(1))

    total = passed + failed + skipped + errors
    score = (passed / max(total - skipped, 1)) * 100 if total > 0 else 0

    return {
        "category": info["label"],
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "total": total,
        "score": round(score, 1),
        "elapsed_s": round(elapsed, 1),
        "exit_code": result.returncode,
        "output": output if verbose else "",
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LegacyLens Eval Runner")
    parser.add_argument("--fast", action="store_true", help="Skip evals that need API keys")
    parser.add_argument("--category", choices=list(CATEGORIES.keys()), help="Run single category")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose pytest output")
    args = parser.parse_args()

    cats = CATEGORIES
    if args.category:
        cats = {args.category: CATEGORIES[args.category]}
    if args.fast:
        cats = {k: v for k, v in cats.items() if not v["needs_api"]}

    print("=" * 64)
    print("  LegacyLens Eval Suite")
    print("=" * 64)
    print()

    results = {}
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    t_start = time.time()

    for name, info in cats.items():
        label = info["label"]
        print(f"  Running: {label} ...", end=" ", flush=True)
        r = run_category(name, info, verbose=args.verbose)
        results[name] = r
        total_passed += r["passed"]
        total_failed += r["failed"]
        total_skipped += r["skipped"]

        status = "PASS" if r["failed"] == 0 and r["errors"] == 0 else "FAIL"
        icon = "OK" if status == "PASS" else "XX"
        print(f"[{icon}] {r['passed']}/{r['total']} passed  ({r['score']}%)  {r['elapsed_s']}s")

        if args.verbose and r["output"]:
            for line in r["output"].split("\n"):
                if "FAILED" in line or "ERROR" in line:
                    print(f"    {line.strip()}")

    total_elapsed = time.time() - t_start

    print()
    print("-" * 64)
    grand_total = total_passed + total_failed
    grand_score = (total_passed / max(grand_total, 1)) * 100
    print(f"  TOTAL: {total_passed}/{grand_total} passed  "
          f"({grand_score:.0f}%)  "
          f"{total_skipped} skipped  "
          f"{total_elapsed:.1f}s")
    print("-" * 64)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "categories": results,
        "summary": {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "score_pct": round(grand_score, 1),
            "elapsed_s": round(total_elapsed, 1),
        },
    }
    report_path = PROJECT_ROOT / "tests" / "evals" / "eval_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report saved to: {report_path.relative_to(PROJECT_ROOT)}")
    print()

    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    main()
