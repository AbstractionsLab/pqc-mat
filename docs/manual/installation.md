# Installation

## Requirements

### Host system

- [Docker](https://www.docker.com/) 20.10 or later, installed and running
- [VS Code](https://code.visualstudio.com/) with the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension (v0.300+)
- x86_64 host architecture — the CodeQL CLI has no ARM64 build; the container will not function on Apple Silicon or ARM servers

### Resources

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 4 GB | 8 GB |
| Disk (container image + tools) | 6 GB | 10 GB |
| Disk per CodeQL database | ~100 MB | — |
| Internet access | Required at build time | — |

## Installation instructions

TOR runs inside a VS Code Dev Container. The container build installs most dependencies automatically.

1. Open the project root folder in VS Code.
2. When prompted, click **Reopen in Container**, or run `Dev Containers: Reopen in Container` from the Command Palette (`Ctrl+Shift+P`).
3. Wait for the container to build (typically 5–15 minutes on first run).

The container automatically installs:

- Python 3.11, Poetry, Go 1.24
- CodeQL CLI and CodeQL cryptographic queries (Santandersecurityresearch)
- testssl.sh, ZGrab2, cloc

### Installing cryptobom-forge (required — manual step)

`cryptobom-forge` is **not** installed automatically. It is distributed as a wheel file bundled with the project. After the container starts, run:

```bash
cd /home/vector/tools
pip install cryptobom_forge-1.1.0-py3-none-any.whl
```

This step is required before using VECTOR-Code. If it is skipped, CBOM generation will fail with a `cryptobom: command not found` error.

## Verifying the installation

Run these commands inside the container to confirm all tools are available:

```bash
vector --help            # VECTOR unified CLI — all three subcommands listed
python3 --version        # Python 3.11.x
codeql --version         # CodeQL CLI x.y.z
cloc --version           # vN.NN
zgrab2 --help            # ZGrab2 usage
cryptobom --help         # cryptobom-forge CLI (only after manual install above)
/home/vector/tools/testssl.sh/testssl.sh --version   # testssl.sh 3.x
```

If `vector` is not found or returns an import error, the Python package has not been installed into the active virtual environment. Run:

```bash
cd /home/vector/vector-project
poetry install
```

This installs the `vector` package and registers the `vector` CLI entry point. The Dev Container build does this automatically, but it may need to be re-run after manually pulling updated code or switching branches.

## Troubleshooting

**Container build fails**
Check that Docker is running and that you have at least 6 GB of free disk space. Re-run the build with `Dev Containers: Rebuild Container`.

**`codeql: command not found` inside the container**
The CodeQL CLI is placed in `/home/vector/tools/codeql/`. If it is not on `PATH`, add it: `export PATH="/home/vector/tools/codeql:$PATH"`.

**`cryptobom: command not found`**
The manual install step was skipped. Run `pip install /home/vector/tools/cryptobom_forge-1.1.0-py3-none-any.whl`.

**Dev Containers extension not found**
Install it from the VS Code marketplace: search for `ms-vscode-remote.remote-containers`.