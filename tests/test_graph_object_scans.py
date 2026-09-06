from pathlib import Path

from pseudepigrapha_tf import conversion
from pseudepigrapha_tf.graph import _Builder
from pseudepigrapha_tf.parser import parse_bytes, parse_file


FIXTURES = Path(__file__).parent / "fixtures"


class _TrackingObjects(list):
    def __init__(self):
        super().__init__()
        self.full_iterations = 0
        self.yielded = 0
        self.slice_reads: list[slice] = []

    def __iter__(self):
        self.full_iterations += 1
        for item in super().__iter__():
            self.yielded += 1
            yield item

    def __getitem__(self, index):
        if isinstance(index, slice):
            self.slice_reads.append(index)
        return super().__getitem__(index)


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


def test_version_identity_stamping_does_not_slice_graph_objects():
    builder = _Builder()
    builder.objects = _TrackingObjects()
    builder.slot(g_word_utf8="slot")
    builder.node("before", "marker", {1}, version_id="older")
    start = len(builder.objects)
    builder.node("current-a", "marker", {1})
    builder.node("current-b", "marker", {1})

    conversion._stamp_version_identity(builder, start, "Current")

    assert builder.objects.slice_reads == []
    assert builder.objects[0].features["version_id"] == "older"
    assert builder.objects[1].features["version_id"] == "Current"
    assert builder.objects[2].features["version_id"] == "Current"


def test_finalize_groups_objects_with_one_global_iteration():
    builder = _Builder()
    builder.objects = _TrackingObjects()
    builder.slot(g_word_utf8="slot")
    builder.node("a1", "alpha", {1}, marker="a1")
    builder.node("b1", "beta", {1}, marker="b1")
    builder.node("a2", "alpha", {1}, marker="a2")

    data = builder.finalize(
        upstream_repository="https://example.invalid/source",
        upstream_commit="",
        converter_version="test",
    )

    assert builder.objects.full_iterations == 1
    non_slots = range(data.max_slot + 1, data.max_node + 1)
    assert [data.node_features["otype"][node] for node in non_slots] == [
        "alpha",
        "alpha",
        "beta",
    ]
    assert [data.node_features["marker"][node] for node in non_slots] == [
        "a1",
        "a2",
        "b1",
    ]


def test_core_undeclared_witness_is_reused_by_orphan_reading():
    book = parse_bytes(
        b'''<book filename="Reuse" title="Witness reuse">
  <version title="Greek" author="Anonymous" language="Greek">
    <divisions><division label="Chapter"/></divisions>
    <manuscripts>
      <ms abbrev="A" language="Greek" show="yes"><name>A</name></ms>
    </manuscripts>
    <text>
      <div number="1">
        <unit id="1"><reading option="0" mss="X ">alpha</reading></unit>
        <reading option="2" mss="X ">orphan beta</reading>
      </div>
    </text>
  </version>
</book>''',
        source_path="witness-reuse.xml",
    )

    data = conversion.build_tf_data([book])
    x_nodes = [
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "manuscript" and data.node_features.get("ms_abbrev", {}).get(node) == "X"
    ]
    assert len(x_nodes) == 1
    x_node = x_nodes[0]
    assert data.node_features["undefined_manuscript"][x_node] == 1

    reading = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "reading" and data.node_features.get("reading_text", {}).get(node) == "alpha"
    )
    orphan = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "orphan_reading"
    )
    owner = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "book"
    )

    assert data.edge_features["witness"][reading] == {x_node}
    assert data.edge_features["witness"][orphan] == {x_node}
    assert data.edge_features["manuscript_of"][x_node] == {owner}
    assert data.node_features["version_id"][x_node] == data.node_features["version_id"][orphan]
