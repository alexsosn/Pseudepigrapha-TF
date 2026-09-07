from __future__ import annotations

import json
from pathlib import Path

import pytest
from tf.fabric import Fabric

from pseudepigrapha_tf.classifications import (
    HistoricalClassifications,
    attach_historical_classifications,
    augment_conversion_report_with_historical_classifications,
    load_historical_classifications,
)
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.metadata import attach_public_metadata, load_public_metadata
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.writer import write_tf


ONE_XML = '''<book filename="One" title="One">
  <version title="Greek" author="Anonymous" language="Greek">
    <divisions><division label="Paragraph" delimiter="."/></divisions>
    <manuscripts><ms abbrev="A" language="Greek" show="yes"><name>A</name></ms></manuscripts>
    <text><div number="1"><unit id="1"><reading option="0" mss="A ">abc</reading></unit></div></text>
  </version>
</book>
'''

TWO_XML = ONE_XML.replace('filename="One" title="One"', 'filename="Two" title="Two"')


def _write_docs(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "One.xml").write_text(ONE_XML, encoding="utf-8")
    (docs / "Two.xml").write_text(TWO_XML, encoding="utf-8")
    intros = {
        "_meta": {"exported": "2026-09-05"},
        "documents": {
            "One.xml": {"title": "One", "version": 1.0, "citation": "One", "fields": {}},
            "Two.xml": {"title": "Two", "version": 1.0, "citation": "Two", "fields": {}},
        },
    }
    (docs / "intros.json").write_text(
        json.dumps(intros, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return docs


def _fixture_payload() -> dict:
    return {
        "source": {
            "repository": "OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha",
            "historical_commit": "deadbeef",
            "historical_commit_date": "2017-10-30T20:32:12-04:00",
            "storage_sqlite_git_blob": "0123456789abcdef0123456789abcdef01234567",
            "storage_sqlite_sha256": "a" * 64,
            "status": "historical OCP catalogue snapshot (2017)",
        },
        "genres": [
            {"id": 3, "label": "testaments"},
            {"id": 4, "label": "parabiblical works (re-written Bible)"},
        ],
        "biblical_figures": [
            {"id": 6, "label": "Moses"},
            {"id": 9, "label": "Job"},
        ],
        "documents": [
            {
                "historical_doc_id": 1,
                "work_id": "One",
                "genre_ids": [3, 4],
                "biblical_figure_ids": [9],
            },
            {
                "historical_doc_id": 2,
                "work_id": "Two",
                "genre_ids": [3],
                "biblical_figure_ids": [6],
            },
        ],
    }


def _write_fixture(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "classifications.json"
    path.write_text(
        json.dumps(payload or _fixture_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _build(tmp_path: Path, payload: dict | None = None):
    docs = _write_docs(tmp_path)
    books, _ = load_source_directory(docs)
    data = build_tf_data(books)
    attach_public_metadata(data, load_public_metadata(docs))
    fixture = _write_fixture(tmp_path, payload)
    classifications = load_historical_classifications(fixture)
    attach_historical_classifications(data, classifications)
    return docs, books, fixture, classifications, data


def test_default_public_fixture_inventory_is_complete_and_exact():
    classifications = load_historical_classifications()
    assert len(classifications.documents) == 32
    assert len(classifications.genres) == 11
    assert len(classifications.biblical_figures) == 17
    assert sum(len(doc.genre_ids) for doc in classifications.documents.values()) == 39
    assert sum(len(doc.biblical_figure_ids) for doc in classifications.documents.values()) == 25

    mois = classifications.documents["Mois"]
    assert tuple(classifications.genres[i] for i in mois.genre_ids) == (
        "apocalypses and visionary texts",
        "parabiblical works (re-written Bible)",
        "testaments",
    )
    adameve = classifications.documents["AdamEve"]
    assert tuple(classifications.biblical_figures[i] for i in adameve.biblical_figure_ids) == (
        "Adam",
        "Eve",
    )


def test_loader_rejects_dangling_vocabulary_reference(tmp_path: Path):
    payload = _fixture_payload()
    payload["documents"][0]["genre_ids"] = [999]
    with pytest.raises(ValueError, match="genre.*999"):
        load_historical_classifications(_write_fixture(tmp_path, payload))


def test_loader_rejects_duplicate_work_and_vocabulary_identity(tmp_path: Path):
    payload = _fixture_payload()
    payload["documents"].append(dict(payload["documents"][0], historical_doc_id=3))
    with pytest.raises(ValueError, match="duplicate.*work.*One"):
        load_historical_classifications(_write_fixture(tmp_path, payload))

    payload = _fixture_payload()
    payload["genres"].append({"id": 77, "label": "testaments"})
    with pytest.raises(ValueError, match="duplicate.*genre.*label.*testaments"):
        load_historical_classifications(_write_fixture(tmp_path, payload))


def test_attachment_uses_existing_document_metadata_nodes_and_preserves_exact_labels(tmp_path: Path):
    _, _, _, _, data = _build(tmp_path)
    nodes = {
        data.node_features["ocp_book"].get(node): node
        for node, kind in data.node_features["otype"].items()
        if kind == "document_metadata"
    }
    one = nodes["One"]
    assert data.node_features["historical_ocp_doc_id"][one] == 1
    assert json.loads(data.node_features["historical_genres_json"][one]) == [
        "testaments",
        "parabiblical works (re-written Bible)",
    ]
    assert json.loads(data.node_features["historical_biblical_figures_json"][one]) == ["Job"]
    assert not any(kind in {"genre", "biblical_figure"} for kind in data.node_features["otype"].values())


def test_attachment_fails_loudly_when_source_work_has_no_unique_document_metadata_node(tmp_path: Path):
    docs = _write_docs(tmp_path)
    books, _ = load_source_directory(docs)
    data = build_tf_data(books)
    fixture = _write_fixture(tmp_path)
    classifications = load_historical_classifications(fixture)
    with pytest.raises(ValueError, match="document_metadata"):
        attach_historical_classifications(data, classifications)


def test_api_survives_real_tf_reload_and_supports_reverse_queries(tmp_path: Path):
    _, _, _, _, data = _build(tmp_path)
    out = tmp_path / "tf"
    assert write_tf(data, out)
    api = Fabric(locations=[str(out)], modules=[""], silent="deep").load(
        " ".join(HistoricalClassifications.REQUIRED_FEATURES), silent="deep"
    )
    assert api is not False and not isinstance(api, bool)

    C = HistoricalClassifications(api)
    assert C["One"] == {
        "historical_doc_id": 1,
        "genres": ("testaments", "parabiblical works (re-written Bible)"),
        "biblical_figures": ("Job",),
    }
    assert C.works_by_genre("testaments") == ("One", "Two")
    assert C.works_by_genre("parabiblical works (re-written Bible)") == ("One",)
    assert C.works_by_figure("Moses") == ("Two",)
    assert C.works_by_figure("unknown") == ()
    assert C.genres() == ("parabiblical works (re-written Bible)", "testaments")
    assert C.figures() == ("Job", "Moses")


def test_independent_audit_detects_assignment_and_provenance_tampering(tmp_path: Path):
    docs, books, fixture, _, data = _build(tmp_path)
    report = augment_conversion_report_with_historical_classifications(
        build_conversion_report(docs, books, data), data, fixture
    )
    assert report["status"] == "ok", report["failed_checks"]
    assert report["source"]["historical_classified_works"] == 2
    assert report["source"]["historical_genre_assignments"] == 3
    assert report["source"]["historical_biblical_figure_assignments"] == 2
    assert report["semantic_checks"]["historical_classification_values"] is True
    assert report["semantic_checks"]["historical_classification_provenance"] is True

    one = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "document_metadata" and data.node_features["ocp_book"].get(node) == "One"
    )
    data.node_features["historical_genres_json"][one] = json.dumps(["tampered"])
    bad = augment_conversion_report_with_historical_classifications(
        build_conversion_report(docs, books, data), data, fixture
    )
    assert bad["status"] == "failed"
    assert "historical_classification_values" in bad["failed_checks"]

    data.node_features["historical_genres_json"][one] = json.dumps(
        ["testaments", "parabiblical works (re-written Bible)"]
    )
    data.metadata[""]["historicalClassificationsCommit"] = "wrong"
    bad = augment_conversion_report_with_historical_classifications(
        build_conversion_report(docs, books, data), data, fixture
    )
    assert bad["status"] == "failed"
    assert "historical_classification_provenance" in bad["failed_checks"]


def test_research_extract_encodes_expected_historical_coverage_without_inference():
    root = Path(__file__).resolve().parents[1]
    raw = json.loads((root / "research/issue-75/public-source-extract.json").read_text(encoding="utf-8"))
    docs = {row["filename"]: row for row in raw["docs"]}
    assert len(docs) == 32
    assert sum(len(row["genres"]) for row in docs.values()) == 39
    assert sum(len(row["biblical_figures"]) for row in docs.values()) == 25
    assert [item["label"] for item in docs["TJob"]["genres"]] == ["testaments"]
    assert [item["label"] for item in docs["TJob"]["biblical_figures"]] == ["Job"]
    assert [item["label"] for item in docs["Mois"]["genres"]] == [
        "apocalypses and visionary texts",
        "parabiblical works (re-written Bible)",
        "testaments",
    ]

    newer_unclassified = {
        "2Bar-Syr", "Esdl", "Esdr", "JosAsen", "Jubi", "TAbA", "TAbB"
    }
    assert newer_unclassified.isdisjoint(docs)
