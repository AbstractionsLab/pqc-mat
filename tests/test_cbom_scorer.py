"""
Tests for cbom_scorer.py — CBOM annotation engine.

Covers TCS-013 (annotated CBOM contains pqcmat: properties), plus additional
correctness and non-mutation tests.
"""

import copy
import json
import os

from vector_score.cbom_scorer import score_cbom


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_fixture(name: str) -> dict:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_prop(props: list, name: str):
    for p in props:
        if p.get("name") == name:
            return p.get("value")
    return None


class TestCbomScorer:
    """Validate that the CBOM scored with cbom_scorer.py contains informative 'pqcmat:' properties."""

    def setup_method(self):
        self.cbom = _load_fixture("sample4risk-scorer-cbom.json")

    def test_scored_cbom_has_pqcmat_properties(self):
        """Test that all assets of type 'algorithm' carry 'pqcmat:' risk properties."""
        scored = score_cbom(self.cbom)

        algo_components = [
            c for c in scored["components"]
            if c.get("cryptoProperties", {}).get("assetType") == "algorithm"
        ]
        assert algo_components, "Expected at least one algorithm component"

        for comp in algo_components:
            props = comp.get("properties", [])
            assert props, f"Component {comp['name']} has no properties array"

            classification = _get_prop(props, "pqcmat:risk-classification")
            assert classification, f"Component {comp['name']} missing pqcmat:risk-classification"

            risk_score = _get_prop(props, "pqcmat:risk-score")
            assert risk_score is not None, f"Component {comp['name']} missing pqcmat:risk-score"
            assert risk_score in ("high","medium","low","none")

            migration = _get_prop(props, "pqcmat:recommended-migration")
            assert migration is not None, f"Component {comp['name']} missing pqcmat:recommended-migration"

            rationale = _get_prop(props, "pqcmat:rationale")
            assert rationale is not None, f"Component {comp['name']} missing pqcmat:rationale"

    def test_metadata_has_scored_at_property(self):
        """Verify that the metadata.properties entry contains pqcmat:scored-at."""
        scored = score_cbom(self.cbom)

        meta_props = scored.get("metadata", {}).get("properties", [])
        scored_at = _get_prop(meta_props, "pqcmat:scored-at")
        assert scored_at, "metadata.properties missing pqcmat:scored-at"

    def test_non_algorithm_components_not_annotated(self):
        """Non-algorithmic components (e.g., protocols and related material) must not receive pqcmat: properties."""
        scored = score_cbom(self.cbom)

        non_algo = [
            c for c in scored["components"]
            if c.get("cryptoProperties", {}).get("assetType") != "algorithm"
        ]
        assert len(non_algo) > 0
        for comp in non_algo:
            props = comp.get("properties", [])
            pqcmat_props = [p for p in props if p.get("name", "").startswith("pqcmat:")]
            assert not pqcmat_props, (
                f"Non-algorithm component {comp.get('name')} unexpectedly has pqcmat: properties"
            )

    def test_crypto_asset_type_handled(self):
        """Test that CBOMs generated with the "crypto-asset" variant are scored
        and every algorithm is annotated with pqcmat: properties."""
        cbom = _load_fixture("sample-short-frmt-cbom.json")
        scored = score_cbom(cbom)

        crypto_assets_in = [c for c in cbom["components"] if c.get("type") == "crypto-asset"]
        assert crypto_assets_in, "No crypto-asset components in test file"

        # All crypto-asset components must appear in the scored output
        scored_ids = {c["bom-ref"]: c for c in scored["components"]}
        for comp in crypto_assets_in:
            assert comp["bom-ref"] in scored_ids, (
                f"crypto-asset component '{comp['name']}' was dropped by scorer"
            )

        # Every crypto-asset algorithm must be annotated with pqcmat: properties
        for comp in crypto_assets_in:
            if comp.get("cryptoProperties", {}).get("assetType") != "algorithm":
                continue
            scored_comp = scored_ids[comp["bom-ref"]]
            props = scored_comp.get("properties", [])
            assert props, f"crypto-asset algorithm '{comp['name']}' has no properties array"
            assert _get_prop(props, "pqcmat:risk-classification"), (
                f"crypto-asset algorithm '{comp['name']}' missing pqcmat:risk-classification"
            )


    # ── Pure function — input must not be mutated ──────────────────────────────

    def test_score_cbom_does_not_mutate_input(self):
        """score_cbom() must not modify the original CBOM dict."""
        original = copy.deepcopy(self.cbom)
        score_cbom(self.cbom)
        assert self.cbom == original, "score_cbom() mutated the input CBOM"

    # ── Specific classification assertions via scorer ──────────────────────────

    def test_rsa_component_is_quantum_vulnerable(self):
        scored = score_cbom(self.cbom)

        rsa = next(
            (c for c in scored["components"] if c.get("name") == "RSA"), None
        )
        assert rsa is not None
        classification = _get_prop(rsa.get("properties", []), "pqcmat:risk-classification")
        assert classification == "quantum-vulnerable"

    def test_mlkem768_component_is_non_hybrid(self):
        scored = score_cbom(self.cbom)

        mlkem = next(
            (c for c in scored["components"] if c.get("name") == "ML-KEM-768"), None
        )
        assert mlkem is not None
        classification = _get_prop(mlkem.get("properties", []), "pqcmat:risk-classification")
        assert classification == "non-hybrid"

    def test_aes256_component_is_quantum_safe(self):
        scored = score_cbom(self.cbom)

        aes256 = next(
            (c for c in scored["components"] if c.get("name") == "AES-256-GCM"), None
        )
        assert aes256 is not None
        classification = _get_prop(aes256.get("properties", []), "pqcmat:risk-classification")
        assert classification == "quantum-safe"
