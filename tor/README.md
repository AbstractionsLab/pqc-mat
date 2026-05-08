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
├── VECTOR-Code/
│   ├── main.py
│   └── src/
│       ├── language_detection.py
│       ├── codeql_database.py
│       ├── codeql_queries.py
│       └── cbom_generator.py
├── VECTOR-Network/
│   ├── network-scanning.py
│   ├── testssl_to_cbom.py
│   └── zgrab2_to_cbom.py
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
cd tor/VECTOR-Code
python3 main.py <path>
```

**Arguments:**
- `path` (required): path to the project to analyze

A test project is included in the container at `/home/vector/test-project/cryptography` (the [pyca/cryptography](https://github.com/pyca/cryptography) library). You can use it to quickly verify the pipeline:

```bash
cd tor/VECTOR-Code
python3 main.py /home/vector/test-project/cryptography
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

Launch the interactive network scanning tool:

```bash
cd tor/VECTOR-Network
python3 network-scanning.py
```

#### Interactive Menu

```
Select protocol
  1. SSH (port 22)
  2. TLS (port 443)
  3. Custom
Choice (1/2/3): _
```

#### TLS Analysis with testssl.sh

Provides comprehensive TLS/SSL cipher suite enumeration for target hosts:

```bash
Select protocol
  1. SSH (port 22)
  2. TLS (port 443)
  3. Custom
Choice (1/2/3): 2
Target (domain or IP): example.com

Scanning example.com (TLS)
  Scan saved: example_com_tls_scan.json

Generating CBOM

Completed
```

**Output files generated:**
- `example_com_tls_scan.json`: Raw testssl.sh scan results
- `example_com_tls_cbom.json`: Cryptographic Bill of Materials in CycloneDX format

#### SSH Analysis with ZGrab2

Scans SSH services for supported key exchange and host key algorithms:

```bash
Select protocol
  1. SSH (port 22)
  2. TLS (port 443)
  3. Custom
Choice (1/2/3): 1
Target (domain or IP): github.com

Scanning github.com (SSH)
  Scan saved: github_com_ssh_scan.json

Generating CBOM

Completed
```

**Output files generated:**
- `github_com_ssh_scan.json`: Raw ZGrab2 scan results
- `github_com_ssh_cbom.json`: Cryptographic Bill of Materials in CycloneDX format

#### Custom Port Scanning

Analyze SSH or TLS on non-standard ports:

```bash
Select protocol
  1. SSH (port 22)
  2. TLS (port 443)
  3. Custom
Choice (1/2/3): 3

Select protocol
  SSH
  TLS
Choice (1/2): 2
Port: 8443
Target (domain or IP): internal.example.com

Scanning internal.example.com (TLS)
  Scan saved: internal_example_com_tls_scan.json

Generating CBOM

Completed
```

**Output files generated:**
- `internal_example_com_tls_scan.json`: Raw scan results on custom port
- `internal_example_com_tls_cbom.json`: Cryptographic Bill of Materials

## Known Limitations

- **x86_64 only**: The Dev Container uses the CodeQL CLI which is only available for x86_64. GitHub does not provide ARM64.

## Documentation

Full user manual: [`docs/manual/`](../docs/manual/README.md) 
