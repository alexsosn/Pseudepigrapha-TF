"""RED regression for Git index flags that conceal changed source XML (#204)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pseudepigrapha_tf import cli, provenance
from pseudepigrapha_tf.source import git_source_is_clean

FIXTURE = Path(__file__).parent / "fixtures" / "sample.xml"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _checkout(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    repo = tmp_path / "ocp"
    source_dir = repo / "static" / "docs"
    source_dir.mkdir(parents=True)
    path = source_dir / "Sample.xml"
    path.write_bytes(FIXTURE.read_bytes())
    _git(repo, "init")
    _git(repo, "config", "user.name", "Pseudepigrapha-TF tests")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "add", "static/docs/Sample.xml")
    _git(repo, "commit", "-m", "pinned sample")
    return repo, source_dir, path, _git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize("flag,index_tag", [
    ("--assume-unchanged", "h"),
    ("--skip-worktree", "S"),
])
def test_dirty_xml_cannot_be_verified_when_git_index_flag_hides_edit(
    tmp_path, flag, index_tag
):
    repo, source_dir, path, _ = _checkout(tmp_path)
    assert git_source_is_clean(source_dir)
    path.write_bytes(path.read_bytes() + b"\n")
    assert _git(source_dir, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "--", ".")
    _git(repo, "update-index", flag, "static/docs/Sample.xml")
    assert _git(source_dir, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "--", ".") == ""
    assert _git(source_dir, "ls-files", "-v", "--", ".").startswith(index_tag + " ")
    assert not git_source_is_clean(source_dir)


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_index_flag_is_not_proof_of_worktree_identity_even_when_bytes_current(
    tmp_path, flag
):
    repo, source_dir, _, _ = _checkout(tmp_path)
    assert git_source_is_clean(source_dir)
    _git(repo, "update-index", flag, "static/docs/Sample.xml")
    # Deliberate conservative policy: Git is configured not to check these
    # working files, so a status-only attestation is insufficient.
    assert _git(source_dir, "status", "--porcelain=v1", "--", ".") == ""
    assert not git_source_is_clean(source_dir)


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_cli_conversion_can_proceed_but_must_downgrade_hidden_dirty_source(
    monkeypatch, tmp_path, flag
):
    repo, source_dir, path, commit = _checkout(tmp_path)
    path.write_bytes(path.read_bytes() + b"\n")
    _git(repo, "update-index", flag, "static/docs/Sample.xml")
    assert _git(source_dir, "status", "--porcelain=v1", "--", ".") == ""
    monkeypatch.setattr(provenance, "OCP_PIN", commit)
    captured = {}

    def capture_writer(data, output_dir, *, after_install=None, publication_committed=None):
        captured.update(data.metadata[""])
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "otype.tf").write_text(
            "@node\n@valueType=str\n\n1\tword\n", encoding="utf-8"
        )
        if after_install is not None:
            after_install()
        return True

    monkeypatch.setattr(cli, "_write_prevalidated_tf", capture_writer)
    assert cli.main(["convert", str(source_dir), "--output", str(tmp_path / "tf")]) == 0
    assert captured["upstreamCommit"] == commit
    assert captured["sourceIdentityStatus"] == "unverified"
    assert captured["contentLicenseStatus"] == "unverified"
    assert "contentLicense" not in captured
