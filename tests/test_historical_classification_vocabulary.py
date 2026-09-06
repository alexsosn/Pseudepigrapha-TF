from __future__ import annotations

import json
from pathlib import Path

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


XML = '''<book filename="One" title="One">
  <version title="Greek" author="Anonymous" language="Greek">
    <divisions><division label="Paragraph" delimiter="."/></divisions>
    <manuscripts><ms abbrev="A" language="Greek" show="yes"><name>A</name></ms></manuscripts>
    <text><div number="1"><unit id="1"><reading option="0" mss="A ">abc</reading></unit></div></text>
  </version>
</book>
'''


def test_unused_controlled_vocabulary_is_preserved_and_audited_after_tf_reload(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "One.xml").write_text(XML, encoding="utf-8")
    (docs / "intros.json").write_text(
        json.dumps(
            {
                "_meta": {"exported": "2026-09-05"},
                "documents": {
                    "One.xml": {
                        "title": "One",
                        "version": 1.0,
                        "citation": "One",
                        "fields": {},
                    }
                },
            }
        ) + "\n",
        encoding="utf-8",
    )
    fixture = tmp_path / "classifications.json"
    fixture.write_text(
        json.dumps(
            {
                "source": {
                    "repository": "OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha",
                    "historical_commit": "deadbeef",
                    "historical_commit_date": "2017-10-30T20:32:12-04:00",
                    "storage_sqlite_git_blob": "0123456789abcdef0123456789abcdef01234567",
                    "storage_sqlite_sha256": "a" * 64,
                    "status": "historical OCP catalogue snapshot (2017)",
                },
                "genres": [
                    {"id": 1, "label": "assigned genre"},
                    {"id": 2, "label": "unused genre"},
                ],
                "biblical_figures": [
                    {"id": 1, "label": "Assigned Figure"},
                    {"id": 2, "label": "Unused Figure"},
                ],
                "documents": [
                    {
                        "historical_doc_id": 1,
                        "work_id": "One",
                        "genre_ids": [1],
                        "biblical_figure_ids": [1],
                    }
                ],
            }
        ) + "\n",
        encoding="utf-8",
    )

    books, _ = load_source_directory(docs)
    data = build_tf_data(books)
    attach_public_metadata(data, load_public_metadata(docs))
    attach_historical_classifications(data, load_historical_classifications(fixture))

    report = augment_conversion_report_with_historical_classifications(
        build_conversion_report(docs, books, data), data, fixture
    )
    assert report["status"] == "ok", report["failed_checks"]
    assert report["graph"]["historical_genre_labels"] == 2
    assert report["graph"]["historical_biblical_figure_labels"] == 2

    out = tmp_path / "tf"
    assert write_tf(data, out)
    api = Fabric(locations=[str(out)], modules=[""], silent="deep").load(
        " ".join(HistoricalClassifications.REQUIRED_FEATURES), silent="deep"
    )
    assert api is not False and not isinstance(api, bool)
    classifications = HistoricalClassifications(api)
    assert classifications.genres() == ("assigned genre", "unused genre")
    assert classifications.figures() == ("Assigned Figure", "Unused Figure")
    assert classifications.works_by_genre("unused genre") == ()
    assert classifications.works_by_figure("Unused Figure") == ()
