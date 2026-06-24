#!/usr/bin/env python3

import os
import argparse
import shutil

from .src.language_detection import detect_languages
from .src.codeql_database import create_databases
from .src.codeql_queries import run_queries
from .src.cbom_generator import generate_cbom
from .src.github_resolver import is_github_url, resolve as resolve_github

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_PACKAGE_DIR, "output")
DATABASE_DIR = os.path.join(OUTPUT_DIR, "databases")
RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")
CBOM_DIR = os.path.join(OUTPUT_DIR, "cbom")


def setup_directories():
    # each run of 'vector code' deletes the output of a previous run
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(CBOM_DIR, exist_ok=True)


def run(source: str, app_name: str = "application") -> int:
    if not source:
        print("Error: Project path or Github URL cannot be empty")
        return 1

    clone_result = None
    try:
        if is_github_url(source):
            print(f"GitHub URL detected, cloning repository")
            try:
                clone_result = resolve_github(source)
            except (ValueError, RuntimeError) as exc:
                print(f"  Error: {exc}")
                return 1

            project_path = clone_result.path
            print(f"  Cloned:  {source}")
            print(f"  Path:    {project_path}")

            if app_name == "application":
                app_name = clone_result.app_name
        else:
            project_path = os.path.abspath(source)

            if not os.path.exists(project_path):
                print(f"Error: Path '{project_path}' does not exist")
                parent = os.path.dirname(project_path)
                if os.path.isdir(parent):
                    try:
                        entries = sorted(os.listdir(parent))
                        print(f"  Contents of '{parent}':")
                        for entry in entries[:20]:
                            print(f"    {entry}")
                    except Exception:
                        pass
                return 1

            if not os.path.isdir(project_path):
                print(f"Error: Path '{project_path}' is not a directory")
                return 1

            if not os.access(project_path, os.R_OK):
                print(f"Error: No read permission for '{project_path}'")
                return 1

        setup_directories()

        print("Language detection")
        languages = detect_languages(project_path)

        if not languages:
            print(f"  Warning: No supported languages detected in {project_path}")
            print("  Supported languages: Python, C, C++")
            return 1

        for lang, data in languages.items():
            print(f"  Detected: {lang} ({data['percentage']:.1f}%)")

        print("\nCreating CodeQL databases")
        databases = create_databases(project_path, languages, DATABASE_DIR)

        if not databases:
            print("  Error: Failed to create CodeQL databases")
            return 1

        for lang, _ in databases.items():
            print(f"  Created: db-{lang}")

        if clone_result is not None:
            print("\n  Removing cloned source (databases built)")
            clone_result.cleanup()
            clone_result = None

        print("\nRunning crypto queries")
        sarif_files = run_queries(databases, RESULTS_DIR)

        if not sarif_files:
            print("  Warning: No SARIF files generated")
            return 1

        for sarif in sarif_files:
            print(f"  Results generated: {os.path.basename(sarif)}")

        print("\nGenerating CBOM")
        cbom_file = generate_cbom(RESULTS_DIR, CBOM_DIR, app_name)

        if not cbom_file:
            print("  Warning: No CBOM file generated")
            return 1
        print(f"  CBOM file generated at: {cbom_file}")

        print("\nCompleted successfully")
        return 0

    except RuntimeError as e:
        print(f"\nError: {e}")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 2
    finally:
        if clone_result is not None:
            clone_result.cleanup()


def main():
    import sys
    parser = argparse.ArgumentParser(description="Crypto Inventory Pipeline", formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
            vector code /path/to/project
            vector code /path/to/project --name my-app
            vector code https://github.com/owner/repo
            vector code https://github.com/owner/repo --name my-app
            vector code https://github.com/owner/repo/tree/main
    """.strip())
    parser.add_argument("path", help="Local directory path or GitHub URL to analyze")
    parser.add_argument("--name", default="application", help="Application name for CBOM")
    args = parser.parse_args()
    sys.exit(run(args.path, args.name))


if __name__ == "__main__":
    main()
