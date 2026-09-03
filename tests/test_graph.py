from pathlib import Path

from pseudepigrapha_tf.graph import build_tf_data
from pseudepigrapha_tf.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def nodes_of_type(data, kind):
    return [n for n, t in data.node_features["otype"].items() if t == kind]


def test_bhsa_compatible_warp_and_lossless_apparatus_overlay():
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    assert data.validate() == []

    otype = data.node_features["otype"]
    max_slot = data.max_slot
    assert max_slot >= 3
    assert all(otype[n] == "word" for n in range(1, max_slot + 1))
    assert data.metadata["otext"]["sectionTypes"] == "book,chapter,verse"
    assert data.metadata["otext"]["sectionFeatures"] == "book,chapter,verse"
    assert data.metadata["otext"]["fmt:text-orig-full"] == "{g_word_utf8}{trailer_utf8}"

    assert data.node_features["g_word_utf8"][1] == "λόγος"
    assert data.node_features["g_word_utf8"][2] == "θεοῦ"
    assert data.node_features["morph"][2] == "N"
    assert data.node_features["lex"][2] == "θεός"

    gap_slots = list(data.node_features["is_gap"])
    assert len(gap_slots) == 1
    assert gap_slots[0] <= max_slot

    unit_nodes = nodes_of_type(data, "unit")
    reading_nodes = nodes_of_type(data, "reading")
    variant_words = nodes_of_type(data, "variant_word")
    assert len(unit_nodes) == 2
    assert len(reading_nodes) == 4
    assert [data.node_features["g_word_utf8"][n] for n in variant_words] == ["λόγος", "κυρίου", "πλήρης"]

    first_unit = next(n for n in unit_nodes if data.node_features["unit_id"][n] == "0")
    variant_reading = next(n for n in reading_nodes if data.node_features["reading_option"][n] == 1 and data.node_features["unit_id"][data.edge_features["reading_of"][n].copy().pop()] == "0")
    assert data.edge_features["oslots"][variant_reading] == data.edge_features["oslots"][first_unit]
    assert data.node_features["reading_text"][variant_reading] == "λόγος κυρίου"
    omission_readings = [n for n in reading_nodes if data.node_features.get("is_omission", {}).get(n) == 1]
    assert len(omission_readings) == 1

    ms_nodes = {data.node_features["ms_abbrev"][n]: n for n in nodes_of_type(data, "manuscript")}
    assert data.edge_features["oslots"][ms_nodes["A"]]
    assert data.edge_features["oslots"][ms_nodes["C"]] == set()


def test_single_division_synthesizes_chapter_and_uses_source_div_as_verse():
    data = build_tf_data([parse_file(FIXTURES / "one_division.xml")])
    chapters = nodes_of_type(data, "chapter")
    verses = nodes_of_type(data, "verse")
    assert [data.node_features["chapter"][n] for n in chapters] == ["1"]
    assert [data.node_features["verse"][n] for n in verses] == ["7"]


def test_deeper_divisions_are_preserved_without_distorting_bhsa_sections():
    data = build_tf_data([parse_file(FIXTURES / "three_divisions.xml")])
    chapters = nodes_of_type(data, "chapter")
    verses = nodes_of_type(data, "verse")
    source_divs = nodes_of_type(data, "div")
    assert [data.node_features["chapter"][n] for n in chapters] == ["9"]
    assert [data.node_features["verse"][n] for n in verses] == ["4b"]
    assert "heading" in [data.node_features["div_number"][n] for n in source_divs]


def test_versions_get_unique_book_section_ids():
    data = build_tf_data([parse_file(FIXTURES / "multiple_versions.xml")])
    books = nodes_of_type(data, "book")
    assert [data.node_features["book"][n] for n in books] == ["Multi__Syriac", "Multi__Greek"]
    assert [data.node_features["language"][n] for n in books] == ["Syriac", "Greek"]
