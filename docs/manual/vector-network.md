# VECTOR-Network reference

VECTOR-Network scans a live SSH or TLS service to list the cryptography it offers (key exchange, ciphers, MACs, certificates, post-quantum KEMs) and produces a Cryptographic Bill of Materials (CBOM) in CycloneDX 1.6 format.

It can be run from the command line (detailed below) or from the [web GUI](./start.md#3-use-the-web-gui).

> **Only scan systems you are authorized to scan.** Network scanning without permission may violate laws and terms of service.

## Running a scan

| Mode | Command |
|---|---|
| Standalone container (host terminal) | `./vector.sh cli network --protocol <ssh\|tls> --target <host> --port <port> [--output <dir>]` |
| Dev Container | `vector network --protocol <ssh\|tls> --target <host> --port <port> [--output <dir>]` |

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--protocol` | Yes | — | `ssh` or `tls` |
| `--target` | Yes | — | Domain name or IP address |
| `--port` | Yes | — | Port number (1–65535), e.g. `22` for SSH, `443` for HTTPS |
| `--output` | No | `output` | Output directory. With `vector.sh`, a directory given here must already exist on the host; if omitted, `./output` is created in the current directory |

### Examples

```bash
# Standalone container
./vector.sh cli network --protocol tls --target example.com --port 443 --output results

# Dev Container
vector network --protocol ssh --target github.com --port 22 --output results
```

### Console output

```
Scanning github.com:22 (SSH)
  Scan saved: results/github_com_ssh_scan.json

Generating CBOM
CBOM saved: github.com_ssh_cbom.json
Components: 37

Completed
```

TLS scans also print the live testssl.sh progress, which can take several minutes.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Scan completed and a CBOM was generated |
| `1` | Scan failed: invalid port, target unreachable or refused the connection, DNS failure, timeout, or CBOM generation failed |

## How it works

```
Target host:port
        │
        ▼
  zgrab2 ssh  (SSH)          testssl.sh  (TLS)
        │                          │
        │  raw JSON output         │  raw JSON output
        ▼                          ▼
  zgrab2_to_cbom.py         testssl_to_cbom.py
        │                          │
        ▼                          ▼
  <target>_ssh_cbom.json    <target>_tls_cbom.json
  (CycloneDX 1.6 CBOM)      (CycloneDX 1.6 CBOM)
```


| | SSH | TLS |
|---|---|---|
| **Scanner** | [ZGrab2](https://github.com/zmap/zgrab2) | [testssl.sh](https://testssl.sh) |
| **What it does** | Starts an SSH handshake and records the algorithms the server advertises; no login is attempted | Probes every protocol version and cipher suite the server supports, and reads its certificate |
| **Timeout** | 5 minutes | 10 minutes |

The raw scanner output is then converted into a CBOM. Each algorithm or cipher suite is broken down into its cryptographic building blocks (e.g. `curve25519-sha256` → Curve25519 key agreement + SHA-256), using mapping tables shipped with VECTOR.

### What the CBOM contains

| SSH | TLS |
|---|---|
| Protocol version and server software (e.g. `OpenSSH_9.2p1`) | Offered protocol versions (SSLv2 to TLS 1.3) |
| Key exchange algorithms | Cipher suites per TLS version, split into key exchange, authentication, encryption, and MAC |
| Host key algorithms and SHA-256 host key fingerprint | Elliptic curves and finite-field DH groups |
| Encryption ciphers and MAC algorithms (both directions) | Post-quantum and hybrid KEMs (e.g. `X25519MLKEM768`) |
| Compression algorithms | Signature algorithms |
| The algorithm selected in each category | Certificate signature algorithm and public key (e.g. RSA-2048, EC P-256) |

Algorithms missing from the mapping tables still appear in the CBOM, but without the breakdown; TLS scans print a warning for each.

## Output

Two files are written to the output directory:

| | Raw scanner output | CBOM |
|---|---|---|
| SSH | `<target>_ssh_scan.json` | `<host>_ssh_cbom.json` |
| TLS | `<target>_tls_scan.json` | `<host>_tls_cbom.json` |

- In the raw output name, every character other than letters, digits, and `-` becomes `_` — `github.com` gives `github_com_ssh_scan.json`.
- In the CBOM name, the host keeps its dots — `github.com_ssh_cbom.json`.

Running the same scan again overwrites both files. To assess quantum risk, pass the CBOM to [VECTOR-Score](./vector-score.md). See [Understanding CBOM output](./cbom-output.md) for the file format.

## Re-generating a CBOM from an existing scan

In the Dev Container, a CBOM can be rebuilt from a raw scan file without scanning again, for example after the mapping tables are updated. The CBOM is written to the current directory:

```bash
python /home/vector/vector-project/tor/vector_network/zgrab2_to_cbom.py  <target>_ssh_scan.json
```
or
```bash
python /home/vector/vector-project/tor/vector_network/testssl_to_cbom.py <target>_tls_scan.json
```

## Known limitations

- **One target per run** — no batch or address-range scanning.
- **No authentication** — SSH scans see only what the server advertises before login.
- **Offered, not used** — the CBOM lists what the server offers, not what a particular client would negotiate.
- **Direct network access** — the container must reach the target; proxies are not supported.
- **Timeouts** — unresponsive SSH targets can take up to 5 minutes to fail; large or slow TLS servers may hit the 10-minute limit before every cipher suite is tested.
- **Mapping tables** — newly introduced algorithm names may not be recognized until the tables are updated.
