# Installation

VECTOR runs in a Docker container. Choose one of two setups:

| | Requires | Best for |
|---|---|---|
| **Standalone container** | Docker, Bash | Running scans, the web GUI, CI/CD pipelines |
| **Dev Container** | Docker, VS Code + [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension | Developing VECTOR, exploring output |

## Requirements

- [Docker](https://www.docker.com/) 20.10 or later, installed and running.
- **x86_64 host** for VECTOR-Code. The image also builds on ARM (e.g. Apple Silicon), but without the CodeQL CLI, so only VECTOR-Network and VECTOR-Score work there.
- **Internet access** to build the image, and at run time for GitHub URLs and network scans.

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 4 GB | 8 GB |
| Disk (image and tools) | 6 GB | 10 GB |
| Disk per CodeQL database | ~100 MB, depending on project size | — |

## Standalone container

From the repository root:

```bash
chmod +x vector.sh   # first time only
./vector.sh build    # build the image
```

The first build downloads all tools and precompiles the CodeQL queries, thus, it can take several minutes (~4-5); `./vector.sh` and `./vector.sh cli` also build the image automatically if it doesn't exist yet.

**After updating the code** (e.g. `git pull`), rebuild with `./vector.sh build` as the image is not rebuilt automatically.

## Dev Container

1. Open the repository folder in VS Code.
2. Click **Reopen in Container** when prompted, or run `Dev Containers: Reopen in Container` from the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).
3. When the build finishes, run
```bash
poetry install
poetry shell
```

**After updating the code**, run `poetry install` in the container terminal, or `Dev Containers: Rebuild Container` if the `Dockerfile` changed.

## What the image contains


| For component | Bundled dependencies |
|---|---|
| **All** | Python 3.12, the `vector` CLI and its Poetry dependencies |
| **VECTOR-Code** | CodeQL CLI and the CodeQL cryptography queries (x86_64 only), cloc, cryptobom-forge, and the demo project ([pyca/cryptography](https://github.com/pyca/cryptography) 49.0.0) |
| **VECTOR-Network** | testssl.sh, ZGrab2 |
| **VECTOR-Score** | PyYAML (Poetry dependency) |
| **VECTOR-GUI** | Flask (Poetry dependency) |

## Verifying the installation

Standalone container:

```bash
./vector.sh cli                        # vector CLI help
mkdir -p results && ./vector.sh cli code demo --output results    # demo scan (x86_64 only)
```

Dev Container terminal:

```bash
vector --help
codeql --version
cryptobom --help
zgrab2 --help
/home/vector/tools/testssl.sh/testssl.sh --version
```

Next: [Quick start](./start.md).

## Troubleshooting

| Problem | Solution |
|---|---|
| Image build fails | Check that Docker is running, there is enough free disk space, and the internet is reachable; then run `./vector.sh build` (or `Dev Containers: Rebuild Container`) again. |
| `codeql: command not found` | The host is not x86_64, so CodeQL was not installed. VECTOR-Code needs an x86_64 host. |
| `vector: command not found` in the Dev Container | Run `poetry install` in `/home/vector/vector-project`. |
| Code changes have no effect (standalone) | Rebuild the image with `./vector.sh build`. |

See [Troubleshooting](./troubleshooting.md) for scan-related problems.
