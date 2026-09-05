from pathlib import Path

import pytest

from pseudepigrapha_tf import Apparatus
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


class FakeFabric:
    instances = []

    def __init__(self, *args, **kwargs):
        self.saved = None
        self.__class__.instances.append(self)

    def save(self, **kwargs):
        self.saved = kwargs
        return True


def _data():
    return build_tf_data([parse_file(FIXTURES / "no_witnesses.xml")])


def test_writer_serializes_empty_core_apparatus_edges_without_mutating_graph(tmp_path):
    data = _data()

    assert not data.node_features.get("ms_abbrev")
    assert "witness" not in data.edge_features
    assert "manuscript_of" not in data.edge_features
    assert "variant_word_of" not in data.edge_features

    assert write_tf(data, tmp_path / "tf", fabric_factory=FakeFabric)
    saved = FakeFabric.instances[-1].saved

    assert saved["edgeFeatures"] is not data.edge_features
    assert saved["edgeFeatures"]["witness"] == {}
    assert saved["edgeFeatures"]["manuscript_of"] == {}
    assert "variant_word_of" not in saved["edgeFeatures"]
    assert saved["metaData"]["witness"]["valueType"] == "str"
    assert saved["metaData"]["manuscript_of"]["valueType"] == "str"

    # Serialization requirements must not become invented semantic graph data.
    assert "witness" not in data.edge_features
    assert "manuscript_of" not in data.edge_features


def test_witness_free_corpus_reloads_core_edges_and_passage_has_empty_witnesses(tmp_path):
    pytest.importorskip("tf")
    from tf.fabric import Fabric

    data = _data()
    output = tmp_path / "tf"
    assert write_tf(data, output)

    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = TF.load(
        "reading_text source_ref unit_id is_primary undefined_manuscript "
        "reading_of witness manuscript_of",
        silent="deep",
    )
    assert api is not None
    assert hasattr(api.E, "witness")
    assert hasattr(api.E, "manuscript_of")

    passage = Apparatus(api).passage("NoWitness", "1", "1")
    assert passage["source_refs"] == ("1:1",)
    assert len(passage["units"]) == 1
    assert [reading["text"] for reading in passage["units"][0]["readings"]] == ["alpha beta"]
    assert passage["witnesses"] == {}
