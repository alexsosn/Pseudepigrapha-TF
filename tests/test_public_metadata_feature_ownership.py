from __future__ import annotations

import json
from pathlib import Path

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.metadata import (
    attach_public_metadata,
    augment_conversion_report_with_public_metadata,
    load_public_metadata,
)
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


ONE_XML = '''<book filename="One" title="One-level work">
  <version title="Greek" author="Anonymous" language="Greek">
    <divisions><division label="Paragraph" delimiter="."/></divisions>
    <manuscripts><ms abbrev="A" language="Greek" show="yes"><name>A</name></ms></manuscripts>
    <text><div number="7"><unit id="1"><reading option="0" mss="A ">abc def</reading></unit></div></text>
  </version>
</book>
'''


def _build(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "One.xml").write_text(ONE_XML, encoding="utf-8")
    (docs / "intros.json").write_text(
        json.dumps(
            {
                "_meta": {"exported": "2026-09-05"},
                "documents": {
                    "One.xml": {
                        "title": "One",
                        "version": 1.0,
                        "citation": "<p>Cite One.</p>",
                        "fields": {"bibliography": "<p>Source bibliography.</p>"},
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    books, _ = load_source_directory(docs)
    data = build_tf_data(books)
    attach_public_metadata(data, load_public_metadata(docs))
    return docs, books, data


def _audit(docs: Path, books, data):
    return augment_conversion_report_with_public_metadata(
        build_conversion_report(docs, books, data), docs, data
    )


def _assert_orphan(report, *, node: int, node_type, feature: str, secret: str) -> None:
    assert report["status"] == "failed"
    assert report["semantic_checks"]["public_metadata_documents"] is True
    assert report["semantic_checks"]["public_metadata_values"] is False
    assert "public_metadata_values" in report["failed_checks"]
    diagnostics = report["diagnostics"]["public_metadata"]["orphan_feature_owners"]
    assert diagnostics == [
        {"node": node, "node_type": node_type, "feature": feature}
    ]
    assert secret not in json.dumps(diagnostics, ensure_ascii=False)


def test_audit_rejects_intro_body_feature_owned_by_book_node(tmp_path: Path):
    docs, books, data = _build(tmp_path)
    assert _audit(docs, books, data)["status"] == "ok"

    book_node = next(
        node for node, kind in data.node_features["otype"].items() if kind == "book"
    )
    secret = "ORPHAN-LONG-HTML-SECRET"
    data.node_features["intro_bibliography_json"][book_node] = json.dumps(
        f"<p>{secret}</p>"
    )

    _assert_orphan(
        _audit(docs, books, data),
        node=book_node,
        node_type="book",
        feature="intro_bibliography_json",
        secret=secret,
    )


def test_audit_rejects_intro_top_level_feature_owned_by_word_node(tmp_path: Path):
    docs, books, data = _build(tmp_path)
    word_node = next(
        node for node, kind in data.node_features["otype"].items() if kind == "word"
    )
    secret = "ORPHAN-TITLE-SECRET"
    data.node_features["intro_title_json"][word_node] = json.dumps(secret)

    _assert_orphan(
        _audit(docs, books, data),
        node=word_node,
        node_type="word",
        feature="intro_title_json",
        secret=secret,
    )


def test_audit_rejects_intro_feature_owned_by_node_without_otype(tmp_path: Path):
    docs, books, data = _build(tmp_path)
    orphan_node = data.max_node + 100
    secret = "ORPHAN-NO-OTYPE-SECRET"
    data.node_features["intro_citation_json"][orphan_node] = json.dumps(secret)

    _assert_orphan(
        _audit(docs, books, data),
        node=orphan_node,
        node_type=None,
        feature="intro_citation_json",
        secret=secret,
    )
