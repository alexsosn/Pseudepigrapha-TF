from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    build_distribution_manifest,
    canonical_manifest_bytes,
    validate_distribution,
)
from pseudepigrapha_tf.provenance import OCP_PIN, OCP_REPOSITORY
from test_support.distribution import (
    canonical_otype_payload,
    canonical_report_provenance,
)

UPSTREAM_REPOSITORY = OCP_REPOSITORY
UPSTREAM_COMMIT = OCP_PIN
RELEASE_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _report(*, status: str = "ok", source_status: str = "verified", license_status: str = "verified") -> dict:
    return {
        "status": status,
        "failed_checks": [] if status == "ok" else ["probe"],
        "semantic_checks": {"probe": status == "ok"},
        "provenance": canonical_report_provenance(
            overrides={
                "source_identity_status": source_status,
                "content_license_status": license_status,
            }
        ),
    }


def _archive_identity(archive: Path) -> dict:
    with ZipFile(archive) as zf:
        records = [
            {
                "name": name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name in sorted(zf.namelist())
            for payload in (zf.read(name),)
        ]
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "feature_count": len(records),
        "features": records,
        "feature_set_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def _assets(tmp_path: Path, *, report: dict | None = None) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    archive = tmp_path / "tf-0.1.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        # Deliberately write in non-lexical order: manifest feature identity must
        # normalize archive container ordering rather than inherit it.
        zf.writestr("otype.tf", canonical_otype_payload())
        zf.writestr("book.tf", "@node\n@valueType=str\n2\t1En__Ethiopic\n")
        zf.writestr("oslots.tf", "@edge\n2\t1\n")
    if report is None:
        report = _report()
        report["text_fabric"] = _archive_identity(archive)
    report_path = tmp_path / "conversion-report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return archive, report_path


def _manifest(tmp_path: Path, *, report: dict | None = None) -> tuple[dict, Path, Path]:
    archive, report_path = _assets(tmp_path, report=report)
    manifest = build_distribution_manifest(
        archive,
        report_path,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
    )
    return manifest, archive, report_path


def test_manifest_is_deterministic_report_derived_and_feature_set_bound(tmp_path):
    manifest, archive, report = _manifest(tmp_path)
    second = build_distribution_manifest(
        archive,
        report,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
    )

    assert manifest == second
    assert canonical_manifest_bytes(manifest) == canonical_manifest_bytes(second)
    assert canonical_manifest_bytes(manifest).endswith(b"\n")

    assert manifest["schema_version"] == 1
    assert manifest["release"] == {"tag": "v0.1.1-test", "commit": RELEASE_COMMIT}
    assert manifest["converter"] == {"version": "0.1.0"}
    assert manifest["text_fabric"]["data_version"] == "0.1"
    assert manifest["upstream"] == {
        "repository": UPSTREAM_REPOSITORY,
        "commit": UPSTREAM_COMMIT,
    }
    assert manifest["audit"]["status"] == "ok"
    assert manifest["provenance"]["source_identity_status"] == "verified"
    assert manifest["provenance"]["content_license_status"] == "verified"
    assert manifest["provenance"]["content_license"] == "CC-BY-4.0"

    tf_asset = manifest["assets"]["tf"]
    assert tf_asset["name"] == "tf-0.1.zip"
    assert tf_asset["bytes"] == archive.stat().st_size
    assert len(tf_asset["sha256"]) == 64

    report_asset = manifest["assets"]["report"]
    assert report_asset["name"] == "conversion-report.json"
    assert report_asset["bytes"] == report.stat().st_size
    assert len(report_asset["sha256"]) == 64

    features = manifest["text_fabric"]["features"]
    assert [item["name"] for item in features] == ["book.tf", "oslots.tf", "otype.tf"]
    assert all(len(item["sha256"]) == 64 and item["bytes"] > 0 for item in features)
    assert manifest["text_fabric"]["feature_count"] == 3
    assert len(manifest["text_fabric"]["feature_set_sha256"]) == 64

    assert validate_distribution(manifest, archive, report) is None


def test_validation_rejects_mutated_archive_and_report(tmp_path):
    manifest, archive, report = _manifest(tmp_path)

    archive.write_bytes(archive.read_bytes() + b"x")
    with pytest.raises(DistributionContractError, match="archive.*sha256|TF archive.*sha256"):
        validate_distribution(manifest, archive, report)

    manifest, archive, report = _manifest(tmp_path / "second")
    report.write_bytes(report.read_bytes() + b" ")
    with pytest.raises(DistributionContractError, match="report.*sha256"):
        validate_distribution(manifest, archive, report)


def test_validation_rejects_identity_and_filename_mismatches(tmp_path):
    manifest, archive, report = _manifest(tmp_path)

    wrong = deepcopy(manifest)
    wrong["upstream"]["commit"] = "f" * 40
    with pytest.raises(DistributionContractError, match="upstream.*commit"):
        validate_distribution(wrong, archive, report)

    with pytest.raises(DistributionContractError, match="release.*tag"):
        validate_distribution(
            manifest,
            archive,
            report,
            expected_release_tag="v9.9.9",
        )

    with pytest.raises(DistributionContractError, match="release.*commit"):
        validate_distribution(
            manifest,
            archive,
            report,
            expected_release_commit="e" * 40,
        )

    with pytest.raises(DistributionContractError, match="data version"):
        validate_distribution(
            manifest,
            archive,
            report,
            expected_data_version="9.9",
        )

    renamed = archive.with_name("wrong-name.zip")
    archive.replace(renamed)
    with pytest.raises(DistributionContractError, match="filename|name"):
        validate_distribution(manifest, renamed, report)


def test_builder_and_validator_fail_closed_on_bad_report_provenance(tmp_path):
    for bad_report, match in (
        (_report(status="failed"), "status"),
        (_report(source_status="unverified"), "source.*identity"),
        (_report(license_status="unverified"), "license"),
    ):
        archive, report = _assets(tmp_path / match.replace(".*", "_"), report=bad_report)
        with pytest.raises(DistributionContractError, match=match):
            build_distribution_manifest(
                archive,
                report,
                release_tag="v0.1.1-test",
                release_commit=RELEASE_COMMIT,
                converter_version="0.1.0",
                data_version="0.1",
            )


def test_builder_rejects_internally_inconsistent_success_report(tmp_path):
    bad_reports = []

    failed_checks = _report()
    failed_checks["failed_checks"] = ["source_hashes"]
    bad_reports.append((failed_checks, "failed_checks"))

    false_check = _report()
    false_check["semantic_checks"]["source_hashes"] = False
    bad_reports.append((false_check, "semantic_checks"))

    missing_checks = _report()
    missing_checks["semantic_checks"] = {}
    bad_reports.append((missing_checks, "semantic_checks"))

    wrong_failed_checks_type = _report()
    wrong_failed_checks_type["failed_checks"] = ""
    bad_reports.append((wrong_failed_checks_type, "failed_checks"))

    for index, (bad_report, match) in enumerate(bad_reports):
        archive, report = _assets(tmp_path / f"inconsistent-{index}", report=bad_report)
        with pytest.raises(DistributionContractError, match=match):
            build_distribution_manifest(
                archive,
                report,
                release_tag="v0.1.1-test",
                release_commit=RELEASE_COMMIT,
                converter_version="0.1.0",
                data_version="0.1",
            )


def test_builder_rejects_converter_version_disagreement_with_report(tmp_path):
    archive, report = _assets(tmp_path)

    with pytest.raises(DistributionContractError, match="converter.*version"):
        build_distribution_manifest(
            archive,
            report,
            release_tag="v0.1.1-test",
            release_commit=RELEASE_COMMIT,
            converter_version="9.9.9",
            data_version="0.1",
        )
