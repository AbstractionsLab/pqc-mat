"""
algorithm_classifier.py — Quantum risk classification for cryptographic algorithms.

Loads the algorithm risk catalog from data/algorithm-risk-catalog.yaml at import time
and exposes a single classify() function.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

import yaml


_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "algorithm-risk-catalog.yaml")

VALID_CLASSIFICATIONS = frozenset({
    "quantum-vulnerable",
    "non-hybrid",
    "classically-deprecated",
    "quantum-safe",
    "hybrid",
    "unknown",
})

VALID_RISK_SCORES = frozenset({"high", "medium", "low", "none"})

_UNKNOWN_RESULT_FIELDS = {
    "classification": "unknown",
    "risk_score": "high",
    "rationale": "Algorithm not found in the quantum risk catalog. Manual review required.",
    "recommended_migration": "Review against NIST FIPS 203/204/205 and BSI TR-02102-1",
    "references": [],
}


@dataclass
class RiskClassification:
    classification: str
    risk_score: str
    rationale: str
    recommended_migration: str
    references: list = field(default_factory=list)


def _load_catalog(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("entries", [])


_CATALOG: list = _load_catalog(_CATALOG_PATH)


def _entry_to_result(entry: dict) -> RiskClassification:
    return RiskClassification(
        classification=entry.get("risk_classification", "unknown"),
        risk_score=entry.get("risk_score", "high"),
        rationale=entry.get("rationale", "").strip(),
        recommended_migration=entry.get("recommended_migration", ""),
        references=list(entry.get("references", [])),
    )


def _param_in_range(entry: dict, param_set_identifier: Optional[str]) -> bool:
    """Return True if the entry's key-size range matches the given parameterSetIdentifier."""
    min_bits = entry.get("min_key_bits")
    max_bits = entry.get("max_key_bits")
    if min_bits is None and max_bits is None:
        return True
    if param_set_identifier is None:
        return True
    try:
        bits = int(param_set_identifier)
    except (ValueError, TypeError):
        return min_bits is None and max_bits is None
    if min_bits is not None and bits < min_bits:
        return False
    if max_bits is not None and bits > max_bits:
        return False
    return True


def classify(
    name: str,
    primitive: Optional[str] = None,
    param_set_identifier: Optional[str] = None,
) -> RiskClassification:
    """Classify a cryptographic algorithm by its quantum risk.

    Matching order:
      1. Exact name match (case-insensitive), respecting key-size range if specified.
      2. Regex pattern match on name, respecting key-size range.
      3. Primitive-type fallback (entries with no name_patterns that match primitive).
      4. Unknown.

    Args:
        name: Algorithm name as it appears in the CBOM component.
        primitive: CBOM algorithmProperties.primitive value (e.g., "pke", "hash").
        param_set_identifier: CBOM algorithmProperties.parameterSetIdentifier (e.g., "128", "256").

    Returns:
        RiskClassification dataclass with classification, risk_score, rationale,
        recommended_migration, and references.
    """
    name_lower = name.lower() if name else ""

    # Pass 1: exact name match
    for entry in _CATALOG:
        patterns = entry.get("name_patterns", [])
        for pat in patterns:
            if pat.lower() == name_lower and _param_in_range(entry, param_set_identifier):
                return _entry_to_result(entry)

    # Pass 2: regex match on name
    for entry in _CATALOG:
        patterns = entry.get("name_patterns", [])
        for pat in patterns:
            if not pat:
                continue
            try:
                if re.fullmatch(pat, name, re.IGNORECASE) and _param_in_range(entry, param_set_identifier):
                    return _entry_to_result(entry)
            except re.error:
                # Invalid regex in catalog — treat as literal and skip
                continue

    # Pass 3: primitive-type fallback (entries that have primitive_types but no/empty name_patterns)
    if primitive:
        for entry in _CATALOG:
            patterns = entry.get("name_patterns", [])
            prim_types = entry.get("primitive_types", [])
            if not patterns and prim_types and primitive in prim_types:
                return _entry_to_result(entry)

    # Pass 4: unknown
    return RiskClassification(**_UNKNOWN_RESULT_FIELDS)
