from __future__ import annotations

import json
import os
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
RELEASE_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _report(*, upstream_commit: str = UPSTREAM_COMMIT) -> dict:
    return {
        "status": "ok",
        "failed_checks": [],
        "semantic_checks": {"probe": True},
        "provenance": {
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": upstream_commit,
            "converter_version": "0.1.0",
            "source_identity_status": "verified",
            "content_license_status": "verified",
            "content_license": "CC-BY-4.0",
            "converter_software_license": "MIT",
            "upstream_software_license": "GPL-3.0",
        },
    }


def _archive_and_report(tmp_path: Path, *, upstream_commit: str = UPSTREAM_COMMIT) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    archive = tmp_path / "tf-0.1.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("otype.tf", "@node\n@valueType=str\n1\tword\n")
    report = tmp_path / "conversion-report.json"
    report.write_text(json.dumps(_report(upstream_commit=upstream_commit)) + "\n", encoding="utf-8")
    return archive, report


def _materialized(tmp_path: Path) -> Path:
    source = tmp_path / "tf" / "0.1"
    source.mkdir(parents=True)
    (source / "otype.tf").write_bytes(b"@node\n@valueType=str\n1\tword\n")
    (source / "oslots.tf").write_bytes(b"@edge\n")
    (source / "conversion-report.json").write_text(
        json.dumps(_report(), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return source


def _stage(source: Path, destination: Path) -> None:
    stage_distribution_assets(
        source,
        destination,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
    )


def test_manifest_builder_rejects_non_sha_release_commit(tmp_path):
    archive, report = _archive_and_report(tmp_path)

    with pytest.raises(DistributionContractError, match="release commit.*(sha|SHA|40|hex)"):
        build_distribution_manifest(
            archive,
            report,
            release_tag="v0.1.1-test",
            release_commit="main",
            converter_version="0.1.0",
            data_version="0.1",
        )


def test_manifest_builder_rejects_non_sha_upstream_commit(tmp_path):
    archive, report = _archive_and_report(tmp_path, upstream_commit="main")

    with pytest.raises(DistributionContractError, match="upstream commit.*(sha|SHA|40|hex)"):
        build_distribution_manifest(
            archive,
            report,
            release_tag="v0.1.1-test",
            release_commit=RELEASE_COMMIT,
            converter_version="0.1.0",
            data_version="0.1",
        )


def test_staging_rejects_nested_feature_files_instead_of_silently_omitting_them(tmp_path):
    source = _materialized(tmp_path)
    nested = source / "stale-generation"
    nested.mkdir()
    (nested / "ghost.tf").write_bytes(b"@node\n1\tghost\n")
    destination = tmp_path / "release-assets"

    with pytest.raises(DistributionContractError, match="nested.*feature|feature.*nested"):
        _stage(source, destination)

    assert not destination.exists()


@pytest.mark.skipif(os.name == "nt", reason="symlink creation is not reliably available on Windows CI")
def test_staging_rejects_symlinked_feature_files(tmp_path):
    source = _materialized(tmp_path)
    external = tmp_path / "external.tf"
    external.write_bytes(b"@node\n1\texternal\n")
    link = source / "linked.tf"
    link.symlink_to(external)
    destination = tmp_path / "release-assets"

    with pytest.raises(DistributionContractError, match="symlink"):
        _stage(source, destination)

    assert not destination.exists()
