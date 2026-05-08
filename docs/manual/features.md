# TOR — Feature matrix

| Aspect | Supported | Note |
|--------|-----------|------|
| **Source languages (VECTOR-Code)** | Python, C, C++ | Java has no CodeQL queries — not supported |
| **Network protocols (VECTOR-Network)** | TLS, SSH | No additional protocols planned at this stage |
| **Deployment** | Docker Dev Container | Local install without Docker is not supported |
| **Output format** | CycloneDX 1.6 CBOM (JSON) | One CBOM file per language (code) or per scan (network) |
| **Architecture** | Static code analysis (VECTOR-Code) + live network scanning (VECTOR-Network) + quantum risk scoring (VECTOR-Score) | Tools operate independently |
| **Risk scoring** | 7 risk classifications: `quantum-vulnerable`, `quantum-weakened`, `classically-deprecated`, `quantum-safe`, `post-quantum`, `hybrid`, `unknown` | Data-driven YAML catalog; covers NIST, BSI TR-02102, ANSSI |
| **Risk scoring input** | Any CycloneDX 1.6 CBOM JSON | Compatible with VECTOR-Code and VECTOR-Network output |

---

## Comparison with existing tools

### VECTOR-Code

VECTOR-Code orchestrates three existing tools — `cloc`, CodeQL (with [Santandersecurityresearch](https://github.com/santandersecurityresearch/codeql-crypto) queries), and `cryptobom-forge` — into a single command. An analyst could replicate this with a shell script, or use [CBOMkit](https://github.com/PQCA/cbomkit) (open-source, maintained by PQCA), which targets the same use case and additionally provides visualization and quantum risk scoring. VECTOR-Code's contribution is automating the pipeline within a consistent, containerized workflow whose output is aligned with VECTOR-Network's CBOM format.

### VECTOR-Network

No widely available tool converts testssl.sh or ZGrab2 output to CycloneDX CBOM format. VECTOR-Network's parsers fill this gap. The specific added value over running the scanners directly:

- **Cipher suite decomposition**: each cipher suite is broken into individual algorithm components (key exchange, authentication, encryption, MAC) as separate CBOM entries, rather than recording the composite cipher string.
- **Post-quantum KEM detection**: standalone ML-KEM-512/768/1024 entries are captured when offered by the server.
- **Hybrid KEM decomposition**: hybrid schemes (X25519Kyber768Draft00, SecP256r1MLKEM768, X25519MLKEM768, SecP384r1MLKEM1024) are decomposed into their constituent EC and KEM components.

Running testssl.sh or ZGrab2 directly produces raw scanner output that requires manual interpretation to extract a structured cryptographic inventory; VECTOR-Network automates this conversion step.

---

## VECTOR-Code

VECTOR-Code uses CodeQL to analyze source code and detect cryptographic API calls. It operates on three supported languages.

### Detected algorithm categories

| Category | Examples detected |
|----------|------------------|
| Symmetric ciphers | AES (all modes), ChaCha20, 3DES, Blowfish, RC4 |
| Asymmetric algorithms | RSA, DSA, ECDSA, EdDSA, DH, ECDH |
| Hash functions | SHA-1, SHA-2 family, MD5, SHA-3 |
| MAC algorithms | HMAC, CMAC |
| Key derivation | PBKDF2, HKDF, bcrypt, scrypt |
| Random number generation | Calls to cryptographic RNG APIs |

Detection is driven by CodeQL queries maintained by [Santandersecurityresearch](https://github.com/santandersecurityresearch/codeql-crypto). Results reflect which APIs are *called* in the source code, not which algorithms are *negotiated* at runtime.

### Language support

| Language | Status | CodeQL queries available |
|----------|--------|--------------------------|
| Python | Supported | Yes |
| C | Supported | Yes (uses `cpp` query pack) |
| C++ | Supported | Yes (uses `cpp` query pack) |
| Java | Not supported | No queries available — planned for a future release |

Mixed-language projects are analyzed per language: one CodeQL database and one CBOM per language.

### Limitations

- Requires the project to contain at least 5% of a supported language by lines of code (configurable threshold).
- Uses `--build-mode=none`: compiled artifacts are not required, but compiled code is not analyzed — only source text.
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
