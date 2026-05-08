# TOR - System Concept Document

---

## Project Information

| Field | Value |
|-------|-------|
| **Project Name** | TOR |
| **Program** | CyFORT |
| **Status** | In Development |
| **Version** | 0.1 |
| **Date** | May 2026 |
| **Author** | MCI |
| **Supervisor** | AAT |

---

## Document Overview

This System Concept document describes the TOR project, an automated cryptographic inventory and analysis system designed to assess organizational readiness for post-quantum cryptography (PQC) migration. The system performs comprehensive cryptographic asset discovery across both source code and network infrastructure, generating standardized Cryptographic Bills of Materials (CBOM) for quantum risk assessment.

**Key Objectives:**
- Automated detection of cryptographic algorithms in source code (Python, C, C++)
- Network service analysis for TLS/SSH cipher suite identification

---

## Document Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | December 2025 | Initial draft | MCI |
| 0.1.1 | May 2026 | Fix Java support status, clarify CBOMkit integration scope | MCI |

---


# Background

## Organizational Context and CyFORT Project

The TOR project is part of the CyFORT program, an initiative aimed at strengthening cybersecurity resilience of infrastructures against emerging threats.

## The Quantum Threat and the Urgency of PQC Migration

The advent of quantum computers represents a major threat to current cryptography. The "Harvest Now, Decrypt Later" (HTDL) scenario describes an attack where adversaries collect data encrypted today with classical algorithms (RSA, ECDSA, ECDH) with the intention of decrypting it later once sufficiently powerful quantum computers become available.

According to the TNO PQC Migration Handbook [1], experts predict a realistic probability of 25% that cryptographically relevant quantum computers will exist in 10 years, reaching over 60% in 20 years. Shor's algorithm [Sho94] would completely compromise current asymmetric primitives (RSA, ECDH, ECDSA, EdDSA), while Grover's algorithm [Gro96] would halve the security of symmetric algorithms.

Recommendations from NIST (National Institute of Standards and Technology), Germany's BSI, and France's ANSSI call for organizations to begin their migration to post-quantum cryptography (PQC) now. In August 2024, NIST published the first PQC standards, marking the beginning of a new phase of global migration.

## Need for Comprehensive Cryptographic Inventory

Without a comprehensive cryptographic inventory, organizations cannot assess their quantum attack surface nor effectively plan their transition to quantum-resistant algorithms. As indicated in the TNO Handbook [1], previous cryptographic migrations (e.g., SHA-1 to SHA-256) took more than 5 years even after specifications and implementations were available.

The Cryptographic Bill of Materials (CBOM), based on the CycloneDX standard [3], provides a standardized machine-readable format for inventorying cryptographic assets. The methodological approach presented in "Mapping Quantum Threats: An Engineering Inventory of Cryptographic Dependencies" by Carlos Benitez [2] emphasizes the importance of systematic discovery of cryptographic dependencies in modern infrastructures.


## Reference Documents

The preliminary work and design of TOR are based on the following documents:

1. **"The PQC Migration Handbook"** (2nd Edition, December 2024) - AIVD, CWI, TNO  
   Comprehensive methodological guide for PQC migration in three steps: quantum vulnerability diagnosis, planning, and execution  
   https://publications.tno.nl/publication/34643386/fXcPVHsX/TNO-2024-pqc-en.pdf

2. **"Mapping Quantum Threats: An Engineering Inventory of Cryptographic Dependencies"** - Carlos Benitez  
   Engineering analysis of cryptographic inventory methodologies facing quantum threats  
   https://arxiv.org/pdf/2509.24623v1

3. **CycloneDX CBOM Standard Specifications** (v1.6)  
   OWASP specifications for standardized representation of cryptographic inventories  
   https://github.com/CycloneDX/specification  

4. **CBOMkit Documentation & Source Code**  
   Open-source toolset for CBOM generation, visualization, analysis and quantum risk assessment developed by IBM Research and donated to the Post-Quantum Cryptography Alliance (PQCA)  
   https://github.com/PQCA/cbomkit  
   https://github.com/IBM/CBOM


## TOR Objective

TOR aims to create an automated analysis system to diagnose an organization's cryptographic posture from both network and source code perspectives. The objective is to identify all cryptographic algorithms in use within the analyzed scope (source code repositories and accessible network services), generate inventories compliant with the CBOM standard, and provide quantum risk assessment to prepare for PQC migration.

The system operates on two complementary axes:

- **TOR-Code**: Static source code analysis to detect cryptographic primitives in applications:
  - CLOC for language detection
  - CodeQL with Santandersecurityresearch queries for cryptographic discovery
  - CryptoBOM-forge for CBOM generation

- **TOR-Network**: Network service analysis (TLS, SSH) to identify cipher suites and cryptographic configurations using testssl.sh for comprehensive TLS analysis and ZGrab2 for SSH scanning

# Solution Concept

TOR is designed as a modular dual-component system operating independently on two complementary analysis axes:

## Component 1 : TOR-Code (Static Source Code Analysis)

### Purpose
Automated detection and inventory of cryptographic primitives within application source code across multiple programming languages.


### Supported Languages

| Language | Status | Query Source |
|----------|--------|--------------|
| **Python** | Fully Supported | Santandersecurityresearch |
| **C/C++** | Fully Supported | Santandersecurityresearch | 
| **Java** | Not supported | No CodeQL queries available — planned for a future release |


### Technical Implementation Details

**1. Language Detection Phase**
```bash
cloc <repository_path> --json
```
- Identifies programming language distribution
- Determines which CodeQL queries to execute
 
**2. CodeQL Database Creation**
```bash
codeql database create <db_name> --language=<lang> --source-root=<path> --build-mode=none
```
- Creates queryable database representation of source code
- For Java and C++: Uses `--build-mode=none` to enable extraction without requiring a successful build, allowing analysis of codebases

**3. Query Execution**
```bash
codeql database analyze <db_name> <query_suite> --format=sarif-latest --output=<results.sarif> --sarif-add-snippets
```
- Executes cryptographic detection queries
- Queries identify algorithm usage, key sizes, modes of operation
- Output format SARIF 

**4. CBOM Generation**
```bash
cryptobom generate <path_to_sariffile> --application-name "<app_name>" --output-file <path_to_outputfile>
```
- Converts SARIF findings to CycloneDX CBOM format
- Maps cryptographic detections to CBOM component structure with algorithm type, primitive, and usage context

## Component 2 : TOR-Network (Network Infrastructure Analysis)

### Purpose
Comprehensive cryptographic configuration analysis of network services (TLS, SSH) to identify cipher suites, protocol versions, and key exchange algorithms.

### TLS Analysis with testssl.sh

**Why testssl.sh over ZGrab2 for TLS?**
- **Comprehensive enumeration**: Identifies ALL supported cipher suites, not just negotiated ones
- **Protocol version coverage**: Tests TLS 1.0, 1.1, 1.2, 1.3, SSL 2.0, SSL 3.0

**Execution:**
```bash
testssl.sh --jsonfile <output.json> <target>:443
```

**Captured Information:**
- Supported cipher suites (all, not negotiated only)
- Protocol versions enabled
- Certificate chain and validity
- Key exchange algorithms
- Forward Secrecy support

### SSH Analysis with ZGrab2

**Execution:**
```bash
echo '<target>' | zgrab2 ssh --port <port> -o <results.json>
```

**Captured Information:**
- SSH protocol version (SSH-1.x, SSH-2.0)
- Key exchange algorithms offered
- Host key algorithms
- Encryption ciphers (symmetric algorithms)
- MAC algorithms

### Custom CBOM Generation

**Python Parsers:**
- `testssl_to_cbom.py`: Converts testssl.sh JSON -> CBOM
- `zgrab2_to_cbom.py`: Converts ZGrab2 JSON -> CBOM

## Integration with CBOMkit

### Purpose
CBOMkit is an open-source toolset developed by IBM Research and donated to the Post-Quantum Cryptography Alliance (PQCA). Integration with CBOMkit is planned as a future capability and is not yet implemented in TOR. When available, it is expected to provide:
- Visualization of cryptographic asset inventory
- Quantum-safe compliance checking
- Risk scoring


## System Execution Workflow

### Automated Pipeline
```
1. User Input Target repository URL or network range
              │
              ▼
2. TOR-Code Clone repository -> Language detection -> CodeQL analysis -> CBOM
              │
              ▼
3. TOR-Network Scan services -> testssl.sh/ZGrab2 -> Parse -> CBOM
              │
              ▼
4. Output CBOM files (one per language / one per scan target)
```

### Deployment Considerations
- **Environment**: Python 3.10+, CodeQL CLI, testssl.sh, ZGrab2
- **Dependencies**: cryptobom-forge v1.1.0, CLOC, network scanning tools

## Technology Stack Summary

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language Detection | CLOC | Latest | Identify programming languages |
| Static Analysis | CodeQL | Latest CLI | Create queryable code databases |
| Crypto Queries | Santandersecurityresearch | Latest | Detect cryptographic patterns |
| SARIF Conversion | cryptobom-forge | v1.1.0 | Generate CycloneDX CBOMs |
| TLS Analysis | testssl.sh | v3.2+ | Comprehensive TLS scanning |
| SSH Analysis | ZGrab2 | Latest | SSH handshake analysis |
| CBOM Management | CBOMkit | Latest | Visualization & compliance |
| Output Format | CycloneDX | v1.6 | Industry-standard SBOM |

