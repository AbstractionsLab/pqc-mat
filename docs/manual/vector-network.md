# VECTOR-Network reference

VECTOR-Network scans live network services (SSH and TLS) to enumerate their cryptographic configurations and produce a Cryptographic Bill of Materials (CBOM).

> **Web interface:** VECTOR-Network is also accessible through the browser-based GUI. See [Web interface](./start.md#web-interface) in the quick start guide.

## Pipeline overview

```
Target host:port
        │
        ▼
  zgrab2 ssh  (SSH)          testssl.sh  (TLS)
        │                          │
        │  raw JSON output          │  raw JSON output
        ▼                          ▼
  zgrab2_to_cbom.py         testssl_to_cbom.py
        │                          │
        ▼                          ▼
  <target>_ssh_cbom.json    <target>_tls_cbom.json
  (CycloneDX 1.6 CBOM)      (CycloneDX 1.6 CBOM)
```

## Prerequisites

- The target host must be reachable from the container on the specified port.
- No authentication is supported. VECTOR-Network inspects only the unauthenticated portion of the handshake (SSH) or the full cipher suite negotiation (TLS). Targets that block unauthenticated connections may produce empty or incomplete results.
- **Legal and ethical requirement**: Only scan systems you are authorized to scan. Network scanning without authorization may violate laws and terms of service.

## Invocation

```bash
vector network --protocol <ssh|tls> --target <host> --port <port>
```

### CLI mode

All three arguments must be provided together:

```bash
vector network --protocol tls --target example.com --port 443
vector network --protocol ssh --target github.com --port 22
```

### Arguments

| Argument | Required | Values | Default |
|----------|----------|--------|---------|
| `--protocol` | Yes | `ssh`, `tls` | — |
| `--target` | Yes | domain name or IP address | — |
| `--port` | Yes | 1–65535 | — |

### Interactive mode

Running `tor/vector_network/main.py` directly without arguments launches an interactive menu:

```
Select protocol
  1. SSH (port 22)
  2. TLS (port 443)
  3. Custom
Choice (1/2/3): _
```

Options 1 and 2 prompt for a target hostname or IP address. Option 3 prompts for protocol, target, and port number.

## Output files

Output files are written to the current working directory (wherever `main.py` is invoked from, or the directory the `vector network` command is run from).

| Scan type | Raw scan output | CBOM output |
|-----------|----------------|-------------|
| SSH | `<target>_ssh_scan.json` | `<target>_ssh_cbom.json` |
| TLS | `<target>_tls_scan.json` | `<target>_tls_cbom.json` |

Target names are sanitized for use in file names (dots and colons replaced with underscores).

## SSH scanning

SSH scanning is performed by [ZGrab2](https://github.com/zmap/zgrab2).

**What is scanned:**  
ZGrab2 initiates an SSH handshake and records the algorithm lists advertised by the server in its `SSH_MSG_KEXINIT` message. No authentication is attempted.

**External tool:** `zgrab2` must be on `PATH` (pre-installed in the container).

**Timeout:** 300 seconds.

**What is captured in the CBOM:**

| Field | Description |
|-------|-------------|
| Protocol version | SSH-1.x or SSH-2.0, server banner string |
| Server software | Extracted from banner (e.g., `OpenSSH_9.2p1`) |
| Key exchange algorithms | All KEX algorithms offered by the server |
| Host key algorithms | All host key algorithm types offered |
| Encryption ciphers | Client-to-server and server-to-client cipher lists |
| MAC algorithms | Client-to-server and server-to-client MAC lists |
| Compression | Compression algorithms offered |
| Algorithm selection | The algorithm negotiated for each category |
| Host key fingerprint | SHA-256 fingerprint of the server's public host key |

**Algorithm mapping:**  
Each SSH algorithm name is looked up in CSV mapping files (`ssh-mapping/*.csv`) to determine its cryptographic primitives (e.g., `curve25519-sha256` → Curve25519 key agreement + SHA-256 hash). Algorithm names that do not match any entry in the mapping files are included in the CBOM with a warning but without primitive decomposition.

## TLS scanning

TLS scanning is performed by [testssl.sh](https://testssl.sh).

**What is scanned:**  
testssl.sh connects to the target and systematically probes all cipher suites and protocol versions supported by the server, including the full certificate chain.

**External tool path:** Hardcoded to `/home/vector/tools/testssl.sh/testssl.sh`. This path is not configurable via CLI.

**Timeout:** 600 seconds.

**What is captured in the CBOM:**

| Field | Description |
|-------|-------------|
| Protocol versions | Which of SSLv2, SSLv3, TLS 1.0, 1.1, 1.2, 1.3 are offered |
| Cipher suites | All offered cipher suites per TLS version |
| Cipher decomposition | Each cipher suite broken into Kx, Au, Enc, Mac components |
| Elliptic curves | All named groups/curves supported for key exchange |
| DH groups | Finite-field DH groups offered (ffdhe2048–ffdhe8192, custom) |
| Post-quantum KEMs | Hybrid and standalone KEMs offered (ML-KEM, Kyber draft) |
| Signature algorithms | TLS 1.2 and TLS 1.3 signature algorithm lists |
| Certificate signature | Algorithm and hash used to sign the server certificate |
| Certificate public key | Public key algorithm and size (e.g., RSA-2048, EC P-256) |

**Cipher decomposition:**  
Each cipher suite name is parsed against `tls-mapping/cipher-mapping.txt`, which maps IANA and OpenSSL cipher suite names to their algorithm components. Hybrid KEM cipher suites (e.g., `X25519MLKEM768`) are further decomposed into their classical EC component and post-quantum KEM component. Cipher suites not found in the mapping file are included in the CBOM without decomposition, and a warning is printed to the console.

## Standalone converter usage

If you already have raw scan output (e.g., from a previous scan or from running the tools manually), you can regenerate the CBOM without re-scanning:

```bash
cd tor/vector_network

# Re-process an SSH scan result
python3 zgrab2_to_cbom.py <filename>_ssh_scan.json

# Re-process a TLS scan result
python3 testssl_to_cbom.py <filename>_tls_scan.json
```

The converter scripts validate the input file structure before processing. If the file is missing expected fields, an error is printed and no CBOM is generated.

## Known limitations

| Limitation | Detail |
|-----------|--------|
| Hardcoded testssl.sh path | `/home/vector/tools/testssl.sh/testssl.sh` — not configurable via CLI |
| No authentication | Only unauthenticated handshake data is accessible |
| Single target per run | No batch or range scanning |
| No proxy support | The container must have direct network access to the target |
| Static mapping files | `ssh-mapping/*.csv` and `tls-mapping/cipher-mapping.txt` are maintained manually; newly introduced algorithm names may not be recognized |
| Offers only | Both tools report what the server *offers*; client negotiation behavior is not modeled |
| ZGrab2 timeout | 300 s — unresponsive targets may cause a long wait before an error is reported |
| testssl.sh timeout | 600 s — large or slow TLS servers may time out before all cipher suites are tested |
