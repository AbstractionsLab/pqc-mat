import glob
import json
import os
import shutil
import socket
import subprocess
import tempfile
from unittest.mock import patch
import pytest
from tor.vector_code.main import run
from tor.vector_code.src.github_resolver import _parse_github_url, resolve

SMALL_TEST_REPO = "https://github.com/kokke/tiny-AES-c"

def _github_reachable(timeout=3):
    try:
        socket.create_connection(("github.com", 443), timeout=timeout).close()
        return True
    except OSError:
        return False


def _codeql_available():
    return shutil.which("codeql") is not None and os.path.isdir(
        "/home/vector/tools/codeql-queries"
    )


requires_network = pytest.mark.skipif(
    not _github_reachable(),
    reason="github.com is not reachable from this environment",
)

requires_codeql = pytest.mark.skipif(
    not _codeql_available(),
    reason="CodeQL CLI and/or query checkout not available in this environment",
)


class TestGithubResolver:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_github_resolver_")
        self.output_dir = os.path.join(self.tmp_dir, "output")
        os.makedirs(self.output_dir)

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


    @requires_network
    @requires_codeql
    def test_run_completes_github_scan(self):
        # all vector_code_* directories that exist at the temp system folder (e.g. `/tmp`)
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "vector_code_*")))
        rc = run(SMALL_TEST_REPO, "application", self.output_dir)

        assert rc == 0
        cbom_files = glob.glob(os.path.join(self.output_dir, "cbom", "*.json"))
        assert cbom_files

        with open(cbom_files[0]) as f:
            cbom = json.load(f)
        assert cbom.get("bomFormat") == "CycloneDX"
        assert cbom.get("metadata", {}).get("component", {}).get("name") == "kokke/tiny-AES-c"
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "vector_code_*")))
        assert after == before

    @requires_network
    def test_run_fails_explicitly_for_inexistent_repository(self, capsys):
        """Check that an appropriate message is displayed when a Github repository
        does not exist
        """
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "vector_code_*")))

        rc = run(
            "https://github.com/vector-tor-integration-test/"
            "non_existent_repository",
            "application",
            self.output_dir,
        )

        assert rc == 1
        assert not os.path.isdir(os.path.join(self.output_dir, "databases"))
        assert not os.path.isdir(os.path.join(self.output_dir, "cbom"))
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "vector_code_*")))
        assert after == before

        output = capsys.readouterr().out
        assert "Error: git clone failed" in output
        assert "may be private and require authentication" in output

    def test_run_fails_for_a_non_github_url(self, capsys):
        rc = run("https://gitlab.com/owner/repo", "application", self.output_dir)
        assert rc == 1
        assert not os.path.isdir(os.path.join(self.output_dir, "databases"))
        assert not os.path.isdir(os.path.join(self.output_dir, "cbom"))

        output = capsys.readouterr().out
        assert "Error: Path" in output
        assert "does not exist" in output

    def test_url_with_ref_clones_selected_branch(self):
        """Verify that a /tree/<ref> URL is cloned with `--branch <ref>`
        to ensure that the selected branch or tag is checked out."""
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch(
            "tor.vector_code.src.github_resolver.subprocess.run",
            return_value=completed,
        ) as mock_run:
            result = resolve("https://github.com/DaveGamble/cJSON/tree/v1.7.18")

        try:
            executed_cmd = mock_run.call_args.args[0]
            assert "--branch" in executed_cmd
            assert executed_cmd[executed_cmd.index("--branch") + 1] == "v1.7.18"
            assert "https://github.com/DaveGamble/cJSON.git" in executed_cmd
            assert result.app_name == "DaveGamble/cJSON"
        finally:
            result.cleanup()

    def test_ssh_url_is_rejected_with_an_informative_message(self):
        with pytest.raises(ValueError) as exc_info:
            _parse_github_url("git@github.com:owner/repo.git")
        message = str(exc_info.value)
        assert "SSH-style GitHub URLs are not supported" in message
        assert "https://github.com/<owner>/<repo>" in message

    @requires_network
    def test_resolve_returns_subpath_when_it_exists_in_clone(self):
        result = resolve(f"https://github.com/DaveGamble/cJSON/tree/v1.7.18/tests")
        try:
            assert result.path == os.path.join(result.clone_root, "tests")
            assert os.path.isdir(result.path)
            assert os.listdir(result.path)
        finally:
            result.cleanup()
 
    @requires_network
    def test_resolve_raises_raw_git_error_when_destination_already_exists(self):
        occupied_dir = tempfile.mkdtemp(prefix="test_dest_conflict_")
        with open(os.path.join(occupied_dir, "junk.txt"), "w") as f:
            f.write("occupied")
        try:
            with patch("tor.vector_code.src.github_resolver.tempfile.mkdtemp", return_value=occupied_dir):
                with pytest.raises(RuntimeError) as exc_info:
                    resolve("https://github.com/DaveGamble/cJSON")
            message = str(exc_info.value)
            assert "already exists and is not an empty directory" in message
            assert "may be private and require authentication" not in message
        finally:
            shutil.rmtree(occupied_dir, ignore_errors=True)

    def test_run_fails_with_raw_git_error_when_proxy_is_unreachable(self, monkeypatch, capsys):
        monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "vector_code_*")))
        rc = run("https://github.com/DaveGamble/cJSON", "application", self.output_dir)
 
        assert rc == 1
        assert not os.path.isdir(os.path.join(self.output_dir, "databases"))
        assert not os.path.isdir(os.path.join(self.output_dir, "cbom"))
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "vector_code_*")))
        assert after == before
 
        output = capsys.readouterr().out
        assert "Error: git clone failed for" in output
        assert any(
            phrase in output
            for phrase in ("Connection refused", "Failed to connect")
        )
        assert "may be private and require authentication" not in output