# 0.5.0 (2026-10-17)

## Added

- In the VECTOR GUI, support for scanning code from a Github URL and stopping active scans from the scan details page.
- Test cases and validation test reports for Web GUI source input file and stopping the scan.

## Modified

- The GUI now allows selecting an input file (from the GUI's endpoint) for VECTOR Code via a file explorer
- Docker images were upgraded to Python 3.12 (`python:3.12-slim-trixie`) and made smaller and faster to rebuild: the Go toolchain is no longer shipped (only the zgrab2 binary, now at `/usr/local/bin/zgrab2`), the CodeQL CLI is pinned and checksum-verified, and source code changes no longer rebuild the external tools; OpenSSL C headers are included in the images to enable dependency resolution by CodeQL
- `.dockerignore` now excludes `.git`, CI and editor configuration, `docs/`, and `output/` from the build context
- cryptobom-forge is installed in the container from the new `cryptobom-requirements.txt`, shared by `Dockerfile` and `dev.Dockerfile`. It pins the wheel with its SHA-256, the cyclonedx-python-lib fork at a commit, and all other dependencies at exact versions
- VECTOR-Code scans are faster: the CodeQL crypto inventory queries are precompiled when the Docker images are built instead of being compiled on every scan
- The user manual and technical documentation have been updated as per this release


# Fixed
- TOR's image build was failing due to external updates to the CodeQL GitHub repository. The commit-pinning mechanism in `Dockerfile` and `dev.Dockerfile` was changed to account for updates to the dependencies.


# 0.4.0 (2026-07-22)

## Added

- `vector gui [--port PORT]` CLI subcommand to start the web interface directly, enabling `vector.sh` to reach the GUI without overriding the container entry point (SRS-019)
- `vector.sh` runner script at the repository root: builds the standalone image on demand, starts VECTOR in CLI or GUI mode; usage documented in `docs/manual/start.md`
- Standalone VECTOR container (`Dockerfile`) for direct execution on endpoints and embedding into CI/CD pipelines (SRS-018)
- Unit tests for GitHub URL resolution (`tests/test_github_resolver.py`): URL parsing, clone/cleanup lifecycle, explicit error on non-existent repositories
- New requirements: `SRS-018` (standalone container deployment), `SRS-019` (runner script and `vector gui`)
- Test cases and validation test reports
    - (`docs/specs/tcs/TCS-015`) and (`docs/specs/trp/TRP-015`) for the web-based interface
    - (`docs/specs/tcs/TCS-016`) and (`docs/specs/trp/TRP-016`) for the standalone container
    - (`docs/specs/tcs/TCS-017`) and (`docs/specs/trp/TRP-017`) for the runner script
    - (`docs/specs/tcs/TCS-018`) and (`docs/specs/trp/TRP-018`) for Github URL support in VECTOR-Code

## Modified

- Updated Go base image from 1.24 to 1.25 in `Dockerfile` and `dev.Dockerfile`
- Refreshed `README.md`, `tor/README.md`, `docs/manual/start.md`, and `docs/manual/installation.md`: corrected output directory paths, GUI invocation commands, Go version references, and quick-start examples
- Improved GUI failure output: `_extract_failure_reason` now surfaces the last `Error`/`Warning`/`Unexpected error` line with its `Details:` context instead of a generic fallback message

# 0.3.0 (2026-06-24)

## Added

- Dev Container mount of host home directory to `/mnt/host-home`, enabling direct scanning of code on the host machine via `vector code /mnt/host-home/...`
- VECTOR-Code multi-language unified reporting: generates a single consolidated risk report when multiple languages are detected.
- Source code location tracking: the report includes file paths and line numbers of algorithms found in code scanning
- Web Interface: Added Flask-based web interface for submitting VECTOR-Code and VECTOR-Network scans, monitoring progress in real time, and reviewing risk findings (risk report, CBOM explorer, raw output)
- Scanning source code via Github URL is supported in VECTOR Code
- Product presentation page (`docs/website/product-presentation.html`) and release notes page (`docs/website/release-notes.html`) published as standalone HTML artifacts
- Unit tests for CBOM generator (`test_cbom_generator.py`) and risk report validation (`test_risk_report.py`)

## Modified

- Streamlined VECTOR-Score quantum risk classifications from 7 to 6 categories (merged `quantum-weakened` and `post-quantum` into `non-hybrid`)
- Updated documentation, specifications, and tests to reflect the new classification model
- Enhanced algorithm risk catalog with improved regex patterns
- Renamed `tests/content/` to `tests/data/` for clarity

## Fixed

- Unknown algorithms were silently omitted from the risk report; they now appear under the `unknown` classification

# 0.2.0 (2026-05-11)

## Added

- Unified `vector` CLI entry point (`vector/cli.py`) with three subcommands: `vector code`, `vector network`, and `vector score`
- `[tool.poetry.scripts]` entry in `pyproject.toml` registering `vector = "vector.cli:main"`
- `packages` declaration in `pyproject.toml` covering `vector`, `vector_code`, `vector_network`, and `vector_score`
- `run()` function in each module's `main.py` (`vector_code`, `vector_network`, `vector_score`) so the CLI can call module logic directly without going through `argparse`
- `__init__.py` files for `tor/`, `tor/vector_code/`, and `tor/vector_network/` to make them proper Python packages
- `poetry install` troubleshooting entry and note in `docs/manual/installation.md` and `docs/manual/troubleshooting.md`

## Modified

- Renamed `tor/VECTOR-Code/` to `tor/vector_code/` (Python-valid package name)
- Renamed `tor/VECTOR-Network/` to `tor/vector_network/` (Python-valid package name); `network-scanning.py` renamed to `main.py`
- Renamed `tor/VECTOR-Score/` to `tor/vector_score/` (Python-valid package name)
- Fixed implicit relative imports in `tor/vector_code/main.py` (`from src.*` → `from .src.*`)
- Fixed implicit relative imports in `tor/vector_score/cbom_scorer.py` and `tor/vector_score/main.py` (`from algorithm_classifier` / `from cbom_scorer` / `from report_generator` to dotted relative form)
- Updated test imports in `tests/test_algorithm_classifier.py` and `tests/test_cbom_scorer.py` to use `from vector_score.*` package imports instead of `sys.path.insert`
- Updated all user manual pages (`start.md`, `vector-code.md`, `vector-network.md`, `vector-score.md`, `installation.md`, `troubleshooting.md`) to document the `vector` CLI
- Updated `README.md` and `tor/README.md` quick-start sections to use `vector` CLI commands
- Embedded VECTOR-Code CBOM generation pipeline diagram into `ARC-002` (VECTOR-Code processing component)
- Embedded VECTOR-Network cryptography scanning diagram into `ARC-004` (External analysis tool adapters)
- Corrected swapped diagram filenames under `docs/specs/arc/assets/diagrams/`

## Fixed

- Make the `dev.Dockerfile` cross platform (skip CodeQL CLI if not x64)

# 0.1.0 (2026-05-09)

- Initial release of PQC-MAT providing the VECTOR subsystem