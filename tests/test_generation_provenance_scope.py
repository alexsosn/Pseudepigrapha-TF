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


def test_unknown_snapshot_preserves_generated_status_without_inventing_generator_provenance() -> None:
    data = build_tf_data([_book()], upstream_commit="future-unresearched-snapshot")
    node = _generated_book(data)

    assert data.node_features["generation_marker"][node] == "OCP-Trans"
    assert data.node_features["generated_language"][node] == "French"
    assert node not in data.node_features.get("generation_method", {})
    assert node not in data.node_features.get("generation_model", {})
