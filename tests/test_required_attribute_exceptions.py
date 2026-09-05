from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


def test_ps_eup_missing_manuscript_language_stays_unknown_and_audited(tmp_path):
    source = b'''<book filename="Ps-Eup" title="Pseudo-Eupolemus" textStructure="fragmentary">
  <version title="Praep. Evang. (Frag. 1)" author="Eusebius" language="Greek" fragment="1">
    <divisions><division label="Paragraph"/></divisions>
    <manuscripts><ms abbrev="Mras" show="yes"><name>Mras</name></ms></manuscripts>
    <text><div number="1"><unit id="1"><reading option="0" mss="Mras ">alpha</reading></unit></div></text>
  </version>
</book>'''
    path = tmp_path / "Ps-Eup.xml"
    path.write_bytes(source)

    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    manuscript = books[0].versions[0].manuscripts[0]
    assert manuscript.language == ""

    graph = build_tf_data(books)
    manuscript_node = next(
        node
        for node, kind in graph.node_features["otype"].items()
        if kind == "manuscript"
    )
    assert graph.node_features.get("ms_language", {}).get(manuscript_node, "") == ""

    report = build_conversion_report(tmp_path, books, graph)
    assert report["status"] == "ok", report["failed_checks"]
    assert report["semantic_checks"]["manuscripts"] is True
