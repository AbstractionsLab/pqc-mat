"""
Tests for cbom_generator.generate_cbom.
"""

import json
import os
import shutil
import subprocess
import tempfile
from unittest.mock import patch

from tor.vector_code.src.cbom_generator import generate_cbom

# Test files in tests/data/sarif: crypto-python.sarif, crypto-cpp.sarif
CONTENT = os.path.join(os.path.dirname(__file__), "data/sarif")
APP_NAME = "test-app"


class TestGenerateCbom:

    @classmethod
    def setup_class(cls):
        # Directory for multiple-language test case
        cls.sarif_multi = CONTENT

    def setup_method(self):
        # Create a temporal root dir
        self.tmp_test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        # Remove the temp dir after each test.
        shutil.rmtree(self.tmp_test_dir, ignore_errors=True)

    def _dir_with_file(self, filename, src=None):
        """Make a fresh subdir under tmp_test_dir holding exactly one file.

        Copies CONTENT/<src> in when src is given; otherwise creates an
        empty file. Returns the directory path.
        """
        d = tempfile.mkdtemp(dir=self.tmp_test_dir)
        dest = os.path.join(d, filename)
        if src:
            shutil.copy(os.path.join(CONTENT, src), dest)
        else:
            open(dest, "w").close()
        return d

    @staticmethod
    def _load_json(path):
        with open(path) as f:
            return json.load(f)

    def test_single_sarif_cbom_output_file(self):
        "Test that the cbom file is created at the correct path"
        sarif_single = self._dir_with_file("crypto-python.sarif", src="crypto-python.sarif")
        result = generate_cbom(sarif_single, self.tmp_test_dir, APP_NAME)
        assert result is not None
        assert os.path.isabs(result)
        assert os.path.isfile(result)
        # the generated CBOM is saved in the given output arg
        assert os.path.dirname(result) == self.tmp_test_dir
        assert os.path.basename(result) == "crypto-python-cbom.json"

    def test_output_is_cbom(self):
        sarif_single = self._dir_with_file("crypto-cpp.sarif", src="crypto-cpp.sarif")
        result = generate_cbom(sarif_single, self.tmp_test_dir, APP_NAME)
        data = self._load_json(result)
        assert isinstance(data, dict)
        assert data["bomFormat"] == "CycloneDX"
        assert data["specVersion"] == "1.6"

    def test_multi_sarif_output_named_combined(self):
        result = generate_cbom(self.sarif_multi, self.tmp_test_dir, APP_NAME)
        assert os.path.dirname(result) == self.tmp_test_dir
        assert os.path.basename(result) == "crypto-combined-cbom.json"

    def test_combined_cbom_contains_components_from_both_languages(self):
        result = generate_cbom(self.sarif_multi, self.tmp_test_dir, APP_NAME)
        cbom = self._load_json(result)
        names = [c["name"] for c in cbom["components"]]
        assert "SHA256" in names        # from the Python SARIF
        assert "AES-128-CFB" in names   # from the C++ SARIF

    def test_no_per_language_cbom_files_written(self):
        generate_cbom(self.sarif_multi, self.tmp_test_dir, APP_NAME)
        cbom_files = [f for f in os.listdir(self.tmp_test_dir) if f.endswith("-cbom.json")]
        assert cbom_files == ["crypto-combined-cbom.json"]

    def test_single_valid_json_sarif_cbom_output(self):
        """Test that a CBOM is created from a folder with only a valid SARIF file
        saved as .json"""
        json_dir = self._dir_with_file("crypto-cpp.json", src="crypto-cpp.sarif")
        result = generate_cbom(json_dir, self.tmp_test_dir, APP_NAME)
        assert os.path.basename(result) == "crypto-cpp-cbom.json"

    def test_single_invalid_json_sarif_cbom_output(self, capsys):
        """Test that no CBOM is created from a folder with only
        an invalid SARIF file saved as .json"""
        # An empty .json file is not valid SARIF, so cryptobom produces no output
        json_dir = self._dir_with_file("crypto.json")
        result = generate_cbom(json_dir, self.tmp_test_dir, APP_NAME)
        # generate_cbom returns None and reports the error.
        assert result is None
        assert "Error generating CBOM" in capsys.readouterr().out

    def test_returns_none_for_unsupported_single_file(self):
        other_dir = self._dir_with_file("notes.txt")
        assert generate_cbom(other_dir, self.tmp_test_dir, APP_NAME) is None

    def test_returns_none_on_subprocess_failure(self):
        with patch("tor.vector_code.src.cbom_generator.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "cryptobom", stderr="tool error")
            result = generate_cbom(self.sarif_multi, self.tmp_test_dir, APP_NAME)
        assert result is None

    def test_returns_none_on_normalisation_failure(self):
        with patch("tor.vector_code.src.cbom_generator.subprocess.run"), \
             patch("tor.vector_code.src.cbom_generator.normalise_file", side_effect=RuntimeError("bad")):
            result = generate_cbom(self.sarif_multi, self.tmp_test_dir, APP_NAME)
        assert result is None
