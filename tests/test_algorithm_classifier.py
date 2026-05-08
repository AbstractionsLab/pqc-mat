"""
Tests for algorithm_classifier.py — quantum risk classification logic.

Covers TCS-011 (quantum-vulnerable classification) and TCS-012 (post-quantum classification),
plus additional cases for quantum-safe, quantum-weakened, classically-deprecated, and unknown.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tor", "VECTOR-Score"))

from algorithm_classifier import classify, RiskClassification


class TestAlgorithmClassifier:
    # ── TCS-011: quantum-vulnerable algorithms ──────────────────────────────────

    def test_rsa_is_quantum_vulnerable(self):
        """TCS-011 step 2: RSA classified as quantum-vulnerable."""
        result = classify("RSA", "pke", None)
        assert result.classification == "quantum-vulnerable"
        assert result.risk_score == "high"

    def test_ecdhe_is_quantum_vulnerable(self):
        """TCS-011 step 3: ECDHE classified as quantum-vulnerable."""
        result = classify("ECDHE", "key-agree", None)
        assert result.classification == "quantum-vulnerable"
        assert result.risk_score == "high"

    def test_dhe_is_quantum_vulnerable(self):
        """TCS-011 step 4: DHE classified as quantum-vulnerable."""
        result = classify("DHE", "key-agree", None)
        assert result.classification == "quantum-vulnerable"
        assert result.risk_score == "high"

    def test_ecdsa_is_quantum_vulnerable(self):
        """TCS-011 step 5: ECDSA classified as quantum-vulnerable."""
        result = classify("ECDSA", "signature", None)
        assert result.classification == "quantum-vulnerable"
        assert result.risk_score == "high"

    def test_dsa_is_quantum_vulnerable(self):
        result = classify("DSA", "signature", None)
        assert result.classification == "quantum-vulnerable"
        assert result.risk_score == "high"

    def test_x25519_is_quantum_vulnerable(self):
        result = classify("X25519", "key-agree", None)
        assert result.classification == "quantum-vulnerable"
        assert result.risk_score == "high"

    def test_ecdh_variants_are_quantum_vulnerable(self):
        for name in ["ECDH", "ECDH/RSA", "ECDH/ECDSA"]:
            result = classify(name, "key-agree", None)
            assert result.classification == "quantum-vulnerable", f"Expected quantum-vulnerable for {name}"

    def test_ffdhe2048_is_quantum_vulnerable(self):
        result = classify("ffdhe2048", "dh", None)
        assert result.classification == "quantum-vulnerable"

    # ── TCS-012: post-quantum algorithms ───────────────────────────────────────

    def test_mlkem768_is_post_quantum(self):
        """TCS-012 step 2: ML-KEM-768 classified as post-quantum."""
        result = classify("ML-KEM-768", "kem", None)
        assert result.classification == "post-quantum"
        assert result.risk_score == "none"

    def test_mlkem1024_is_post_quantum(self):
        """TCS-012 step 3: ML-KEM-1024 classified as post-quantum."""
        result = classify("ML-KEM-1024", "kem", None)
        assert result.classification == "post-quantum"
        assert result.risk_score == "none"

    def test_mldsa65_is_post_quantum(self):
        """TCS-012 step 4: ML-DSA-65 classified as post-quantum."""
        result = classify("ML-DSA-65", "signature", None)
        assert result.classification == "post-quantum"
        assert result.risk_score == "none"

    def test_slhdsa_is_post_quantum(self):
        """TCS-012 step 5: SLH-DSA classified as post-quantum."""
        result = classify("SLH-DSA", "signature", None)
        assert result.classification == "post-quantum"
        assert result.risk_score == "none"

    def test_mlkem512_is_post_quantum(self):
        result = classify("ML-KEM-512", "kem", None)
        assert result.classification == "post-quantum"

    def test_crystals_kyber_is_post_quantum(self):
        result = classify("CRYSTALS-Kyber-768", "kem", None)
        assert result.classification == "post-quantum"

    def test_sntrup761_is_post_quantum(self):
        result = classify("sntrup761", "kem", None)
        assert result.classification == "post-quantum"

    # ── Quantum-safe algorithms ─────────────────────────────────────────────────

    def test_aes256_gcm_is_quantum_safe(self):
        result = classify("AES-256-GCM", "block-cipher", "256")
        assert result.classification == "quantum-safe"
        assert result.risk_score == "none"

    def test_sha256_is_quantum_safe(self):
        result = classify("SHA-256", "hash", "256")
        assert result.classification == "quantum-safe"
        assert result.risk_score == "none"

    def test_sha384_is_quantum_safe(self):
        result = classify("SHA-384", "hash", "384")
        assert result.classification == "quantum-safe"

    def test_sha512_is_quantum_safe(self):
        result = classify("SHA-512", "hash", "512")
        assert result.classification == "quantum-safe"

    def test_chacha20_poly1305_is_quantum_safe(self):
        result = classify("ChaCha20-Poly1305", "ae", None)
        assert result.classification == "quantum-safe"

    # ── Quantum-weakened algorithms ─────────────────────────────────────────────

    def test_aes128_is_quantum_weakened(self):
        result = classify("AES-128-GCM", "block-cipher", "128")
        assert result.classification == "quantum-weakened"
        assert result.risk_score == "medium"

    def test_sha1_is_quantum_weakened(self):
        result = classify("SHA-1", "hash", None)
        assert result.classification == "quantum-weakened"
        assert result.risk_score == "medium"

    def test_3des_is_quantum_weakened(self):
        result = classify("3DES-EDE", "block-cipher", None)
        assert result.classification == "quantum-weakened"

    # ── Classically deprecated algorithms ──────────────────────────────────────

    def test_rc4_is_classically_deprecated(self):
        result = classify("RC4", "stream-cipher", None)
        assert result.classification == "classically-deprecated"
        assert result.risk_score == "high"

    def test_des_is_classically_deprecated(self):
        result = classify("DES", "block-cipher", None)
        assert result.classification == "classically-deprecated"

    def test_md5_is_classically_deprecated(self):
        result = classify("MD5", "hash", None)
        assert result.classification == "classically-deprecated"

    def test_null_cipher_is_classically_deprecated(self):
        result = classify("NULL", None, None)
        assert result.classification == "classically-deprecated"

    # ── Hybrid algorithms ───────────────────────────────────────────────────────

    def test_x25519mlkem768_is_hybrid(self):
        result = classify("X25519MLKEM768", None, None)
        assert result.classification == "hybrid"
        assert result.risk_score == "low"

    def test_secp256r1mlkem768_is_hybrid(self):
        result = classify("SecP256r1MLKEM768", None, None)
        assert result.classification == "hybrid"

    # ── Unknown algorithm ───────────────────────────────────────────────────────

    def test_unknown_algorithm_returns_unknown(self):
        result = classify("SuperQuantumAlgo9000", None, None)
        assert result.classification == "unknown"

    def test_empty_name_returns_unknown(self):
        result = classify("", None, None)
        assert result.classification == "unknown"

    # ── Return type ─────────────────────────────────────────────────────────────

    def test_returns_risk_classification_dataclass(self):
        result = classify("RSA", "pke", None)
        assert isinstance(result, RiskClassification)
        assert result.classification
        assert result.risk_score
        assert result.rationale
        assert result.recommended_migration
        assert isinstance(result.references, list)

    def test_references_is_non_empty_for_known_algorithm(self):
        result = classify("RSA", "pke", None)
        assert len(result.references) > 0
