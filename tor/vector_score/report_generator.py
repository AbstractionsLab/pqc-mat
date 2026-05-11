"""
report_generator.py — Generates a Markdown quantum risk report from a scored CBOM.

Exposes a single generate_report() function that returns a Markdown string.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional


_SCORER_VERSION = "0.1"

_CLASSIFICATION_ORDER = [
    "quantum-vulnerable",
    "classically-deprecated",
    "quantum-weakened",
    "hybrid",
    "quantum-safe",
    "post-quantum",
    "unknown",
]

_CLASSIFICATION_LABELS = {
    "quantum-vulnerable":    "Quantum-Vulnerable",
    "quantum-weakened":      "Quantum-Weakened",
    "classically-deprecated":"Classically Deprecated",
    "quantum-safe":          "Quantum-Safe",
    "post-quantum":          "Post-Quantum",
    "hybrid":                "Hybrid (Classical + PQC)",
    "unknown":               "Unknown / Unclassified",
}

_RISK_SCORE_LABELS = {
    "high":   "High",
    "medium": "Medium",
    "low":    "Low",
    "none":   "None",
}


def _get_pqcmat_prop(props: list, prop_name: str) -> str:
    for p in props:
        if p.get("name") == prop_name:
            return p.get("value", "")
    return ""


def _get_all_pqcmat_props(props: list, prop_name: str) -> list:
    return [p.get("value", "") for p in props if p.get("name") == prop_name]


def _get_algo_findings(components: list) -> list:
    """Extract a list of finding dicts from scored algorithm components."""
    findings = []
    for comp in components:
        crypto = comp.get("cryptoProperties", {})
        if crypto.get("assetType") != "algorithm":
            continue
        props = comp.get("properties", [])
        classification = _get_pqcmat_prop(props, "pqcmat:risk-classification")
        if not classification:
            continue
        algo_props = crypto.get("algorithmProperties", {})
        findings.append({
            "name": comp.get("name", ""),
            "primitive": algo_props.get("primitive", ""),
            "key_size": algo_props.get("parameterSetIdentifier", ""),
            "classification": classification,
            "risk_score": _get_pqcmat_prop(props, "pqcmat:risk-score"),
            "rationale": _get_pqcmat_prop(props, "pqcmat:rationale"),
            "migration": _get_pqcmat_prop(props, "pqcmat:recommended-migration"),
            "references": _get_all_pqcmat_props(props, "pqcmat:reference"),
        })
    return findings


def _md_table_row(cells: list) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _md_table_header(headers: list) -> str:
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    return _md_table_row(headers) + "\n" + separator


def generate_report(scored_cbom: dict) -> str:
    """Generate a Markdown risk report from a scored CBOM.

    Args:
        scored_cbom: A CBOM dict already annotated by score_cbom().

    Returns:
        A Markdown string suitable for writing to a .md file.
    """
    metadata = scored_cbom.get("metadata", {})
    meta_component = metadata.get("component", {})
    target_name = meta_component.get("name", "Unknown application")
    meta_props = metadata.get("properties", [])
    scored_at = _get_pqcmat_prop(meta_props, "pqcmat:scored-at")

    components = scored_cbom.get("components", [])
    findings = _get_algo_findings(components)

    # Group by classification
    by_class: dict = defaultdict(list)
    for f in findings:
        by_class[f["classification"]].append(f)

    # Collect all unique references
    all_refs: list = []
    seen_refs: set = set()
    for f in findings:
        for ref in f["references"]:
            if ref and ref not in seen_refs:
                all_refs.append(ref)
                seen_refs.add(ref)

    lines = []

    # ── Header ──────────────────────────────────────────────────────────────────
    lines.append(f"# Quantum risk report — {target_name}")
    lines.append("")
    lines.append(f"**Scored at:** {scored_at}  ")
    lines.append(f"**VECTOR-Score version:** {_SCORER_VERSION}  ")
    lines.append(f"**Algorithm components scored:** {len(findings)}  ")
    lines.append("")

    # ── Summary table ────────────────────────────────────────────────────────────
    lines.append("## Summary")
    lines.append("")
    lines.append(_md_table_header(["Classification", "Risk score", "Count"]))
    for cls in _CLASSIFICATION_ORDER:
        items = by_class.get(cls, [])
        if not items:
            continue
        score_label = _RISK_SCORE_LABELS.get(items[0]["risk_score"], items[0]["risk_score"])
        lines.append(_md_table_row([
            _CLASSIFICATION_LABELS.get(cls, cls),
            score_label,
            len(items),
        ]))
    lines.append("")

    # ── Per-classification sections ──────────────────────────────────────────────
    lines.append("## Findings by classification")
    lines.append("")

    for cls in _CLASSIFICATION_ORDER:
        items = by_class.get(cls, [])
        if not items:
            continue
        label = _CLASSIFICATION_LABELS.get(cls, cls)
        lines.append(f"### {label}")
        lines.append("")
        lines.append(_md_table_header(["Algorithm", "Primitive", "Key size", "Rationale", "Recommended migration"]))
        for item in sorted(items, key=lambda x: x["name"]):
            # Truncate long rationale for table readability
            rationale = item["rationale"]
            if len(rationale) > 500:
                rationale = rationale[:497] + "..."
            lines.append(_md_table_row([
                item["name"],
                item["primitive"] or "—",
                item["key_size"] or "—",
                rationale,
                item["migration"],
            ]))
        lines.append("")

    # ── Normative references ─────────────────────────────────────────────────────
    if all_refs:
        lines.append("## Normative references")
        lines.append("")
        for ref in all_refs:
            lines.append(f"- {ref}")
        lines.append("")

    return "\n".join(lines)
