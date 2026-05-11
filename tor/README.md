# TOR - Cryptographic Inventory Tools

TOR provides tools for cryptographic inventory, helping organizations identify cryptographic algorithms vulnerable to quantum attacks across source code and network infrastructure.

## Table of contents

- [Overview](#overview)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Usage](#usage)

## Overview

The project is divided into two complementary components:

- **VECTOR-Code**: Analyzes source code to detect cryptographic algorithms using CodeQL
- **VECTOR-Network**: Scans network services (SSH, TLS) to identify cryptographic configurations

## Project Structure

```
tor/
├── vector_code/
│   ├── main.py
│   └── src/
│       ├── language_detection.py
│       ├── codeql_database.py
│       ├── codeql_queries.py
│       └── cbom_generator.py
├── vector_network/
│   ├── main.py
│   ├── testssl_to_cbom.py
│   └── zgrab2_to_cbom.py
├── vector_score/
│   ├── main.py
│   ├── algorithm_classifier.py
│   ├── cbom_scorer.py
│   ├── report_generator.py
│   └── data/
│       └── algorithm-risk-catalog.yaml
└── README.md
```

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

A test project is included in the container at `/home/vector/test-project/cryptography` (the [pyca/cryptography](https://github.com/pyca/cryptography) library). You can use it to quickly verify the pipeline:

```bash
vector code /home/vector/test-project/cryptography
```

**Example output:**
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

**Supported Languages:**
- Python
- C/C++
- Java (planned)

**Output structure:**
```
output/
├── databases/   (CodeQL databases)
├── results/     (SARIF files)
└── cbom/        (CBOM files)
```

**Notes:**
- Language threshold is set to 5% by default
- CodeQL databases stored in `output/databases/`

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

## Documentation

Full user manual: [`docs/manual/`](../docs/manual/README.md) 
