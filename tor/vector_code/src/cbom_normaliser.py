"""
cbom_normaliser.py — Converts cryptobom-forge output to valid CycloneDX 1.6 CBOM.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Optional

_CYCLONEDX_16_SCHEMA = (
    "http://cyclonedx.org/schema/bom-1.6.schema.json"
)

_PRIMITIVE_MAP: dict[str, str] = {
    "blockcipher": "block-cipher",
    "streamcipher": "stream-cipher",
    "keyagree": "key-agree",
    "drbg": "drbg",
    "mac": "mac",
    "block-cipher": "block-cipher",
    "stream-cipher": "stream-cipher",
    "signature": "signature",
    "hash": "hash",
    "pke": "pke",
    "xof": "xof",
    "kdf": "kdf",
    "key-agree": "key-agree",
    "kem": "kem",
    "ae": "ae",
    "combiner": "combiner",
    "other": "other",
    "unknown": "unknown",
}

_ASSET_TYPE_MAP: dict[str, str] = {
    "relatedCryptoMaterial": "related-crypto-material",
    "algorithm": "algorithm",
    "certificate": "certificate",
    "protocol": "protocol",
    "related-crypto-material": "related-crypto-material",
}


def _fix_detection_context(component: dict) -> dict:
    crypto = component.get("cryptoProperties", {})
    detection_ctx = crypto.pop("detectionContext", None)

    if not detection_ctx:
        return component

    occurrences = []
    for ctx in detection_ctx:
        file_path = ctx.get("filePath", "")
        line_numbers = ctx.get("lineNumbers", [])
        additional = ctx.get("additionalContext", "")

        occ: dict = {}
        if file_path:
            occ["location"] = file_path
        if line_numbers:
            occ["line"] = line_numbers[0]
        if additional:
            occ["additionalContext"] = additional.strip()
        if occ.get("location"):
            occurrences.append(occ)

    if occurrences:
        evidence = component.setdefault("evidence", {})
        existing = evidence.get("occurrences", [])
        evidence["occurrences"] = existing + occurrences

    return component


def _fix_component(component: dict) -> dict:
    comp = copy.deepcopy(component)
    if comp.get("type") == "crypto-asset":
        comp["type"] = "cryptographic-asset"

    crypto = comp.get("cryptoProperties", {})
    if not crypto:
        return comp

    asset_type = crypto.get("assetType", "")
    crypto["assetType"] = _ASSET_TYPE_MAP.get(asset_type, asset_type)

    algo_props = crypto.get("algorithmProperties", {})
    if algo_props:
        prim = algo_props.get("primitive", "")
        if prim:
            algo_props["primitive"] = _PRIMITIVE_MAP.get(prim, prim)
        algo_props.pop("variant", None)

    rcm_props = crypto.get("relatedCryptoMaterialProperties", {})
    if rcm_props:
        if "relatedCryptoMaterialType" in rcm_props:
            raw = rcm_props.pop("relatedCryptoMaterialType")
            rcm_props["type"] = _RCM_TYPE_MAP.get(raw, raw)
        elif "type" in rcm_props:
            rcm_props["type"] = _RCM_TYPE_MAP.get(rcm_props["type"], rcm_props["type"])
    comp = _fix_detection_context(comp)
    return comp


def normalise(cbom: dict) -> dict:
    """Return a new dict with all IBM-draft, CycloneDX 1.6 fixes applied"""
    out = copy.deepcopy(cbom)
    out["bomFormat"]   = "CycloneDX"
    out["specVersion"] = "1.6"
    out["$schema"] = _CYCLONEDX_16_SCHEMA
    out["components"] = [_fix_component(c) for c in out.get("components", [])]
    return out


def normalise_file(input_path: str, output_path: Optional[str] = None) -> str:
    """Read a CBOM file, normalise it, and write it back"""
    if output_path is None:
        output_path = input_path

    with open(input_path, "r", encoding="utf-8") as f:
        cbom = json.load(f)

    normalised = normalise(cbom)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalised, f, indent=2, ensure_ascii=False)
    return output_path


_RCM_TYPE_MAP: dict[str, str] = {
    "privateKey": "private-key",
    "publicKey": "public-key",
    "secretKey":"secret-key",
    "keyPair":"key",
    "initializationVector": "initialization-vector",
    "private-key": "private-key",
    "public-key": "public-key",
    "secret-key": "secret-key",
    "key": "key",
    "ciphertext": "ciphertext",
    "signature": "signature",
    "digest": "digest",
    "initialization-vector": "initialization-vector",
    "nonce": "nonce",
    "seed": "seed",
    "salt": "salt",
    "shared-secret": "shared-secret",
    "tag": "tag",
    "additional-data": "additional-data",
    "password": "password",
    "credential": "credential",
    "token": "token",
    "other": "other",
    "unknown": "unknown",
}