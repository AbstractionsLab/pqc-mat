# VECTOR-Code reference

VECTOR-Code performs static analysis of source code to detect cryptographic API usage and produce a Cryptographic Bill of Materials (CBOM).

> **Web interface:** VECTOR-Code is also accessible through the browser-based GUI. See [Web interface](./start.md#web-interface) in the quick start guide.

## Pipeline overview

```
Source code directory
        │
        ▼
  cloc (language detection)
        │  identifies languages present above 5% threshold
        ▼
  codeql database create (per language)
        │  one database per CodeQL language (python, cpp)
        ▼
  codeql database analyze (per language)
        │  runs crypto inventory queries → SARIF output
        ▼
  cryptobom generate
        │  converts SARIF → unified CycloneDX 1.6 CBOM JSON
        ▼
  output/cbom/<app_name>-cbom.json
```

## Invocation

```bash
vector code <path> [--name <app_name>]
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `path` | Yes | — | Absolute or relative path to the source code directory to analyze |
| `--name` | No | `application` | Application name written into the `metadata` section of every generated CBOM |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | All steps completed successfully |
| `1` | A recoverable error occurred (e.g., no supported languages detected, a CodeQL database creation failed, a query run failed, or CBOM generation failed for one language) |
| `2` | An unexpected exception occurred |

### Example

```bash
vector code /home/vector/test-project/cryptography --name pyca-cryptography
```

Expected console output:

```
Language detection
  Detected: Python (18.8%)

Creating CodeQL databases
  Created: db-python

Running crypto queries
  Generated: crypto-python.sarif

Generating CBOM
  Generated: crypto-python-cbom.json

Completed
```

### Scanning code from your host machine

The code on host machine can be scanned without copying it into the container. The container has access to the home directory via the `/mnt/host-home` mount point:

```bash
vector code /mnt/host-home/path/to/your/project --name my-app
```

## Language detection

VECTOR-Code calls `cloc --json <path>` to count lines of code per language. Languages are included for analysis only if they make up at least **5%** of the total source lines.

### Supported languages

| Source language | CodeQL language | Status |
|----------------|-----------------|--------|
| Python | `python` | Supported |
| C | `cpp` | Supported |
| C++ | `cpp` | Supported — analyzed in the same database as C |
| Java | `java` | **Not supported** — CodeQL query pack is not available |

If a project contains both C and C++, a single `cpp` database is created and a single per-language CBOM is generated for both.

If no supported language meets the 5% threshold, the tool exits with code `1` and prints an error message.

## Multi-language output

When multiple supported languages are detected in a single project:
- One CodeQL database is created per unique language
- One SARIF file is generated per language
- A single **unified CBOM** is generated from the SARIF path

The unified CBOM is the final output artifact and is named `crypto-combined-cbom.json`. Individual per-language SARIF files are retained as intermediate artifacts in `output/results/` for traceability.


## CodeQL database creation

One CodeQL database is created per unique CodeQL language. The database is stored in:

```
output/databases/db-<codeql-language>/
```

For example, a Python project produces `output/databases/db-python/`.

The database is created with `--build-mode=none`, which means:
- No build system is invoked — the source tree is extracted directly.
- Compiled artifacts (`.class`, `.o`, etc.) are **not** analyzed.
- The tool works on unbuilt repositories.

If a database for that language already exists in the output directory, it is deleted and recreated on each run.

## CodeQL query execution

Cryptographic inventory queries are run against each database. The query paths are hardcoded to the container environment:

| Language | Query path |
|----------|-----------|
| Python | `/home/vector/tools/codeql-queries/python/ql/src/experimental/cryptography/inventory` |
| C/C++ | `/home/vector/tools/codeql-queries/cpp/ql/src/experimental/cryptography/inventory` |

These paths are not configurable via CLI. If the queries do not exist at these locations, the query step is skipped for that language and a warning is printed; no SARIF file is produced.

**What the queries detect:**  
The Santandersecurityresearch queries identify calls to cryptographic APIs — functions, classes, and constants from well-known libraries (e.g., Python's `cryptography`, `hashlib`, `ssl`; OpenSSL in C/C++). Each finding includes:
- The algorithm name (e.g., `AES`, `SHA256`, `RSA`)
- Key size or curve name where available
- Mode of operation where applicable
- Source file, line number, and code snippet

SARIF output is written to:

```
output/results/crypto-<language>.sarif
```

## CBOM generation

SARIF files are converted to CycloneDX 1.6 CBOM JSON using the cryptobom CLI (from the cryptobom-forge package):

```bash
cryptobom generate <sarif_path> \
  --application-name <app_name> \
  --output-file <output_path>
```

Output is written to:

```
output/cbom/crypto-<language>-cbom.json
```

`cryptobom-forge` must be installed manually before running VECTOR-Code. See [Installation](./installation.md#installing-cryptobom-forge-required--manual-step).

## Output files

All output is relative to the `tor/vector_code/` directory.

```
output/
├── databases/
│   └── db-python/          CodeQL database (queryable representation of source)
├── results/
│   └── crypto-python.sarif SARIF findings from CodeQL queries
└── cbom/
    └── crypto-python-cbom.json  CycloneDX 1.6 CBOM
```

Re-running VECTOR-Code overwrites all existing output files.

## Known limitations

| Limitation | Detail |
|-----------|--------|
| Java not supported | No CodeQL crypto inventory queries are available for Java |
| 5% threshold | Languages present below 5% of total LOC are not analyzed |
| Source-only | `--build-mode=none` means compiled binaries and dynamic behavior are not analyzed |
| Hardcoded query paths | Queries must exist at the exact container paths listed above; no CLI override |
| No incremental analysis | Every run recreates databases and re-runs all queries from scratch |
| Single CBOM per run | All findings across all detected languages are merged into one CBOM |
