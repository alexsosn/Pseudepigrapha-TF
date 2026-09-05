from pathlib import Path

from pseudepigrapha_tf import cli
from pseudepigrapha_tf.graph import TFData

FIXTURES = Path(__file__).parent / "fixtures"


class FakeFabric:
    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        return True


def test_cli_validates_generated_graph_once(monkeypatch, tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "sample.xml").write_text(
        (FIXTURES / "sample.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    validate_calls = 0
    original_validate = TFData.validate

    def counted_validate(self):
        nonlocal validate_calls
        validate_calls += 1
        return original_validate(self)

    monkeypatch.setattr(TFData, "validate", counted_validate)

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
