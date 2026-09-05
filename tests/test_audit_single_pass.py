from pathlib import Path

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


FIXTURES = Path(__file__).parent / "fixtures"


def test_semantic_audit_reads_special_structure_source_once(tmp_path, monkeypatch):
    source = FIXTURES / "ellipsis.xml"
    target = tmp_path / source.name
    target.write_bytes(source.read_bytes())
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    data = build_tf_data(books)

    original_read_bytes = Path.read_bytes
    source_reads: list[str] = []

    def counted_read_bytes(path: Path) -> bytes:
        if path.parent == tmp_path and path.suffix == ".xml":
            source_reads.append(path.name)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read_bytes)

    report = build_conversion_report(tmp_path, books, data)

    assert report["status"] == "ok", report["failed_checks"]
    assert report["source"]["ellipses"] == report["graph"]["ellipses"] == 1
    assert source_reads == [source.name]
