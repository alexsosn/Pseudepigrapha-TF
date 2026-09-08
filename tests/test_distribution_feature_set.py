from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest


UPSTREAM_REPOSITORY = (
    "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
)
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
RELEASE_COMMIT = "a" * 40
FEATURES = {
    "book.tf": b"@node\n1\t1En__Ethiopic\n",
    "otype.tf": b"@node\n1\tword\n",
}


def _distribution():
    return importlib.import_module("pseudepigrapha_tf.distribution")


def _report_path(tmp_path: Path) -> Path:
    report_path = tmp_path / "conversion-report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "provenance": {
                    "upstream_repository": UPSTREAM_REPOSITORY,
                    "upstream_commit": UPSTREAM_COMMIT,
                    "converter_version": "0.1.0",
                    "source_identity_status": "verified",
                    "content_license_status": "verified",
                    "content_license": "CC-BY-4.0",
                    "converter_software_license": "MIT",
                    "upstream_software_license": "GPL-3.0",
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return report_path


def _archive(path: Path, *, comment: bytes = b"", reverse: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(FEATURES.items(), reverse=reverse)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as zf:
        zf.comment = comment
        for name, payload in items:
            zf.writestr(name, payload)
    return path


def _manifest(tmp_path: Path):
    distribution = _distribution()
    archive = _archive(tmp_path / "tf-0.1.zip")
    report_path = _report_path(tmp_path)
    manifest = distribution.build_distribution_manifest(
        archive,
        report_path,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
    )
    return distribution, archive, report_path, manifest


def _expected_feature_records():
    return [
        {
            "name": name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for name, payload in sorted(FEATURES.items())
    ]


def _feature_set_digest(records):
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_manifest_binds_extracted_tf_feature_bytes_independently_of_zip_container(tmp_path):
    _, _, _, manifest = _manifest(tmp_path)
    expected = _expected_feature_records()

    assert manifest["text_fabric"]["features"] == expected
    assert manifest["text_fabric"]["feature_set_sha256"] == _feature_set_digest(expected)


def test_feature_identity_is_stable_when_zip_container_metadata_changes(tmp_path):
    distribution, archive, report_path, first = _manifest(tmp_path)

    repacked = _archive(
        tmp_path / "repacked" / "tf-0.1.zip",
        comment=b"different container metadata",
        reverse=True,
    )
    second = distribution.build_distribution_manifest(
        repacked,
        report_path,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
    )

    assert first["assets"]["tf"]["sha256"] != second["assets"]["tf"]["sha256"]
    assert first["text_fabric"]["features"] == second["text_fabric"]["features"]
    assert first["text_fabric"]["feature_set_sha256"] == second["text_fabric"]["feature_set_sha256"]


def test_validator_rejects_manifest_feature_record_tampering(tmp_path):
    distribution, archive, report_path, manifest = _manifest(tmp_path)
    manifest = json.loads(json.dumps(manifest))
    manifest["text_fabric"]["features"][0]["sha256"] = "0" * 64

    with pytest.raises(distribution.DistributionContractError, match="feature"):
        distribution.validate_distribution(manifest, archive, report_path)


def test_builder_rejects_non_feature_entry_in_native_tf_archive(tmp_path):
    distribution = _distribution()
    report_path = _report_path(tmp_path)
    bad = tmp_path / "bad" / "tf-0.1.zip"
    bad.parent.mkdir()
    with ZipFile(bad, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("otype.tf", FEATURES["otype.tf"])
        zf.writestr("conversion-report.json", b"must remain separate")

    with pytest.raises(distribution.DistributionContractError, match="feature"):
        distribution.build_distribution_manifest(
            bad,
            report_path,
            release_tag="v0.1.1-test",
            release_commit=RELEASE_COMMIT,
            converter_version="0.1.0",
            data_version="0.1",
        )
