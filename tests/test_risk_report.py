"""
Tests for:
  SRS-015 — Include source code locations of detected cryptographic components.
"""

import json
import os
import shutil
import tempfile

from tor.vector_code.src.cbom_generator import generate_cbom
from tor.vector_score.cbom_scorer import score_cbom
from tor.vector_score.report_generator import generate_report

# Test files in tests/data/sarif: crypto-python.sarif, crypto-cpp.sarif
CONTENT = os.path.join(os.path.dirname(__file__), "data/sarif")
APP_NAME = "test-app"


class TestRiskReport:

    def setup_method(self):
        # Directory holding the multi-language SARIF fixtures
        self.sarif_dir = CONTENT
        # Temp output dir for the generated CBOM
        self.tmp = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def _load_json(path):
        with open(path) as f:
            return json.load(f)

    def test_components_retain_source_locations_after_merge(self):
        cbom_path = generate_cbom(self.sarif_dir, self.tmp, APP_NAME)
        result = self._load_json(cbom_path)

        sha256 = next(c for c in result["components"] if c["name"] == "SHA256")
        aes128 = next(c for c in result["components"] if c["name"] == "AES-128-CFB")

        sha256_locations = {(o["location"], o["line"]) for o in sha256["evidence"]["occurrences"]}
        assert ("tuf/api/_payload.py", 1217) in sha256_locations
        assert ("tuf/api/_payload.py", 1339) in sha256_locations
        assert aes128["evidence"]["occurrences"][0]["location"] == "src/gen_ssl_cert/gen_ssl_cert.cpp"
        assert aes128["evidence"]["occurrences"][0]["line"] == 189


    def test_report_shows_file_path_and_first_line(self):
        cbom_path = generate_cbom(self.sarif_dir, self.tmp, APP_NAME)
        cbom = self._load_json(cbom_path)
        report = generate_report(score_cbom(cbom))

        assert "src/gen_ssl_cert/gen_ssl_cert.cpp" in report
        assert "L1217" in report


    def test_report_lists_all_distinct_locations_for_one_component(self):
        cbom_path = generate_cbom(self.sarif_dir, self.tmp, APP_NAME)
        cbom = self._load_json(cbom_path)
        report = generate_report(score_cbom(cbom))

        assert "tuf/api/_payload.py" in report
        assert "L1217" in report
        assert "L1339" in report


    def test_report_renders_without_error_when_component_has_no_locations(self):
        cbom_path = generate_cbom(self.sarif_dir, self.tmp, APP_NAME)
        cbom = self._load_json(cbom_path)

        cbom["components"].append({
            "bom-ref": "alg-RSA",
            "type": "cryptographic-asset",
            "name": "RSA",
            "cryptoProperties": {
                "assetType": "algorithm",
                "algorithmProperties": {"primitive": "pke"},
            },
        })

        report = generate_report(score_cbom(cbom))
        assert "RSA" in report
