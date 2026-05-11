#!/usr/bin/env python3
import os
import json
import uuid
import sys
import re
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


KX_MAP = {
    "ECDH":     {"name": "ECDHE",            "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "ECDH/RSA": {"name": "ECDH",             "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "ECDH/ECDSA":{"name": "ECDH",            "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "DH":       {"name": "DHE",              "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "DH/RSA":   {"name": "DH",               "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "DH/DSS":   {"name": "DH",               "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "RSA":      {"name": "RSA-KeyTransport", "primitive": "pke",       "cryptoFunctions": ["encrypt", "decrypt"]},
    "PSK":      {"name": "PSK",              "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "DHEPSK":   {"name": "DHE-PSK",          "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "ECDHEPSK": {"name": "ECDHE-PSK",        "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "RSAPSK":   {"name": "RSA-PSK",          "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "SRP":      {"name": "SRP",              "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "KRB5":     {"name": "KRB5",             "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "GOST":     {"name": "GOST",             "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
    "CECPQ1":   {"name": "CECPQ1",           "primitive": "key-agree", "cryptoFunctions": ["keygen", "keyagree"]},
}

AU_MAP = {
    "RSA":    {"name": "RSA",       "primitive": "signature", "cryptoFunctions": ["sign", "verify"]},
    "ECDSA":  {"name": "ECDSA",     "primitive": "signature", "cryptoFunctions": ["sign", "verify"]},
    "DSS":    {"name": "DSA",       "primitive": "signature", "cryptoFunctions": ["sign", "verify"]},
    "GOST94": {"name": "GOST-94",   "primitive": "signature", "cryptoFunctions": ["sign", "verify"]},
    "GOST01": {"name": "GOST-2001", "primitive": "signature", "cryptoFunctions": ["sign", "verify"]},
    "KRB5":   {"name": "KRB5",      "primitive": "signature", "cryptoFunctions": ["sign", "verify"]},
}

ENC_MAP = {
    "AESGCM":      ("AES",              "gcm",  "block-cipher"),
    "AESCCM":      ("AES",              "ccm",  "block-cipher"),
    "AESCCM8":     ("AES",              "ccm-8","block-cipher"),
    "AES":         ("AES",              "cbc",  "block-cipher"),
    "ChaCha20":    ("ChaCha20-Poly1305", None,  "ae"),
    "Camellia":    ("Camellia",          "cbc",  "block-cipher"),
    "CamelliaGCM": ("Camellia",          "gcm",  "block-cipher"),
    "3DES":        ("3DES-EDE",          "cbc",  "block-cipher"),
    "SEED":        ("SEED",              "cbc",  "block-cipher"),
    "IDEA":        ("IDEA",              "cbc",  "block-cipher"),
    "RC4":         ("RC4",               None,   "stream-cipher"),
    "RC2":         ("RC2",               "cbc",  "block-cipher"),
    "DES":         ("DES",               "cbc",  "block-cipher"),
    "ARIA":        ("ARIA",              "cbc",  "block-cipher"),
    "ARIAGCM":     ("ARIA",              "gcm",  "block-cipher"),
    "GOST":        ("GOST-28147",        "cnt",  "block-cipher"),
}

MAC_MAP = {
    "AEAD":       None,
    "SHA1":       ("SHA-1",        "160"),
    "SHA256":     ("SHA-256",      "256"),
    "SHA384":     ("SHA-384",      "384"),
    "MD5":        ("MD5",          "128"),
    "GOST89IMIT": ("GOST-28147-IMIT", None),
    "GOST94":     ("GOST-94",      None),
    "GOSTR3411":  ("GOST-R-34.11", None),
    "STREEBOG256":("Streebog-256", "256"),
    "M1":         ("MD5",          "128"),
    "Null":       None,
}


def load_cipher_mapping():
    mapping = {}
    filepath = os.path.join(SCRIPT_DIR, "tls-mapping", "cipher-mapping.txt")
    if not os.path.exists(filepath):
        return mapping
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            kx_match = re.search(r'Kx=(\S+)', line)
            au_match = re.search(r'Au=(\S+)', line)
            enc_match = re.search(r'Enc=(\S+)', line)
            mac_match = re.search(r'Mac=(\S+)', line)
            if not (kx_match and au_match and enc_match and mac_match):
                continue
            parts = line.split()
            iana_name = None
            openssl_name = None
            for i, p in enumerate(parts):
                if p == "-" and i > 0:
                    if i + 1 < len(parts):
                        openssl_name = parts[i + 1]
                    break
            for p in parts:
                if p.startswith("TLS_") or p.startswith("SSL_"):
                    iana_name = p
                    break
            enc_raw = enc_match.group(1)
            enc_size = None
            enc_algo = enc_raw
            size_match = re.match(r'(.+?)\((\d+)\)', enc_raw)
            if size_match:
                enc_algo = size_match.group(1)
                enc_size = size_match.group(2)
            kx_raw = kx_match.group(1)
            kx_size_match = re.search(r'\((\d+)\)', kx_raw)
            kx_size = kx_size_match.group(1) if kx_size_match else None
            kx_clean = re.sub(r'\(\d+\)', '', kx_raw)
            entry = {
                "kx": kx_clean,
                "kx_size": kx_size,
                "au": au_match.group(1),
                "enc_algo": enc_algo,
                "enc_size": enc_size,
                "mac": mac_match.group(1),
            }
            if iana_name and iana_name != "-":
                mapping[iana_name] = entry
            if openssl_name and openssl_name != "-":
                mapping[openssl_name] = entry
    return mapping


CIPHER_MAPPING = load_cipher_mapping()


def load_curves_mapping():
    mapping = {}
    filepath = os.path.join(SCRIPT_DIR, "tls-mapping", "curves-mapping.txt")
    if not os.path.exists(filepath):
        return mapping
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 4 or parts[1] != "-":
                continue
            hex_code = parts[0]
            name = parts[2]
            if name == "NULL":
                continue
            hex_parts = hex_code.split(",")
            if len(hex_parts) == 2:
                high = int(hex_parts[0], 16)
                if high == 0x00:
                    ctype = "ec"
                elif high == 0x01:
                    ctype = "ffdhe"
                elif high == 0x02:
                    ctype = "kem"
                elif high in (0x11, 0x63):
                    ctype = "hybrid"
                else:
                    ctype = "unknown"
            else:
                ctype = "unknown"
            mapping[name] = ctype
    return mapping


CURVES_MAPPING = load_curves_mapping()


def build_hybrid_decomposition(curves_mapping):
    ec_names = sorted(
        [n for n, ctype in curves_mapping.items() if ctype == "ec"],
        key=len, reverse=True,
    )
    kem_names = sorted(
        [n for n, ctype in curves_mapping.items() if ctype == "kem"],
        key=len, reverse=True,
    )
    decomposition = {}
    for name, ctype in curves_mapping.items():
        if ctype != "hybrid":
            continue
        name_lower = name.lower()
        for ec in ec_names:
            if not name_lower.startswith(ec.lower()):
                continue
            kem_part = name[len(ec):]
            if not kem_part:
                break
            kem_match = next((k for k in kem_names if k.lower() == kem_part.lower()), kem_part)
            decomposition[name] = (ec, kem_match)
            break
    return decomposition


HYBRID_DECOMPOSITION = build_hybrid_decomposition(CURVES_MAPPING)


def _decompose_from_mapping(entry):
    algorithms = []

    kx = entry["kx"]
    kx_size = entry.get("kx_size")
    if kx != "any" and kx != "None" and kx in KX_MAP:
        algo = KX_MAP[kx].copy()
        if kx_size:
            algo["name"] = f"{algo['name']}-{kx_size}"
            algo["parameterSetIdentifier"] = kx_size
        algorithms.append(algo)

    au = entry["au"]
    if au != "any" and au != "None" and au != kx and au in AU_MAP:
        algorithms.append(AU_MAP[au].copy())

    enc_algo = entry["enc_algo"]
    enc_size = entry["enc_size"]
    if enc_algo != "None" and enc_algo in ENC_MAP:
        base_name, mode, primitive = ENC_MAP[enc_algo]
        if mode:
            cipher_name = f"{base_name}-{enc_size}-{mode.upper()}" if enc_size else base_name
        else:
            cipher_name = f"{base_name}" if not enc_size else base_name
        algo = {
            "name": cipher_name, "primitive": primitive,
            "cryptoFunctions": ["encrypt", "decrypt"],
        }
        if enc_size:
            algo["parameterSetIdentifier"] = enc_size
        if mode:
            algo["mode"] = mode
        if primitive == "ae":
            algo["cryptoFunctions"] = ["encrypt", "decrypt", "tag"]
        algorithms.append(algo)

    mac = entry["mac"]
    if mac in MAC_MAP and MAC_MAP[mac] is not None:
        mac_name, mac_param = MAC_MAP[mac]
        algo = {
            "name": mac_name, "primitive": "hash",
            "cryptoFunctions": ["digest"],
        }
        if mac_param:
            algo["parameterSetIdentifier"] = mac_param
        algorithms.append(algo)

    return algorithms


def get_ciphers(data, prefix):
    ciphers = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get("id", "").startswith(prefix) and item.get("finding"):
            parts = item["finding"].split()
            if parts:
                ciphers.append(parts[-1])
    return ciphers


def get_version_status(data, version_id):
    item = next((item for item in data if item["id"] == version_id), None)
    if item:
        finding = item["finding"].lower()
        return "offered" in finding and "not offered" not in finding
    return False


def get_fs_info(data, fs_id):
    item = next((item for item in data if item["id"] == fs_id), None)
    if item:
        finding = item["finding"]
        if "not offered" in finding.lower() or ("no " in finding.lower() and "offered" in finding.lower()):
            return []
        return finding.split()
    return []


def get_dh_groups(data):
    item = next((item for item in data if item["id"] == "DH_groups"), None)
    if not item:
        return []
    finding = item["finding"]
    if "not offered" in finding.lower() or "not supported" in finding.lower():
        return []
    unknown_match = re.match(r"Unknown DH group \((\d+) bits\)", finding)
    if unknown_match:
        bits = unknown_match.group(1)
        return [f"DH-custom-{bits}"]
    return finding.split()


def get_cert_info(data, prefix):
    return [item["finding"] for item in data if item["id"].startswith(prefix)]


def get_target_info(data):
    for item in data:
        if item.get("ip") and "/" in item["ip"]:
            parts = item["ip"].split("/")
            if parts[0]:
                return parts[0], item.get("port", "443")
    return "unknown", "443"



def decompose_cipher_suite(name):
    entry = CIPHER_MAPPING.get(name)
    if entry:
        return _decompose_from_mapping(entry)
    print(f"Warning: cipher '{name}' not found in cipher-mapping.txt — skipped", file=sys.stderr)
    return []


def parse_testssl_json(data):
    result = {
        "versions": {},
        "ciphers_tls10": [],
        "ciphers_tls11": [],
        "ciphers_tls12": [],
        "ciphers_tls13": [],
        "curves": [],
        "kems": [],
        "dh_groups": [],
        "sig_algs_tls12": [],
        "sig_algs_tls13": [],
        "cert_signatures": [],
        "cert_keys": []
    }

    version_ids = {
        "SSLv2": "SSLv2",
        "SSLv3": "SSLv3",
        "TLSv1.0": "TLS1",
        "TLSv1.1": "TLS1_1",
        "TLSv1.2": "TLS1_2",
        "TLSv1.3": "TLS1_3"
    }

    for name, tid in version_ids.items():
        result["versions"][name] = get_version_status(data, tid)

    result["ciphers_tls10"] = get_ciphers(data, "cipher-tls1_x")
    result["ciphers_tls11"] = get_ciphers(data, "cipher-tls1_1_")
    result["ciphers_tls12"] = get_ciphers(data, "cipher-tls1_2_")
    result["ciphers_tls13"] = get_ciphers(data, "cipher-tls1_3_")

    result["curves"] = get_fs_info(data, "FS_ECDHE_curves")
    result["kems"] = get_fs_info(data, "FS_KEMs")
    result["dh_groups"] = get_dh_groups(data)
    result["sig_algs_tls12"] = get_fs_info(data, "FS_TLS12_sig_algs")
    result["sig_algs_tls13"] = get_fs_info(data, "FS_TLS13_sig_algs")

    result["cert_signatures"] = get_cert_info(data, "cert_signatureAlgorithm")
    result["cert_keys"] = get_cert_info(data, "cert_keySize")
    result["cert_key_usages"] = get_cert_info(data, "cert_keyUsage")

    return result


def _add_algorithm(name, primitive, components, seen, algo_refs, algo_properties, description=None):
    key = f"{name}:{primitive}"
    if key in algo_refs:
        return algo_refs[key]

    seen.add(key)
    bom_ref = str(uuid.uuid4())
    algo_refs[key] = bom_ref

    props = {k: v for k, v in algo_properties.items() if v is not None}

    component = {
        "type": "cryptographic-asset",
        "bom-ref": bom_ref,
        "name": name,
        "cryptoProperties": {
            "assetType": "algorithm",
            "algorithmProperties": props
        }
    }
    if description:
        component["description"] = description

    components.append(component)
    return bom_ref


def _add_group_or_curve(name, default_type, description, components, seen, algo_refs):
    ctype = CURVES_MAPPING.get(name, default_type)
    if ctype == "ec":
        _add_algorithm(
            name, "ecc", components, seen, algo_refs,
            {"primitive": "ecc", "curve": name, "cryptoFunctions": ["keyagree"]},
            description=description,
        )
    else:
        if ctype == "ffdhe":
            bits = name.replace("ffdhe", "")
        elif name.startswith("DH-custom-"):
            bits = name.replace("DH-custom-", "")
        else:
            bits = name
        _add_algorithm(
            name, "key-agree", components, seen, algo_refs,
            {"primitive": "key-agree", "parameterSetIdentifier": bits,
             "cryptoFunctions": ["keyagree"]},
            description=description,
        )


def generate_cbom(parsed_data, target, port):
    components = []
    seen = set()
    algo_refs = {} 

    all_cipher_suites = set(
        parsed_data["ciphers_tls10"] + parsed_data["ciphers_tls11"] +
        parsed_data["ciphers_tls12"] + parsed_data["ciphers_tls13"]
    )

    suite_algo_refs = {}

    for suite_name in all_cipher_suites:
        if not suite_name:
            continue
        algos = decompose_cipher_suite(suite_name)
        refs = []
        for algo in algos:
            ref = _add_algorithm(
                algo["name"], algo["primitive"],
                components, seen, algo_refs,
                {
                    "primitive": algo["primitive"],
                    "mode": algo.get("mode"),
                    "parameterSetIdentifier": algo.get("parameterSetIdentifier"),
                    "cryptoFunctions": algo["cryptoFunctions"],
                },
                description="Cipher suite component"
            )
            refs.append(ref)
        suite_algo_refs[suite_name] = refs

    for curve in parsed_data["curves"]:
        if curve not in CURVES_MAPPING:
            continue
        _add_group_or_curve(
            curve, "ec",
            "TLS supported elliptic curve", components, seen, algo_refs,
        )

    for dh_group in parsed_data["dh_groups"]:
        _add_group_or_curve(
            dh_group, "key-agree",
            "DH group for key exchange", components, seen, algo_refs,
        )

    for kem in parsed_data["kems"]:
        if kem not in CURVES_MAPPING:
            continue
        ctype = CURVES_MAPPING[kem]
        if ctype == "hybrid" and kem in HYBRID_DECOMPOSITION:
            ec_name, kem_name = HYBRID_DECOMPOSITION[kem]
            ec_ref = _add_algorithm(
                ec_name, "ecc", components, seen, algo_refs,
                {"primitive": "ecc", "curve": ec_name, "cryptoFunctions": ["keyagree"]},
                description=f"EC component of hybrid KEM {kem}"
            )
            kem_ref = _add_algorithm(
                kem_name, "kem", components, seen, algo_refs,
                {"primitive": "kem", "cryptoFunctions": ["encapsulate", "decapsulate"]},
                description=f"PQ-KEM component of hybrid KEM {kem}"
            )
            _add_algorithm(
                kem, "kem", components, seen, algo_refs,
                {"primitive": "kem", "cryptoFunctions": ["encapsulate", "decapsulate"],
                 "primitiveRefs": [ec_ref, kem_ref]},
                description=f"Hybrid KEM combining classical EC and post-quantum KEM"
            )
        else:
            _add_algorithm(
                kem, "kem", components, seen, algo_refs,
                {"primitive": "kem", "cryptoFunctions": ["encapsulate", "decapsulate"]},
                description="Key encapsulation mechanism"
            )

    all_sig_algs = set(parsed_data["sig_algs_tls12"] + parsed_data["sig_algs_tls13"])
    for sig_alg in all_sig_algs:
        _add_algorithm(
            sig_alg, "signature", components, seen, algo_refs,
            {"primitive": "signature", "cryptoFunctions": ["sign", "verify"]},
            description="TLS handshake signature algorithm"
        )

    # Certificate components — pair signature algorithm and public key by index
    cert_count = max(len(parsed_data["cert_signatures"]), len(parsed_data["cert_keys"]))
    for i in range(cert_count):
        sig_ref = None
        key_ref = None

        if i < len(parsed_data["cert_signatures"]):
            normalized = parsed_data["cert_signatures"][i].replace(" with ", "-")
            sig_ref = _add_algorithm(
                normalized, "signature", components, seen, algo_refs,
                {"primitive": "signature", "cryptoFunctions": ["sign", "verify"]},
                description="Certificate signature algorithm"
            )

        if i < len(parsed_data["cert_keys"]):
            keysize = parsed_data["cert_keys"][i]
            parts = keysize.split()
            if len(parts) >= 2:
                key_type = parts[0]
                key_bits = parts[1]
                key_name = f"{key_type}-{key_bits}"
                primitive = "pke" if key_type == "RSA" else "ecc"
                algo_props = {
                    "primitive": primitive,
                    "parameterSetIdentifier": f"{key_bits} bits",
                    "cryptoFunctions": ["keygen"],
                }
                if key_type == "EC" and "curve" in keysize:
                    algo_props["curve"] = keysize.split("curve ")[-1].rstrip(")")
                key_ref = _add_algorithm(
                    key_name, primitive, components, seen, algo_refs,
                    algo_props,
                    description="Certificate public key"
                )

        cert_props = {"certificateFormat": "X.509"}
        if i < len(parsed_data["cert_key_usages"]):
            cert_props["keyUsage"] = parsed_data["cert_key_usages"][i]
        if sig_ref:
            cert_props["signatureAlgorithmRef"] = sig_ref
        if key_ref:
            cert_props["subjectPublicKeyRef"] = key_ref

        cert_label = "Server Certificate" if cert_count == 1 else f"Server Certificate #{i + 1}"
        components.append({
            "type": "cryptographic-asset",
            "bom-ref": str(uuid.uuid4()),
            "name": cert_label,
            "cryptoProperties": {
                "assetType": "certificate",
                "certificateProperties": cert_props
            }
        })

    version_to_ciphers = {
        "SSLv2":   [],
        "SSLv3":   [],
        "TLSv1.0": parsed_data["ciphers_tls10"],
        "TLSv1.1": parsed_data["ciphers_tls11"],
        "TLSv1.2": parsed_data["ciphers_tls12"],
        "TLSv1.3": parsed_data["ciphers_tls13"],
    }

    for version, offered in parsed_data["versions"].items():
        if not offered:
            continue

        cipher_suites_for_version = version_to_ciphers.get(version, [])
        cipher_suites_list = []
        for suite_name in cipher_suites_for_version:
            if suite_name and suite_name in suite_algo_refs:
                cipher_suites_list.append({
                    "name": suite_name,
                    "algorithms": suite_algo_refs[suite_name]
                })

        proto_props = {
            "type": "tls",
            "version": version,
        }
        if cipher_suites_list:
            proto_props["cipherSuites"] = cipher_suites_list

        components.append({
            "type": "cryptographic-asset",
            "bom-ref": str(uuid.uuid4()),
            "name": version,
            "cryptoProperties": {
                "assetType": "protocol",
                "protocolProperties": proto_props
            }
        })

    cbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "component": {
                "type": "application",
                "name": target,
                "description": f"TLS service on {target}:{port}"
            }
        },
        "components": components
    }

    return cbom


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 testssl_to_cbom.py <testssl_output.json>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{input_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read '{input_file}': {e}")
        sys.exit(1)

    try:
        target, port = get_target_info(data)
        parsed = parse_testssl_json(data)
        cbom = generate_cbom(parsed, target, port)
    except Exception as e:
        print(f"Error: Failed to parse testssl data: {e}")
        sys.exit(1)

    output_file = f"{target}_tls_cbom.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cbom, f, indent=2)
    except Exception as e:
        print(f"Error: Failed to write '{output_file}': {e}")
        sys.exit(1)

    print(f"CBOM saved {output_file}")
    print(f"Components {len(cbom['components'])}")


if __name__ == "__main__":
    main()
