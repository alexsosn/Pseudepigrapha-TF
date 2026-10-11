"""RED: reuse validated source XML models without a second full parse (#213)."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from pseudepigrapha_tf import cli, metadata
from pseudepigrapha_tf.source import load_source_directory


TEMPLATE = '''<book filename="{name}" title="{name}">
  <version title="Greek" author="Anonymous" language="Greek">
    <divisions><division label="Chapter" delimiter="."/></divisions>
    <manuscripts><ms abbrev="A" language="Greek" show="yes"><name>A</name></ms></manuscripts>
    <text><div number="1"><unit id="1"><reading option="0" mss="A ">alpha beta</reading></unit></div></text>
  </version>
</book>
'''


def _docs(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ("One", "Two"):
        (docs / f"{name}.xml").write_text(TEMPLATE.format(name=name), encoding="utf-8")
    (docs / "Empty.xml").write_text(" \n\t", encoding="utf-8")
    (docs / "intros.json").write_text(
        json.dumps({"documents": {
            "One.xml": {"title": "One", "version": 1.0, "fields": {"status": "valid"}},
            "Empty.xml": {"title": "Empty", "version": None, "fields": {}},
        }}),
        encoding="utf-8",
    )
    return docs


def test_preparsed_corpus_skips_second_full_xml_read_and_parse(tmp_path, monkeypatch):
    docs = _docs(tmp_path)
    books, _ = load_source_directory(docs)
    original_read = Path.read_bytes
    reads = []

    def counted_read(self):
        if self.parent == docs and self.suffix == ".xml":
            reads.append(self.name)
            if self.name != "Empty.xml":
                raise AssertionError("already validated XML must not be reread")
        return original_read(self)

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("metadata re-parsed already validated XML")

    monkeypatch.setattr(Path, "read_bytes", counted_read)
    monkeypatch.setattr(metadata.ET, "fromstring", unexpected_parse)
    corpus = metadata.load_public_metadata(docs, parsed_books=books)
    assert set(corpus.documents) == {"One.xml", "Empty.xml"}
    assert corpus.documents["One.xml"].fields == {"status": "valid"}
    assert reads == ["Empty.xml"]


@pytest.mark.parametrize("mutate", ["missing", "wrong_work", "wrong_path", "duplicate"])
def test_reused_source_inventory_fails_closed_for_incomplete_or_forged_books(
    tmp_path, mutate
):
    docs = _docs(tmp_path)
    books, _ = load_source_directory(docs)
    if mutate == "missing":
        books = books[:1]
    elif mutate == "wrong_work":
        books[0] = replace(books[0], filename="Rogue")
    elif mutate == "wrong_path":
        books[0] = replace(books[0], source_path="Elsewhere.xml")
    else:
        books.append(books[0])
    with pytest.raises(ValueError, match="source|XML|identity|missing|duplicate|unparsed"):
        metadata.load_public_metadata(docs, parsed_books=books)


def test_reused_inventory_rejects_new_nonempty_xml_but_allows_empty_placeholder(tmp_path):
    docs = _docs(tmp_path)
    books, _ = load_source_directory(docs)
    (docs / "New.xml").write_text(TEMPLATE.format(name="New"), encoding="utf-8")
    with pytest.raises(ValueError, match="New.xml"):
        metadata.load_public_metadata(docs, parsed_books=books)
    (docs / "New.xml").write_text(" \n", encoding="utf-8")
    corpus = metadata.load_public_metadata(docs, parsed_books=books)
    assert len(corpus.documents) == 2


@pytest.mark.parametrize("malformation", ["identity", "invalid_xml"])
def test_standalone_loader_still_parses_full_xml_and_rejects_invalid_sources(tmp_path, malformation):
    docs = _docs(tmp_path)
    path = docs / "One.xml"
    path.write_text(
        TEMPLATE.format(name="Wrong") if malformation == "identity"
        else '<book filename="One"><broken',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="One.xml"):
        metadata.load_public_metadata(docs)


def test_cli_passes_loaded_books_to_metadata_loader(tmp_path, monkeypatch):
    docs = _docs(tmp_path)
    parsed = []
    original_source = cli.load_source_directory
    original_meta = cli.load_public_metadata

    def source_loader(path):
        books, warnings = original_source(path)
        parsed.extend(books)
        return books, warnings

    def metadata_loader(path, *, parsed_books):
        assert parsed_books is not None
        assert len(parsed_books) == 2
        assert all(a is b for a, b in zip(parsed_books, parsed))
        return original_meta(path, parsed_books=parsed_books)

    def stop_after_metadata(*args, **kwargs):
        raise RuntimeError("metadata loader was called with real parsed books")

    monkeypatch.setattr(cli, "load_source_directory", source_loader)
    monkeypatch.setattr(cli, "load_public_metadata", metadata_loader)
    monkeypatch.setattr(cli, "build_tf_data", stop_after_metadata)
    with pytest.raises(RuntimeError, match="metadata loader was called"):
        cli.main(["convert", str(docs), "--output", str(tmp_path / "tf")])
