# TOR - Cryptographic Inventory Tools

TOR provides tools for cryptographic inventory, helping organizations identify cryptographic algorithms vulnerable to quantum attacks across source code and network infrastructure.

## Table of contents

- [Overview](#overview)
- [Getting started](#getting-started)
- [Usage](#usage)

## Overview

The project is divided into two complementary scanning components:

- **VECTOR-Code**: Analyzes source code to detect cryptographic algorithms using CodeQL
- **VECTOR-Network**: Scans network services (SSH, TLS) to identify cryptographic configurations

An additional component, **VECTOR-Score**, is used on the output of any or both of the components above, to assign a risk classification and a score to the inventorized cryptographic algorithms.

**VECTOR-GUI** provides a browser-based Flask interface that covers the full pipeline — scan submission, live output monitoring, and results browsing — without requiring the CLI.

## Getting Started

The project runs inside a VS Code Dev Container, which automatically installs all required dependencies and tools.

### Prerequisites

- [Docker](https://www.docker.com/) installed and running
- [VS Code](https://code.visualstudio.com/) with the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension

### Setup

1. Open the project root folder in VS Code
2. When prompted, click "Reopen in Container", or run the command: `Dev Containers: Reopen in Container` (`Ctrl+Shift+P`)
3. Wait for the container to build 

The container automatically installs all required dependencies and tools:
- Python 3.11, Poetry, Go 1.24
- CodeQL CLI and CodeQL cryptographic queries
- testssl.sh, ZGrab2, cloc
- cryptobom-forge

## Usage

All commands are run from inside the Dev Container.

### VECTOR-Code

Analyzes source code to detect programming languages and create CodeQL databases for cryptographic analysis.

```bash
vector code <path>
```

**Arguments:**
- `path` (required): path to the project to analyze
- `--name` (optional): application name for CBOM metadata (default: `application`)

The [pyca/cryptography](https://github.com/pyca/cryptography) library is included as a test project in the container.
You can use it to quickly verify the pipeline with:

```bash
vector code /home/vector/test-project/cryptography
```

**Output:**

Results are written to an `output/` directory containing three sub-folders: `databases/` with the generated CodeQL databases, `results/` with the SARIF files, and `cbom/` with the CBOM file.

The CBOM file is the end result compiling all the cryptographic assets found during the scan in a CycloneDX formatted file.

**Supported Languages:**
- Python
- C/C++

> **NOTES:**
>
> - Languages used in less than 5% of the codebase at the input path are ignored during detection and thus not scanned
> - In C/C++ projects, the compiled object files (`<name>.o`) are needed for the scan to give results

### VECTOR-Network

Scans network services to identify cryptographic configurations and generate Cryptographic Bills of Materials (CBOM).

```bash
vector network --protocol <ssh|tls> --target <host> --port <port>
```

#### TLS Analysis with testssl.sh

```bash
vector network --protocol tls --target example.com --port 443
```

**Output files generated:**
- `example_com_tls_scan.json`: Raw testssl.sh scan results
- `example_com_tls_cbom.json`: Cryptographic Bill of Materials in CycloneDX format

#### SSH Analysis with ZGrab2

Scans SSH services for supported key exchange and host key algorithms:

```bash
vector network --protocol ssh --target github.com --port 22
```

**Output files generated:**
- `github_com_ssh_scan.json`: Raw ZGrab2 scan results
- `github_com_ssh_cbom.json`: Cryptographic Bill of Materials in CycloneDX format

#### Custom Port Scanning

Analyze SSH or TLS on non-standard ports:

```bash
vector network --protocol tls --target internal.example.com --port 8443
```

**Output files generated:**
- `internal_example_com_tls_scan.json`: Raw scan results on custom port
- `internal_example_com_tls_cbom.json`: Cryptographic Bill of Materials

## Known Limitations

- **x86_64 only**: The Dev Container uses the CodeQL CLI which is only available for x86_64. GitHub does not provide ARM64.

## VECTOR-GUI: web interface

VECTOR-GUI is a Flask-based browser interface for submitting scans, monitoring live terminal output, and reviewing results without the CLI.

**Starting the server:**

```bash
VECTOR_ROOT=/home/vector/vector-project VECTOR_PORT=5000 python3 tor/gui/app.py
```

Forward port `5000` in the VS Code **Ports** panel, then open `http://localhost:5000`.

The interface provides three result views for each completed scan: a **risk report** with a quantum risk distribution chart and per-classification summary, a **CBOM explorer** with filterable per-algorithm risk cards and migration guidance, and a **raw output** tab with the original scanner output. Past scans are accessible from the **scan history** page.

<img src="../docs/manual/assets/VECTOR-GUI-NetScanRiskReport.png" alt="Risk report view showing a donut chart with quantum risk distribution and classification summary table" width="800"/>

<img src="../docs/manual/assets/VECTOR-GUI-NetScan-CBOM-Explorer.png" alt="CBOM explorer showing per-algorithm quantum risk cards with migration guidance and standards references" width="800"/>

## Documentation

Full user manual: [`docs/manual/`](../docs/manual/README.md) 
