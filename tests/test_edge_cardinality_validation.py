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
            parse_file(FIXTURES / "metadata_only_version.xml"),
            parse_file(FIXTURES / "undeclared_witness.xml"),
            parse_file(FIXTURES / "no_witnesses.xml"),
            parse_file(FIXTURES / "ellipsis.xml"),
        ]
    )


def _nodes(data, kind):
    return [node for node, node_kind in data.node_features["otype"].items() if node_kind == kind]


def _node(data, kind):
    return _nodes(data, kind)[0]


def _other_node(data, kind, excluded):
    return next(node for node in _nodes(data, kind) if node != excluded)


def _assert_cardinality_error(errors, feature, node, node_type, count, expected):
    assert any(
        feature in error
        and str(node) in error
        and node_type in error
        and str(count) in error
        and expected in error
        for error in errors
    ), errors


EXACT_ONE_CASES = (
    ("reading_of", "reading", "unit"),
    ("variant_word_of", "variant_word", "reading"),
    ("manuscript_of", "manuscript", "book"),
    ("resource_of", "resource", "book"),
    ("parent", "unit", "div"),
    ("parent", "ellipsis", "div"),
    ("parent", "orphan_reading", "div"),
)


@pytest.mark.parametrize("feature,source_type,target_type", EXACT_ONE_CASES)
def test_validate_rejects_missing_exact_one_canonical_relation(feature, source_type, target_type):
    data = _data()
    source = _node(data, source_type)
    data.edge_features[feature].pop(source, None)

    errors = data.validate()
    _assert_cardinality_error(errors, feature, source, source_type, 0, "exactly 1")


@pytest.mark.parametrize("feature,source_type,target_type", EXACT_ONE_CASES)
def test_validate_rejects_second_exact_one_canonical_target(feature, source_type, target_type):
    data = _data()
    source = _node(data, source_type)
    targets = data.edge_features[feature][source]
    existing = next(iter(targets))
    second = _other_node(data, target_type, existing)
    targets.add(second)

    errors = data.validate()
    _assert_cardinality_error(errors, feature, source, source_type, 2, "exactly 1")


def test_validate_rejects_div_with_second_parent_but_allows_top_level_without_parent():
    data = _data()
    divs = _nodes(data, "div")
    parent = data.edge_features["parent"]

    top_level = next(div for div in divs if div not in parent)
    assert data.node_features["div_level"][top_level] == 1

    nested = next(div for div in divs if div in parent)
    existing = next(iter(parent[nested]))
    parent[nested].add(_other_node(data, "div", existing))

    errors = data.validate()
    _assert_cardinality_error(errors, "parent", nested, "div", 2, "at most 1")


def test_witness_remains_zero_to_many():
    data = _data()
    witnesses = data.edge_features.get("witness", {})

    no_witness_reading = next(
        reading for reading in _nodes(data, "reading") if not witnesses.get(reading, set())
    )
    multi_witness_source = next(
        source for source, targets in witnesses.items() if len(targets) >= 2
    )

    assert no_witness_reading not in witnesses or witnesses[no_witness_reading] == set()
    assert len(witnesses[multi_witness_source]) >= 2
    assert data.validate() == []


def test_metadata_only_manuscript_and_resource_require_exactly_one_owner():
    data = _data()
    otype = data.node_features["otype"]

    metadata_manuscript = next(
        source
        for source, targets in data.edge_features["manuscript_of"].items()
        if any(otype[target] == "version_metadata" for target in targets)
    )
    metadata_resource = next(
        source
        for source, targets in data.edge_features["resource_of"].items()
        if any(otype[target] == "version_metadata" for target in targets)
    )

    data.edge_features["manuscript_of"].pop(metadata_manuscript)
    data.edge_features["resource_of"].pop(metadata_resource)
    errors = data.validate()

    _assert_cardinality_error(errors, "manuscript_of", metadata_manuscript, "manuscript", 0, "exactly 1")
    _assert_cardinality_error(errors, "resource_of", metadata_resource, "resource", 0, "exactly 1")


def test_undeclared_witness_manuscript_requires_exactly_one_owner():
    data = _data()
    manuscript = next(
        node
        for node in _nodes(data, "manuscript")
        if data.node_features.get("undefined_manuscript", {}).get(node) == 1
    )
    data.edge_features["manuscript_of"].pop(manuscript)

    errors = data.validate()
    _assert_cardinality_error(errors, "manuscript_of", manuscript, "manuscript", 0, "exactly 1")


class NeverSaveFabric:
    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        raise AssertionError("cardinality-corrupted graph reached Text-Fabric save")


def test_writer_rejects_type_correct_multi_owner_before_fabric_save(tmp_path):
    data = deepcopy(_data())
    reading = _node(data, "reading")
    existing = next(iter(data.edge_features["reading_of"][reading]))
    second_unit = _other_node(data, "unit", existing)
    data.edge_features["reading_of"][reading].add(second_unit)

    with pytest.raises(ValueError, match="reading_of"):
        write_tf(data, tmp_path / "tf", fabric_factory=NeverSaveFabric)
