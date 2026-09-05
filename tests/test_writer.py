from pathlib import Path

import pytest

from pseudepigrapha_tf.graph import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


class FakeFabric:
    instances = []

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.saved = None
        self.__class__.instances.append(self)

    def save(self, **kwargs):
        self.saved = kwargs
        return True


class ExplodingFabric:
    def __init__(self, *args, **kwargs):
        raise AssertionError("serializer must not be constructed for invalid graph data")


def _feature_snapshots(data):
    return (
        {name: dict(values) for name, values in data.node_features.items()},
        {
            name: {source: set(targets) for source, targets in values.items()}
            for name, values in data.edge_features.items()
        },
    )


def test_writer_delegates_validated_features_to_text_fabric(tmp_path):
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    assert write_tf(data, tmp_path / "tf", fabric_factory=FakeFabric)
    saved = FakeFabric.instances[-1].saved
    assert saved["nodeFeatures"] is not data.node_features
    for name, values in data.node_features.items():
        assert saved["nodeFeatures"][name] == values
    for name in (
        "prefix_utf8", "g_word_utf8", "trailer_utf8", "boundary_utf8",
        "reading_text", "ms_abbrev", "resource_name", "undefined_manuscript",
    ):
        assert name in saved["nodeFeatures"]
        assert saved["metaData"][name]["valueType"] in {"str", "int"}
    assert saved["metaData"]["undefined_manuscript"]["valueType"] == "int"

    assert saved["edgeFeatures"] is not data.edge_features
    for name, values in data.edge_features.items():
        assert saved["edgeFeatures"][name] == values
        assert saved["edgeFeatures"][name] is not values
        for source, targets in values.items():
            assert saved["edgeFeatures"][name][source] is not targets
    assert "witness" in saved["edgeFeatures"]
    assert "manuscript_of" in saved["edgeFeatures"]

    assert saved["metaData"] is not data.metadata
    assert saved["metaData"]["otext"] == data.metadata["otext"]
    assert saved["location"] == str(tmp_path / "tf")
    assert saved["module"] == ""


def test_public_writer_rejects_mutated_invalid_graph_before_serializer(tmp_path):
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    book = next(node for node, kind in data.node_features["otype"].items() if kind == "book")
    data.edge_features["oslots"][book].add(data.max_slot + 1)

    with pytest.raises(ValueError, match="oslots points outside slot range"):
        write_tf(data, tmp_path / "tf", fabric_factory=ExplodingFabric)


def test_default_writer_reuses_graph_feature_payloads_without_mutation(monkeypatch, tmp_path):
    import tf.fabric

    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    node_snapshot, edge_snapshot = _feature_snapshots(data)
    monkeypatch.setattr(tf.fabric, "Fabric", FakeFabric)

    assert write_tf(data, tmp_path / "tf")
    saved = FakeFabric.instances[-1].saved

    assert saved["nodeFeatures"] is not data.node_features
    for name, values in data.node_features.items():
        assert saved["nodeFeatures"][name] is values

    assert saved["edgeFeatures"] is not data.edge_features
    for name, values in data.edge_features.items():
        assert saved["edgeFeatures"][name] is values

    assert data.node_features == node_snapshot
    assert data.edge_features == edge_snapshot


def test_real_text_fabric_write_does_not_mutate_reused_graph_payloads(tmp_path):
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    node_snapshot, edge_snapshot = _feature_snapshots(data)

    assert write_tf(data, tmp_path / "tf")

    assert data.node_features == node_snapshot
    assert data.edge_features == edge_snapshot
