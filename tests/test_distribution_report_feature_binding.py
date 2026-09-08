from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf.distribution import DistributionContractError, build_distribution_manifest


UPSTREAM_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
RELEASE_COMMIT = "d" * 40


def _feature_identity(features: dict[str, bytes]) -> dict:
    records = [
        {
            "name": name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for name, payload in sorted(features.items())
    ]
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "feature_count": len(records),
        "features": records,
        "feature_set_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def _report(*, feature_identity: dict | None) -> dict:
    report = {
        "status": "ok",
        "failed_checks": [],
        "semantic_checks": {"probe": True},
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
    }
    if feature_identity is not None:
        report["text_fabric"] = feature_identity
    return report


def _write_assets(tmp_path: Path, features: dict[str, bytes], report: dict) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    archive = tmp_path / "tf-0.1.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        for name, payload in features.items():
            zf.writestr(name, payload)
    report_path = tmp_path / "conversion-report.json"
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    return archive, report_path


def _build(archive: Path, report: Path):
    return build_distribution_manifest(
        archive,
        report,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
    )


def test_builder_requires_conversion_report_to_identify_serialized_tf_generation(tmp_path):
    features = {
        "otype.tf": b"@node\n1\tword\n",
        "oslots.tf": b"@edge\n2\t1\n",
    }
    archive, report = _write_assets(tmp_path, features, _report(feature_identity=None))

    with pytest.raises(DistributionContractError, match="report.*Text-Fabric|report.*feature"):
        _build(archive, report)


def test_builder_rejects_ok_report_from_different_tf_generation(tmp_path):
    audited = {
        "otype.tf": b"@node\n1\tword\n",
        "oslots.tf": b"@edge\n2\t1\n",
    }
    published = {
        **audited,
        "otype.tf": b"@node\n1\tword\n2\tbook\n",
    }
    archive, report = _write_assets(
        tmp_path,
        published,
        _report(feature_identity=_feature_identity(audited)),
    )

    with pytest.raises(DistributionContractError, match="report.*feature|serialized.*feature"):
        _build(archive, report)
