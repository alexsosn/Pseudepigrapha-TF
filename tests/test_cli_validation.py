from pathlib import Path

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


def test_cli_validates_generated_graph_once(monkeypatch, tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "sample.xml").write_text(
        (FIXTURES / "sample.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

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
