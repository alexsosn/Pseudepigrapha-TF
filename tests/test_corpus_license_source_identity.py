from pathlib import Path

from pseudepigrapha_tf import cli
from pseudepigrapha_tf.provenance import OCP_PIN

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_override_cannot_verify_license_for_non_git_source(monkeypatch, tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "sample.xml").write_text(
        (FIXTURES / "sample.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    captured = {}

    def capture_writer(data, output_dir):
        captured.update(data.metadata[""])
        return True

    monkeypatch.setattr(cli, "_write_prevalidated_tf", capture_writer)

    assert cli.main(
        [
            "convert",
            str(source_dir),
            "--output",
            str(tmp_path / "tf"),
            "--upstream-commit",
            OCP_PIN,
        ]
    ) == 0

    assert captured["upstreamCommit"] == OCP_PIN
    assert captured["contentLicenseStatus"] == "unverified"
    assert "contentLicense" not in captured
    assert "upstreamLicenseCommit" not in captured
