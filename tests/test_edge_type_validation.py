from copy import deepcopy
from pathlib import Path

import pytest

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


def _data():
    return build_tf_data(
        [
            parse_file(FIXTURES / "sample.xml"),
            parse_file(FIXTURES / "orphan_reading.xml"),
            parse_file(FIXTURES / "ownership_edges.xml"),
        ]
    )


def _node(data, kind):
    return next(node for node, node_kind in data.node_features["otype"].items() if node_kind == kind)


SOURCE_CASES = (
    ("parent", "manuscript", "div"),
    ("reading_of", "manuscript", "unit"),
    ("variant_word_of", "manuscript", "reading"),
    ("witness", "unit", "manuscript"),
    ("manuscript_of", "reading", "book"),
    ("resource_of", "reading", "book"),
)

TARGET_CASES = (
    ("parent", "unit", "book"),
    ("reading_of", "reading", "book"),
    ("variant_word_of", "variant_word", "unit"),
    ("witness", "reading", "unit"),
    ("manuscript_of", "manuscript", "unit"),
    ("resource_of", "resource", "reading"),
)


@pytest.mark.parametrize("feature,wrong_source_type,target_type", SOURCE_CASES)
def test_validate_rejects_wrong_canonical_edge_source_type(feature, wrong_source_type, target_type):
    data = _data()
    wrong_source = _node(data, wrong_source_type)
    target = _node(data, target_type)
    data.edge_features.setdefault(feature, {})[wrong_source] = {target}

    errors = data.validate()
    assert any(
        feature in error
        and str(wrong_source) in error
        and wrong_source_type in error
        and "source" in error
        for error in errors
    ), errors


@pytest.mark.parametrize("feature,source_type,wrong_target_type", TARGET_CASES)
def test_validate_rejects_wrong_canonical_edge_target_type(feature, source_type, wrong_target_type):
    data = _data()
    source = _node(data, source_type)
    wrong_target = _node(data, wrong_target_type)
    data.edge_features.setdefault(feature, {}).setdefault(source, set()).add(wrong_target)

    errors = data.validate()
    assert any(
        feature in error
        and str(wrong_target) in error
        and wrong_target_type in error
        and "target" in error
        for error in errors
    ), errors


def test_special_and_metadata_edge_type_unions_are_valid():
    data = _data()
    otype = data.node_features["otype"]

    orphan = _node(data, "orphan_reading")
    assert any(otype[target] == "div" for target in data.edge_features["parent"][orphan])
    assert any(otype[target] == "manuscript" for target in data.edge_features["witness"][orphan])

    metadata = _node(data, "version_metadata")
    assert any(
        otype[source] == "manuscript" and metadata in targets
        for source, targets in data.edge_features["manuscript_of"].items()
    )
    assert any(
        otype[source] == "resource" and metadata in targets
        for source, targets in data.edge_features["resource_of"].items()
    )
    assert data.validate() == []


def test_unregistered_custom_edge_keeps_generic_existing_node_contract():
    data = _data()
    reading = _node(data, "reading")
    book = _node(data, "book")
    data.edge_features["research_link"] = {reading: {book}}
    assert data.validate() == []


class NeverSaveFabric:
    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        raise AssertionError("type-corrupted graph reached Text-Fabric save")


def test_writer_rejects_canonical_edge_type_corruption_before_fabric_save(tmp_path):
    data = deepcopy(_data())
    manuscript = _node(data, "manuscript")
    unit = _node(data, "unit")
    data.edge_features["reading_of"][manuscript] = {unit}

    with pytest.raises(ValueError, match="reading_of"):
        write_tf(data, tmp_path / "tf", fabric_factory=NeverSaveFabric)
