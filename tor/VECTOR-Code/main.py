#!/usr/bin/env python3

import os
import argparse

OUTPUT_DIR = "output"
DATABASE_DIR = os.path.join(OUTPUT_DIR, "databases")
RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")
CBOM_DIR = os.path.join(OUTPUT_DIR, "cbom")

from src.language_detection import detect_languages
from src.codeql_database import create_databases
from src.codeql_queries import run_queries
from src.cbom_generator import generate_cbom


def setup_directories():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(CBOM_DIR, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Crypto Inventory Pipeline")
    parser.add_argument("path", help="Path to the project to analyze")
    parser.add_argument("--name", default="application", help="Application name for CBOM")
    args = parser.parse_args()

    project_path = args.path
    app_name = args.name

    if not project_path:
        print("Error: Project path cannot be empty")
        return 1

    project_path = os.path.abspath(project_path)

    if not os.path.exists(project_path):
        print(f"Error: Path '{project_path}' does not exist")
        return 1

    if not os.path.isdir(project_path):
        print(f"Error: Path '{project_path}' is not a directory")
        return 1

    if not os.access(project_path, os.R_OK):
        print(f"Error: No read permission for '{project_path}'")
        return 1

    try:
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
            print("  Error: Failed to create any CodeQL databases")
            return 1

        for lang, path in databases.items():
            print(f"  Created: db-{lang}")

        print("\nRunning crypto queries")
        sarif_files = run_queries(databases, RESULTS_DIR)

        if not sarif_files:
            print("  Warning: No SARIF files generated")
            return 1

        for sarif in sarif_files:
            print(f"  Generated: {os.path.basename(sarif)}")

        print("\nGenerating CBOM")
        cbom_files = generate_cbom(sarif_files, CBOM_DIR, app_name)

        if not cbom_files:
            print("  Warning: No CBOM files generated")
            return 1

        for cbom in cbom_files:
            print(f"  Generated: {os.path.basename(cbom)}")

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


if __name__ == "__main__":
    import sys
    sys.exit(main())