# VECTOR-Code reference

VECTOR-Code scans source code to detect cryptographic API usage (for example AES, SHA-256, RSA) and produces a Cryptographic Bill of Materials (CBOM) in CycloneDX 1.6 format.

VECTOR-Code can be run from the command line (detailed below) or from the [web GUI](./start.md#3-use-the-web-gui).

## Running a scan

| Mode | Command |
|---|---|
| Standalone container (host terminal) | `./vector.sh cli code <source> [--name <app_name>] [--output <dir>]` |
| Dev Container | `vector code <source> [--name <app_name>] [--output <dir>]` |

See [Which command form to use](./start.md#2-run-a-scan-from-the-command-line) for how paths are handled in each mode.

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `<source>` | Yes | — | Project directory, or a public GitHub repository URL. With `vector.sh`, `demo` selects the demo project bundled in the image |
| `--name` | No | `application` (`<owner>/<repo>` for GitHub URLs) | Application name written into the CBOM |
| `--output` | No | `output` | Output directory. With `vector.sh`, a directory given here must already exist on the host; if omitted, `./output` is created in the current directory |

### Examples

```bash
# Standalone container
mkdir -p results
./vector.sh cli code demo --output results
./vector.sh cli code ~/projects/my-app --name my-app --output results
./vector.sh cli code https://github.com/pyca/cryptography --output results

# Dev Container
vector code /home/vector/test-project/cryptography --output results
vector code /mnt/host-home/path/to/project --name my-app --output results
```

In the Dev Container, `/mnt/host-home` is the VS Code workspace folder on the host.

### Local folders: CLI vs GUI

When VECTOR runs on a remote machine (e.g. a VM) and you open the GUI from another computer (e.g. your laptop), the CLI and the GUI see different local folders:

| | Can scan local folders on |
|---|---|
| CLI (`./vector.sh cli code <dir>`) | The machine where `vector.sh` runs (the VM) |
| GUI (**Choose folder…**) | The computer where the browser is open (your laptop) — the folder is uploaded to VECTOR |

To scan code that is on the VM, use the CLI. To scan code that is on your laptop, use the GUI, or copy the code to the VM first. GitHub URLs work the same way in both.

### GitHub repositories

| URL form | Example |
|---|---|
| Repository | `https://github.com/<owner>/<repo>` |
| Branch or tag | `https://github.com/<owner>/<repo>/tree/<branch-or-tag>` |
| Subdirectory | `https://github.com/<owner>/<repo>/tree/<branch-or-tag>/<path>` |

The repository is cloned shallowly into a temporary directory and deleted once the CodeQL databases are built. Only public repositories are supported; a repository that requires authentication fails with an error.

### Console output

Example
```
Language detection
  Detected: Python (18.8%)

Creating CodeQL databases
  Created: db-python

Running crypto queries
  Results generated: crypto-python.sarif

Generating CBOM
  CBOM file generated at: /home/vector/vector-project/results/cbom/crypto-python-cbom.json

Completed successfully
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Scan completed and a CBOM was generated |
| `1` | Scan failed: invalid source, clone error, no supported language, or a CodeQL / CBOM step failed |
| `2` | Unexpected error (a traceback is printed) |

## How it works

```
Local path or GitHub URL
        │
        ▼
  cloc (language detection)
        │  counts lines of code identifying languages used in at least 5% of the codebase
        ▼
  codeql database create (per language)
        │  creates one database per CodeQL language (python, cpp)
        ▼
  codeql database analyze (per language)
        │  runs crypto inventory queries → SARIF output
        ▼
  cryptobom generate
        │  merges SARIF files into a unified CycloneDX 1.6 CBOM JSON
        ▼
  <output_dir>/cbom/<app_name>-cbom.json
```

### CodeQL queries

The CodeQL queries identify calls to cryptographic APIs — functions, classes, and constants from well-known libraries (e.g., Python's `cryptography`, `hashlib`, `ssl`; OpenSSL in C/C++). Each finding includes:
- The algorithm name (e.g., `AES`, `SHA256`, `RSA`)
- Key size or curve name where available
- Mode of operation where applicable
- Source file, line number, and code snippet

The VECTOR images precompile these queries at build time to prevent each scan having to spend time compiling them.

### Supported languages

| Language | Status |
|---|---|
| Python | Supported (e.g. `cryptography`, `hashlib`, `ssl`) |
| C, C++ | Supported — OpenSSL only; C and C++ share one `cpp` database |

The query step is skipped for not supported languages and a warning is printed; no SARIF file is produced.


## Output

```
<output>/
  ├── databases/           CodeQL databases (db-python/, db-cpp/)
  ├── results/             SARIF results (crypto-python.sarif, crypto-cpp.sarif)
  └── cbom/                The CBOM
      └── crypto-python-cbom.json
```

Exactly one CBOM is produced:

| Languages analyzed | CBOM file |
|---|---|
| One | `crypto-<language>-cbom.json` (`crypto-python-cbom.json` or `crypto-cpp-cbom.json`) |
| Several | `crypto-combined-cbom.json` |

Each run **deletes** the existing `databases/`, `results/`, and `cbom/` folders in the output directory before starting; use a different `--output` directory to keep earlier results.

To assess quantum risk, pass the CBOM to [VECTOR-Score](./vector-score.md). See [Understanding CBOM output](./cbom-output.md) for the file format.

## Header resolution for C and C++

Projects are not built from source code, thus, include paths in C (`-I` flags) are unknown. An OpenSSL call is detected when its header can be found without them:

- `#include <openssl/...>` resolves to the OpenSSL 3 headers installed in the image.
- `#include "openssl/..."` also resolves when the header is shipped with the project, relative to the including file.

May be missed:

- APIs not declared by OpenSSL 3, e.g. BoringSSL/LibreSSL-specific functions or APIs removed since OpenSSL 1.x — unless the project ships those headers and includes them with quotes.
- Code that depends on project headers found only through `-I` flags, which may be left unparsed.

## Known limitations

- **x86_64 only** — no ARM64 build of the CodeQL CLI exists.
- **Languages** — Python, C, and C++ only; languages below 5% of the code are skipped.
- **C/C++ coverage** — OpenSSL only, subject to [header resolution](#header-resolution-for-c-and-c).
- **Source only** — binaries and object files are not analyzed.
- **No incremental scans** — every run rebuilds databases and re-runs all queries.
- **Public GitHub repositories only.**
