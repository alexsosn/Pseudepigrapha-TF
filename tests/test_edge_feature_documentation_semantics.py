from __future__ import annotations

from pathlib import Path

from pseudepigrapha_tf import build_tf_data
from pseudepigrapha_tf.feature_docs import render_feature_docs, serialized_feature_contract
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import (
    _edge_features_with_api_dependencies,
    _metadata_with_serialized_features,
    _node_features_with_format_dependencies,
)


FIXTURE = Path(__file__).parent / "fixtures" / "sample.xml"


def _data():
    return build_tf_data([parse_file(FIXTURE)])


def test_unvalued_edge_docs_match_text_fabric_edge_value_semantics():
    data = _data()
    contract = serialized_feature_contract(data, include_supported=True)["edge"]

    # Pseudepigrapha-TF currently represents every supported relation with
    # set-valued adjacency maps, i.e. no per-edge values. Text-Fabric 13.1
    # reports such edge features with type `none`, not the serializer's
    # technical @valueType fallback.
    for name, feature in contract.items():
        assert feature["edgeValues"] is False, name
        assert feature["valueType"] == "none", name

    pages = render_feature_docs(data)
    for name in ("oslots", "parent", "witness", "translation_of"):
        assert "**Value type:** `none`" in pages[f"{name}.md"], name


def test_unvalued_edge_docs_do_not_change_tf_serializer_metadata_contract():
    data = _data()
    node_features = _node_features_with_format_dependencies(data, isolate=True)
    edge_features = _edge_features_with_api_dependencies(data, isolate=True)
    metadata = _metadata_with_serialized_features(data, node_features, edge_features)

    # Fabric.save still needs valid feature metadata on disk; documentation
    # semantics must therefore be modeled separately from @valueType.
    assert metadata["parent"]["valueType"] == "str"
    assert metadata["oslots"]["valueType"] == "str"
