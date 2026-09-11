from __future__ import annotations

import pytest

from pseudepigrapha_tf import comparison


APPARATUS_RESULT = {
    "work": "Work",
    "title": "Demo <Work>",
    "reference": ("1", "2"),
    "versions": {
        "Work__Greek": {
            "node": 1,
            "id": "Work__Greek",
            "title": "Greek",
            "language": "Greek",
            "author": "Editor <A>",
            "status": "available",
            "witnesses": {},
            "passage": {
                "reference": ("Work__Greek", "1", "2"),
                "verse_node": 101,
                "source_refs": ("1:2",),
                "units": (
                    {
                        "node": 11,
                        "unit": "u1",
                        "source_ref": "1:2",
                        "readings": (
                            {
                                "node": 21,
                                "text": "alpha",
                                "primary": True,
                                "omission": False,
                                "witness_nodes": (31,),
                                "witnesses": ("A",),
                            },
                            {
                                "node": 22,
                                "text": "WRONG-ANCHOR-ALTERNATIVE",
                                "primary": False,
                                "omission": False,
                                "witness_nodes": (32,),
                                "witnesses": ("B",),
                            },
                        ),
                    },
                    {
                        "node": 12,
                        "unit": "u2",
                        "source_ref": "1:2",
                        "readings": (
                            {
                                "node": 23,
                                "text": "",
                                "primary": True,
                                "omission": True,
                                "witness_nodes": (31,),
                                "witnesses": ("A",),
                            },
                        ),
                    },
                ),
                "witnesses": {
                    "A": {
                        "node": 31,
                        "abbrev": "A",
                        "declared": True,
                        "language": "Greek",
                        "name": "Witness A",
                        "show": "yes",
                        "segments": (
                            {"unit": "u1", "unit_node": 11, "status": "reading", "reading": 21, "text": "alpha-A"},
                            {"unit": "u2", "unit_node": 12, "status": "omission", "reading": 23, "text": ""},
                        ),
                        "coverage": {"reading": 1, "omission": 1},
                        "complete": True,
                        "text": "alpha-A",
                        "attested_text": "alpha-A",
                    },
                    "B": {
                        "node": 32,
                        "abbrev": "B",
                        "declared": True,
                        "language": "Greek",
                        "name": "Witness B",
                        "show": "yes",
                        "segments": (
                            {"unit": "u1", "unit_node": 11, "status": "reading", "reading": 22, "text": "beta-B"},
                            {"unit": "u2", "unit_node": 12, "status": "unattested", "reading": None, "text": None},
                        ),
                        "coverage": {"reading": 1, "unattested": 1},
                        "complete": False,
                        "text": None,
                        "attested_text": "beta-B",
                    },
                    "C": {
                        "node": 33,
                        "abbrev": "C",
                        "declared": True,
                        "language": "Greek",
                        "name": "Witness C",
                        "show": "yes",
                        "segments": (
                            {"unit": "u1", "unit_node": 11, "status": "reading", "reading": 21, "text": "gamma-C"},
                            {"unit": "u2", "unit_node": 12, "status": "reading", "reading": 24, "text": "gamma-2"},
                        ),
                        "coverage": {"reading": 2},
                        "complete": True,
                        "text": "gamma-C gamma-2",
                        "attested_text": "gamma-C gamma-2",
                    },
                    "D": {
                        "node": 34,
                        "abbrev": "D",
                        "declared": True,
                        "language": "Greek",
                        "name": "Witness D",
                        "show": "yes",
                        "segments": (
                            {"unit": "u1", "unit_node": 11, "status": "reading", "reading": 21, "text": "delta-D"},
                            {"unit": "u2", "unit_node": 12, "status": "reading", "reading": 24, "text": "delta-2"},
                        ),
                        "coverage": {"reading": 2},
                        "complete": True,
                        "text": "delta-D delta-2",
                        "attested_text": "delta-D delta-2",
                    },
                    "E": {
                        "node": 35,
                        "abbrev": "E",
                        "declared": True,
                        "language": "Greek",
                        "name": "Witness E",
                        "show": "yes",
                        "segments": (
                            {"unit": "u1", "unit_node": 11, "status": "reading", "reading": 21, "text": "epsilon-E"},
                            {"unit": "u2", "unit_node": 12, "status": "reading", "reading": 24, "text": "epsilon-2"},
                        ),
                        "coverage": {"reading": 2},
                        "complete": True,
                        "text": "epsilon-E epsilon-2",
                        "attested_text": "epsilon-E epsilon-2",
                    },
                },
            },
        },
        "Work__Syriac": {
            "node": 2,
            "id": "Work__Syriac",
            "title": "Syriac",
            "language": "Syriac",
            "author": "Editor S",
            "status": "available",
            "witnesses": {},
            "passage": {
                "reference": ("Work__Syriac", "1", "2"),
                "verse_node": 102,
                "source_refs": ("1:2",),
                "units": (
                    {
                        "node": 13,
                        "unit": "s1",
                        "source_ref": "1:2",
                        "readings": (
                            {
                                "node": 25,
                                "text": "ܐܠܦܐ",
                                "primary": True,
                                "omission": False,
                                "witness_nodes": (36,),
                                "witnesses": ("S",),
                            },
                        ),
                    },
                ),
                "witnesses": {
                    "S": {
                        "node": 36,
                        "abbrev": "S",
                        "declared": True,
                        "language": "Syriac",
                        "name": "Witness S",
                        "show": "yes",
                        "segments": (
                            {"unit": "s1", "unit_node": 13, "status": "reading", "reading": 25, "text": "ܐܠܦܐ"},
                        ),
                        "coverage": {"reading": 1},
                        "complete": True,
                        "text": "ܐܠܦܐ",
                        "attested_text": "ܐܠܦܐ",
                    }
                },
            },
        },
        "Work__Latin": {
            "node": 3,
            "id": "Work__Latin",
            "title": "Latin fragments",
            "language": "Latin",
            "author": "Editor L",
            "status": "not_present",
            "witnesses": {},
            "passage": None,
        },
    },
    "metadata_only_versions": {
        "Work__Coptic": {
            "node": 4,
            "id": "Work__Coptic",
            "title": "Coptic metadata only",
            "language": "Coptic",
            "author": "Editor C",
            "status": "metadata_only",
            "witnesses": {},
            "passage": None,
        }
    },
}


TRANSLATION_RECORDS = (
    {
        "node": 201,
        "id": "Work__Greek__translation__English",
        "work": "Work",
        "title": "Greek (English)",
        "language": "English",
        "source_node": 1,
        "source_id": "Work__Greek",
        "generation_marker": "OCP-Trans",
        "generation_method": "llm",
        "generation_model": "model-x",
    },
    {
        "node": 202,
        "id": "Work__Greek__translation__French",
        "work": "Work",
        "title": "Greek (French)",
        "language": "French",
        "source_node": 1,
        "source_id": "Work__Greek",
        "generation_marker": "OCP-Trans",
        "generation_method": "llm",
        "generation_model": "model-x",
    },
    {
        "node": 203,
        "id": "Work__Syriac__translation__English",
        "work": "Work",
        "title": "Syriac (English)",
        "language": "English",
        "source_node": 2,
        "source_id": "Work__Syriac",
        "generation_marker": "OCP-Trans",
        "generation_method": "llm",
        "generation_model": "model-x",
    },
    {
        "node": 204,
        "id": "Work__Latin__translation__English",
        "work": "Work",
        "title": "Latin (English)",
        "language": "English",
        "source_node": 3,
        "source_id": "Work__Latin",
        "generation_marker": "OCP-Trans",
        "generation_method": "llm",
        "generation_model": "model-x",
    },
)


TRANSLATION_PASSAGES = {
    "Work__Greek__translation__English": {
        "reference": ("Work__Greek__translation__English", "1", "2"),
        "book_node": 201,
        "source_book_node": 1,
        "units": (
            {
                "translation_unit": 301,
                "source_unit": 11,
                "translation_unit_id": "en-1",
                "source_unit_id": "u1",
                "source_ref": "1:2",
                "translation_text": "word",
                "source_text": "alpha",
            },
            {
                "translation_unit": 302,
                "source_unit": 12,
                "translation_unit_id": "en-2",
                "source_unit_id": "u2",
                "source_ref": "1:2",
                "translation_text": "omitted source",
                "source_text": "",
            },
        ),
    },
    "Work__Greek__translation__French": {
        "reference": ("Work__Greek__translation__French", "1", "2"),
        "book_node": 202,
        "source_book_node": 1,
        "units": (
            {
                "translation_unit": 303,
                "source_unit": 11,
                "translation_unit_id": "fr-1",
                "source_unit_id": "u1",
                "source_ref": "1:2",
                "translation_text": "mot <unsafe>",
                "source_text": "alpha",
            },
        ),
    },
    "Work__Syriac__translation__English": {
        "reference": ("Work__Syriac__translation__English", "1", "2"),
        "book_node": 203,
        "source_book_node": 2,
        "units": (
            {
                "translation_unit": 304,
                "source_unit": 13,
                "translation_unit_id": "en-s1",
                "source_unit_id": "s1",
                "source_ref": "1:2",
                "translation_text": "syriac word",
                "source_text": "ܐܠܦܐ",
            },
        ),
    },
}


class FakeApparatus:
    calls = []

    def __init__(self, api):
        self.api = api

    def work_passage(self, work, chapter, verse):
        self.__class__.calls.append((str(work), str(chapter), str(verse)))
        return APPARATUS_RESULT


class FakeTranslations:
    version_calls = []
    passage_calls = []

    def __init__(self, api):
        self.api = api

    def versions(self, *, work=None, language=None):
        self.__class__.version_calls.append((work, language))
        return TRANSLATION_RECORDS

    def aligned_to_source_units(self, generated_book, source_units):
        generated_id = next(
            record["id"] for record in TRANSLATION_RECORDS if record["node"] == generated_book
        )
        passage = TRANSLATION_PASSAGES.get(generated_id)
        if passage is None:
            return ()
        wanted = set(source_units)
        return tuple(
            unit for unit in passage["units"] if unit["source_unit"] in wanted
        )

    def passage(self, generated_book, chapter, verse):
        self.__class__.passage_calls.append((generated_book, str(chapter), str(verse)))
        if generated_book == "Work__Latin__translation__English":
            raise KeyError("translation section not found")
        return TRANSLATION_PASSAGES[generated_book]


@pytest.fixture(autouse=True)
def fake_semantic_helpers(monkeypatch):
    FakeApparatus.calls.clear()
    FakeTranslations.version_calls.clear()
    FakeTranslations.passage_calls.clear()
    monkeypatch.setattr(comparison, "Apparatus", FakeApparatus)
    monkeypatch.setattr(comparison, "Translations", FakeTranslations)


def _version(model, version_id):
    return next(version for version in model["versions"] if version["id"] == version_id)


def _witness(version, abbrev):
    return next(witness for witness in version["witnesses"] if witness["abbrev"] == abbrev)


def test_default_comparison_selects_two_available_source_versions_and_never_generated_books():
    model = comparison.build_passage_comparison(object(), "Work", "1", "2")

    assert FakeApparatus.calls == [("Work", "1", "2")]
    assert FakeTranslations.version_calls == [("Work", None)]
    assert [choice["id"] for choice in model["version_choices"]] == [
        "Work__Greek",
        "Work__Syriac",
        "Work__Latin",
    ]
    assert [version["id"] for version in model["versions"]] == ["Work__Greek", "Work__Syriac"]
    assert not any("translation" in choice["id"] for choice in model["version_choices"])


def test_explicit_source_selection_keeps_not_present_version_and_metadata_only_is_secondary():
    model = comparison.build_passage_comparison(
        object(),
        "Work",
        "1",
        "2",
        selected_versions=("Work__Greek", "Work__Latin"),
    )

    assert [version["id"] for version in model["versions"]] == ["Work__Greek", "Work__Latin"]
    assert _version(model, "Work__Latin")["status"] == "not_present"
    assert [item["id"] for item in model["metadata_only_versions"]] == ["Work__Coptic"]
    assert "Work__Coptic" not in {choice["id"] for choice in model["version_choices"]}


def test_unknown_source_version_selection_fails_closed():
    with pytest.raises(ValueError, match="unknown source version"):
        comparison.build_passage_comparison(
            object(),
            "Work",
            "1",
            "2",
            selected_versions=("Work__Greek", "Work__translation__English"),
        )


def test_witness_comparison_preserves_distinct_reading_omission_and_unattested_states():
    model = comparison.build_passage_comparison(object(), "Work", "1", "2")
    greek = _version(model, "Work__Greek")
    a = _witness(greek, "A")
    b = _witness(greek, "B")

    assert a["segments"][0]["text"] == "alpha-A"
    assert b["segments"][0]["text"] == "beta-B"
    assert a["segments"][0]["text"] != b["segments"][0]["text"]
    assert a["segments"][1]["status"] == "omission"
    assert b["segments"][1]["status"] == "unattested"
    assert b["complete"] is False


def test_default_witness_selection_is_bounded_and_explicit_selection_is_honored():
    default_model = comparison.build_passage_comparison(object(), "Work", "1", "2")
    default_greek = _version(default_model, "Work__Greek")
    assert [row["abbrev"] for row in default_greek["witnesses"]] == ["A", "B", "C", "D"]

    selected_model = comparison.build_passage_comparison(
        object(),
        "Work",
        "1",
        "2",
        selected_witnesses={"Work__Greek": ("B",)},
    )
    selected_greek = _version(selected_model, "Work__Greek")
    assert [row["abbrev"] for row in selected_greek["witnesses"]] == ["B"]


def test_primary_source_segments_use_apparatus_primary_readings_not_alternative_anchor_text():
    model = comparison.build_passage_comparison(object(), "Work", "1", "2")
    greek = _version(model, "Work__Greek")

    assert greek["primary_segments"] == (
        {"unit": "u1", "status": "reading", "text": "alpha"},
        {"unit": "u2", "status": "omission", "text": ""},
    )
    assert greek["primary_text"] == "alpha"
    assert "WRONG-ANCHOR-ALTERNATIVE" not in greek["primary_text"]


def test_generated_translations_are_attached_by_explicit_source_id_with_aligned_units():
    model = comparison.build_passage_comparison(object(), "Work", "1", "2")
    greek = _version(model, "Work__Greek")
    syriac = _version(model, "Work__Syriac")

    assert [item["id"] for item in greek["translations"]] == [
        "Work__Greek__translation__English",
        "Work__Greek__translation__French",
    ]
    assert [item["id"] for item in syriac["translations"]] == [
        "Work__Syriac__translation__English"
    ]
    aligned = greek["translations"][0]["units"]
    assert [(row["source_unit_id"], row["translation_unit_id"]) for row in aligned] == [
        ("u1", "en-1"),
        ("u2", "en-2"),
    ]
    assert greek["translations"][0]["text"] == "word omitted source"


def test_missing_generated_passage_is_visible_under_its_actual_source_version():
    model = comparison.build_passage_comparison(
        object(),
        "Work",
        "1",
        "2",
        selected_versions=("Work__Latin",),
    )
    latin = _version(model, "Work__Latin")

    assert latin["status"] == "not_present"
    assert [item["id"] for item in latin["translations"]] == [
        "Work__Latin__translation__English"
    ]
    assert latin["translations"][0]["status"] == "not_present"
    assert latin["translations"][0]["units"] == ()


def test_html_places_translations_inside_source_card_preserves_states_and_escapes_text():
    model = comparison.build_passage_comparison(object(), "Work", "1", "2")
    html = comparison.render_passage_comparison(model)

    assert 'class="comparison-page"' in html
    assert 'class="version-grid"' in html
    assert 'data-version-id="Work__Greek"' in html
    assert 'class="translation-block"' in html
    assert 'class="state-omission"' in html
    assert 'class="state-unattested"' in html
    assert "Demo &lt;Work&gt;" in html
    assert "Editor &lt;A&gt;" in html
    assert "mot &lt;unsafe&gt;" in html
    assert "<unsafe>" not in html

    greek_start = html.index('data-version-id="Work__Greek"')
    french_translation = html.index("mot &lt;unsafe&gt;")
    syriac_start = html.index('data-version-id="Work__Syriac"')
    assert greek_start < french_translation < syriac_start


def test_html_renders_selected_not_present_source_as_a_comparison_card():
    model = comparison.build_passage_comparison(
        object(),
        "Work",
        "1",
        "2",
        selected_versions=("Work__Latin",),
    )
    html = comparison.render_passage_comparison(model)

    assert 'data-version-id="Work__Latin"' in html
    assert 'class="state-not-present"' in html
    assert "not present" in html.lower()
    assert "Coptic metadata only" in html
