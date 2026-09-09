from pathlib import Path

import pytest

from pseudepigrapha_tf import cli
from pseudepigrapha_tf.graph import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


def _copy_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.xml").write_text(
        (FIXTURES / "sample.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return source


def _sentinel_generation(output: Path) -> dict[str, bytes]:
    output.mkdir(parents=True, exist_ok=True)
    payloads = {
        "otype.tf": b"OLD OTYPE SENTINEL\n",
        "oslots.tf": b"OLD OSLOTS SENTINEL\n",
    }
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
    return payloads


def _invoke(source: Path, output: Path) -> int:
    return cli.main(
        [
            "convert",
            str(source),
            "--output",
            str(output),
            "--upstream-commit",
            "test-commit",
        ]
    )


def test_cli_rejects_final_component_output_symlink_before_writer_or_report(monkeypatch, tmp_path):
    source = _copy_source(tmp_path)
    real_output = tmp_path / "real-tf"
    original = _sentinel_generation(real_output)
    output_alias = tmp_path / "tf-alias"
    output_alias.symlink_to(real_output, target_is_directory=True)
    writer_calls = 0

    def mutating_writer(data, output_dir):
        nonlocal writer_calls
        writer_calls += 1
        # If the pre-write gate is missing, make the failure-atomicity violation
        # deterministic rather than depending on Text-Fabric serializer details.
        (Path(output_dir) / "otype.tf").write_bytes(b"NEW GENERATION\n")
        return True

    monkeypatch.setattr(cli, "_write_prevalidated_tf", mutating_writer)

    with pytest.raises(ValueError, match="output.*symlink|symlink.*output"):
        try:
            _invoke(source, output_alias)
        finally:
            assert writer_calls == 0
            assert {
                name: (real_output / name).read_bytes()
                for name in original
            } == original
            assert not (real_output / "conversion-report.json").exists()

    assert output_alias.is_symlink()


def test_cli_accepts_real_output_directory(monkeypatch, tmp_path):
    source = _copy_source(tmp_path)
    output = tmp_path / "tf"
    writer_calls = 0

    def writer(data, output_dir):
        nonlocal writer_calls
        writer_calls += 1
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        (target / "otype.tf").write_bytes(b"@node\n\n1\tword\n")
        (target / "oslots.tf").write_bytes(b"@edge\n\n")
        return True

    monkeypatch.setattr(cli, "_write_prevalidated_tf", writer)

    assert _invoke(source, output) == 0
    assert writer_calls == 1
    assert (output / "conversion-report.json").is_file()


def test_cli_accepts_real_output_reached_through_symlinked_parent(monkeypatch, tmp_path):
    source = _copy_source(tmp_path)
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    parent_alias = tmp_path / "parent-alias"
    parent_alias.symlink_to(real_parent, target_is_directory=True)
    output = parent_alias / "tf"
    output.mkdir()
    assert not output.is_symlink()
    writer_calls = 0

    def writer(data, output_dir):
        nonlocal writer_calls
        writer_calls += 1
        target = Path(output_dir)
        (target / "otype.tf").write_bytes(b"@node\n\n1\tword\n")
        (target / "oslots.tf").write_bytes(b"@edge\n\n")
        return True

    monkeypatch.setattr(cli, "_write_prevalidated_tf", writer)

    assert _invoke(source, output) == 0
    assert writer_calls == 1
    assert (real_parent / "tf" / "conversion-report.json").is_file()


def test_cli_accepts_dotdot_spelling_of_real_output(monkeypatch, tmp_path):
    source = _copy_source(tmp_path)
    lexical_parent = tmp_path / "lex"
    lexical_parent.mkdir()
    real_output = tmp_path / "tf"
    real_output.mkdir()
    output = lexical_parent / ".." / "tf"
    assert not output.is_symlink()
    writer_calls = 0

    def writer(data, output_dir):
        nonlocal writer_calls
        writer_calls += 1
        target = Path(output_dir)
        (target / "otype.tf").write_bytes(b"@node\n\n1\tword\n")
        (target / "oslots.tf").write_bytes(b"@edge\n\n")
        return True

    monkeypatch.setattr(cli, "_write_prevalidated_tf", writer)

    assert _invoke(source, output) == 0
    assert writer_calls == 1
    assert (real_output / "conversion-report.json").is_file()


def test_direct_writer_api_keeps_symlink_destination_support(tmp_path):
    real_output = tmp_path / "real-tf"
    real_output.mkdir()
    output_alias = tmp_path / "tf-alias"
    output_alias.symlink_to(real_output, target_is_directory=True)
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])

    assert write_tf(data, output_alias)
    assert output_alias.is_symlink()
    assert (real_output / "otype.tf").is_file()
