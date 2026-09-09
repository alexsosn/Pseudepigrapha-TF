from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    feature_directory_identity,
    stage_distribution_assets,
    validate_distribution,
)
from distribution_support import (
    canonical_otype_payload,
    canonical_report_provenance,
)

RELEASE_COMMIT = "b" * 40


def _materialized(tmp_path: Path, *, status: str = "ok") -> Path:
    source = tmp_path / "tf" / "0.1"
    source.mkdir(parents=True)
    (source / "otype.tf").write_bytes(canonical_otype_payload())
    (source / "book.tf").write_bytes(b"@node\n@valueType=str\n2\t1En__Ethiopic\n")
    (source / "oslots.tf").write_bytes(b"@edge\n2\t1\n")
    (source / "conversion-report.json").write_text(
        json.dumps(
            {
                "status": status,
                "failed_checks": [] if status == "ok" else ["probe"],
                "semantic_checks": {"probe": status == "ok"},
                "text_fabric": feature_directory_identity(source),
                "provenance": canonical_report_provenance(),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return source


def test_staging_builds_exact_native_archive_report_and_manifest_set(tmp_path):
    source = _materialized(tmp_path)
    destination = tmp_path / "release-assets"
    original_report = (source / "conversion-report.json").read_bytes()

    assets = stage_distribution_assets(
        source,
        destination,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
    )

    assert set(path.name for path in destination.iterdir()) == {
        "tf-0.1.zip",
        "conversion-report.json",
        "dataset-manifest.json",
    }
    assert assets == {
        "tf": destination / "tf-0.1.zip",
        "report": destination / "conversion-report.json",
        "manifest": destination / "dataset-manifest.json",
    }
    assert assets["report"].read_bytes() == original_report

    with ZipFile(assets["tf"]) as zf:
        assert zf.namelist() == ["book.tf", "oslots.tf", "otype.tf"]
        assert "conversion-report.json" not in zf.namelist()
        for name in zf.namelist():
            assert zf.read(name) == (source / name).read_bytes()

    manifest = json.loads(assets["manifest"].read_text(encoding="utf-8"))
    assert validate_distribution(
        manifest,
        assets["tf"],
        assets["report"],
        expected_release_tag="v0.1.1-test",
        expected_release_commit=RELEASE_COMMIT,
        expected_converter_version="0.1.0",
        expected_data_version="0.1",
    ) is None


def test_staging_fails_closed_without_report_and_leaves_no_partial_destination(tmp_path):
    source = _materialized(tmp_path)
    (source / "conversion-report.json").unlink()
    destination = tmp_path / "release-assets"

    with pytest.raises(DistributionContractError, match="report"):
        stage_distribution_assets(
            source,
            destination,
            release_tag="v0.1.1-test",
            release_commit=RELEASE_COMMIT,
            converter_version="0.1.0",
            data_version="0.1",
        )

    assert not destination.exists()


def test_staging_fails_closed_on_failed_report_and_leaves_no_partial_destination(tmp_path):
    source = _materialized(tmp_path, status="failed")
    destination = tmp_path / "release-assets"

    with pytest.raises(DistributionContractError, match="status"):
        stage_distribution_assets(
            source,
            destination,
            release_tag="v0.1.1-test",
            release_commit=RELEASE_COMMIT,
            converter_version="0.1.0",
            data_version="0.1",
        )

    assert not destination.exists()


def test_staging_refuses_to_mix_with_existing_release_directory(tmp_path):
    source = _materialized(tmp_path)
    destination = tmp_path / "release-assets"
    destination.mkdir()
    sentinel = destination / "old.txt"
    sentinel.write_text("old generation\n", encoding="utf-8")

    with pytest.raises(DistributionContractError, match="destination"):
        stage_distribution_assets(
            source,
            destination,
            release_tag="v0.1.1-test",
            release_commit=RELEASE_COMMIT,
            converter_version="0.1.0",
            data_version="0.1",
        )

    assert sentinel.read_text(encoding="utf-8") == "old generation\n"
    assert set(destination.iterdir()) == {sentinel}
