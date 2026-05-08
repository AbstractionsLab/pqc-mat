#!/usr/bin/env python3

import csv
import json
import uuid
import sys
import os
from datetime import datetime, timezone


_DIR = os.path.dirname(os.path.abspath(__file__))

_CATEGORY_DEFAULTS = {
    'kex':      {'primitive': 'key-agree',    'cryptoFunctions': ['keygen'],             'parameterSetIdentifier': None, 'curve': None, 'hash': None, 'dh_group': None, 'pq_component': None, 'mode': None, 'etm': None, 'mac_type': None},
    'cipher':   {'primitive': 'block-cipher', 'cryptoFunctions': ['encrypt', 'decrypt'], 'parameterSetIdentifier': None, 'curve': None, 'hash': None, 'dh_group': None, 'pq_component': None, 'mode': None, 'etm': None, 'mac_type': None},
    'mac':      {'primitive': 'mac',          'cryptoFunctions': ['tag'],                'parameterSetIdentifier': None, 'curve': None, 'hash': None, 'dh_group': None, 'pq_component': None, 'mode': None, 'etm': None, 'mac_type': None},
    'host_key': {'primitive': 'signature',    'cryptoFunctions': ['keygen', 'sign'],     'parameterSetIdentifier': None, 'curve': None, 'hash': None, 'dh_group': None, 'pq_component': None, 'mode': None, 'etm': None, 'mac_type': None},
}


def _load_csv(filename, name_col):
    path = os.path.join(_DIR, filename)
    exact = {}
    wildcards = []
    try:
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                name = row.get(name_col, '').strip()
                if not name:
                    continue
                if name.endswith('*'):
                    wildcards.append((name[:-1], row))
                else:
                    exact[name] = row
    except FileNotFoundError:
        pass
    wildcards.sort(key=lambda x: len(x[0]), reverse=True)
    return exact, wildcards


def _row_to_result(row, algo_name='', was_wildcard=False):
    raw_funcs = row.get('cryptoFunctions', '').strip()
    funcs = [f.strip() for f in raw_funcs.split(',') if f.strip()] if raw_funcs else []
    raw_etm = row.get('etm', '').strip().lower()
    curve = row.get('curve', '').strip() or None
    if was_wildcard and not curve and algo_name.startswith('ecdh-sha2-'):
        curve = algo_name[len('ecdh-sha2-'):] or None
    return {
        'primitive':              row.get('primitive', '').strip(),
        'cryptoFunctions':        funcs,
        'parameterSetIdentifier': row.get('parameterSetIdentifier', '').strip() or None,
        'curve':                  curve,
        'hash':                   row.get('hash', '').strip() or None,
        'dh_group':               row.get('dh_group', '').strip() or None,
        'pq_component':           row.get('pq_component', '').strip() or None,
        'mode':                   row.get('mode', '').strip() or None,
        'etm':                    True if raw_etm == 'true' else (False if raw_etm == 'false' else None),
        'mac_type':               row.get('mac_type', '').strip() or None,
    }


_KEX_EXACT,     _KEX_WILD     = _load_csv('ssh-mapping/ssh-parameters-KEX.csv',        'Method Name')
_CIPHER_EXACT,  _CIPHER_WILD  = _load_csv('ssh-mapping/ssh-parameters-encryption.csv', 'Encryption Algorithm Name')
_MAC_EXACT,     _MAC_WILD     = _load_csv('ssh-mapping/ssh-parameters-MAC.csv',        'MAC Algorithm Name')
_HOSTKEY_EXACT, _HOSTKEY_WILD = _load_csv('ssh-mapping/ssh-parameters-hostkey.csv',     'Public Key Algorithm Name')

_TABLES = {
    'kex':      (_KEX_EXACT,     _KEX_WILD),
    'cipher':   (_CIPHER_EXACT,  _CIPHER_WILD),
    'mac':      (_MAC_EXACT,     _MAC_WILD),
    'host_key': (_HOSTKEY_EXACT, _HOSTKEY_WILD),
}


def _normalize_list(names, category):
    exact_map, _ = _TABLES.get(category, ({}, []))
    seen = set()
    result = []
    for name in names:
        normalized = name.split('@')[0] if '@' in name and name.split('@')[0] in exact_map else name
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _lookup(algo_name, category):
    exact_map, wildcard_list = _TABLES.get(category, ({}, []))
    if algo_name in exact_map:
        return _row_to_result(exact_map[algo_name], algo_name)
    for prefix, row in wildcard_list:
        if algo_name.startswith(prefix):
            return _row_to_result(row, algo_name, was_wildcard=True)
    return dict(_CATEGORY_DEFAULTS.get(category, {
        'primitive': '', 'cryptoFunctions': [], 'parameterSetIdentifier': None,
        'curve': None, 'hash': None, 'dh_group': None, 'pq_component': None,
        'mode': None, 'etm': None, 'mac_type': None,
    }))


_CURVE_PSI = {
    'nistp256': '256',
    'nistp384': '384',
    'nistp521': '521',
    'x25519':   '255',
    'x448':     '448',
}

_PQ_PSI = {
    'mlkem512':  '512',
    'mlkem768':  '768',
    'mlkem1024': '1024',
    'sntrup761': '761',
}


def create_component(name, category, description=None, primitive_refs=None):
    info = _lookup(name, category)

    algo_props = {}
    if info['primitive']:
        algo_props['primitive'] = info['primitive']

    if info['primitive'] == 'key-agree':
        algo_props['cryptoFunctions'] = ['keyagree']
    elif info['primitive'] == 'kem':
        algo_props['cryptoFunctions'] = ['encapsulate', 'decapsulate']
    elif info['cryptoFunctions']:
        algo_props['cryptoFunctions'] = info['cryptoFunctions']

    if info['parameterSetIdentifier']:
        algo_props['parameterSetIdentifier'] = info['parameterSetIdentifier']

    if info.get('mode'):
        algo_props['mode'] = info['mode']

    if primitive_refs:
        algo_props['primitiveRefs'] = primitive_refs

    comp = {
        'type': 'cryptographic-asset',
        'bom-ref': str(uuid.uuid4()),
        'name': name,
        'cryptoProperties': {
            'assetType': 'algorithm',
            'algorithmProperties': algo_props
        }
    }
    if description:
        comp['description'] = description
    return comp


def create_hash_component(hash_name):
    return {
        'type': 'cryptographic-asset',
        'bom-ref': str(uuid.uuid4()),
        'name': hash_name,
        'description': 'Hash algorithm used in key exchange',
        'cryptoProperties': {
            'assetType': 'algorithm',
            'algorithmProperties': {
                'primitive': 'hash',
                'cryptoFunctions': ['digest'],
            }
        }
    }


def create_curve_component(curve_name):
    algo_props = {
        'primitive': 'ecc',
        'curve': curve_name,
        'cryptoFunctions': ['keyagree'],
    }
    psi = _CURVE_PSI.get(curve_name)
    if psi:
        algo_props['parameterSetIdentifier'] = psi

    return {
        'type': 'cryptographic-asset',
        'bom-ref': str(uuid.uuid4()),
        'name': curve_name,
        'description': 'Elliptic curve used in key exchange',
        'cryptoProperties': {
            'assetType': 'algorithm',
            'algorithmProperties': algo_props
        }
    }


def create_pq_component(pq_name):
    algo_props = {
        'primitive': 'kem',
        'cryptoFunctions': ['encapsulate', 'decapsulate'],
    }
    psi = _PQ_PSI.get(pq_name)
    if psi:
        algo_props['parameterSetIdentifier'] = psi

    return {
        'type': 'cryptographic-asset',
        'bom-ref': str(uuid.uuid4()),
        'name': pq_name,
        'description': 'Post-quantum component of hybrid key exchange',
        'cryptoProperties': {
            'assetType': 'algorithm',
            'algorithmProperties': algo_props
        }
    }


def create_dh_group_component(dh_group):
    algo_props = {
        'primitive': 'dh',
        'cryptoFunctions': ['keyagree'],
    }
    if dh_group != 'dynamic':
        algo_props['parameterSetIdentifier'] = dh_group

    return {
        'type': 'cryptographic-asset',
        'bom-ref': str(uuid.uuid4()),
        'name': f"DH-group-{dh_group}",
        'description': 'Diffie-Hellman group used in key exchange',
        'cryptoProperties': {
            'assetType': 'algorithm',
            'algorithmProperties': algo_props
        }
    }


def parse_zgrab2_ssh(data):
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data).__name__}")

    if 'data' not in data or 'ssh' not in data.get('data', {}) or 'result' not in data.get('data', {}).get('ssh', {}):
        raise ValueError("Invalid zgrab2 structure: missing required keys (data/ssh/result)")

    result = data['data']['ssh']['result']

    if 'server_key_exchange' not in result:
        raise ValueError("Invalid zgrab2 structure: missing server_key_exchange")

    server_kex = result['server_key_exchange']
    server_id  = result.get('server_id', {})

    parsed = {
        'domain':              data.get('domain', 'unknown'),
        'ip':                  data.get('ip', 'unknown'),
        'port':                data.get('data', {}).get('ssh', {}).get('port', 22),
        'protocol':            data.get('data', {}).get('ssh', {}).get('protocol', 'ssh'),
        'ssh_version':         server_id.get('version', '2.0'),
        'server_software':     server_id.get('software', ''),
        'server_os':           server_id.get('comment', ''),
        'server_banner':       result.get('banner', ''),
        'hassh':               server_kex.get('serverHaSSH', ''),
        'kex_algorithms':      _normalize_list(server_kex.get('kex_algorithms', []), 'kex'),
        'host_key_algorithms': _normalize_list(server_kex.get('host_key_algorithms', []), 'host_key'),
        'ciphers':             [],
        'macs':                [],
        'algorithm_selection': result.get('algorithm_selection', {}),
    }

    ciphers_cs = server_kex.get('client_to_server_ciphers', [])
    ciphers_sc = server_kex.get('server_to_client_ciphers', [])
    parsed['ciphers'] = _normalize_list(ciphers_cs + ciphers_sc, 'cipher')

    macs_cs = server_kex.get('client_to_server_macs', [])
    macs_sc = server_kex.get('server_to_client_macs', [])
    parsed['macs'] = _normalize_list(macs_cs + macs_sc, 'mac')

    comp_cs = server_kex.get('client_to_server_compression', [])
    comp_sc = server_kex.get('server_to_client_compression', [])
    parsed['compressions'] = list(set(comp_cs + comp_sc))

    server_host_key = result.get('key_exchange', {}).get('server_host_key', {})
    parsed['server_host_key'] = {
        'algorithm':          server_host_key.get('algorithm', ''),
        'fingerprint_sha256': server_host_key.get('fingerprint_sha256', '')
    }

    return parsed


def generate_cbom(parsed):

    primitive_components   = []
    kex_components         = []
    host_key_components    = []
    cipher_components      = []
    mac_components         = []
    compression_components = []
    material_components    = []
    protocol_components    = []

    seen      = set()
    algo_refs = {}
    sub_refs  = {}

    for algo in parsed['kex_algorithms']:
        if algo in seen:
            continue
        seen.add(algo)

        info           = _lookup(algo, 'kex')
        primitive_refs = []

        if info.get('hash'):
            h = info['hash']
            if h not in sub_refs:
                hc = create_hash_component(h)
                sub_refs[h] = hc['bom-ref']
                primitive_components.append(hc)
            primitive_refs.append(sub_refs[h])

        if info.get('curve'):
            c = info['curve']
            if c not in sub_refs:
                cc = create_curve_component(c)
                sub_refs[c] = cc['bom-ref']
                primitive_components.append(cc)
            primitive_refs.append(sub_refs[c])

        if info.get('dh_group'):
            dh = info['dh_group']
            dh_key = f"dh_group_{dh}"
            if dh_key not in sub_refs:
                dhc = create_dh_group_component(dh)
                sub_refs[dh_key] = dhc['bom-ref']
                primitive_components.append(dhc)
            primitive_refs.append(sub_refs[dh_key])

        if info.get('pq_component'):
            pq = info['pq_component']
            if pq not in sub_refs:
                pqc = create_pq_component(pq)
                sub_refs[pq] = pqc['bom-ref']
                primitive_components.append(pqc)
            primitive_refs.append(sub_refs[pq])

        comp = create_component(
            algo, 'kex',
            description='SSH key exchange algorithm',
            primitive_refs=primitive_refs if primitive_refs else None
        )
        algo_refs[algo] = comp['bom-ref']
        kex_components.append(comp)

    for algo in parsed['host_key_algorithms']:
        if algo not in seen:
            seen.add(algo)
            comp = create_component(algo, 'host_key', description='SSH host key algorithm')
            algo_refs[algo] = comp['bom-ref']
            host_key_components.append(comp)

    for algo in parsed['ciphers']:
        if algo not in seen:
            seen.add(algo)
            comp = create_component(algo, 'cipher', description='SSH encryption cipher')
            algo_refs[algo] = comp['bom-ref']
            cipher_components.append(comp)

    for algo in parsed['macs']:
        if algo not in seen:
            seen.add(algo)

            info           = _lookup(algo, 'mac')
            primitive_refs = []

            if info.get('hash'):
                h = info['hash']
                if h not in sub_refs:
                    hc = create_hash_component(h)
                    sub_refs[h] = hc['bom-ref']
                    primitive_components.append(hc)
                primitive_refs.append(sub_refs[h])

            comp = create_component(
                algo, 'mac',
                description='SSH MAC algorithm',
                primitive_refs=primitive_refs if primitive_refs else None
            )

            if info.get('etm') is True:
                comp['cryptoProperties']['algorithmProperties']['etm'] = True

            if info.get('mac_type'):
                comp['cryptoProperties']['algorithmProperties']['macType'] = info['mac_type']

            algo_refs[algo] = comp['bom-ref']
            mac_components.append(comp)

    for algo in parsed.get('compressions', []):
        if algo not in seen:
            seen.add(algo)
            comp = {
                'type': 'cryptographic-asset',
                'bom-ref': str(uuid.uuid4()),
                'name': algo,
                'description': 'SSH compression algorithm',
                'cryptoProperties': {
                    'assetType': 'algorithm',
                    'algorithmProperties': {
                        'cryptoFunctions': ['compress']
                    }
                }
            }
            algo_refs[algo] = comp['bom-ref']
            compression_components.append(comp)

    host_key_info = parsed.get('server_host_key', {})
    if host_key_info.get('algorithm') and host_key_info.get('fingerprint_sha256'):
        algo     = host_key_info['algorithm']
        key_comp = {
            'type': 'cryptographic-asset',
            'bom-ref': str(uuid.uuid4()),
            'name': 'Server Host Key',
            'description': 'Server host public key',
            'cryptoProperties': {
                'assetType': 'related-crypto-material',
                'relatedCryptoMaterialProperties': {
                    'type': 'public-key',
                    'value': host_key_info['fingerprint_sha256']
                }
            }
        }
        if algo in algo_refs:
            key_comp['cryptoProperties']['relatedCryptoMaterialProperties']['algorithmRef'] = algo_refs[algo]
        material_components.append(key_comp)

    negotiated      = parsed.get('algorithm_selection', {})
    negotiated_refs = []

    for key in ['dh_kex_algorithm', 'host_key_algorithm']:
        name = negotiated.get(key, '')
        if name and name in algo_refs:
            negotiated_refs.append(algo_refs[name])

    seen_refs = set(negotiated_refs)
    for direction in ['client_to_server_alg_group', 'server_to_client_alg_group']:
        group = negotiated.get(direction, {})
        for field in ['cipher', 'mac', 'compression']:
            name = group.get(field, '')
            if name and name in algo_refs and algo_refs[name] not in seen_refs:
                negotiated_refs.append(algo_refs[name])
                seen_refs.add(algo_refs[name])

    proto_props = {
        'type':    'ssh',
        'version': parsed['ssh_version'],
    }
    if negotiated_refs:
        proto_props['cipherSuites'] = [{'name': 'negotiated', 'algorithms': negotiated_refs}]

    protocol_components.append({
        'type': 'cryptographic-asset',
        'bom-ref': str(uuid.uuid4()),
        'name': f"SSH-{parsed['ssh_version']}",
        'description': 'SSH protocol with negotiated algorithm suite',
        'cryptoProperties': {
            'assetType': 'protocol',
            'protocolProperties': proto_props
        }
    })

    components = (
        primitive_components +
        kex_components +
        host_key_components +
        cipher_components +
        mac_components +
        compression_components +
        material_components +
        protocol_components
    )

    properties = [
        {'name': 'server.ip',       'value': parsed['ip']},
        {'name': 'server.domain',   'value': parsed['domain']},
        {'name': 'server.protocol', 'value': parsed['protocol']},
        {'name': 'scan.port',       'value': str(parsed['port'])},
    ]
    if parsed.get('server_software'):
        properties.append({'name': 'server.software', 'value': parsed['server_software']})
    if parsed.get('server_os'):
        properties.append({'name': 'server.os', 'value': parsed['server_os']})
    if parsed.get('hassh'):
        properties.append({'name': 'server.hassh', 'value': parsed['hassh']})

    return {
        'bomFormat':    'CycloneDX',
        'specVersion':  '1.6',
        'serialNumber': f"urn:uuid:{uuid.uuid4()}",
        'version':      1,
        'metadata': {
            'timestamp': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'component': {
                'type':        'application',
                'name':        parsed['domain'],
                'description': f"SSH service on {parsed['domain']}:{parsed['port']}"
            },
            'properties': properties
        },
        'components': components,
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 zgrab2_to_cbom.py <zgrab2_ssh_output.json>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{input_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read '{input_file}': {e}")
        sys.exit(1)

    try:
        parsed = parse_zgrab2_ssh(data)
        cbom   = generate_cbom(parsed)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to generate CBOM: {e}")
        sys.exit(1)

    domain      = parsed['domain'].replace('/', '_').replace('\\', '_')
    output_file = f"{domain}_ssh_cbom.json"

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cbom, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error: Failed to write '{output_file}': {e}")
        sys.exit(1)

    print(f"CBOM saved: {output_file}")
    print(f"Components: {len(cbom['components'])}")


if __name__ == "__main__":
    main()
