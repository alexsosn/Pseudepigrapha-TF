from pathlib import Path

from pseudepigrapha_tf import conversion
from pseudepigrapha_tf.graph import _Builder
from pseudepigrapha_tf.parser import parse_file


FIXTURES = Path(__file__).parent / "fixtures"


class _TrackingObjects(list):
    def __init__(self):
        super().__init__()
        self.full_iterations = 0
        self.yielded = 0

    def __iter__(self):
        self.full_iterations += 1
        for item in super().__iter__():
            self.yielded += 1
            yield item


class _TrackingBuilder(_Builder):
    scans_before_finalize = -1
    yielded_before_finalize = -1

    def __init__(self):
        super().__init__()
        self.objects = _TrackingObjects()

    def finalize(self, **kwargs):
        type(self).scans_before_finalize = self.objects.full_iterations
        type(self).yielded_before_finalize = self.objects.yielded
        return super().finalize(**kwargs)


def test_textual_versions_do_not_full_scan_global_objects_before_finalize(monkeypatch):
    book = parse_file(FIXTURES / "multiple_versions.xml")
    monkeypatch.setattr(conversion, "_Builder", _TrackingBuilder)

    data = conversion.build_tf_data([book])

    assert data.validate() == []
    assert _TrackingBuilder.scans_before_finalize == 0
    assert _TrackingBuilder.yielded_before_finalize == 0

    manuscripts = {
        data.node_features["ms_abbrev"][node]: node
        for node, kind in data.node_features["otype"].items()
        if kind == "manuscript" and data.node_features.get("ms_abbrev", {}).get(node)
    }
    assert set(manuscripts) == {"S", "G"}
    assert data.node_features["version_id"][manuscripts["S"]] == "Multi__Syriac"
    assert data.node_features["version_id"][manuscripts["G"]] == "Multi__Greek"
