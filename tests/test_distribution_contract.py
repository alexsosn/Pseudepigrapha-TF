from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest


UPSTREAM_REPOSITORY = (
    "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
)
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
RELEASE_COMMIT = "a" * 40


def _distribution():
    return importlib.import_module("pseudepigrapha_tf.distribution")


def _report(*, status: str = "ok", source_identity: str = "verified", license_status: str = "verified"):
    return {
        "status": status,
        "provenance": {
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": UPSTREAM_COMMIT,
            "source_identity_status": source_identity,
            "content_license_status": license_status,
            "content_license": "CC-BY-4.0",
            "converter_software_license": "MIT",
            "upstream_software_license": "GPL-3.0",
        },
    }


def _files(tmp_path: Path, *, report: dict | None = None):
    archive = tmp_path / "tf-0.1.zip"
    archive.write_bytes(b"canonical tf express archive\n")
    report_path = tmp_path / "conversion-report.json"
    report_path.write_text(
        json.dumps(report or _report(), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return archive, report_path


def _build(tmp_path: Path, *, report: dict | None = None):
    distribution = _distribution()
    archive, report_path = _files(tmp_path, report=report)
    manifest = distribution.build_dataset_manifest(
        archive,
        report_path,
        release_tag="v0.1.0",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        tf_data_version="0.1",
    )
    return distribution, archive, report_path, manifest


def test_manifest_is_deterministic_and_binds_exact_assets_and_provenance(tmp_path):
    distribution, archive, report_path, manifest = _build(tmp_path)
    again = distribution.build_dataset_manifest(
        archive,
        report_path,
        release_tag="v0.1.0",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        tf_data_version="0.1",
    )

    assert manifest == again
    assert manifest["schema_version"] == 1
    assert manifest["release"] == {"tag": "v0.1.0", "commit": RELEASE_COMMIT}
    assert manifest["converter"] == {"version": "0.1.0"}
    assert manifest["text_fabric"] == {"data_version": "0.1"}
    assert manifest["upstream"] == {
        "repository": UPSTREAM_REPOSITORY,
        "commit": UPSTREAM_COMMIT,
    }
    assert manifest["audit"] == {"status": "ok"}
    assert manifest["provenance"] == {
        "source_identity_status": "verified",
        "content_license_status": "verified",
        "content_license": "CC-BY-4.0",
        "converter_software_license": "MIT",
        "upstream_software_license": "GPL-3.0",
    }

    archive_asset = manifest["assets"]["tf"]
    assert archive_asset["name"] == "tf-0.1.zip"
    assert archive_asset["bytes"] == archive.stat().st_size
    assert archive_asset["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()

    report_asset = manifest["assets"]["report"]
    assert report_asset["name"] == "conversion-report.json"
    assert report_asset["bytes"] == report_path.stat().st_size
    assert report_asset["sha256"] == hashlib.sha256(report_path.read_bytes()).hexdigest()


def test_intact_manifest_validates_against_expected_release_identity(tmp_path):
    distribution, archive, report_path, manifest = _build(tmp_path)

    distribution.validate_dataset_manifest(
        manifest,
        archive,
        report_path,
        expected_release_tag="v0.1.0",
        expected_release_commit=RELEASE_COMMIT,
        expected_converter_version="0.1.0",
        expected_tf_data_version="0.1",
    )


@pytest.mark.parametrize("target", ["archive", "report"])
def test_validator_rejects_asset_mutation(tmp_path, target):
    distribution, archive, report_path, manifest = _build(tmp_path)
    if target == "archive":
        archive.write_bytes(archive.read_bytes() + b"tampered")
    else:
        report_path.write_bytes(report_path.read_bytes() + b" ")

    with pytest.raises(distribution.DistributionContractError, match=target if target == "archive" else "report"):
        distribution.validate_dataset_manifest(manifest, archive, report_path)


def test_builder_rejects_non_ok_or_unverified_conversion_report(tmp_path):
    distribution = _distribution()

    for report, expected in (
        (_report(status="failed"), "status"),
        (_report(source_identity="unverified"), "source identity"),
        (_report(license_status="unverified"), "license"),
    ):
        case = tmp_path / expected.replace(" ", "-")
        case.mkdir()
        archive, report_path = _files(case, report=report)
        with pytest.raises(distribution.DistributionContractError, match=expected):
            distribution.build_dataset_manifest(
                archive,
                report_path,
                release_tag="v0.1.0",
                release_commit=RELEASE_COMMIT,
                converter_version="0.1.0",
                tf_data_version="0.1",
            )


def test_validator_rejects_wrong_publication_identity(tmp_path):
    distribution, archive, report_path, manifest = _build(tmp_path)

    expectations = (
        ({"expected_release_tag": "v9.9.9"}, "release tag"),
        ({"expected_release_commit": "b" * 40}, "release commit"),
        ({"expected_converter_version": "9.9.9"}, "converter version"),
        ({"expected_tf_data_version": "9.9"}, "TF data version"),
    )
    for kwargs, expected in expectations:
        with pytest.raises(distribution.DistributionContractError, match=expected):
            distribution.validate_dataset_manifest(
                manifest,
                archive,
                report_path,
                **kwargs,
            )


def test_validator_rejects_manifest_upstream_that_disagrees_with_report(tmp_path):
    distribution, archive, report_path, manifest = _build(tmp_path)
    manifest = json.loads(json.dumps(manifest))
    manifest["upstream"]["commit"] = "0" * 40

    with pytest.raises(distribution.DistributionContractError, match="upstream commit"):
        distribution.validate_dataset_manifest(manifest, archive, report_path)


def test_builder_requires_native_tf_asset_name_for_data_version(tmp_path):
    distribution = _distribution()
    archive, report_path = _files(tmp_path)
    wrong = archive.with_name("dataset.zip")
    archive.rename(wrong)

    with pytest.raises(distribution.DistributionContractError, match="tf-0.1.zip"):
        distribution.build_dataset_manifest(
            wrong,
            report_path,
            release_tag="v0.1.0",
            release_commit=RELEASE_COMMIT,
            converter_version="0.1.0",
            tf_data_version="0.1",
        )
