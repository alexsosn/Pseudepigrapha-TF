"""Compact OCP originals and source-declared (non-generated) parallel translations."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tf.fabric import Fabric

from pseudepigrapha_tf import Apparatus, Translations
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.writer import write_tf


COMPACT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<book filename="Compact.xml" title="Compact demonstration">
  <version id="Latin" title="Latin Text" lang="lat">
    <divisions><division id="1" title="Text" type="section"/></divisions>
    <manuscripts><manuscript id="MS1" name="Codex One"/></manuscripts>
    <text>
      <div number="1">
        <unit id="1.1"><reading option="base" mss="MS1">Prima vox.</reading></unit>
        <unit id="1.2"><reading option="base" mss="MS1">Secunda vox.</reading></unit>
      </div>
      <div number="2">
        <unit id="2.1"><reading option="base" mss="MS1">Tertia vox.</reading></unit>
      </div>
    </text>
  </version>
  <version id="English" title="English Translation" lang="eng">
    <divisions><division id="1" title="Text" type="section"/></divisions>
    <manuscripts><manuscript id="Eng" name="English Translation"/></manuscripts>
    <text>
      <div number="1">
        <unit id="1.1"><reading option="base" mss="Eng">First word.</reading></unit>
        <unit id="1.2"><reading option="base" mss="Eng">Second word.</reading></unit>
      </div>
      <div number="2">
        <unit id="2.1"><reading option="base" mss="Eng">Third word.</reading></unit>
      </div>
    </text>
  </version>
</book>
"""


def _docs(tmp_path: Path, xml: str = COMPACT_XML) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "Compact.xml").write_text(xml, encoding="utf-8")
    return docs


def test_compact_source_retains_original_identities_and_parallel_english(tmp_path):
    docs = _docs(tmp_path)
    books, warnings = load_source_directory(docs)
    assert not warnings and len(books) == 1
    book = books[0]
    assert book.filename == "Compact"
    assert book.source_path == "Compact.xml"
    assert len(book.versions) == 2
    original, english = book.versions
    assert original.source_id == "Latin"
    assert original.source_format == "compact"
    assert original.language == "lat"
    assert original.author == ""
    assert original.divisions[0].label == "Text"
    assert original.divisions[0].source_id == "1"
    assert original.divisions[0].source_type == "section"
    assert original.manuscripts[0].abbrev == "MS1"
    assert original.manuscripts[0].name == "Codex One"
    assert original.manuscripts[0].language == ""
    assert original.manuscripts[0].show == ""
    assert original.divs[0].units[1].unit_id == "1.2"
    assert original.divs[0].units[1].readings[0].option == "base"
    assert english.kind == "parallel_translation"
    assert english.language == "eng"
    assert english.manuscripts[0].abbrev == "Eng"
    assert english.divs[0].units[1].readings[0].text == "Second word."


def test_compact_source_reloads_sections_and_aligned_translation(tmp_path):
    docs = _docs(tmp_path)
    books, _ = load_source_directory(docs)
    data = build_tf_data(books)
    report = build_conversion_report(docs, books, data)
    assert report["status"] == "ok", report["failed_checks"]
    assert report["source"]["units"] == report["graph"]["units"] == 6
    assert report["source"]["readings"] == report["graph"]["readings"] == 6
    assert report["semantic_checks"]["parallel_translation_alignment"]

    tf_dir = tmp_path / "tf"
    assert write_tf(data, tf_dir)
    api = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep").load(
        " ".join(set(Apparatus.PASSAGE_FEATURES)
                 | set(Translations.PARALLEL_FEATURES)
                 | {"source_format", "version_source_id", "division_source_ids",
                    "division_source_types", "unit_id", "reading_option_source",
                    "synthetic_witness"}), silent="deep"
    )
    assert api is not None
    original, english = books[0].versions
    by_title = {
        api.F.version_title.v(node): node for node in api.F.otype.s("book")
    }
    original_book = by_title["Latin Text"]
    english_book = by_title["English Translation"]
    assert api.F.version_kind.v(original_book) == "source"
    assert api.F.version_kind.v(english_book) == "parallel_translation"
    assert api.F.version_source_id.v(original_book) == "Latin"
    assert api.F.version_source_id.v(english_book) == "English"
    assert api.F.source_format.v(original_book) == "compact"
    assert api.F.division_source_ids.v(original_book) == '["1"]'
    assert api.F.division_source_types.v(original_book) == '["section"]'
    original_id = api.F.book.v(original_book)
    english_id = api.F.book.v(english_book)
    assert api.T.nodeFromSection((original_id, "1", "1.1")) is not None
    assert api.T.nodeFromSection((original_id, "1", "1.2")) is not None
    assert api.T.nodeFromSection((original_id, "2", "2.1")) is not None
    source_passage = Apparatus(api).passage(original_id, "1", "1.2")
    assert source_passage["units"]
    assert source_passage["source_refs"] == ("1.2",), source_passage
    source_unit = source_passage["units"][0]["node"]
    assert api.F.source_ref.v(source_unit) == "1.2"
    with pytest.raises(ValueError, match="translation|Translations"):
        Apparatus(api).passage(english_id, "1", "1.2")
    translated = Translations(api)
    assert translated.source_version(english_book) == original_book
    linked = translated.passage(english_id, "1", "1.2")
    assert len(linked["units"]) == 1
    assert linked["units"][0]["source_unit_id"] == "1.2"
    assert linked["units"][0]["translation_unit_id"] == "1.2"
    assert linked["units"][0]["translation_text"] == "Second word."
    assert linked["units"][0]["source_text"] == "Secunda vox."



def test_compact_independent_audit_rejects_reversed_source_unit_order(tmp_path):
    docs = _docs(tmp_path)
    books, _ = load_source_directory(docs)
    data = build_tf_data(books)
    assert build_conversion_report(docs, books, data)["status"] == "ok"
    kinds = data.node_features["otype"]
    work = data.node_features["version_kind"]
    ids = data.node_features["unit_id"]
    first = next(n for n, kind in kinds.items()
                 if kind == "unit" and work.get(n) == "source" and ids.get(n) == "1.1")
    second = next(n for n, kind in kinds.items()
                  if kind == "unit" and work.get(n) == "source" and ids.get(n) == "1.2")
    order = data.node_features["unit_index"]
    order[first], order[second] = order[second], order[first]
    report = build_conversion_report(docs, books, data)
    assert report["status"] == "failed"
    assert not report["semantic_checks"]["parallel_translation_alignment"]


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ('filename="Compact.xml"', 'filename="Alien.xml"', "filename|identity"),
        ('id="English" title=', 'id="Latin" title=', "duplicate|version"),
        ('lang="eng"', 'lang="lat"', "English|language"),
        ('id="1.2"><reading option="base" mss="Eng"', 'id="1.9"><reading option="base" mss="Eng"', "alignment|unit"),
        ('mss="Eng">Second word', 'mss="Phantom">Second word', "undeclared|witness|manuscript"),
        ('option="base" mss="Eng">Second word', 'option="0" mss="Eng">Second word', "base|option"),
        ('id="MS1" name=', 'id="Eng" name=', "Eng|duplicate|witness"),
        ('type="section"', 'type="other"', "type|unsupported"),
        ('id="1.2"><reading option="base" mss="MS1"', 'id="1.1"><reading option="base" mss="MS1"', "duplicate|unit"),
    ],
)
def test_compact_fail_closed_on_bad_source_identity_and_translation(tmp_path, old, new, error):
    xml = COMPACT_XML.replace(old, new, 1 if 'id="1.2"><reading option="base" mss="Eng"' not in old else 0)
    # For the English unit perturbation, target the English version only.
    if 'mss="Eng"' in old and 'id="1.2"' in old:
        xml = COMPACT_XML.replace(old, new)
    with pytest.raises((InvalidSourceError, ValueError), match=error):
        load_source_directory(_docs(tmp_path, xml))


def test_compact_translations_not_forged_machine_generated(tmp_path):
    docs = _docs(tmp_path)
    book = load_source_directory(docs)[0][0]
    assert not book.generated_translations
    data = build_tf_data([book])
    assert not any(data.node_features.get("generation_marker", {}).values())
    assert not any(data.node_features.get("generated_language", {}).values())
    english = next(
        node for node, kind in data.node_features["otype"].items()
        if kind == "book" and data.node_features["version_kind"].get(node) == "parallel_translation"
    )
    manuscript_nodes = {
        node for node, kind in data.node_features["otype"].items()
        if kind == "manuscript" and data.node_features["version_id"].get(node)
        == data.node_features["version_id"][english]
    }
    assert len(manuscript_nodes) == 1
    assert all(data.node_features["synthetic_witness"][node] == 1 for node in manuscript_nodes)


def test_compact_parallel_english_is_not_a_source_in_real_compare_ui(tmp_path):
    from pseudepigrapha_tf.comparison import (
        PassageNavigator, build_passage_comparison, render_passage_comparison,
    )
    from pseudepigrapha_tf.web import list_comparison_work_options

    book = load_source_directory(_docs(tmp_path))[0][0]
    tf_dir = tmp_path / "tf"
    assert write_tf(build_tf_data([book]), tf_dir)
    required = set(Apparatus.WORK_PASSAGE_FEATURES) | set(Translations.PARALLEL_FEATURES)
    required.update({"title", "author", "language", "verse_index", "source_ref"})
    api = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep").load(
        " ".join(sorted(required)), silent="deep",
    )
    assert api is not None
    version_nodes = {
        api.F.version_title.v(node): node for node in api.F.otype.s("book")
    }
    source = version_nodes["Latin Text"]
    parallel = version_nodes["English Translation"]
    original_id = api.F.book.v(source)
    english_id = api.F.book.v(parallel)
    model = build_passage_comparison(api, "Compact", "1", "1.2")
    assert tuple(choice["id"] for choice in model["version_choices"]) == (original_id,)
    assert len(model["versions"]) == 1
    translations = model["versions"][0]["translations"]
    assert len(translations) == 1
    assert translations[0]["id"] == english_id
    assert translations[0]["translation_kind"] == "parallel_translation"
    assert translations[0]["text"] == "Second word."
    html = render_passage_comparison(model)
    assert "Source-declared parallel translation" in html
    assert 'data-translation-kind="parallel_translation"' in html
    assert f'data-translation-id="{english_id}"' in html
    assert f'data-version-id="{english_id}"' not in html
    assert 'data-witness="Eng"' not in html
    choices = list_comparison_work_options(api)
    assert choices == (("Compact", "Compact demonstration (Compact)"),)
    neighbors = PassageNavigator(api).neighbors(
        "Compact", "1", "1.2", preferred_versions=(english_id,),
    )
    assert neighbors["context_version"] == original_id
    with pytest.raises(ValueError, match="unknown source version"):
        build_passage_comparison(
            api, "Compact", "1", "1.2", selected_versions=(english_id,),
        )
