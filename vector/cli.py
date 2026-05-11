"""
cli.py — VECTOR unified CLI entry point.

Usage:
    vector code <path> [--name <app>]
    vector network --protocol <ssh|tls> --target <host> --port <port>
    vector score <cbom.json> [--output <path>] [--report <path>] [--no-report]
"""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vector",
        description="VECTOR: cryptographic inventory and quantum risk scoring toolkit",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- vector code ---
    code = subparsers.add_parser(
        "code",
        help="Static analysis of source code to produce a CBOM (VECTOR-Code)",
    )
    code.add_argument("path", help="Path to the project directory to analyze")
    code.add_argument(
        "--name",
        default="application",
        metavar="NAME",
        help="Application name embedded in the CBOM (default: application)",
    )

    # --- vector network ---
    net = subparsers.add_parser(
        "network",
        help="SSH/TLS network scan to produce a CBOM (VECTOR-Network)",
    )
    net.add_argument(
        "--protocol",
        choices=["ssh", "tls"],
        required=True,
        help="Protocol to scan",
    )
    net.add_argument(
        "--target",
        required=True,
        help="Target domain or IP address",
    )
    net.add_argument(
        "--port",
        type=int,
        required=True,
        help="Port number (1-65535)",
    )

    # --- vector score ---
    score = subparsers.add_parser(
        "score",
        help="Quantum risk scoring of a CycloneDX CBOM file (VECTOR-Score)",
    )
    score.add_argument(
        "cbom",
        metavar="cbom.json",
        help="Path to the input CycloneDX CBOM JSON file",
    )
    score.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Output path for the annotated CBOM (default: <input-stem>_scored.json)",
    )
    score.add_argument(
        "--report",
        metavar="PATH",
        default=None,
        help="Output path for the Markdown risk report (default: <input-stem>_risk_report.md)",
    )
    score.add_argument(
        "--no-report",
        action="store_true",
        help="Suppress Markdown report generation",
    )

    args = parser.parse_args()

    if args.command == "code":
        from vector_code.main import run as run_code
        sys.exit(run_code(args.path, args.name))

    elif args.command == "network":
        from vector_network.main import run as run_network
        sys.exit(run_network(args.protocol, args.port, args.target))

    elif args.command == "score":
        from vector_score.main import run as run_score
        sys.exit(run_score(args.cbom, args.output, args.report, args.no_report))
