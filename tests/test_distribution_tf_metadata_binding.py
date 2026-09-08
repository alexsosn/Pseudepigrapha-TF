from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    build_distribution_manifest,
    feature_directory_identity,
)


UPSTREAM_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
OTHER_COMMIT = "a" * 40
RELEASE_COMMIT = "b" * 40


def _otype(
    *,
    upstream_commit: str = UPSTREAM_COMMIT,
    data_version: str = "0.1",
    converter_version: str = "0.1.0",
    content_license: str = "CC-BY-4.0",
) -> bytes:
    return (
        "@node\n"
        "@valueType=str\n"
        f"@version={data_version}\n"
        f"@converterVersion={converter_version}\n"
        f"@upstreamRepository={UPSTREAM_REPOSITORY}\n"
        f"@upstreamCommit={upstream_commit}\n"
        "@sourceIdentityStatus=verified\n"
        "@contentLicenseStatus=verified\n"
        f"@contentLicense={content_license}\n"
        "@converterSoftwareLicense=MIT\n"
        "@upstreamSoftwareLicense=GPL-3.0\n"
        "\n"
        "1\tword\n"
    ).encode("utf-8")


def _fixture(
    tmp_path: Path,
    *,
    serialized_commit: str = UPSTREAM_COMMIT,
    report_commit: str = UPSTREAM_COMMIT,
    serialized_data_version: str = "0.1",
    archive_data_version: str = "0.1",
    serialized_converter_version: str = "0.1.0",
    serialized_content_license: str = "CC-BY-4.0",
) -> tuple[Path, Path]:
    source = tmp_path / "features"
    source.mkdir(parents=True)
    (source / "otype.tf").write_bytes(
        _otype(
            upstream_commit=serialized_commit,
            data_version=serialized_data_version,
            converter_version=serialized_converter_version,
            content_license=serialized_content_license,
        )
    )
    (source / "oslots.tf").write_bytes(b"@edge\n@valueType=str\n\n2\t1\n")

    archive = tmp_path / f"tf-{archive_data_version}.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        for feature in sorted(source.glob("*.tf"), key=lambda path: path.name):
            zf.writestr(feature.name, feature.read_bytes())

    report = tmp_path / "conversion-report.json"
    report.write_text(
        json.dumps(
            {
                "status": "ok",
                "failed_checks": [],
                "semantic_checks": {"probe": True},
                "text_fabric": feature_directory_identity(source),
                "provenance": {
                    "upstream_repository": UPSTREAM_REPOSITORY,
                    "upstream_commit": report_commit,
                    "converter_version": "0.1.0",
                    "source_identity_status": "verified",
                    "content_license_status": "verified",
                    "content_license": "CC-BY-4.0",
                    "converter_software_license": "MIT",
                    "upstream_software_license": "GPL-3.0",
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return archive, report


def _build(archive: Path, report: Path, *, data_version: str = "0.1") -> None:
    build_distribution_manifest(
        archive,
        report,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version=data_version,
    )


def test_manifest_rejects_report_upstream_commit_that_disagrees_with_serialized_tf(tmp_path):
    archive, report = _fixture(
        tmp_path,
        serialized_commit=UPSTREAM_COMMIT,
        report_commit=OTHER_COMMIT,
    )

    with pytest.raises(DistributionContractError, match="upstream.*commit|serialized.*identity"):
        _build(archive, report)


def test_manifest_rejects_data_version_that_disagrees_with_serialized_tf(tmp_path):
    archive, report = _fixture(
        tmp_path,
        serialized_data_version="0.1",
        archive_data_version="9.9",
    )

    with pytest.raises(DistributionContractError, match="data.*version|serialized.*version"):
        _build(archive, report, data_version="9.9")


def test_manifest_rejects_converter_version_that_disagrees_with_serialized_tf(tmp_path):
    archive, report = _fixture(tmp_path, serialized_converter_version="9.9.9")

    with pytest.raises(DistributionContractError, match="converter.*version|serialized.*identity"):
        _build(archive, report)


def test_manifest_rejects_license_claim_that_disagrees_with_serialized_tf(tmp_path):
    archive, report = _fixture(tmp_path, serialized_content_license="DIFFERENT")

    with pytest.raises(DistributionContractError, match="license|serialized.*identity"):
        _build(archive, report)
