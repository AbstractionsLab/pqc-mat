# VECTOR-Score reference

VECTOR-Score reads any CycloneDX 1.6 CBOM JSON file, classifies each cryptographic algorithm component by its quantum risk posture, annotates the CBOM with `pqcmat:`-namespaced properties, and produces a Markdown risk report.

## Prerequisites

- Python 3.11
- PyYAML (included in the Poetry dependencies at the project root)

VECTOR-Score does not require Docker, CodeQL, testssl.sh, or ZGrab2. It can be run stand-alone against any valid CycloneDX CBOM.

## Invocation

```bash
cd tor/VECTOR-Score

# Minimal invocation — output files written next to the input file
python3 main.py /path/to/cbom.json

# Specify output paths explicitly
python3 main.py cbom.json --output cbom_scored.json --report risk_report.md

# Score only (suppress report generation)
python3 main.py cbom.json --no-report
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `cbom` | yes | — | Path to a CycloneDX 1.6 CBOM JSON file |
| `--output` | no | `<stem>_scored.json` | Path for the annotated output CBOM |
| `--report` | no | `<stem>_risk_report.md` | Path for the Markdown risk report |
| `--no-report` | no | — | Skip report generation; write annotated CBOM only |

## Output files

### Annotated CBOM

A deep copy of the input CBOM with `pqcmat:`-namespaced properties appended to every algorithm component (`cryptoProperties.assetType == "algorithm"`). The input file is never modified.

Added properties on each algorithm component:

| Property name | Example value |
|---------------|---------------|
| `pqcmat:risk-classification` | `quantum-vulnerable` |
| `pqcmat:risk-score` | `high` |
| `pqcmat:rationale` | `RSA relies on the hardness of integer factorisation…` |
| `pqcmat:recommended-migration` | `ML-KEM-768 (NIST FIPS 203) for key encapsulation` |
| `pqcmat:reference` | `NIST FIPS 203` (repeated entry per reference) |

Two properties are also added to `metadata.properties`:

| Property name | Description |
|---------------|-------------|
| `pqcmat:scored-at` | ISO 8601 UTC timestamp of the scoring run |
| `pqcmat:scorer-version` | VECTOR-Score release version (e.g. `0.1`) |

### Risk report

A Markdown file containing:

1. Header — target application name, timestamp, scorer version, total algorithm count.
2. Summary table — counts grouped by risk classification with the associated risk score level.
3. Per-classification finding tables — algorithm name, primitive type, key size (if present), rationale, and recommended migration target.
4. Normative references — links to NIST FIPS 203/204/205, BSI TR-02102-1, ANSSI, SP 800-131A Rev.2.

## Risk classifications

VECTOR-Score assigns one of seven classifications to each algorithm component.

| Classification | Risk score | Description |
|---------------|------------|-------------|
| `quantum-vulnerable` | High | Relies on integer factorisation or discrete logarithm problems that are broken by Shor's algorithm on a cryptographically relevant quantum computer (CRQC). Includes RSA, ECDH/ECDHE, DHE, ECDSA, DSA, EdDSA, X25519/X448. Immediate migration planning required. |
| `quantum-weakened` | Medium | Symmetric or hash algorithms with key/output sizes, the search spaces of which are often said to be halved by Grover's algorithm. However, this is not accurate as Grover's algorithm is not embarrassingly parallel and partitioning the search space would degrade the Grover quadratic speedup. This is subject to ongoing research. The algorithm remains usable at appropriate sizes but should be reviewed for long-term security (as suggested by NIST or BSI). Includes AES-128, SHA-1, 3DES-EDE, HMAC-SHA1. |
| `classically-deprecated` | High | Already broken or deprecated by classical cryptanalysis, independent of quantum threats. Includes RC4, DES, MD5, IDEA, SEED, NULL ciphers, and EXPORT suites. Remove immediately. |
| `quantum-safe` | None | Symmetric and hash algorithms with sufficient key/output sizes to provide at least 128-bit post-quantum security under Grover's algorithm. Includes AES-256, ChaCha20-Poly1305, SHA-256/384/512, HMAC-SHA-256+. No migration required. |
| `post-quantum` | None | NIST-standardised or NIST-candidate post-quantum algorithms. Includes ML-KEM (FIPS 203), ML-DSA (FIPS 204), SLH-DSA (FIPS 205), FN-DSA, and candidates such as CRYSTALS-Kyber, sntrup761, NTRU. |
| `hybrid` | None | Combinations of a classical key exchange with a post-quantum KEM (e.g. X25519MLKEM768, SecP256r1MLKEM768). Provides a hedge against both classical and quantum attacks. |
| `unknown` | High | Algorithm name did not match any catalog entry. Manual review required. |

## Data-driven catalog

The classification rules are stored in `tor/VECTOR-Score/data/algorithm-risk-catalog.yaml`. Each entry maps algorithm name patterns (exact strings or Python regular expressions) and optional key-size ranges to a classification, risk score, rationale, migration recommendation, and normative references. Extending coverage requires only editing the YAML file — no code changes are needed.

## Normative references

- NIST FIPS 203 — ML-KEM (Module-Lattice-Based Key-Encapsulation Mechanism Standard)
- NIST FIPS 204 — ML-DSA (Module-Lattice-Based Digital Signature Standard)
- NIST FIPS 205 — SLH-DSA (Stateless Hash-Based Digital Signature Standard)
- NIST SP 800-131A Rev.2 — Transitioning the Use of Cryptographic Algorithms and Key Lengths
- BSI TR-02102-1 — Cryptographic Mechanisms: Recommendations and Key Lengths (2024)
- ANSSI — Recommandations de sécurité relatives aux mécanismes cryptographiques (2021)

## Integration with VECTOR-Code and VECTOR-Network

VECTOR-Score is compatible with CBOM output from both VECTOR-Code (component type `crypto-asset`) and VECTOR-Network (component type `cryptographic-asset`). The scorer handles both type variants transparently.

Typical pipeline:

```
VECTOR-Code / VECTOR-Network
        │
        ▼  <target>_cbom.json
  VECTOR-Score
        │
        ├── <target>_cbom_scored.json   (annotated CBOM)
        └── <target>_cbom_risk_report.md
```
