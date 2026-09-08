from __future__ import annotations

from pathlib import Path

import yaml

import pseudepigrapha_tf.feature_docs as feature_docs
from pseudepigrapha_tf import build_tf_data
from pseudepigrapha_tf.parser import parse_file


FIXTURE = Path(__file__).parent / "fixtures" / "sample.xml"
ROOT = Path(__file__).parents[1]


def _data():
    return build_tf_data([parse_file(FIXTURE)])


def test_feature_contract_exposes_canonical_documentation_categories():
    contract = feature_docs.serialized_feature_contract(_data(), include_supported=True)

    assert contract["node"]["otype"]["metadata"]["documentationCategory"] == "Text-Fabric warp and section/text features"
    assert contract["node"]["source_ref"]["metadata"]["documentationCategory"] == "Source/version identity and provenance"
    assert contract["node"]["reading_text"]["metadata"]["documentationCategory"] == "Apparatus and witness features/relations"
    assert contract["node"]["generation_model"]["metadata"]["documentationCategory"] == "Generated-translation features/relations"
    assert contract["node"]["is_empty_div"]["metadata"]["documentationCategory"] == "Preserved anomalies / technical anchors"


def test_renderer_covers_supported_contract_deterministically():
    data = _data()
    first = feature_docs.render_feature_docs(data)
    second = feature_docs.render_feature_docs(data)
    contract = feature_docs.serialized_feature_contract(data, include_supported=True)

    expected = {"0_home.md"}
    expected.update(f"{name}.md" for name in contract["node"])
    expected.update(f"{name}.md" for name in contract["edge"])

    assert first == second
    assert set(first) == expected
    assert first["source_ref.md"].startswith("# `source_ref`\n")
    assert "**Kind:** node" in first["source_ref.md"]
    assert "**Value type:** `str`" in first["source_ref.md"]
    assert contract["node"]["source_ref"]["description"] in first["source_ref.md"]


def test_node_page_exposes_observed_node_applicability():
    data = _data()
    contract = feature_docs.serialized_feature_contract(data, include_supported=True)["node"]["source_ref"]
    observed = contract["observedNodeTypes"]
    assert observed

    page = feature_docs.render_feature_docs(data)["source_ref.md"]
    expected = ", ".join(f"`{node_type}`" for node_type in observed)
    assert f"**Observed node types:** {expected}" in page


def test_optional_metadata_page_exposes_canonical_supported_node_applicability():
    data = _data()
    contract = feature_docs.serialized_feature_contract(data, include_supported=True)["node"]["intro_title_json"]

    # The small XML fixture does not attach the public metadata layer, but the
    # real emitter establishes document_metadata as its canonical node type.
    assert contract["observedNodeTypes"] == ()
    assert contract["supportedNodeTypes"] == ("document_metadata",)

    page = feature_docs.render_feature_docs(data)["intro_title_json.md"]
    assert "**Observed node types:** none in this graph" in page
    assert "**Supported node types:** `document_metadata`" in page


def test_renderer_preserves_controlled_vocabulary_from_canonical_metadata():
    data = _data()
    data.node_features["controlled_probe"] = {1: "alpha"}
    data.metadata["controlled_probe"] = {
        "valueType": "str",
        "description": "controlled test feature",
        "documentationCategory": "Remaining source-preserved XML attributes/content",
        "controlledVocabularyJson": '["alpha","beta"]',
    }

    page = feature_docs.render_feature_docs(data)["controlled_probe.md"]

    assert "## Controlled vocabulary" in page
    assert "- `alpha`" in page
    assert "- `beta`" in page


def test_edge_pages_are_generated_from_reusable_endpoint_contracts():
    pages = feature_docs.render_feature_docs(_data())

    translation = pages["translation_of.md"]
    assert "**Direction:** `book` → `book`" in translation
    assert "**Cardinality:** exactly 1" in translation
    assert "`version_kind=generated_translation`" in translation

    resource = pages["resource_of.md"]
    assert "**Direction:** `resource` → `book`, `version_metadata`" in resource

    oslots = pages["oslots.md"]
    assert "technical" in oslots.lower()
    assert "not scholarly containment" in oslots.lower()


def test_supported_but_unserialized_feature_is_explicit_on_its_page():
    data = _data()
    data.edge_features.pop("resource_of", None)

    resource = feature_docs.render_feature_docs(data)["resource_of.md"]

    assert "Serialized in this corpus:" not in resource
    assert "**Supported by converter:** yes" in resource
    assert "Availability is corpus-dependent" in resource


def test_landing_page_has_frozen_researcher_groups_and_exact_feature_links():
    landing = feature_docs.render_feature_docs(_data())["0_home.md"]

    for title in (
        "Text-Fabric warp and section/text features",
        "Source/version identity and provenance",
        "Apparatus and witness features/relations",
        "Generated-translation features/relations",
        "Public work metadata",
        "Historical classifications",
        "Preserved anomalies / technical anchors",
        "Remaining source-preserved XML attributes/content",
    ):
        assert f"## {title}" in landing
    assert "[`source_ref`](source_ref.md)" in landing
    assert "[`translation_of`](translation_of.md)" in landing


def test_write_and_validate_feature_docs_detect_drift(tmp_path):
    data = _data()
    destination = tmp_path / "features"

    feature_docs.write_feature_docs(data, destination)
    assert feature_docs.validate_feature_docs(data, destination) == []

    source_ref = destination / "source_ref.md"
    source_ref.write_text(source_ref.read_text(encoding="utf-8") + "\nstale edit\n", encoding="utf-8")
    failures = feature_docs.validate_feature_docs(data, destination)
    assert any("source_ref.md" in failure and "stale" in failure for failure in failures)


def test_text_fabric_feature_help_routing_targets_tracked_feature_pages():
    config = yaml.safe_load((ROOT / "app" / "config.yaml").read_text(encoding="utf-8"))
    docs = config["docs"]

    assert docs["featurePage"] == "0_home"
    feature_base = docs.get("featureBase", "{docBase}/features/<feature>{docExt}")
    landing_url = (
        feature_base.replace("{docBase}", docs["docBase"])
        .replace("<feature>", docs["featurePage"])
        .replace("{docExt}", docs["docExt"])
    )
    source_ref_url = (
        feature_base.replace("{docBase}", docs["docBase"])
        .replace("<feature>", "source_ref")
        .replace("{docExt}", docs["docExt"])
    )
    assert landing_url.endswith("/docs/features/0_home.md")
    assert source_ref_url.endswith("/docs/features/source_ref.md")


def test_tracked_feature_docs_cover_browser_help_without_drift():
    feature_dir = ROOT / "docs" / "features"

    assert feature_dir.is_dir(), "Text-Fabric feature-help target docs/features/ is missing"
    assert feature_docs.validate_feature_docs(_data(), feature_dir) == []
