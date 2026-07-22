"""
cli.py — VECTOR unified CLI entry point.

Usage:
    vector code <path> [--name <app>]
    vector network --protocol <ssh|tls> --target <host> --port <port>
    vector score <cbom.json> [--output <path>] [--report <path>] [--no-report]
    vector gui [--port <port>]
"""

import argparse
import os
import sys
from pathlib import Path


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
    code.add_argument(
        "--output",
        dest="output_dir",
        default="output",
        help="Directory to write scan output to (default: output/ directory)"
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
    net.add_argument(
        "--output",
        dest="output_dir",
        default="output",
        help="Directory to write scan output to (default: output/ directory)"
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

    # --- vector gui ---
    gui = subparsers.add_parser(
        "gui",
        help="Start the VECTOR GUI web interface",
    )
    gui.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("VECTOR_PORT", 5992)),
        metavar="PORT",
        help="Port to serve the web interface on (default: 5992, or $VECTOR_PORT)",
    )

    args = parser.parse_args()

    if args.command == "code":
        from vector_code.main import run as run_code
        sys.exit(run_code(source=args.path, app_name=args.name, output_dir=args.output_dir))

    elif args.command == "network":
        from vector_network.main import run as run_network
        sys.exit(run_network(protocol=args.protocol, port=args.port, target=args.target, output_dir=args.output_dir))

    elif args.command == "score":
        from vector_score.main import run as run_score
        sys.exit(run_score(args.cbom, args.output, args.report, args.no_report))

    elif args.command == "gui":
        repo_root = Path(__file__).resolve().parent.parent
        app_path = repo_root / "tor" / "gui" / "app.py"
        if not app_path.exists():
            print(f"Error: could not find VECTOR GUI at {app_path}", file=sys.stderr)
            sys.exit(1)
        env = os.environ.copy()
        env["VECTOR_PORT"] = str(args.port)
        env["VECTOR_ROOT"] = str(repo_root)
        os.execve(sys.executable, [sys.executable, str(app_path)], env)