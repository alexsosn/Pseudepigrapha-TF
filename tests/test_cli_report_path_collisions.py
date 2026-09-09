from pathlib import Path

import pytest

from pseudepigrapha_tf import cli

FIXTURES = Path(__file__).parent / "fixtures"


def _copy_source_fixture(tmp_path: Path) -> Path:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "sample.xml").write_text(
        (FIXTURES / "sample.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return source_dir


def test_cli_rejects_tf_named_report_symlink_entry_inside_output_before_write(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    output = tmp_path / "tf"
    output.mkdir()
    original = {
        "otype.tf": b"@node\n@valueType=str\n1\told-word\n",
        "oslots.tf": b"@edge\n1\t1\n",
    }
    for name, payload in original.items():
        (output / name).write_bytes(payload)

    external_target = tmp_path / "external-report.json"
    external_target.write_text('{"status":"old"}\n', encoding="utf-8")
    report_path = output / "report.tf"
    report_path.symlink_to(external_target)
    writer_calls = 0

    def counted_writer(data, output_dir):
        nonlocal writer_calls
        writer_calls += 1
        return True

    monkeypatch.setattr(cli, "_write_prevalidated_tf", counted_writer)

    with pytest.raises(ValueError, match="report.*Text-Fabric|Text-Fabric.*report"):
        cli.main(
            [
                "convert",
                str(source_dir),
                "--output",
                str(output),
                "--report",
                str(report_path),
                "--upstream-commit",
                "test-commit",
            ]
        )

    assert writer_calls == 0
    assert report_path.is_symlink()
    assert external_target.read_text(encoding="utf-8") == '{"status":"old"}\n'
    assert {name: (output / name).read_bytes() for name in original} == original
