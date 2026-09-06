from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from tf.fabric import Fabric

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.metadata import (
    WorkMetadata,
    attach_public_metadata,
    augment_conversion_report_with_public_metadata,
    load_public_metadata,
)
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.writer import write_tf


ONE_XML = '''<book filename="One" title="One-level work">
  <version title="Greek" author="Anonymous" language="Greek">
    <divisions><division label="Paragraph" delimiter="."/></divisions>
    <manuscripts><ms abbrev="A" language="Greek" show="yes"><name>A</name></ms></manuscripts>
    <text><div number="7"><unit id="1"><reading option="0" mss="A ">abc def</reading></unit></div></text>
  </version>
</book>
'''


def _write_source(tmp_path: Path, payload: dict) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "One.xml").write_text(ONE_XML, encoding="utf-8")
    (docs / "Empty.xml").write_bytes(b"")
    raw = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    (docs / "intros.json").write_text(raw, encoding="utf-8", newline="")
    return docs


def _payload() -> dict:
    rich = '<h3>Witnesses</h3>\r\n<table><tbody><tr><td><em>A</em></td><td>α &amp; β</td></tr></tbody></table>\r\n<ul><li>First</li></ul>'
    return {
        "_meta": {"exported": "2026-09-05", "source": "test db", "note": "test"},
        "documents": {
            "One.xml": {
                "title": "JSON title deliberately differs",
                "version": 1.0,
                "citation": '<p>Cite <em>One</em>.</p>',
                "fields": {
                    "introduction": rich,
                    "provenance": "",
                    "themes": None,
                    "bibliography": '<h3>Works</h3>\r\n<ul><li>A &amp; B</li></ul>',
                },
            },
            "Empty.xml": {
                "title": "Empty work",
                "version": 2.0,
                "citation": "<p>Empty citation</p>",
                "fields": {"status": "<p>No encoded text.</p>"},
            },
        },
    }


def _build_with_metadata(docs: Path):
    books, warnings = load_source_directory(docs)
    metadata = load_public_metadata(docs)
    data = build_tf_data(books)
    attach_public_metadata(data, metadata)
    return books, warnings, metadata, data


def test_loader_maps_by_filename_and_preserves_sparse_scalars(tmp_path: Path):
    docs = _write_source(tmp_path, _payload())
    metadata = load_public_metadata(docs)

    one = metadata.documents["One.xml"]
    assert one.title == "JSON title deliberately differs"
    assert one.version == 1.0
    assert one.citation == '<p>Cite <em>One</em>.</p>'
    assert one.fields["introduction"].endswith("</ul>")
    assert one.fields["provenance"] == ""
    assert one.fields["themes"] is None
    assert "status" not in one.fields
    assert metadata.source_sha256 == hashlib.sha256((docs / "intros.json").read_bytes()).hexdigest()


def test_loader_rejects_unknown_json_document_key(tmp_path: Path):
    payload = _payload()
    payload["documents"]["Ghost.xml"] = {
        "title": "Ghost",
        "version": 1.0,
        "citation": "<p>ghost</p>",
        "fields": {},
    }
    docs = _write_source(tmp_path, payload)

    with pytest.raises(ValueError, match="Ghost.xml"):
        load_public_metadata(docs)


def test_loader_rejects_nonempty_xml_filename_identity_mismatch(tmp_path: Path):
    docs = _write_source(tmp_path, _payload())
    (docs / "One.xml").write_text(ONE_XML.replace('filename="One"', 'filename="Other"'), encoding="utf-8")

    with pytest.raises(ValueError, match="One.xml"):
        load_public_metadata(docs)


def test_document_metadata_nodes_and_api_preserve_exact_values_after_tf_reload(tmp_path: Path):
    payload = _payload()
    docs = _write_source(tmp_path, payload)
    _, warnings, metadata, data = _build_with_metadata(docs)
    assert any("Empty.xml" in warning for warning in warnings)

    metadata_nodes = [node for node, kind in data.node_features["otype"].items() if kind == "document_metadata"]
    assert len(metadata_nodes) == 2

    one_node = next(node for node in metadata_nodes if data.node_features["ocp_book"].get(node) == "One")
    empty_node = next(node for node in metadata_nodes if data.node_features["ocp_book"].get(node) == "Empty")
    assert one_node != empty_node
    assert data.node_features["intro_introduction_json"][one_node] == json.dumps(
        payload["documents"]["One.xml"]["fields"]["introduction"], ensure_ascii=False
    )
    assert json.loads(data.node_features["intro_provenance_json"][one_node]) == ""
    assert json.loads(data.node_features["intro_themes_json"][one_node]) is None
    assert empty_node in data.edge_features["oslots"]
    assert data.metadata[""]["introsSha256"] == metadata.source_sha256

    out = tmp_path / "tf"
    assert write_tf(data, out)
    fabric = Fabric(locations=[str(out)], modules=[""], silent="deep")
    api = fabric.load(" ".join(WorkMetadata.REQUIRED_FEATURES), silent="deep")
    assert api is not False and not isinstance(api, bool)

    works = WorkMetadata(api)
    one = works.get("One")
    assert one == payload["documents"]["One.xml"]
    assert one["fields"]["introduction"].encode("utf-8") == payload["documents"]["One.xml"]["fields"]["introduction"].encode("utf-8")
    assert works.get("Empty") == payload["documents"]["Empty.xml"]


def test_graph_has_no_metadata_blob_duplication_across_textual_nodes(tmp_path: Path):
    docs = _write_source(tmp_path, _payload())
    _, _, _, data = _build_with_metadata(docs)

    encoded_features = [name for name in data.node_features if name.startswith("intro_") and name.endswith("_json")]
    assert encoded_features
    for feature in encoded_features:
        owners = set(data.node_features[feature])
        assert all(data.node_features["otype"][node] == "document_metadata" for node in owners)


def test_independent_raw_json_audit_detects_metadata_tampering(tmp_path: Path):
    docs = _write_source(tmp_path, _payload())
    books, _, _, data = _build_with_metadata(docs)

    report = augment_conversion_report_with_public_metadata(
        build_conversion_report(docs, books, data), docs, data
    )
    assert report["status"] == "ok"
    assert report["semantic_checks"]["public_metadata_values"] is True
    assert report["source"]["public_metadata_documents"] == 2
    assert report["graph"]["document_metadata"] == 2

    one_node = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "document_metadata" and data.node_features["ocp_book"].get(node) == "One"
    )
    data.node_features["intro_introduction_json"][one_node] = json.dumps("tampered")
    bad = augment_conversion_report_with_public_metadata(
        build_conversion_report(docs, books, data), docs, data
    )
    assert bad["status"] == "failed"
    assert "public_metadata_values" in bad["failed_checks"]
