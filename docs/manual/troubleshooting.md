# Troubleshooting

## Installation

### Container build fails

**Symptom:** The Dev Container build fails or times out.

**Checks:**
- Docker is running: `docker info`
- At least 6 GB of free disk space: `df -h`
- Internet access: the build downloads CodeQL, testssl.sh, ZGrab2, and other tools

**Resolution:** Rebuild with `Dev Containers: Rebuild Container` from the VS Code Command Palette. If the failure is a specific step, check the build log in the VS Code terminal output.

---

### `vector: command not found` or import error

**Symptom:** Running `vector` returns `command not found`, or a subcommand fails with a Python `ModuleNotFoundError`.

**Cause:** The Python package has not been installed into the active virtual environment. The Dev Container build runs `poetry install` automatically, but this step may be missing after a manual code pull or branch switch.

**Resolution:**
```bash
cd /home/vector/vector-project
poetry install
```

Then verify:
```bash
vector --help
```

---

### `cryptobom: command not found`

**Symptom:** VECTOR-Code fails at the "Generating CBOM" step with a command-not-found error.

**Cause:** `cryptobom-forge` is not installed automatically by the container.

**Resolution:**
```bash
cd /home/vector/tools
pip install cryptobom_forge-1.1.0-py3-none-any.whl
```

---

### `codeql: command not found`

**Symptom:** VECTOR-Code fails at the "Creating CodeQL databases" step.

**Resolution:** Add CodeQL to `PATH`:
```bash
export PATH="/home/vector/tools/codeql:$PATH"
```

Add this line to `~/.bashrc` to make it permanent inside the container.

---

### Dev Containers extension not found

**Resolution:** Install from the VS Code marketplace: search for `ms-vscode-remote.remote-containers`.

---

## VECTOR-Code

### No languages detected

**Symptom:**
```
Language detection
  Error: no supported languages detected above the 5% threshold
```

**Causes and resolutions:**

| Cause | Resolution |
|-------|-----------|
| The project is in a language not supported (Java, Go, Rust, etc.) | VECTOR-Code only supports Python, C, and C++ |
| All supported languages are below the 5% threshold | The project contains too little code in supported languages; consider whether the project is the right scope to analyze |
| Wrong path supplied | Verify the path exists and contains source code: `ls <path>` |
| `cloc` not installed | Run `cloc --version`; if missing, install with `sudo apt-get install cloc` |

---

### CodeQL database creation fails

**Symptom:**
```
Creating CodeQL databases
  Error: failed to create database for python
```

**Checks:**
- `codeql --version` returns a version
- The source path is readable: `ls -la <path>`
- Sufficient disk space: each database requires ~100 MB

**Resolution:** Check the error message printed to stderr. Common causes:
- Insufficient disk space
- CodeQL cannot extract the source (check for syntax errors or unsupported Python version)

---

### CodeQL queries not found

**Symptom:**
```
Running crypto queries
  Warning: query path not found for python, skipping
```

**Cause:** The CodeQL crypto queries are missing from `/home/vector/tools/codeql-queries/`.

**Resolution:** Verify the path exists:
```bash
ls /home/vector/tools/codeql-queries/python/ql/src/experimental/cryptography/inventory
ls /home/vector/tools/codeql-queries/cpp/ql/src/experimental/cryptography/inventory
```

If missing, the container may need to be rebuilt (`Dev Containers: Rebuild Container`).

---

### SARIF file is empty or missing

**Symptom:** No CBOM is generated, or `output/results/crypto-<lang>.sarif` is empty.

**Cause:** The CodeQL queries ran successfully but found no cryptographic API calls, or the query run failed silently.

**Checks:**
- Review the SARIF file: it should have `"results": [...]`; an empty array means no findings
- If SARIF is absent, check that the query step reported success in the console output
- Verify the project actually uses cryptographic APIs; purely algorithmic code (sorting, parsing) will produce no findings

---

### CBOM generation fails

**Symptom:**
```
Generating CBOM
  Error: failed to generate CBOM for crypto-python.sarif
```

**Checks:**
- `cryptobom --help` works (confirms installation)
- The SARIF file exists and is valid JSON: `python3 -m json.tool output/results/crypto-python.sarif`

---

## VECTOR-Network

### Target unreachable

**Symptom:** The scan hangs or exits immediately with a connection error.

**Checks:**
- The container has network access: `ping -c 3 <target>`
- The port is open: `nc -zv <target> <port>`
- No firewall is blocking outbound connections from the container

---

### ZGrab2 not found

**Symptom:** SSH scan fails with `zgrab2: command not found`.

**Resolution:** Verify installation:
```bash
which zgrab2
zgrab2 --help
```

If missing, the container needs to be rebuilt.

---

### testssl.sh not found

**Symptom:** TLS scan fails immediately with a "not found" or "no such file" error.

**Resolution:** Verify the path:
```bash
ls -la /home/vector/tools/testssl.sh/testssl.sh
```

If the file is missing, the container needs to be rebuilt. Note: the path is hardcoded and cannot be changed via CLI.

---

### Scan times out

**Symptom:** The scan runs for a long time and then exits with a timeout or empty output.

**Timeouts:**
- SSH (ZGrab2): 300 seconds
- TLS (testssl.sh): 600 seconds

**Causes:**
- Target is responding slowly (high latency, rate limiting, firewall dropping packets)
- TLS scan against a server with a very large number of supported cipher suites

**Resolution:** Verify the target is accessible and responsive before scanning. There is no CLI option to change the timeout — the values are hardcoded in the scripts.

---

### Empty or invalid scan output

**Symptom:** The raw scan file (`_ssh_scan.json` or `_tls_scan.json`) is empty or the CBOM conversion fails with a validation error.

**Causes and resolutions:**

| Symptom | Cause | Resolution |
|---------|-------|-----------|
| Empty JSON file | ZGrab2/testssl.sh produced no output | Check that the service is running on the target port |
| `Error: missing expected field data.ssh.result` | The server closed the connection before completing the handshake | Try scanning a known-responsive server to confirm the tool works |
| `Error: invalid JSON` | The scanner output was corrupted or truncated | Re-run the scan; if persistent, check for disk space issues |

---

### Unknown cipher or algorithm in CBOM

**Symptom:** The CBOM contains components with incomplete information, or the console prints `Warning: unknown cipher suite <name>`.

**Cause:** The cipher suite or algorithm name is not in the static mapping files (`tls-mapping/cipher-mapping.txt`, `ssh-mapping/*.csv`).

**Impact:** The algorithm is still included in the CBOM, but it will not be decomposed into its primitive components. The `algorithmProperties` fields may be empty or set to `unknown`.

**Resolution:** This is a known limitation. Update the mapping files manually to add the new cipher suite, or open an issue in the project repository.
