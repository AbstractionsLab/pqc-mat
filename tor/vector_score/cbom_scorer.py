"""
cbom_scorer.py — Annotates a CycloneDX CBOM with quantum risk classification properties.

Exposes a single pure function score_cbom() that returns an annotated deep copy of the
input CBOM dict. The original dict is never mutated.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Optional

from .algorithm_classifier import classify


_SCORER_VERSION = "0.1"


def _get_algo_props(component: dict) -> Optional[dict]:
    """Return the algorithmProperties sub-dict for an algorithm component, or None."""
    crypto = component.get("cryptoProperties", {})
    if crypto.get("assetType") != "algorithm":
        return None
    # CycloneDX 1.6 uses algorithmProperties; some older CBOM tooling omits the wrapper
    return crypto.get("algorithmProperties", {})


def _append_property(props_list: list, name: str, value: str) -> None:
    props_list.append({"name": name, "value": value})


def _annotate_component(component: dict) -> dict:
    """Return an annotated copy of an algorithm component with pqcmat: risk properties."""
    algo_props = _get_algo_props(component)
    if algo_props is None:
        return component

    algo_name = component.get("name", "") or algo_props.get("variant", "")
    primitive = algo_props.get("primitive")
    param_set = algo_props.get("parameterSetIdentifier")

    # Skip sentinels that are tooling artifacts, not real algorithm names:
    if not algo_name or algo_name.strip().lower() == "none":
        return component

    result = classify(algo_name, primitive, param_set)

    annotated = copy.deepcopy(component)
    props = annotated.setdefault("properties", [])

    _append_property(props, "pqcmat:risk-classification", result.classification)
    _append_property(props, "pqcmat:risk-score", result.risk_score)
    _append_property(props, "pqcmat:rationale", result.rationale)
    _append_property(props, "pqcmat:recommended-migration", result.recommended_migration)
    for ref in result.references:
        _append_property(props, "pqcmat:reference", ref)

    return annotated


def score_cbom(cbom: dict) -> dict:
    """Annotate a CycloneDX CBOM dict with quantum risk properties.

    For each component whose cryptoProperties.assetType is "algorithm", appends
    pqcmat:-namespaced entries to the component's properties array.  All other
    components are copied unchanged.  The metadata.properties array receives a
    pqcmat:scored-at timestamp entry.

    Args:
        cbom: Parsed CycloneDX CBOM as a Python dict (not mutated).

    Returns:
        A new dict — a deep copy of the input with risk annotations added.
    """
    scored = copy.deepcopy(cbom)

    # Annotate each algorithm component
    components = scored.get("components", [])
    scored["components"] = [_annotate_component(c) for c in components]

    # Add scored-at timestamp to metadata.properties
    metadata = scored.setdefault("metadata", {})
    meta_props = metadata.setdefault("properties", [])
    timestamp = datetime.now(timezone.utc).isoformat()
    _append_property(meta_props, "pqcmat:scored-at", timestamp)
    _append_property(meta_props, "pqcmat:scorer-version", _SCORER_VERSION)

    return scored
