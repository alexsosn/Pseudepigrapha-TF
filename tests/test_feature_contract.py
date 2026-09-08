from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pseudepigrapha_tf import build_tf_data
from pseudepigrapha_tf.feature_docs import edge_feature_contracts, serialized_feature_contract
from pseudepigrapha_tf.parser import parse_file


FIXTURE = Path(__file__).parent / "fixtures" / "sample.xml"


def _data():
    return build_tf_data([parse_file(FIXTURE)])


def test_serialized_feature_contract_includes_stable_empty_features_without_mutation():
    data = _data()
    before_node = deepcopy(data.node_features)
    before_edge = deepcopy(data.edge_features)
    before_meta = deepcopy(data.metadata)

    contract = serialized_feature_contract(data)

    assert data.node_features == before_node
    assert data.edge_features == before_edge
    assert data.metadata == before_meta

    assert contract["node"]["prefix_utf8"]["serialized"] is True
    assert contract["node"]["resource_name"]["serialized"] is True
    assert contract["node"]["undefined_manuscript"]["serialized"] is True
    assert contract["edge"]["witness"]["serialized"] is True
    assert contract["edge"]["manuscript_of"]["serialized"] is True


def test_serialized_feature_contract_preserves_canonical_metadata():
    data = _data()
    data.node_features["controlled_probe"] = {1: "alpha"}
    data.metadata["controlled_probe"] = {
        "valueType": "str",
        "description": "controlled test feature",
        "controlledVocabularyJson": '["alpha","beta"]',
    }

    feature = serialized_feature_contract(data)["node"]["controlled_probe"]

    assert feature["valueType"] == "str"
    assert feature["description"] == "controlled test feature"
    assert feature["metadata"]["controlledVocabularyJson"] == '["alpha","beta"]'
    assert feature["observedNodeTypes"] == ("word",)


def test_every_supported_feature_has_a_researcher_facing_description():
    contract = serialized_feature_contract(_data(), include_supported=True)

    placeholders = []
    for kind in ("node", "edge"):
        for name, feature in contract[kind].items():
            description = feature["description"]
            if not description or description == name or description.startswith("OCP/TF feature "):
                placeholders.append(f"{kind}:{name}")

    assert placeholders == []


def test_supported_contract_includes_metadata_layers_even_when_fixture_does_not_attach_them():
    contract = serialized_feature_contract(_data(), include_supported=True)["node"]

    for name in (
        "intro_label",
        "intro_title_json",
        "intro_version_json",
        "intro_citation_json",
        "intro_bibliography_json",
        "intro_manuscripts_json",
        "historical_ocp_doc_id",
        "historical_genres_json",
        "historical_biblical_figures_json",
    ):
        assert name in contract
        assert contract[name]["supported"] is True
        assert contract[name]["description"]

    assert contract["intro_title_json"]["metadata"]["documentationCategory"] == "Public work metadata"
    assert contract["historical_genres_json"]["metadata"]["documentationCategory"] == "Historical classifications"


def test_edge_contracts_are_reusable_and_cover_translation_and_tf_support_semantics():
    contracts = edge_feature_contracts()

    for name in (
        "parent",
        "reading_of",
        "variant_word_of",
        "witness",
        "manuscript_of",
        "resource_of",
        "translation_of",
        "translation_unit_of",
        "oslots",
    ):
        assert name in contracts

    assert contracts["translation_of"]["sourceTypes"] == ("book",)
    assert contracts["translation_of"]["targetTypes"] == ("book",)
    assert contracts["translation_of"]["cardinality"] == "exactly 1"
    assert contracts["translation_unit_of"]["sourceTypes"] == ("unit",)
    assert contracts["translation_unit_of"]["targetTypes"] == ("unit",)
    assert contracts["translation_unit_of"]["cardinality"] == "exactly 1"

    oslots = contracts["oslots"]
    assert oslots["targetTypes"] == ("word",)
    assert oslots["technicalSupport"] is True
    assert "technical" in oslots["description"].lower()


def test_supported_optional_relation_is_documentable_even_when_not_serialized_here():
    data = _data()
    data.edge_features.pop("resource_of", None)
    contract = serialized_feature_contract(data, include_supported=True)

    resource_of = contract["edge"]["resource_of"]
    assert resource_of["serialized"] is False
    assert resource_of["supported"] is True
    assert resource_of["sourceTypes"] == ("resource",)
    assert resource_of["targetTypes"] == ("book", "version_metadata")
