from __future__ import annotations

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_bytes

PINNED_OCP_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
PINNED_GENERATION_MODEL = "openrouter/google/gemini-3.7-flash"


def _book():
    xml = b'''<?xml version="1.0"?>
<book filename="Demo" title="Demo">
  <version title="Greek" author="Editor" language="Greek">
    <divisions><division label="Chapter" delimiter=":"/><division label="Verse"/></divisions>
    <manuscripts><ms abbrev="G" language="Greek" show="yes"><name>G</name></ms></manuscripts>
    <text><div number="1"><div number="1"><unit id="1"><reading option="0" mss="G ">alpha</reading></unit></div></div></text>
  </version>
  <version title="Greek (French)" author="Editor" language="French">
    <divisions><division label="Chapter" delimiter=":"/><division label="Verse"/></divisions>
    <manuscripts><ms abbrev="OCP-Trans" language="French" show="yes"><name>OCP-Trans</name></ms></manuscripts>
    <text><div number="1"><div number="1"><unit id="fr_1"><reading option="0" mss="OCP-Trans ">alpha-fr</reading></unit></div></div></text>
  </version>
</book>
'''
    return parse_bytes(xml, source_path="Demo.xml")


def _metadata_only_book():
    xml = b'''<?xml version="1.0"?>
<book filename="Meta" title="Metadata-only demo">
  <version title="Coptic" author="Editor" language="Coptic">
    <divisions><division label="Chapter" delimiter=":"/><division label="Verse"/></divisions>
    <manuscripts><ms abbrev="C" language="Coptic" show="yes"><name>Coptic</name></ms></manuscripts>
    <text/>
  </version>
</book>
'''
    return parse_bytes(xml, source_path="Meta.xml")


def _generated_book(data) -> int:
    return next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "book" and data.node_features["version_kind"].get(node) == "generated_translation"
    )


def test_parser_does_not_claim_history_derived_model_without_snapshot_context() -> None:
    generated = _book().generated_translations[0]

    assert generated.marker == "OCP-Trans"
    assert generated.target_language == "French"
    assert generated.generation_method == ""
    assert generated.generation_model == ""


def test_exact_evidenced_snapshot_exposes_generation_method_and_model() -> None:
    data = build_tf_data([_book()], upstream_commit=PINNED_OCP_COMMIT)
    node = _generated_book(data)

    assert data.node_features["generation_marker"][node] == "OCP-Trans"
    assert data.node_features["generation_method"][node] == "llm"
    assert data.node_features["generation_model"][node] == PINNED_GENERATION_MODEL


def test_generation_provenance_is_owned_by_generated_book_not_denormalized_to_descendants() -> None:
    data = build_tf_data([_book()], upstream_commit=PINNED_OCP_COMMIT)
    generated_book = _generated_book(data)

    expected = {
        "generation_marker": "OCP-Trans",
        "generated_language": "French",
        "generation_method": "llm",
        "generation_model": PINNED_GENERATION_MODEL,
    }
    for feature, value in expected.items():
        assert data.node_features[feature] == {generated_book: value}

    # Unit-level generated/source classification remains a separate semantic
    # contract used by alignment and apparatus helpers.
    generated_units = [
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "unit" and data.node_features["version_kind"].get(node) == "generated_translation"
    ]
    source_units = [
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "unit" and data.node_features["version_kind"].get(node) == "source"
    ]
    assert generated_units
    assert source_units
    assert all(node in data.edge_features["translation_unit_of"] for node in generated_units)

    synthetic = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "manuscript" and data.node_features.get("ms_abbrev", {}).get(node) == "OCP-Trans"
    )
    assert data.node_features["synthetic_witness"][synthetic] == 1


def test_version_kind_is_scoped_to_version_owners_and_alignment_units() -> None:
    data = build_tf_data(
        [_book(), _metadata_only_book()],
        upstream_commit=PINNED_OCP_COMMIT,
    )
    otype = data.node_features["otype"]
    version_kind = data.node_features["version_kind"]

    semantic_types = {"book", "unit", "version_metadata"}
    expected_nodes = {
        node
        for node, node_type in otype.items()
        if node_type in semantic_types
    }
    assert set(version_kind) == expected_nodes

    books = [node for node in expected_nodes if otype[node] == "book"]
    units = [node for node in expected_nodes if otype[node] == "unit"]
    metadata = [node for node in expected_nodes if otype[node] == "version_metadata"]
    assert books and units and len(metadata) == 1
    assert version_kind[metadata[0]] == "source"
    assert {version_kind[node] for node in books} == {"source", "generated_translation"}
    assert {version_kind[node] for node in units} == {"source", "generated_translation"}

    assert all(node > data.max_slot for node in version_kind)
    assert not any(
        otype[node] in {"reading", "div", "chapter", "verse", "manuscript", "variant_word"}
        for node in version_kind
    )


def test_unknown_snapshot_preserves_generated_status_without_inventing_generator_provenance() -> None:
    data = build_tf_data([_book()], upstream_commit="future-unresearched-snapshot")
    node = _generated_book(data)

    assert data.node_features["generation_marker"][node] == "OCP-Trans"
    assert data.node_features["generated_language"][node] == "French"
    assert node not in data.node_features.get("generation_method", {})
    assert node not in data.node_features.get("generation_model", {})
