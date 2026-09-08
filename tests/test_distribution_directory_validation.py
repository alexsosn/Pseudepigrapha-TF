from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    build_distribution_manifest,
    validate_feature_directory,
)


UPSTREAM_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
FEATURES = {
    "book.tf": b"@node\n1\t1En__Ethiopic\n",
    "otype.tf": b"@node\n1\tword\n",
    "oslots.tf": b"@edge\n2\t1\n",
}


def _fixture(tmp_path: Path):
    source = tmp_path / "tf" / "0.1"
    source.mkdir(parents=True)
    for name, payload in FEATURES.items():
        (source / name).write_bytes(payload)

    archive = tmp_path / "tf-0.1.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        for name, payload in reversed(sorted(FEATURES.items())):
            zf.writestr(name, payload)

    report = tmp_path / "conversion-report.json"
    report.write_text(
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
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = build_distribution_manifest(
        archive,
        report,
        release_tag="v0.1.1-test",
        release_commit="c" * 40,
        converter_version="0.1.0",
        data_version="0.1",
    )
    return source, manifest


def test_manifest_verifies_exact_extracted_feature_directory(tmp_path):
    source, manifest = _fixture(tmp_path)

    assert validate_feature_directory(manifest, source) is None


def test_directory_verifier_rejects_missing_mutated_and_extra_features(tmp_path):
    source, manifest = _fixture(tmp_path)

    (source / "book.tf").unlink()
    with pytest.raises(DistributionContractError, match="feature"):
        validate_feature_directory(manifest, source)

    source, manifest = _fixture(tmp_path / "mutated")
    (source / "book.tf").write_bytes(FEATURES["book.tf"] + b"x")
    with pytest.raises(DistributionContractError, match="feature"):
        validate_feature_directory(manifest, source)

    source, manifest = _fixture(tmp_path / "extra")
    (source / "extra.tf").write_bytes(b"@node\n")
    with pytest.raises(DistributionContractError, match="feature"):
        validate_feature_directory(manifest, source)
