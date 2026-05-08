# TOR User Manual

## Table of contents

- [System concept](./system-concept.md)
- [Features](./features.md)
- [Installation](./installation.md)
- [Quick start](./start.md)
- [VECTOR-Code reference](./vector-code.md)
- [VECTOR-Network reference](./vector-network.md)
- [VECTOR-Score reference](./vector-score.md)
- [Understanding CBOM output](./cbom-output.md)
- [Troubleshooting](./troubleshooting.md)

## Overview

TOR (part of the CyFORT program) is an automated cryptographic inventory and analysis system for assessing organizational readiness for post-quantum cryptography (PQC) migration. It performs cryptographic asset discovery across source code and network infrastructure, generating standardized Cryptographic Bills of Materials (CBOM).

## What TOR does

TOR discovers which cryptographic algorithms are present in a target system and records them in a machine-readable inventory (CBOM). This inventory answers the question: *which parts of this system are vulnerable to quantum attacks, and what do they use?*

TOR works on three complementary axes:

- **VECTOR-Code** — static analysis of source code. Points TOR at a repository; it identifies programming languages, builds a CodeQL database, runs cryptographic detection queries, and produces a CBOM listing every cryptographic API call found.
- **VECTOR-Network** — live scanning of network services. Connects to an SSH or TLS endpoint, enumerates all offered cipher suites, and produces a CBOM listing the cryptographic algorithms in use.
- **VECTOR-Score** — quantum risk scoring for any CycloneDX CBOM. Classifies each algorithm component by its quantum risk posture using a data-driven catalog (NIST FIPS 203/204/205, BSI TR-02102, ANSSI) and produces an annotated CBOM plus a Markdown risk report.

VECTOR-Code and VECTOR-Network output [CycloneDX 1.6 CBOM](https://cyclonedx.org/) JSON files. Those CBOMs can then be passed directly to VECTOR-Score for quantum risk classification, or reviewed manually.

## Typical workflow

1. Run VECTOR-Code against a source repository to find cryptographic API usage.
2. Run VECTOR-Network against the deployed services of the same system to find negotiated cipher suites.
3. Run VECTOR-Score against the generated CBOMs to classify each algorithm by quantum risk posture and produce a prioritized Markdown report.
4. Review the annotated CBOMs and risk reports to identify quantum-vulnerable algorithms (RSA, ECDH, ECDSA, DSA) and plan PQC migration.

## Glossary

| Term | Meaning |
|------|---------|
| **VECTOR** | VErified Cryptography and Transition via Observable Registry — the umbrella name for subsystems VEC and TOR, also used in TOR's three analysis tools (VECTOR-Code, VECTOR-Network, VECTOR-Score) |
| **CBOM** | Cryptographic Bill of Materials — a structured inventory of cryptographic assets, standardized by CycloneDX |
| **SARIF** | Static Analysis Results Interchange Format — intermediate output format produced by CodeQL before CBOM conversion |
| **PQC** | Post-Quantum Cryptography — cryptographic algorithms designed to resist attacks by quantum computers |
| **KEM** | Key Encapsulation Mechanism — a key exchange primitive; post-quantum KEMs (e.g. ML-KEM) replace classical ECDH |
| **CodeQL** | GitHub's static analysis engine; TOR uses it to query source code for cryptographic API calls |
| **CycloneDX** | OWASP standard for Software/Hardware/Cryptography Bills of Materials |
| **HNDL** | Harvest Now, Decrypt Later — attack where encrypted data is collected today and decrypted once quantum computers exist |
| **CRQC** | Cryptographically Relevant Quantum Computer — a quantum computer powerful enough to break classical public-key algorithms using Shor's algorithm |
| **VECTOR-Score** | TOR component that reads a CycloneDX CBOM and annotates each algorithm with a quantum risk classification and recommended migration target |
