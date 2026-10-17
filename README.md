# PQC-MAT

The Post-Quantum Cryptography Migration Assistance Theory and Tools (**PQC-MAT**) project is a sub-project of [CyFORT](https://abstractionslab.com/index.php/research-and-development/cyfort/), standing for "Cloud Cybersecurity Fortress of Open Resources and Tools for Resilience", carried out in the context of the [IPCEI-CIS](https://ec.europa.eu/commission/presscorner/detail/en/ip_23_6246) project.

<img src="./docs/manual/assets/CyFORT-PQC-MAT-logo.png" alt="cyfort_logo" width="500"/>

This repository hosts resources for a secure and methodological migration from classical to post-quantum cryptography (PQC) in cyber-physical systems. PQC migration replaces algorithms based on classical public-key cryptography with quantum-secure alternatives built on mathematical problems that cannot be efficiently solved by a Cryptographically Relevant Quantum Computer (CRQC). It currently provides two subsystems — **VEC** and **TOR**, which together form **VECTOR**: **VE**rified **C**ryptography and **T**ransition via **O**bservable **R**egistry.

Technical specifications are available on the [traceability web page](https://abstractionslab.github.io/pqc-mat/traceability/index.html). See the [user manual](/docs/manual/README.md) for details on installation, quick start, feature matrix, and system concept.

For a visual stakeholder-oriented tour of VECTOR, visit the **[product presentation page](https://abstractionslab.github.io/pqc-mat/website/product-presentation.html)**.

<img src="./docs/manual/assets/VECTOR-product-website.png" alt="pqcmat-cad-website" width="500"/>

> **Security disclaimer:** PQC-MAT is to be currently viewed as a research and audit tool intended for use in controlled environments (e.g., isolated lab networks, Dev Containers). It is not hardened for production deployment. In particular, the network scanning scripts accept user-supplied hostnames that are passed to external tools without full input sanitization. Do not expose PQC-MAT to untrusted input or run it in a production or internet-facing environment.

## Table of contents

- [PQC-MAT suite](#pqc-mat-suite)
- [Quick start](#quick-start)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Contributing / development](#contributing--development)
- [License](#license)
- [Acknowledgment](#acknowledgment)
- [Contact](#contact)

## PQC-MAT suite

PQC-MAT consists of two main modules:

### TOR — Transition via Observable Registry (cryptographic inventory tools)

[**TOR**](/tor/README.md) is an automated cryptographic inventory and analysis system that assesses organizational readiness for PQC migration. It discovers cryptographic assets across source code and network infrastructure and generates standardized [Cryptographic Bills of Materials (CBOM)](https://cyclonedx.org/capabilities/cbom/) in CycloneDX 1.6 format.

- **VECTOR-Code**: CodeQL-based static analysis of source code to detect cryptographic algorithm usage in Python, C, and C++ projects, producing SARIF findings converted to CBOM via cryptobom-forge.
- **VECTOR-Network**: Dynamic network scanning of TLS and SSH services using testssl.sh and ZGrab2, with full protocol version, cipher suite, key exchange, elliptic curve, and post-quantum/hybrid KEM inventory.
- **VECTOR-Score**: Quantum risk scoring for any CycloneDX CBOM. Classifies each algorithm component by its quantum risk posture using a data-driven catalog (NIST FIPS 203/204/205, BSI TR-02102, ANSSI) and produces an annotated CBOM plus a Markdown risk report.
- **VECTOR-GUI**: Browser-based Flask interface for submitting VECTOR-Code and VECTOR-Network scans, monitoring live terminal output, and reviewing results — risk report, CBOM explorer, and raw scanner output — without using the CLI.

**Built on:** [CodeQL](https://codeql.github.com/), [testssl.sh](https://testssl.sh/), [ZGrab2](https://github.com/zmap/zgrab2), [cryptobom-forge](https://github.com/Santandersecurityresearch/cryptobom-forge), [CycloneDX](https://cyclonedx.org/)

VECTOR-Network's custom parsers are the primary novel contribution: testssl.sh and ZGrab2 do not natively produce CBOM output. TOR bridges this gap, including full cipher suite decomposition into individual algorithm components and detection of hybrid post-quantum KEMs. VECTOR-Code automates an existing CodeQL + cryptobom-forge pipeline, which in some cases provides more comprehensive CBOMs compared to [CBOMkit](https://github.com/cbomkit/cbomkit), an established alternative for the same task. The combined value is a single, containerized workflow that produces standardized CycloneDX CBOMs across both code and network surfaces for PQC readiness audits.

### VEC — Verified Cryptography

[**VEC**](/vec/README.md) was developed during an internship by a mathematics MSc student. It currently provides an introductory tutorial on using [F*](https://www.fstar-lang.org/) (a proof-oriented programming language) to produce mathematically verified implementations of cryptographic functions. It demonstrates how to encode algorithm specifications with pre- and post-conditions, prove termination and correctness with SMT solver assistance, and automatically extract verified executable OCaml code.

The included worked example covers the **Extended Euclidean Algorithm (EEA)** — a foundational primitive in public-key cryptography (e.g., modular inverses for RSA).

## Quick start

### Decision tree

- **Need to inventory cryptographic assets in source code?** → use [VECTOR-Code](#vector-code-static-source-analysis)
- **Need to audit TLS/SSH cryptographic configurations?** → use [VECTOR-Network](#vector-network-network-scanning)
- **Have a CBOM and need quantum risk classification?** → use [VECTOR-Score](#vector-score-quantum-risk-scoring)
- **Exploring verified algorithm implementations?** → read the [F* sources](#vec-verified-cryptography)

### Prerequisites

- **Docker engine**: v20.10 or later, installed and running 
- **Bash**: for the `vector.sh` runner (standalone container)
- **Host architecture**: x86_64 for VECTOR-Code (CodeQL CLI limitation); on ARM hosts (e.g. Apple Silicon) only VECTOR-Network and VECTOR-Score are available
- **Internet access**: to build the image, and at run time for GitHub URLs and network scans
- **VS Code + [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension**: Recommended for the Dev Container setup

### Setup

VECTOR can be run in two ways — pick the one that fits your workflow:

| | Requires | Best for |
|---|---|---|
| **Dev Container** | Docker engine + VS Code + Dev Containers extension | Interactive development, exploring output |
| **Standalone container** | Docker engine | One-off scans, CI/CD pipelines |

**Dev Container (VS Code):** Open the project folder in VS Code, then: Command Palette → `Dev Containers: Reopen in Container`. All tools are installed automatically.

**Standalone container:** Use the `vector.sh` runner script at the repository root:

```bash
chmod +x vector.sh   # first time only
./vector.sh          # start VECTOR GUI (builds image automatically if needed)
./vector.sh cli      # show the vector CLI help
./vector.sh build    # force a rebuild after a code change
```

**CLI commands.** The examples below use the Dev Container form; for the standalone container, prefix them with `./vector.sh cli`:

| Form | Where it runs | Paths refer to |
|---|---|---|
| `vector <command> ...` | Inside the Dev Container terminal | The container filesystem |
| `./vector.sh cli <command> ...` | On the host | The host filesystem — source and `--output` directories are mounted into the container; if `--output` is not given, results go to `./output` |

See the [quick start guide](./docs/manual/start.md) for more details and references to detailed usage manuals.

### VECTOR-Code: static source analysis

> **Note:** CodeQL CLI requires an x86_64 host. VECTOR-Code will not run on ARM-based machines.

```bash
# Analyze the demo project bundled in the image
vector code /home/vector/test-project/cryptography                 # Dev Container
mkdir -p results && ./vector.sh cli code demo --output ./results  # standalone container

# Your own project
vector code /path/to/your/project --name my-app --output results

# GitHub repository URL (no local checkout needed)
vector code https://github.com/pyca/cryptography --name pyca-cryptography --output results
```

Output is written to `results/cbom/` (or the directory given by `--output`). See [VECTOR-Code reference](./docs/manual/vector-code.md) for output structure and supported languages.

### VECTOR-Network: network scanning

```bash
vector network --protocol tls --target example.com --port 443 --output results
vector network --protocol ssh --target 192.168.1.1 --port 22 --output results
```

Each scan writes a raw scanner output file and a CycloneDX CBOM to `--output`. See [VECTOR-Network reference](./docs/manual/vector-network.md).

### VECTOR-Score: quantum risk scoring

```bash
vector score /path/to/cbom.json
vector score cbom.json --output cbom_scored.json --report risk_report.md
```

Produces an annotated CBOM (`<stem>_scored.json`) and a Markdown risk report (`<stem>_risk_report.md`). See [VECTOR-Score reference](./docs/manual/vector-score.md).

### VECTOR-GUI: web interface

VECTOR provides a browser-based interface for running and monitoring scans, and visualizing results, including a **risk report**, **CBOM explorer**, and **raw output** tab.

```bash
[./vector.sh | vector] gui [--port <port>]
```

The GUI is available at `http://localhost:5992` by default or at the selected `<port>`.

<img src="docs/manual/assets/VECTOR-GUI-NetScanRiskReport.png" alt="Risk report view showing a donut chart with quantum risk distribution and a classification summary table" width="800"/>

<img src="docs/manual/assets/VECTOR-GUI-NetScan-CBOM-Explorer.png" alt="CBOM explorer showing per-algorithm quantum risk cards with migration guidance and standards references" width="800"/>

> **Disclaimer:** The GUI is still a work in progress. Input validation and sanitization have not yet been fully implemented.

### VEC: verified cryptography

See this component's dedicated [README](/vec/README.md) and its [compilation guide](/vec/compilation-guide.md) for F* installation requirements and instructions for running the verified OCaml extraction.

## Documentation

- **User manual:** [`docs/manual/`](/docs/manual/) — installation, quick start, feature matrix, and system concept
- **Technical specifications:** [`docs/specs/`](/docs/specs/) — interlinked requirements (MRS, SRS, ARC, SWD, TCS, TRP) following the [C5-DEC](https://abstractionslab.github.io/c5dec/website/product-presentation.html) methodology
- **Traceability:** [published traceability page](https://abstractionslab.github.io/pqc-mat/traceability/index.html) — coverage analysis and interlinked HTML spec browser

## Roadmap

- Extended PQC algorithm coverage in VECTOR-Network
- Extended programming language support in VECTOR-Code
- Automated CBOM aggregation across code and network surfaces
- CBOM diff / migration progress tracker (baseline vs. current scan)

## Contributing / development

```bash
# Install Python dependencies (from project root)
poetry install

# Run Doorstop structure validation
poetry run doorstop

# Publish specs and refresh traceability (when specs changed)
cd docs/specs && ./publish.sh
```

## License

Copyright © itrust Abstractions Lab and itrust consulting. All rights reserved.

Licensed under the [GNU Affero General Public License (AGPL) v3.0](LICENSE).

**Disclaimer:** VECTOR-Code uses GitHub's CodeQL CLI, whose terms allow free use on open-source code and academic research only. For use on closed-source code, or in automated CI/CD analysis, see the [GitHub CodeQL Terms & Conditions](https://github.com/github/codeql-cli-binaries).


## Acknowledgment

Co-funded by the Ministry of the Economy of Luxembourg in the context of the CyFORT project.

## Contact

Abstractions Lab: info@abstractionslab.lu