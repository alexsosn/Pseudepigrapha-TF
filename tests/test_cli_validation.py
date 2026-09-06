from pathlib import Path

import pytest

from pseudepigrapha_tf import cli
from pseudepigrapha_tf.graph import TFData

FIXTURES = Path(__file__).parent / "fixtures"


class FakeFabric:
    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        return True


def _graph_snapshot(data):
    return (
        {name: dict(values) for name, values in data.node_features.items()},
        {
            name: {source: set(targets) for source, targets in values.items()}
            for name, values in data.edge_features.items()
        },
    )


def _copy_source_fixture(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "sample.xml").write_text(
        (FIXTURES / "sample.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return source_dir


def test_cli_validates_generated_graph_once(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)

    validate_calls = 0
    original_validate = TFData.validate
    original_report = cli.build_conversion_report

    def counted_validate(self):
        nonlocal validate_calls
        validate_calls += 1
        return original_validate(self)

    def read_only_report(source, books, data):
        node_snapshot, edge_snapshot = _graph_snapshot(data)
        report = original_report(source, books, data)
        assert data.node_features == node_snapshot
        assert data.edge_features == edge_snapshot
        return report

    monkeypatch.setattr(TFData, "validate", counted_validate)
    monkeypatch.setattr(cli, "build_conversion_report", read_only_report)

    import tf.fabric

    monkeypatch.setattr(tf.fabric, "Fabric", FakeFabric)
    result = cli.main(
        [
            "convert",
            str(source_dir),
            "--output",
            str(tmp_path / "tf"),
            "--upstream-commit",
            "test-commit",
        ]
    )

    assert result == 0
    assert validate_calls == 1


def test_cli_does_not_replace_existing_report_when_tf_serialization_fails(monkeypatch, tmp_path):
    source_dir = _copy_source_fixture(tmp_path)
    output = tmp_path / "tf"
    output.mkdir()
    report_path = output / "conversion-report.json"
    old_report = b'{"status":"previous-success"}\n'
    report_path.write_bytes(old_report)

    monkeypatch.setattr(cli, "_write_prevalidated_tf", lambda data, output_dir: False)

    with pytest.raises(SystemExit, match="Text-Fabric refused the generated dataset"):
        cli.main(
            [
                "convert",
                str(source_dir),
                "--output",
                str(output),
                "--upstream-commit",
                "test-commit",
            ]
        )

    assert report_path.read_bytes() == old_report
