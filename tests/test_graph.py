from pathlib import Path

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.graph import TFData
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
    assert data.metadata["otext"]["fmt:text-orig-full"] == "{prefix_utf8}{g_word_utf8}{trailer_utf8}{boundary_utf8}"
    assert data.metadata["otext"]["fmt:reading-default"] == "{reading_text}"
    assert data.metadata["otext"]["fmt:variant_word-default"] == "{prefix_utf8}{g_word_utf8}{trailer_utf8}"
    assert data.metadata["otext"]["fmt:manuscript-default"] == "{ms_abbrev}"
    assert data.metadata["otext"]["fmt:resource-default"] == "{resource_name}"

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

    # Text-Fabric serialization requires every non-slot node to have an oslots anchor.
    # Metadata nodes therefore get exactly one technical anchor, never a fake textual span.
    ms_nodes = {data.node_features["ms_abbrev"][n]: n for n in nodes_of_type(data, "manuscript")}
    assert all(len(data.edge_features["oslots"][n]) == 1 for n in ms_nodes.values())
    resource_nodes = nodes_of_type(data, "resource")
    assert all(len(data.edge_features["oslots"][n]) == 1 for n in resource_nodes)
    assert all(len(data.edge_features["oslots"][n]) <= 1 for n in variant_words)


def test_non_slot_node_types_form_contiguous_ranges_for_text_fabric_indexes():
    data = build_tf_data([parse_file(FIXTURES / "multiple_versions.xml")])
    otype = data.node_features["otype"]
    kinds = {kind for node, kind in otype.items() if node > data.max_slot}
    for kind in kinds:
        nodes = nodes_of_type(data, kind)
        assert nodes == list(range(min(nodes), max(nodes) + 1)), kind


def test_validate_computes_node_bounds_once():
    data = build_tf_data([parse_file(FIXTURES / "multiple_versions.xml")])

    class CountingTFData(TFData):
        max_slot_calls = 0
        max_node_calls = 0

        @property
        def max_slot(self):
            self.max_slot_calls += 1
            return super().max_slot

        @property
        def max_node(self):
            self.max_node_calls += 1
            return super().max_node

    counted = CountingTFData(
        data.node_features,
        data.edge_features,
        data.metadata,
        data.warnings,
    )
    assert counted.validate() == []
    assert counted.max_slot_calls == 1
    assert counted.max_node_calls == 1


def test_single_division_synthesizes_chapter_and_uses_source_div_as_verse():
    data = build_tf_data([parse_file(FIXTURES / "one_division.xml")])
    chapters = nodes_of_type(data, "chapter")
    verses = nodes_of_type(data, "verse")
    assert [data.node_features["chapter"][n] for n in chapters] == ["1"]
    assert [data.node_features["verse"][n] for n in verses] == ["7"]


def test_deeper_divisions_use_compound_parent_path_and_terminal_verse():
    data = build_tf_data([parse_file(FIXTURES / "three_divisions.xml")])
    chapters = nodes_of_type(data, "chapter")
    verses = nodes_of_type(data, "verse")
    source_divs = nodes_of_type(data, "div")
    units = nodes_of_type(data, "unit")
    readings = nodes_of_type(data, "reading")

    assert [data.node_features["chapter"][n] for n in chapters] == ["9.4b"]
    assert [data.node_features["verse"][n] for n in verses] == ["heading", "1"]
    assert "heading" in [data.node_features["div_number"][n] for n in source_divs]
    assert [data.node_features["source_ref"][n] for n in units] == ["9.4b.heading", "9.4b.1"]
    assert [data.node_features["source_ref"][n] for n in readings] == ["9.4b.heading", "9.4b.1"]
    assert [data.node_features["source_ref"][n] for n in range(1, data.max_slot + 1)] == ["9.4b.heading", "9.4b.1"]

    parent = data.edge_features["parent"]
    div_by_path = {data.node_features["source_ref"][n]: n for n in source_divs}
    unit_by_ref = {data.node_features["source_ref"][n]: n for n in units}
    assert parent[unit_by_ref["9.4b.heading"]] == {div_by_path["9.4b.heading"]}


def test_versions_get_unique_book_section_ids():
    data = build_tf_data([parse_file(FIXTURES / "multiple_versions.xml")])
    books = nodes_of_type(data, "book")
    assert [data.node_features["book"][n] for n in books] == ["Multi__Syriac", "Multi__Greek"]
    assert [data.node_features["language"][n] for n in books] == ["Syriac", "Greek"]


def test_metadata_only_version_is_preserved_without_inventing_text_sections():
    data = build_tf_data([parse_file(FIXTURES / "metadata_only_version.xml")])

    books = nodes_of_type(data, "book")
    metadata_versions = nodes_of_type(data, "version_metadata")
    assert len(books) == 1
    assert len(metadata_versions) == 1
    metadata_version = metadata_versions[0]
    assert data.node_features["version_id"][metadata_version] == "Meta__Coptic"
    assert data.node_features["version_title"][metadata_version] == "Coptic"
    assert data.node_features["language"][metadata_version] == "Coptic"
    assert data.node_features["is_metadata_only"][metadata_version] == 1
    assert data.metadata["otext"]["fmt:version_metadata-default"] == "{version_title}"

    # The empty upstream version contributes no fake Coptic book/chapter/verse.
    assert [data.node_features["book"][n] for n in books] == ["Meta__Greek"]
    assert len(nodes_of_type(data, "chapter")) == 1
    assert len(nodes_of_type(data, "verse")) == 1

    coptic_ms = next(
        n for n in nodes_of_type(data, "manuscript")
        if data.node_features["ms_abbrev"][n] == "Coptic"
    )
    assert data.edge_features["manuscript_of"][coptic_ms] == {metadata_version}
    assert len(data.edge_features["oslots"][metadata_version]) == 1
    assert len(data.edge_features["oslots"][coptic_ms]) == 1


def test_empty_source_division_is_preserved_without_fabricating_a_text_section():
    data = build_tf_data([parse_file(FIXTURES / "empty_division.xml")])

    source_divs = nodes_of_type(data, "div")
    empty_div = next(n for n in source_divs if data.node_features["source_ref"][n] == "1:2")
    assert data.node_features["div_fragment"][empty_div] == "empty-upstream"
    assert data.node_features["is_empty_div"][empty_div] == 1
    assert len(data.edge_features["oslots"][empty_div]) == 1

    # The empty source structure remains queryable, but it does not claim a
    # textual verse and does not create a gap/word slot.
    assert [data.node_features["verse"][n] for n in nodes_of_type(data, "verse")] == ["1"]
    assert data.max_slot == 1
    assert data.node_features.get("is_gap", {}) == {}


def test_nested_empty_divisions_preserve_parent_chain_and_nearest_anchor():
    data = build_tf_data([parse_file(FIXTURES / "nested_empty_divisions.xml")])
    assert data.validate() == []

    source_divs = nodes_of_type(data, "div")
    div_by_ref = {data.node_features["source_ref"][n]: n for n in source_divs}
    empty_parent = div_by_ref["2.c"]
    empty_leaf = div_by_ref["2.c.2"]
    textual_ancestor = div_by_ref["2"]

    assert data.node_features["div_fragment"][empty_parent] == "empty-parent"
    assert data.node_features["div_fragment"][empty_leaf] == "empty-leaf"
    assert data.node_features["is_empty_div"][empty_parent] == 1
    assert data.node_features["is_empty_div"][empty_leaf] == 1

    parent = data.edge_features["parent"]
    assert parent[empty_leaf] == {empty_parent}
    assert parent[empty_parent] == {textual_ancestor}

    # Slot 1 belongs to another top-level source region. The empty branch is
    # technically anchored to slot 2 from its nearest non-empty ancestor.
    assert data.edge_features["oslots"][empty_parent] == {2}
    assert data.edge_features["oslots"][empty_leaf] == {2}
    book = nodes_of_type(data, "book")[0]
    assert min(data.edge_features["oslots"][book]) == 1

    chapters = [
        (data.node_features["source_ref"].get(n, ""), data.node_features["chapter"][n])
        for n in nodes_of_type(data, "chapter")
    ]
    verses = [
        (data.node_features["source_ref"].get(n, ""), data.node_features["verse"][n])
        for n in nodes_of_type(data, "verse")
    ]
    assert chapters == [("1.a", "1.a"), ("2.b", "2.b")]
    assert verses == [("1.a.1", "1"), ("2.b.1", "1")]
    assert data.max_slot == 2
    assert data.node_features.get("is_gap", {}) == {}


def test_surface_boundaries_are_explicit_and_deterministic():
    data = build_tf_data([parse_file(FIXTURES / "boundary.xml")])
    assert data.node_features["boundary_utf8"][1] == " "
    assert data.node_features.get("boundary_utf8", {}).get(2, "") == ""

    legacy = build_tf_data([parse_file(FIXTURES / "legacy.xml")])
    assert legacy.node_features["boundary_utf8"][legacy.max_slot] == "\n"


def test_global_provenance_records_upstream_revision():
    data = build_tf_data(
        [parse_file(FIXTURES / "sample.xml")],
        upstream_commit="2d1d14d",
        upstream_repository="https://github.com/example/ocp",
        converter_version="0.1.0",
    )
    assert data.metadata[""]["upstreamCommit"] == "2d1d14d"
    assert data.metadata[""]["upstreamRepository"] == "https://github.com/example/ocp"
    assert data.metadata[""]["converterVersion"] == "0.1.0"
