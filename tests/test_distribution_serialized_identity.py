from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    build_distribution_manifest,
    stage_distribution_assets,
)


UPSTREAM_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
OTHER_COMMIT = "f" * 40
RELEASE_COMMIT = "d" * 40


def _otype_payload(
    *,
    upstream_repository: str = UPSTREAM_REPOSITORY,
    upstream_commit: str = UPSTREAM_COMMIT,
    converter_version: str = "0.1.0",
    data_version: str = "0.1",
    source_identity_status: str = "verified",
    content_license_status: str = "verified",
    content_license: str = "CC-BY-4.0",
) -> bytes:
    metadata = {
        "contentLicense": content_license,
        "contentLicenseStatus": content_license_status,
        "converterSoftwareLicense": "MIT",
        "converterVersion": converter_version,
        "sourceIdentityStatus": source_identity_status,
        "upstreamCommit": upstream_commit,
        "upstreamRepository": upstream_repository,
        "upstreamSoftwareLicense": "GPL-3.0",
        "valueType": "str",
        "version": data_version,
    }
    header = ["@node", *(f"@{key}={value}" for key, value in sorted(metadata.items())), ""]
    return ("\n".join(header) + "\n1\tword\n").encode("utf-8")


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


def _report(
    feature_identity: dict,
    *,
    upstream_repository: str = UPSTREAM_REPOSITORY,
    upstream_commit: str = UPSTREAM_COMMIT,
    converter_version: str = "0.1.0",
    source_identity_status: str = "verified",
    content_license_status: str = "verified",
    content_license: str = "CC-BY-4.0",
) -> dict:
    return {
        "status": "ok",
        "failed_checks": [],
        "semantic_checks": {"probe": True},
        "text_fabric": feature_identity,
        "provenance": {
            "upstream_repository": upstream_repository,
            "upstream_commit": upstream_commit,
            "converter_version": converter_version,
            "source_identity_status": source_identity_status,
            "content_license_status": content_license_status,
            "content_license": content_license,
            "converter_software_license": "MIT",
            "upstream_software_license": "GPL-3.0",
        },
    }


def _assets(
    tmp_path: Path,
    *,
    otype: bytes | None = None,
    report_overrides: dict[str, str] | None = None,
    data_version: str = "0.1",
) -> tuple[Path, Path]:
    features = {
        "otype.tf": otype or _otype_payload(),
        "oslots.tf": b"@edge\n@valueType=str\n\n2\t1\n",
    }
    archive = tmp_path / f"tf-{data_version}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        for name, payload in sorted(features.items()):
            zf.writestr(name, payload)

    overrides = report_overrides or {}
    report = _report(
        _feature_identity(features),
        upstream_repository=overrides.get("upstream_repository", UPSTREAM_REPOSITORY),
        upstream_commit=overrides.get("upstream_commit", UPSTREAM_COMMIT),
        converter_version=overrides.get("converter_version", "0.1.0"),
        source_identity_status=overrides.get("source_identity_status", "verified"),
        content_license_status=overrides.get("content_license_status", "verified"),
        content_license=overrides.get("content_license", "CC-BY-4.0"),
    )
    report_path = tmp_path / "conversion-report.json"
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    return archive, report_path


def _build(archive: Path, report: Path, *, data_version: str = "0.1"):
    return build_distribution_manifest(
        archive,
        report,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version=data_version,
    )


@pytest.mark.parametrize(
    ("otype", "report_overrides", "match"),
    [
        (_otype_payload(upstream_commit=UPSTREAM_COMMIT), {"upstream_commit": OTHER_COMMIT}, "upstream.*commit"),
        (_otype_payload(upstream_repository=UPSTREAM_REPOSITORY), {"upstream_repository": "https://example.invalid/other"}, "upstream.*repository"),
        (_otype_payload(converter_version="9.9.9"), {}, "converter.*version"),
        (_otype_payload(source_identity_status="unverified"), {}, "source.*identity"),
        (_otype_payload(content_license_status="unverified"), {}, "license.*status|content.*license"),
        (_otype_payload(content_license="OTHER"), {}, "content.*license|license"),
    ],
)
def test_manifest_rejects_report_identity_disagreeing_with_serialized_otype_metadata(
    tmp_path,
    otype,
    report_overrides,
    match,
):
    archive, report = _assets(
        tmp_path,
        otype=otype,
        report_overrides=report_overrides,
    )

    with pytest.raises(DistributionContractError, match=match):
        _build(archive, report)


def test_manifest_rejects_data_version_disagreeing_with_serialized_otype_metadata(tmp_path):
    archive, report = _assets(
        tmp_path,
        otype=_otype_payload(data_version="0.1"),
        data_version="9.9",
    )

    with pytest.raises(DistributionContractError, match="data.*version|version"):
        _build(archive, report, data_version="9.9")


def test_staging_rejects_unsafe_data_version_as_a_contract_error(tmp_path):
    source = tmp_path / "tf"
    source.mkdir()
    features = {
        "otype.tf": _otype_payload(),
        "oslots.tf": b"@edge\n@valueType=str\n\n2\t1\n",
    }
    for name, payload in features.items():
        (source / name).write_bytes(payload)
    (source / "conversion-report.json").write_text(
        json.dumps(_report(_feature_identity(features)), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    destination = tmp_path / "release-assets"

    with pytest.raises(DistributionContractError, match="data.*version|safe|path|component"):
        stage_distribution_assets(
            source,
            destination,
            release_tag="v0.1.1-test",
            release_commit=RELEASE_COMMIT,
            converter_version="0.1.0",
            data_version="x/../../escape",
        )

    assert not destination.exists()
    assert not (tmp_path / "escape.zip").exists()
