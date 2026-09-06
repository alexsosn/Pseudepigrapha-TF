import subprocess
from pathlib import Path

from pseudepigrapha_tf import cli, provenance

FIXTURES = Path(__file__).parent / "fixtures"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_dirty_pinned_checkout_cannot_retain_verified_license(monkeypatch, tmp_path):
    repo = tmp_path / "ocp"
    source_dir = repo / "static" / "docs"
    source_dir.mkdir(parents=True)
    sample = source_dir / "sample.xml"
    fixture_text = (FIXTURES / "sample.xml").read_text(encoding="utf-8")
    sample.write_text(fixture_text, encoding="utf-8")

    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Pseudepigrapha-TF tests")
    _git(repo, "add", "static/docs/sample.xml")
    _git(repo, "commit", "-m", "fixture source")
    commit = _git(repo, "rev-parse", "HEAD")

    # Reuse the production profile logic with this disposable commit as the
    # supported pin so the test exercises cleanliness independently of SHA value.
    monkeypatch.setattr(provenance, "OCP_PIN", commit)

    captured = {}

    def capture_writer(data, output_dir):
        captured.clear()
        captured.update(data.metadata[""])
        return True

    monkeypatch.setattr(cli, "_write_prevalidated_tf", capture_writer)

    assert cli.main(["convert", str(source_dir), "--output", str(tmp_path / "clean-tf")]) == 0
    assert captured["sourceIdentityStatus"] == "verified"
    assert captured["contentLicenseStatus"] == "verified"

    sample.write_text(fixture_text + "\n", encoding="utf-8")

    assert cli.main(["convert", str(source_dir), "--output", str(tmp_path / "dirty-tf")]) == 0
    assert captured["upstreamCommit"] == commit
    assert captured["sourceIdentityStatus"] == "unverified"
    assert captured["contentLicenseStatus"] == "unverified"
    assert "contentLicense" not in captured

    # Restore the tracked source, then add another XML file that the converter
    # would ingest but Git does not know about. HEAD still matches; provenance
    # must nevertheless stay unverified because the converted corpus is not the
    # committed source tree.
    _git(repo, "checkout", "--", "static/docs/sample.xml")
    extra = source_dir / "Extra.xml"
    extra.write_text(fixture_text.replace('filename="Sample"', 'filename="Extra"'), encoding="utf-8")

    assert cli.main(["convert", str(source_dir), "--output", str(tmp_path / "untracked-tf")]) == 0
    assert captured["sourceIdentityStatus"] == "unverified"
    assert captured["contentLicenseStatus"] == "unverified"
    assert "contentLicense" not in captured
