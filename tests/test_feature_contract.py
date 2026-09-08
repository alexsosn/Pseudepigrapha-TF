from __future__ import annotations

from copy import deepcopy
import inspect
from pathlib import Path

from pseudepigrapha_tf import build_tf_data
import pseudepigrapha_tf.feature_docs as feature_docs
from pseudepigrapha_tf.feature_contract import documentation_category, with_documentation_category
from pseudepigrapha_tf.feature_docs import edge_feature_contracts, serialized_feature_contract
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import (
    _edge_features_with_api_dependencies,
    _metadata_with_serialized_features,
    _node_features_with_format_dependencies,
)


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


def test_serialization_metadata_owns_documentation_categories():
    data = _data()
    node_features = _node_features_with_format_dependencies(data, isolate=True)
    edge_features = _edge_features_with_api_dependencies(data, isolate=True)
    metadata = _metadata_with_serialized_features(data, node_features, edge_features)

    for name in node_features:
        assert metadata[name]["documentationCategory"] == documentation_category(name, kind="node")
    for name in edge_features:
        assert metadata[name]["documentationCategory"] == documentation_category(name, kind="edge")


def test_canonical_documentation_category_overrides_stale_emitter_metadata():
    metadata = with_documentation_category(
        "source_ref",
        kind="node",
        metadata={"documentationCategory": "stale category", "description": "probe"},
    )

    assert metadata["documentationCategory"] == "Source/version identity and provenance"
    assert metadata["description"] == "probe"


def test_feature_renderer_has_no_private_semantic_registry_or_duplicated_emitter_descriptions():
    source = inspect.getsource(feature_docs)

    for registry in (
        "_SECTION_FEATURES",
        "_IDENTITY_FEATURES",
        "_APPARATUS_FEATURES",
        "_GENERATED_FEATURES",
        "_ANOMALY_FEATURES",
    ):
        assert registry not in source
    assert "published OCP docs.id from the historical 2017 classification snapshot" not in source
    assert "JSON array of exact public OCP genre labels from the historical 2017 catalogue" not in source


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
