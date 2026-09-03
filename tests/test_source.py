from pathlib import Path

from pseudepigrapha_tf.source import load_source_directory

FIXTURES = Path(__file__).parent / "fixtures"


def test_directory_loader_skips_empty_xml_and_reports_it(tmp_path):
    (tmp_path / "empty.xml").write_text("", encoding="utf-8")
    (tmp_path / "sample.xml").write_text((FIXTURES / "sample.xml").read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert [b.filename for b in books] == ["Sample"]
    assert any("empty.xml" in warning for warning in warnings)
