# Understanding CBOM output

Both VECTOR-Code and VECTOR-Network produce output files in the Cryptographic Bill of Materials (CBOM) format — a CycloneDX extension for cryptographic asset inventories. This page explains how to read and use those files.

## File format

CBOM files are JSON. They follow the CycloneDX CBOM 1.0 extension schema (`bomFormat: "CBOM"`, `specVersion: "1.4-cbom-1.0"`).

## Top-level structure

```json
{
  "$schema": "...",
  "bomFormat": "CBOM",
  "specVersion": "1.4-cbom-1.0",
  "serialNumber": "urn:uuid:<uuid>",
  "version": 1,
  "metadata": { ... },
  "components": [ ... ],
  "dependencies": [ ... ]
}
```

| Field | Description |
|-------|-------------|
| `bomFormat` | Always `"CBOM"` |
| `specVersion` | Always `"1.4-cbom-1.0"` (CycloneDX CBOM extension) |
| `serialNumber` | Unique identifier for this CBOM document |
| `metadata` | Information about the analyzed application and the tools used |
| `components` | Array of cryptographic assets found — this is the main content |
| `dependencies` | Relationships between components (e.g., which algorithms a protocol component uses) |

## Metadata section

### VECTOR-Code metadata

```json
"metadata": {
  "component": {
    "bom-ref": "<uuid>",
    "name": "pyca-cryptography",
    "type": "application"
  },
  "timestamp": "2026-04-11T10:31:10.891396+00:00",
  "tools": [
    { "name": "cyclonedx-python-lib", "vendor": "CycloneDX", "version": "4.2.2" },
    { "name": "CodeQL", "vendor": "GitHub", "version": "2.25.1" }
  ]
}
```

- `metadata.component.name` is the value passed to `--name` when running `main.py` (default: `"application"`).
- `metadata.tools` lists `cryptobom-forge`/`cyclonedx-python-lib` and CodeQL with their versions.

### VECTOR-Network metadata

Network CBOMs include server-specific context in `metadata.properties`:

```json
"metadata": {
  "component": {
    "name": "example.com:443",
    "type": "application"
  },
  "properties": [
    { "name": "target_ip",     "value": "93.184.216.34" },
    { "name": "target_domain", "value": "example.com" },
    { "name": "target_port",   "value": "443" }
  ]
}
```

For SSH scans, additional properties include the server software (`ssh_software`), operating system hint (`ssh_os`), and the HSH (SSH Host Software Fingerprinting) hash.

## Component types

Every entry in the `components` array is a cryptographic asset. The type of asset is indicated by `cryptoProperties.assetType`:

| `assetType` | What it represents |
|-------------|-------------------|
| `algorithm` | A cryptographic algorithm or primitive (cipher, hash, KEM, signature, etc.) |
| `certificate` | An X.509 certificate or certificate reference |
| `relatedCryptoMaterial` | A key, key pair, IV, nonce, or other cryptographic material |
| `protocol` | A protocol component (e.g., TLS version + cipher suite, SSH version) |

## Algorithm components

Most components are of type `algorithm`. Example from a VECTOR-Code scan:

```json
{
  "bom-ref": "cryptography:algorithm:52ebfcd4-2307-445b-9883-a72bea8983dd",
  "type": "crypto-asset",
  "name": "52ebfcd4-2307-445b-9883-a72bea8983dd",
  "cryptoProperties": {
    "assetType": "algorithm",
    "algorithmProperties": {
      "primitive": "blockcipher",
      "variant": "AES",
      "mode": "other",
      "padding": "unknown",
      "cryptoFunctions": ["encrypt"]
    },
    "detectionContext": [
      {
        "filePath": "src/hazmat/primitives/ciphers/algorithms.py",
        "lineNumbers": [42],
        "additionalContext": "    alg = algorithms.AES(key)\n    mode = modes.XTS(tweak)\n"
      }
    ]
  }
}
```

**Key fields in `algorithmProperties`:**

| Field | Description |
|-------|-------------|
| `primitive` | Cryptographic primitive class: `blockcipher`, `streamcipher`, `hash`, `signature`, `keyagree`, `kem`, `mac`, `kdf`, etc. |
| `variant` | Algorithm name: `AES`, `RSA`, `SHA256`, `ECDH`, `ML-KEM`, etc. |
| `mode` | Mode of operation for block ciphers: `cbc`, `gcm`, `ctr`, `ccm`, `xts`, etc. |
| `padding` | Padding scheme: `pkcs1v15`, `oaep`, `pss`, `none`, `unknown` |
| `cryptoFunctions` | How the algorithm is used: `encrypt`, `decrypt`, `sign`, `verify`, `keygen`, `digest`, `keyderive`, etc. |

**`detectionContext` (VECTOR-Code only):**  
Shows exactly where in the source code the API call was found — file path, line numbers, and surrounding source code snippet.

## Certificate components

```json
{
  "bom-ref": "cryptography:certificate:<uuid>",
  "type": "crypto-asset",
  "cryptoProperties": {
    "assetType": "certificate",
    "certificateProperties": {
      "certificateAlgorithm": "RSA",
      "certificateFormat": "X.509",
      "issuerName": "",
      "subjectName": ""
    },
    "detectionContext": [ ... ]
  }
}
```

For VECTOR-Network TLS scans, the certificate component includes the actual issuer, subject, and public key size extracted from the server certificate.

## Related crypto material components

These represent keys, key pairs, and similar material:

```json
{
  "cryptoProperties": {
    "assetType": "relatedCryptoMaterial",
    "relatedCryptoMaterialProperties": {
      "relatedCryptoMaterialType": "privateKey",
      "size": 256
    },
    "detectionContext": [ ... ]
  }
}
```

`relatedCryptoMaterialType` values include: `privateKey`, `publicKey`, `secretKey`, `keyPair`.

## Protocol components (VECTOR-Network)

Network CBOMs include protocol-level components that tie together an algorithm suite:

```json
{
  "cryptoProperties": {
    "assetType": "protocol",
    "protocolProperties": {
      "type": "tls",
      "version": "1.3",
      "cipherSuites": [
        {
          "name": "TLS_AES_256_GCM_SHA384",
          "algorithms": [
            "ref-to-AES-256-GCM-component",
            "ref-to-SHA384-component"
          ]
        }
      ]
    }
  }
}
```

## Identifying quantum-vulnerable entries

The following entries in a CBOM indicate algorithms at risk from quantum attacks:

**Broken by Shor's algorithm (quantum computers):**

| What to look for | Example `variant` values |
|-----------------|--------------------------|
| RSA (any use) | `RSA` |
| Elliptic curve key agreement | `ECDH`, `ECDHE` |
| Elliptic curve signatures | `ECDSA`, `EdDSA` |
| Classic Diffie-Hellman | `DH`, `DHE` |
| DSA | `DSA` |

**Weakened by Grover's algorithm (security halved):**

| What to look for | Risk |
|-----------------|------|
| AES-128 | Effective security drops to ~64 bits |
| SHA-256 | Effective preimage resistance drops to ~128 bits |
| HMAC-SHA-256 | Same as SHA-256 |

**Post-quantum safe (no known quantum attack):**

| `variant` | Algorithm |
|-----------|-----------|
| `ML-KEM` | NIST PQC standard (formerly Kyber) |
| `ML-DSA` | NIST PQC standard (formerly Dilithium) |
| `AES-256` | Sufficient margin against Grover |
| `SHA-384`, `SHA-512` | Sufficient margin against Grover |

## Using the CBOM

**Reviewing manually:**  
Open the JSON file in any text editor. Search for `"variant"` to enumerate all algorithm types present. The `detectionContext.filePath` field (VECTOR-Code) tells you where each algorithm is used in source code.

**Loading into CBOMkit:**  
CBOMkit (planned future integration) can ingest CycloneDX CBOM files for risk scoring and visualization.

**Counting findings:**

```bash
# Count total components
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d['components']))" crypto-python-cbom.json

# List all unique algorithm variants
python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
variants = set()
for c in d['components']:
    v = c.get('cryptoProperties', {}).get('algorithmProperties', {}).get('variant', '')
    if v:
        variants.add(v)
for v in sorted(variants):
    print(v)
" crypto-python-cbom.json
```
