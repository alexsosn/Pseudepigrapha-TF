"""RED-first source-file/work identity tests for input without intros.json."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pseudepigrapha_tf.parser import InvalidSourceError
from pseudepigrapha_tf.source import load_source_directory


SAMPLE = Path(__file__).parent / "fixtures" / "sample.xml"


@pytest.mark.parametrize("name", ["Another.xml", "sample.xml"])
def test_source_rejects_book_identity_differing_from_xml_stem_without_intros(
    tmp_path: Path, name: str
) -> None:
    (tmp_path / name).write_bytes(SAMPLE.read_bytes())
    assert not (tmp_path / "intros.json").exists()
    with pytest.raises(InvalidSourceError) as exc:
        load_source_directory(tmp_path)
    assert name in str(exc.value)
    assert "Sample" in str(exc.value)
    assert "filename" in str(exc.value).lower()


def test_source_accepts_exact_book_identity_without_intros_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    raw = SAMPLE.read_bytes()
    (tmp_path / "Sample.xml").write_bytes(raw)
    assert not (tmp_path / "intros.json").exists()
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    assert len(books) == 1
    assert books[0].filename == "Sample"
    assert books[0].source_path == "Sample.xml"
    assert books[0].source_sha256 == hashlib.sha256(raw).hexdigest()


def test_source_skips_empty_xml_even_when_basename_has_no_book_identity(
    tmp_path: Path,
) -> None:
    (tmp_path / "Empty.xml").write_bytes(b"")
    (tmp_path / "Sample.xml").write_bytes(SAMPLE.read_bytes())
    books, warnings = load_source_directory(tmp_path)
    assert [book.filename for book in books] == ["Sample"]
    assert any("Empty.xml" in item for item in warnings)
