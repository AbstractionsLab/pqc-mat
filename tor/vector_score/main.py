#!/usr/bin/env python3
"""
main.py — VECTOR-Score CLI entry point.

Usage:
    python3 main.py <cbom.json> [--output <scored.json>] [--report <report.md>] [--no-report]
"""

import argparse
import json
import os
import sys

from .cbom_scorer import score_cbom
from .report_generator import generate_report


def _default_output_path(input_path: str) -> str:
    stem, _ = os.path.splitext(input_path)
    return stem + "_scored.json"


def _default_report_path(input_path: str) -> str:
    stem, _ = os.path.splitext(input_path)
    return stem + "_risk_report.md"


def run(
    input_path: str,
    output_path: str = None,
    report_path: str = None,
    no_report: bool = False,
) -> int:
    if not os.path.exists(input_path):
        print(f"Error: input file '{input_path}' does not exist.")
        return 1

    if not os.path.isfile(input_path):
        print(f"Error: '{input_path}' is not a file.")
        return 1

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            cbom = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"Error: '{input_path}' is not valid JSON: {exc}")
        return 1

    print(f"Scoring {input_path}")
    scored = score_cbom(cbom)

    algo_count = sum(
        1 for c in scored.get("components", [])
        if c.get("cryptoProperties", {}).get("assetType") == "algorithm"
    )
    print(f"  Algorithm components scored: {algo_count}")

    resolved_output = output_path or _default_output_path(input_path)
    with open(resolved_output, "w", encoding="utf-8") as f:
        json.dump(scored, f, indent=2, ensure_ascii=False)
    print(f"  Annotated CBOM written to: {resolved_output}")

    if not no_report:
        resolved_report = report_path or _default_report_path(input_path)
        report_text = generate_report(scored)
        with open(resolved_report, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"  Risk report written to:    {resolved_report}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="VECTOR-Score: quantum risk scoring for CycloneDX CBOM files.",
        epilog="Example: python3 main.py cbom.json --output cbom_scored.json --report report.md",
    )
    parser.add_argument(
        "cbom",
        metavar="cbom.json",
        help="Path to the input CycloneDX CBOM JSON file.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Output path for the annotated CBOM (default: <input-stem>_scored.json).",
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        default=None,
        help="Output path for the Markdown risk report (default: <input-stem>_risk_report.md).",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Suppress Markdown report generation.",
    )
    args = parser.parse_args()
    return run(args.cbom, args.output, args.report, args.no_report)


if __name__ == "__main__":
    sys.exit(main())
