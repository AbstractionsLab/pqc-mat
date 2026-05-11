"""
Tests for cbom_scorer.py — CBOM annotation engine.

Covers TCS-013 (annotated CBOM contains pqcmat: properties), plus additional
correctness and non-mutation tests.
"""

import copy
import json
import os
import sys

import pytest

from vector_score.cbom_scorer import score_cbom


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "content")


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
    # ── TCS-013: annotated CBOM contains required pqcmat: properties ───────────

    def test_scored_cbom_has_pqcmat_properties(self):
        """TCS-013 steps 3a–3d: all algorithm components carry pqcmat: risk properties."""
        cbom = _load_fixture("sample_tls_cbom.json")
        scored = score_cbom(cbom)

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

            migration = _get_prop(props, "pqcmat:recommended-migration")
            assert migration is not None, f"Component {comp['name']} missing pqcmat:recommended-migration"

    def test_metadata_has_scored_at_property(self):
        """TCS-013 step 4: metadata.properties contains pqcmat:scored-at."""
        cbom = _load_fixture("sample_tls_cbom.json")
        scored = score_cbom(cbom)

        meta_props = scored.get("metadata", {}).get("properties", [])
        scored_at = _get_prop(meta_props, "pqcmat:scored-at")
        assert scored_at, "metadata.properties missing pqcmat:scored-at"

    # ── Non-algorithm components must not be annotated ─────────────────────────

    def test_non_algorithm_components_not_annotated(self):
        """Protocol and material components must not receive pqcmat: properties."""
        cbom = _load_fixture("sample_tls_cbom.json")
        scored = score_cbom(cbom)

        non_algo = [
            c for c in scored["components"]
            if c.get("cryptoProperties", {}).get("assetType") != "algorithm"
        ]
        for comp in non_algo:
            props = comp.get("properties", [])
            pqcmat_props = [p for p in props if p.get("name", "").startswith("pqcmat:")]
            assert not pqcmat_props, (
                f"Non-algorithm component {comp.get('name')} unexpectedly has pqcmat: properties"
            )

    # ── Both CBOM type variants must be handled ────────────────────────────────

    def test_cryptographic_asset_type_handled(self):
        """VECTOR-Network CBOMs use type: cryptographic-asset — scorer must annotate them."""
        cbom = _load_fixture("sample_tls_cbom.json")
        scored = score_cbom(cbom)

        # The TLS fixture uses 'cryptographic-asset'; verify at least one algo component scored
        scored_algos = [
            c for c in scored["components"]
            if c.get("type") == "cryptographic-asset"
            and c.get("cryptoProperties", {}).get("assetType") == "algorithm"
            and _get_prop(c.get("properties", []), "pqcmat:risk-classification")
        ]
        assert scored_algos, "No cryptographic-asset algorithm components were scored"

    def test_crypto_asset_type_handled(self):
        """VECTOR-Code CBOMs use type: crypto-asset — scorer must annotate them."""
        cbom = _load_fixture("sample_code_cbom.json")
        scored = score_cbom(cbom)

        scored_algos = [
            c for c in scored["components"]
            if c.get("type") == "crypto-asset"
            and c.get("cryptoProperties", {}).get("assetType") == "algorithm"
            and _get_prop(c.get("properties", []), "pqcmat:risk-classification")
        ]
        assert scored_algos, "No crypto-asset algorithm components were scored"

    def test_code_cbom_non_algorithm_components_not_annotated(self):
        """relatedCryptoMaterial components in VECTOR-Code CBOMs must not be annotated."""
        cbom = _load_fixture("sample_code_cbom.json")
        scored = score_cbom(cbom)

        material = [
            c for c in scored["components"]
            if c.get("cryptoProperties", {}).get("assetType") == "relatedCryptoMaterial"
        ]
        for comp in material:
            props = comp.get("properties", [])
            pqcmat_props = [p for p in props if p.get("name", "").startswith("pqcmat:")]
            assert not pqcmat_props, (
                f"relatedCryptoMaterial component {comp.get('name')} unexpectedly has pqcmat: properties"
            )

    # ── Pure function — input must not be mutated ──────────────────────────────

    def test_score_cbom_does_not_mutate_input(self):
        """score_cbom() must not modify the original CBOM dict."""
        cbom = _load_fixture("sample_tls_cbom.json")
        original = copy.deepcopy(cbom)
        score_cbom(cbom)
        assert cbom == original, "score_cbom() mutated the input CBOM"

    # ── Specific classification assertions via scorer ──────────────────────────

    def test_rsa_component_is_quantum_vulnerable(self):
        cbom = _load_fixture("sample_tls_cbom.json")
        scored = score_cbom(cbom)

        rsa = next(
            (c for c in scored["components"] if c.get("name") == "RSA"), None
        )
        assert rsa is not None
        classification = _get_prop(rsa.get("properties", []), "pqcmat:risk-classification")
        assert classification == "quantum-vulnerable"

    def test_mlkem768_component_is_post_quantum(self):
        cbom = _load_fixture("sample_tls_cbom.json")
        scored = score_cbom(cbom)

        mlkem = next(
            (c for c in scored["components"] if c.get("name") == "ML-KEM-768"), None
        )
        assert mlkem is not None
        classification = _get_prop(mlkem.get("properties", []), "pqcmat:risk-classification")
        assert classification == "post-quantum"

    def test_aes256_component_is_quantum_safe(self):
        cbom = _load_fixture("sample_tls_cbom.json")
        scored = score_cbom(cbom)

        aes256 = next(
            (c for c in scored["components"] if c.get("name") == "AES-256-GCM"), None
        )
        assert aes256 is not None
        classification = _get_prop(aes256.get("properties", []), "pqcmat:risk-classification")
        assert classification == "quantum-safe"
