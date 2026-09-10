from __future__ import annotations

from pathlib import Path

import pytest

import pseudepigrapha_tf.cli as cli
from pseudepigrapha_tf.classifications import (
    HistoricalClassificationCorpus,
    HistoricalClassificationDocument,
    attach_historical_classifications,
)
from pseudepigrapha_tf.graph import TFData, build_tf_data
from pseudepigrapha_tf.metadata import (
    PublicMetadataCorpus,
    PublicMetadataDocument,
    attach_public_metadata,
)
from pseudepigrapha_tf.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def _public_metadata() -> PublicMetadataCorpus:
    document = PublicMetadataDocument(
        filename="Sample.xml",
        title="Sample Work",
        version="1",
        citation=None,
        citation_present=False,
        fields={},
    )
    return PublicMetadataCorpus(
        documents={"Sample.xml": document},
        source_sha256="intro-sha",
        source_meta={},
    )


def _classifications() -> HistoricalClassificationCorpus:
    source = {
        "repository": "https://example.test/ocp",
        "historical_commit": "deadbeef",
        "historical_commit_date": "2017-01-01",
        "storage_sqlite_git_blob": "blob",
        "storage_sqlite_sha256": "db-sha",
        "status": "historical",
    }
    return HistoricalClassificationCorpus(
        source=source,
        genres={1: "Test genre"},
        biblical_figures={1: "Test figure"},
        documents={
            "Sample": HistoricalClassificationDocument(
                historical_doc_id=1,
                work_id="Sample",
                genre_ids=(1,),
                biblical_figure_ids=(1,),
            )
        },
        source_sha256="fixture-sha",
        source_file="classifications.json",
    )


def test_cli_batches_scholarly_enrichments_into_one_post_build_validation(monkeypatch, tmp_path) -> None:
    book = parse_file(FIXTURES / "sample.xml")
    data = build_tf_data([book])
    metadata = _public_metadata()
    classifications = _classifications()

    calls = 0
    original_validate = TFData.validate

    def counted_validate(self):
        nonlocal calls
        calls += 1
        return original_validate(self)

    monkeypatch.setattr(TFData, "validate", counted_validate)
    monkeypatch.setattr(cli, "load_source_directory", lambda source: ([book], []))
    monkeypatch.setattr(cli, "load_public_metadata", lambda source: metadata)
    monkeypatch.setattr(cli, "load_historical_classifications", lambda: classifications)
    monkeypatch.setattr(cli, "build_tf_data", lambda *args, **kwargs: data)
    monkeypatch.setattr(cli, "detect_git_commit", lambda source: "")
    monkeypatch.setattr(cli, "attest_corpus_license_source_identity", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "build_conversion_report", lambda *args, **kwargs: {"status": "ok", "failed_checks": []})
    monkeypatch.setattr(cli, "augment_conversion_report_with_public_metadata", lambda report, *args: report)
    monkeypatch.setattr(cli, "augment_conversion_report_with_historical_classifications", lambda report, *args: report)
    monkeypatch.setattr(cli, "_write_prevalidated_tf", lambda *args, **kwargs: True)
    monkeypatch.setattr(cli, "feature_directory_identity", lambda *args, **kwargs: {"features": []})

    source = tmp_path / "source"
    source.mkdir()
    (source / "intros.json").write_text("{}", encoding="utf-8")

    assert cli.main(["convert", str(source), "--output", str(tmp_path / "tf")]) == 0
    assert calls == 1
    assert data.node_features["historical_genres_json"]
    assert data.node_features["historical_biblical_figures_json"]


def test_public_metadata_standalone_attachment_still_validates(monkeypatch) -> None:
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    calls = 0

    def invalid(self):
        nonlocal calls
        calls += 1
        return ["sentinel invalid graph"]

    monkeypatch.setattr(TFData, "validate", invalid)
    with pytest.raises(ValueError, match="after public metadata attachment: sentinel invalid graph"):
        attach_public_metadata(data, _public_metadata())
    assert calls == 1


def test_historical_classification_standalone_attachment_still_validates(monkeypatch) -> None:
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    attach_public_metadata(data, _public_metadata())
    calls = 0

    def invalid(self):
        nonlocal calls
        calls += 1
        return ["sentinel invalid graph"]

    monkeypatch.setattr(TFData, "validate", invalid)
    with pytest.raises(ValueError, match="after historical classification attachment: sentinel invalid graph"):
        attach_historical_classifications(data, _classifications())
    assert calls == 1
