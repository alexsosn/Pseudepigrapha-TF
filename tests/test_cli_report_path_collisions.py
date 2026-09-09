from pathlib import Path

import json
import pytest

from pseudepigrapha_tf import cli
from pseudepigrapha_tf.distribution import feature_directory_identity

FIXTURES = Path(__file__).parent / "fixtures"


def _copy_source_fixture(tmp_path: Path) -> Path:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "sample.xml").write_text(
        (FIXTURES / "sample.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return source_dir


def _existing_stub_tf(output: Path) -> dict[str, bytes]:
    output.mkdir(parents=True, exist_ok=True)
    payloads = {
        "otype.tf": b"@node\n@valueType=str\n1\told-word\n",
        "oslots.tf": b"@edge\n1\t1\n",
    }
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
    return payloads


def _write_stub_tf(data, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "otype.tf").write_bytes(b"@node\n@valueType=str\n1\tword\n")
    (output / "oslots.tf").write_bytes(b"@edge\n1\t1\n")
    return True


def _assert_existing_generation(output: Path, expected: dict[str, bytes]) -> None:
    assert {name: (output / name).read_bytes() for name in expected} == expected


def _invoke_with_counted_writer(monkeypatch, source_dir: Path, output: Path, report_path: Path) -> int:
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
    return writer_calls


def test_cli_rejects_direct_tf_report_inside_output_before_write(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    output = tmp_path / "tf"
    original = _existing_stub_tf(output)

    writer_calls = _invoke_with_counted_writer(
        monkeypatch,
        source_dir,
        output,
        output / "otype.tf",
    )

    assert writer_calls == 0
    _assert_existing_generation(output, original)


def test_cli_rejects_report_symlink_targeting_tf_inside_output_before_write(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    output = tmp_path / "tf"
    original = _existing_stub_tf(output)
    report_path = tmp_path / "report.json"
    report_path.symlink_to(output / "otype.tf")

    writer_calls = _invoke_with_counted_writer(
        monkeypatch,
        source_dir,
        output,
        report_path,
    )

    assert writer_calls == 0
    assert report_path.is_symlink()
    _assert_existing_generation(output, original)


def test_cli_rejects_dotdot_alias_to_tf_inside_output_before_write(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    output = tmp_path / "tf"
    original = _existing_stub_tf(output)
    alias_dir = output / "reports"
    alias_dir.mkdir()
    report_path = alias_dir / ".." / "oslots.tf"

    writer_calls = _invoke_with_counted_writer(
        monkeypatch,
        source_dir,
        output,
        report_path,
    )

    assert writer_calls == 0
    _assert_existing_generation(output, original)


def test_cli_rejects_tf_named_report_symlink_entry_inside_output_before_write(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    output = tmp_path / "tf"
    original = _existing_stub_tf(output)
    external_target = tmp_path / "external-report.json"
    external_target.write_text('{"status":"old"}\n', encoding="utf-8")
    report_path = output / "report.tf"
    report_path.symlink_to(external_target)

    writer_calls = _invoke_with_counted_writer(
        monkeypatch,
        source_dir,
        output,
        report_path,
    )

    assert writer_calls == 0
    assert report_path.is_symlink()
    assert external_target.read_text(encoding="utf-8") == '{"status":"old"}\n'
    _assert_existing_generation(output, original)


def test_cli_rejects_nested_tf_report_inside_output_before_write(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    output = tmp_path / "tf"
    original = _existing_stub_tf(output)
    report_path = output / "reports" / "audit.tf"

    writer_calls = _invoke_with_counted_writer(
        monkeypatch,
        source_dir,
        output,
        report_path,
    )

    assert writer_calls == 0
    assert not report_path.parent.exists()
    _assert_existing_generation(output, original)


def test_cli_rejects_tf_report_through_symlinked_output_alias_before_write(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    real_output = tmp_path / "real-tf"
    original = _existing_stub_tf(real_output)
    output_alias = tmp_path / "tf-alias"
    output_alias.symlink_to(real_output, target_is_directory=True)

    writer_calls = _invoke_with_counted_writer(
        monkeypatch,
        source_dir,
        output_alias,
        output_alias / "otype.tf",
    )

    assert writer_calls == 0
    assert output_alias.is_symlink()
    _assert_existing_generation(real_output, original)


def test_cli_allows_tf_suffixed_report_outside_output(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    output = tmp_path / "tf"
    report_path = tmp_path / "reports" / "audit.tf"
    monkeypatch.setattr(cli, "_write_prevalidated_tf", _write_stub_tf)

    assert cli.main(
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
    ) == 0

    published = json.loads(report_path.read_text(encoding="utf-8"))
    assert published["status"] == "ok"
    assert published["text_fabric"] == feature_directory_identity(output)
