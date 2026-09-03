from pathlib import Path

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


def test_writer_delegates_validated_features_to_text_fabric(tmp_path):
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    assert write_tf(data, tmp_path / "tf", fabric_factory=FakeFabric)
    saved = FakeFabric.instances[-1].saved
    assert saved["nodeFeatures"] is not data.node_features
    for name, values in data.node_features.items():
        assert saved["nodeFeatures"][name] == values
    for name in (
        "prefix_utf8", "g_word_utf8", "trailer_utf8", "boundary_utf8",
        "reading_text", "ms_abbrev", "resource_name",
    ):
        assert name in saved["nodeFeatures"]
    assert saved["edgeFeatures"] is data.edge_features
    assert saved["metaData"] is data.metadata
    assert saved["location"] == str(tmp_path / "tf")
    assert saved["module"] == ""
