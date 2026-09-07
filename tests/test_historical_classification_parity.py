from __future__ import annotations

import json
from pathlib import Path

from pseudepigrapha_tf.classifications import load_historical_classifications


def test_packaged_fixture_matches_every_public_sqlite_extraction_assignment():
    root = Path(__file__).resolve().parents[1]
    raw = json.loads(
        (root / "research/issue-75/public-source-extract.json").read_text(encoding="utf-8")
    )
    actual = load_historical_classifications()

    assert actual.source["historical_commit"] == raw["source"]["historical_commit"]
    assert actual.source["historical_commit_date"] == raw["source"]["historical_commit_date"]
    assert actual.source["storage_sqlite_git_blob"] == raw["source"]["storage_sqlite_git_blob"]
    assert actual.source["storage_sqlite_sha256"] == raw["source"]["storage_sqlite_sha256"]

    assert actual.genres == {row["id"]: row["genre"] for row in raw["genres"]}
    assert actual.biblical_figures == {
        row["id"]: row["figure"] for row in raw["biblical_figures"]
    }

    expected_work_ids = {row["filename"] for row in raw["docs"]}
    assert set(actual.documents) == expected_work_ids
    for row in raw["docs"]:
        document = actual.documents[row["filename"]]
        assert document.historical_doc_id == row["doc_id"]
        assert document.genre_ids == tuple(item["id"] for item in row["genres"])
        assert document.biblical_figure_ids == tuple(
            item["id"] for item in row["biblical_figures"]
        )


def test_runtime_fixture_contains_no_private_or_unrelated_database_fields():
    root = Path(__file__).resolve().parents[1]
    payload = json.loads(
        (root / "src/pseudepigrapha_tf/data/ocp_classifications_2017.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(payload) == {"source", "genres", "biblical_figures", "documents"}
    assert set(payload["source"]) == {
        "repository",
        "historical_commit",
        "historical_commit_date",
        "storage_sqlite_git_blob",
        "storage_sqlite_sha256",
        "status",
    }
    assert all(set(row) == {"id", "label"} for row in payload["genres"])
    assert all(set(row) == {"id", "label"} for row in payload["biblical_figures"])
    assert all(
        set(row)
        == {"historical_doc_id", "work_id", "genre_ids", "biblical_figure_ids"}
        for row in payload["documents"]
    )
