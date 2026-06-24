"""
report_generator.py — Generates a Markdown quantum risk report from a scored CBOM.

Exposes a single generate_report() function that returns a Markdown string.
"""

from __future__ import annotations

from collections import defaultdict


_SCORER_VERSION = "0.1"

_CLASSIFICATION_ORDER = [
    "classically-deprecated",
    "quantum-vulnerable",
    "non-hybrid",
    "hybrid",
    "quantum-safe",
    "unknown",
]

_CLASSIFICATION_LABELS = {
    "quantum-vulnerable":    "Quantum-Vulnerable",
    "non-hybrid":            "Non-Hybrid",
    "classically-deprecated":"Classically Deprecated",
    "quantum-safe":          "Quantum-Safe",
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


def _extract_locations(component: dict) -> list[dict]:
    """Return a list of {file, lines} dicts from a component.

    Supports two formats:
    - CycloneDX 1.6 (after normalization): component["evidence"]["occurrences"]
      Each occurrence: {"location": str, "line": int, "additionalContext": str}
    - IBM draft (before normalization): cryptoProperties["detectionContext"]
      Each entry: {"filePath": str, "lineNumbers": [int, ...]}
    """
    locations = []

    # CycloneDX 1.6 format — evidence.occurrences
    occurrences = component.get("evidence", {}).get("occurrences", [])
    if occurrences:
        for occ in occurrences:
            file_path = occ.get("location", "").strip()
            if not file_path:
                continue
            line = occ.get("line")
            locations.append({
                "file": file_path,
                "lines": [line] if line is not None else [],
            })
        return locations

    # IBM draft fallback — cryptoProperties.detectionContext
    detection_context = component.get("cryptoProperties", {}).get("detectionContext", [])
    for ctx in detection_context:
        file_path = ctx.get("filePath", "").strip()
        if not file_path:
            continue
        line_numbers = ctx.get("lineNumbers", [])
        locations.append({
            "file": file_path,
            "lines": line_numbers,
        })
    return locations


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

        # Collect source-code locations
        # for both CycloneDX 1.6 (evidence.occurrences) and IBM draft format (cryptoProperties.detectionContext).
        locations = _extract_locations(comp)

        findings.append({
            "name": algo_props.get("variant", "") or comp.get("name", ""),
            "primitive": algo_props.get("primitive", ""),
            "key_size": algo_props.get("parameterSetIdentifier", ""),
            "classification": classification,
            "risk_score": _get_pqcmat_prop(props, "pqcmat:risk-score"),
            "rationale": _get_pqcmat_prop(props, "pqcmat:rationale"),
            "migration": _get_pqcmat_prop(props, "pqcmat:recommended-migration"),
            "references": _get_all_pqcmat_props(props, "pqcmat:reference"),
            "locations": locations,
        })
    return findings


def _md_table_row(cells: list) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _md_table_header(headers: list) -> str:
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    return _md_table_row(headers) + "\n" + separator


def _has_any_locations(findings: list) -> bool:
    return any(f["locations"] for f in findings)


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

    source_locations_present = _has_any_locations(findings)

    lines = []

    # ── Header ──────────────────────────────────────────────────────────────────
    lines.append(f"# Quantum-threat and cryptography risk report — {target_name}")
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
    lines.append("## Identified algorithms per risk category")
    lines.append("")

    for cls in _CLASSIFICATION_ORDER:
        items = by_class.get(cls, [])
        if not items:
            continue
        label = _CLASSIFICATION_LABELS.get(cls, cls)
        lines.append(f"### {label}")
        lines.append("")

        if source_locations_present:
            # Extended table: includes a Source locations column
            lines.append(_md_table_header([
                "Algorithm", "Primitive", "Key size",
                "Rationale", "Recommended migration", "Source locations",
            ]))
            for item in sorted(items, key=lambda x: x["name"]):
                rationale = item["rationale"]
                if len(rationale) > 500:
                    rationale = rationale[:497] + "..."

                loc_items = item["locations"]
                if loc_items:
                    loc_cell = "<br>".join(
                        f"`{loc['file']}`"
                        + (
                            (" L" + ",".join(str(n) for n in loc["lines"]))
                            if loc["lines"] else ""
                        )
                        for loc in loc_items
                    )
                else:
                    loc_cell = "—"

                lines.append(_md_table_row([
                    item["name"],
                    item["primitive"] or "—",
                    item["key_size"] or "—",
                    rationale,
                    item["migration"],
                    loc_cell,
                ]))
            lines.append("")

        else:
            # No location data
            lines.append(_md_table_header([
                "Algorithm", "Primitive", "Key size", "Rationale", "Recommended migration",
            ]))
            for item in sorted(items, key=lambda x: x["name"]):
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
