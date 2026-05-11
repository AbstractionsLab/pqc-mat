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