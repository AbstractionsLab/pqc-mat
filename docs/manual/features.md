# VEC**TOR** — Feature matrix

| Aspect | Supported | Note |
|--------|-----------|------|
| **Source languages (VECTOR-Code)** | Python, C, C++ | Java has no CodeQL queries — not supported |
| **Network protocols (VECTOR-Network)** | TLS, SSH | No additional protocols planned at this stage |
| **Deployment** | Docker Dev Container | Local install without Docker is not supported |
| **Web interface** | Available | Flask-based browser UI; supports VECTOR-Code and VECTOR-Network scans with live output terminal; alternative to CLI |
| **Output format** | CycloneDX 1.6 CBOM (JSON) | VECTOR-Code produces a unified CBOM per project (for repositories with code in multiple programming languages); VECTOR-Network produces one CBOM per scan |
| **Architecture** | Static code analysis (VECTOR-Code) + live network scanning (VECTOR-Network) + quantum risk scoring (VECTOR-Score) | Tools operate independently |
| **Risk scoring** | 6 risk classifications: `quantum-vulnerable`, `classically-deprecated`, `non-hybrid`, `quantum-safe`, `hybrid`, `unknown` | Data-driven YAML catalog; covers NIST, BSI TR-02102, ANSSI |
| **Risk scoring input** | Any CycloneDX 1.6 CBOM JSON | Compatible with VECTOR-Code and VECTOR-Network output |

---

## VECTOR's key value over existing tools

### The overall pipeline

VECTOR evaluates post-quantum readiness by answering two questions: which cryptography does a system use, and how exposed is it to quantum attacks? VECTOR-Code looks at what the code *calls* and VECTOR-Network inspects what a server *offers* on the network. Both produce a CycloneDX 1.6 CBOM in the same format, which VECTOR-Score rates against a catalog of NIST, BSI and ANSSI guidance to produce a risk report.

```
source code 
(local or GitHub) ──► VECTOR-Code ────┐
                                      ├──► CBOM ──► VECTOR-Score 
                                                        |
                                                        v
                                                    risk report
server 
(TLS or SSH host) ──► VECTOR-Network ─┘
```

Each step relies on established open-source tools and VECTOR's value lies in connecting rather than reimplementing them:

- **One inventory format** for code and network findings, so both can be scored, compared and archived the same way.
- **One container** with every tool installed at a pinned version, so every scan runs with the same tool versions and there is nothing to install beyond Docker.
- **Two ways to work**: the `vector` command line, for scripts and CI/CD pipelines, and a web interface that runs scans from the browser, scores them automatically and shows the findings by risk class, with scan history and CBOM and report downloads. No command line is needed to get from a scan to a risk report.

### VECTOR-Code

VECTOR-Code combines three existing tools — `cloc` (language detection), CodeQL with queries from [github/codeql](https://github.com/github/codeql) (detection of cryptographic API calls), and `cryptobom-forge` (conversion to CBOM) — into a single command. Its advantages over running these tools by hand include:

- **Any source, one step**: accepts a local directory or a GitHub URL, which it clones, scans and cleans up.
- **Mixed-language projects**: Python and C/C++ are detected and scanned in the same run, and the results are merged into one CBOM.
- **Standard-conformant output**: the CBOM is normalised to valid CycloneDX 1.6, ready for VECTOR-Score or other CBOM tools.

The closest alternative is [CBOMkit](https://github.com/PQCA/cbomkit) (open-source, maintained by PQCA), which targets the same use case and also offers visualization and quantum risk scoring. VECTOR-Code has the advantage of sharing output format with VECTOR-Network, which then VECTOR scores jointly.

### VECTOR-Network

VECTOR-Network scans TLS endpoints with testssl.sh and SSH endpoints with ZGrab2. The uderlying scanners report what a server offers, but not as a cryptographic inventory, and no widely available tool converts their output to CBOM. VECTOR-Network's parsers fill this gap:

- **Cipher names to algorithms**: testssl.sh and ZGrab2 report suite and algorithm names (e.g. TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384). VECTOR-Network turns each one into separate CBOM entries per algorithm (ECDHE, RSA, AES-256-GCM, SHA-384), with primitive, mode and key size.
- **Hybrid key exchanges split**: the scanners report a hybrid as a single name (e.g. X25519MLKEM768, mlkem768x25519-sha256). VECTOR-Network splits apart its classical and post-quantum parts, enabling the independent scoring of each part.
- **Ready for scoring**: the result is a CycloneDX 1.6 CBOM that VECTOR-Score can automatically rate, removing the need of manual interpretation of scanner output.

---

## VECTOR-Code

VECTOR-Code uses CodeQL to analyze and detect cryptographic API calls in source code. Detection is driven by the [standard CodeQL queries](https://github.com/github/codeql) and it operates on three supported languages.

### Detected algorithm categories

| Category | Examples detected |
|----------|------------------|
| Symmetric ciphers | AES (all modes), ChaCha20, 3DES, Blowfish, RC4 |
| Asymmetric algorithms | RSA, DSA, ECDSA, EdDSA, DH, ECDH |
| Hash functions | SHA-1, SHA-2 family, MD5, SHA-3 |
| MAC algorithms | HMAC, CMAC |
| Key derivation | PBKDF2, HKDF, bcrypt, scrypt |
| Random number generation | Calls to cryptographic RNG APIs |

### Language support

| Language | Status | CodeQL queries available |
|----------|--------|--------------------------|
| Python | Supported | Yes |
| C | Supported | Yes (uses `cpp` query pack) |
| C++ | Supported | Yes (uses `cpp` query pack) |
| Java | Not supported | No queries available — planned for a future release |

Mixed-language projects are analyzed per language, i.e., one CodeQL database and one CBOM per language are created.

### Limitations

- For a supported language to be considered in the analysis, at least 5% of the total lines of code in the project must be in such a language (configurable threshold).
- To avoid the need of a build system, the analyzed project is not built (`--build-mode=none`). Only source files are analyzed; object code and binaries are not.
- C/C++: the project's include paths are not known. The C/C++ queries model OpenSSL only, and the image installs the OpenSSL headers, so `<openssl/...>` includes resolve; APIs specific to OpenSSL forks and code depending on project headers found through `-I` flags may still be missed. See [Header resolution for C and C++](vector-code.md#header-resolution-for-c-and-c).
- Detection accuracy depends on CodeQL query coverage; direct use of cryptographic constants (without API calls) may not be detected.
- CodeQL query paths are fixed to the container environment; the tool cannot be pointed at a custom query directory via CLI.

---

## VECTOR-Network — TLS

VECTOR-Network uses testssl.sh to enumerate all cipher suites, protocol versions, and certificate properties offered by a TLS endpoint.

### TLS features

| Feature | What goes into the CBOM |
|---------|------------------------|
| Protocol versions | SSLv2, SSLv3, TLS 1.0, 1.1, 1.2, 1.3 (offered/not offered) |
| Cipher suites | Full enumeration per TLS version, decomposed into individual algorithm components |
| Key exchange (Kx) | ECDHE, ECDH, DHE, DH, RSA-KeyTransport, PSK, DHE-PSK, ECDHE-PSK, RSA-PSK, SRP, KRB5, GOST, CECPQ1 |
| Authentication (Au) | RSA, ECDSA, DSA, GOST-94, GOST-2001, KRB5 |
| Encryption (Enc) | AES (CBC/GCM/CCM/CCM-8), ChaCha20-Poly1305, 3DES-EDE, Camellia (CBC/GCM), SEED, IDEA, RC4, RC2, DES, ARIA (CBC/GCM), GOST-28147 |
| MAC | SHA-1, SHA-256, SHA-384, MD5, GOST-28147-IMIT, GOST-94, GOST-R-34.11, Streebog-256 |
| Elliptic curves | NIST (P-160 to P-521), Brainpool, Montgomery (X25519, X448), SEC binary, GOST (GC256/GC512), SM2 |
| DH groups | ffdhe2048 to ffdhe8192, custom groups (with bit size) |
| Post-quantum KEMs | Standalone: ML-KEM-512/768/1024 — Hybrid (decomposed into EC + KEM): X25519Kyber768Draft00, SecP256r1MLKEM768, X25519MLKEM768, SecP384r1MLKEM1024 |
| Signature algorithms | TLS 1.2 and TLS 1.3 handshake signature algorithms |
| Certificate signature | Algorithm used to sign the certificate (e.g., SHA256-RSA, SHA384-ECDSA) |
| Certificate public key | Key type and size (e.g., RSA-2048, EC-256 with curve name) |

### TLS limitations

- Scans a single target:port per invocation; no bulk or range scanning.
- Enumerates what the server *offers*, not what clients actually negotiate.
- Requires the target to be reachable from the container; no proxy support.
- No authentication — scanning targets that require client certificates is not supported.
- testssl.sh path is fixed to the container environment.

---

## VECTOR-Network — SSH

VECTOR-Network uses ZGrab2 to perform an SSH handshake and record the algorithms offered by the server.

### SSH features

| Feature | What goes into the CBOM |
|---------|------------------------|
| Protocol version | SSH-1.x / SSH-2.0 and server banner |
| Key exchange algorithms | Full list offered by server (e.g., curve25519-sha256, diffie-hellman-group14-sha256) |
| Host key algorithms | Algorithms for server authentication (e.g., ssh-rsa, ecdsa-sha2-nistp256, ssh-ed25519) |
| Encryption ciphers | Client-to-server and server-to-client cipher lists |
| MAC algorithms | Client-to-server and server-to-client MAC lists |
| Compression | Compression algorithms offered |
| Host key fingerprint | SHA-256 fingerprint of the server's public host key |
| Algorithm selection | Negotiated (selected) algorithm for each category |
| Server software | SSH daemon software and version from banner (e.g., OpenSSH_9.2) |

### SSH limitations

- Reads algorithm *offers* from the SSH handshake; does not log in or inspect authorized keys/config files.
- No authentication — only the unauthenticated portion of the SSH handshake is inspected.
- Single target per invocation.
- ZGrab2 timeout: 300 seconds.
