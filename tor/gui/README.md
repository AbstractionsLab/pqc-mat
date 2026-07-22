# VECTOR Web Interface

## Running the GUI

### Open the project in the Dev Container

Open the project in VS Code and when prompted click **Reopen in Container**, or run **Dev Containers: Reopen in Container** from the Command Palette (`Ctrl+Shift+P`).

### Start the server

```bash
VECTOR_ROOT=/home/vector/vector-project VECTOR_PORT=5992 python3 tor/gui/app.py
```

### Open in browser

Forward port `5992` in the VS Code **Ports** panel if not already forwarded, then open:

```
http://localhost:5992
```

## Usage notes

> **Work in progress:** input paths and URLs are not yet validated or sanitized. Use with caution and only in trusted environments.

- **Network scan target:** enter only the domain name (e.g. `github.com`), without a scheme or path. Full URLs such as `https://github.com/AbstractionsLab/pqc-mat` are not supported and will produce unexpected results.
