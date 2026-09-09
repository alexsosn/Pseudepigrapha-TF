from __future__ import annotations

import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    build_distribution_manifest,
    feature_directory_identity,
    validate_feature_directory,
)
from pseudepigrapha_tf.provenance import corpus_license_metadata, report_provenance

UPSTREAM_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"

def _canonical_generic() -> dict[str, str]:
    return {
        "upstreamRepository": UPSTREAM_REPOSITORY,
        "upstreamCommit": UPSTREAM_COMMIT,
        "converterVersion": "0.1.0",
        **corpus_license_metadata(
            UPSTREAM_REPOSITORY,
            UPSTREAM_COMMIT,
            source_identity_verified=True,
        ),
    }


def _canonical_otype_payload() -> bytes:
    metadata = {**_canonical_generic(), "valueType": "str", "version": "0.1"}
    lines = ["@node", *(f"@{key}={value}" for key, value in sorted(metadata.items())), ""]
    return ("\n".join(lines) + "\n1\tword\n").encode("utf-8")


FEATURES = {
    "book.tf": b"@node\n1\t1En__Ethiopic\n",
    "otype.tf": _canonical_otype_payload(),
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
                "failed_checks": [],
                "semantic_checks": {"probe": True},
                "text_fabric": feature_directory_identity(source),
                "provenance": report_provenance(_canonical_generic()),
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


def test_directory_verifier_rejects_nested_feature_files(tmp_path):
    source, manifest = _fixture(tmp_path)
    nested = source / "nested"
    nested.mkdir()
    (nested / "shadow.tf").write_bytes(b"@node\n")

    with pytest.raises(DistributionContractError, match="nested.*feature"):
        validate_feature_directory(manifest, source)


@pytest.mark.skipif(os.name == "nt", reason="symlink creation is not reliably available on Windows CI")
def test_directory_verifier_rejects_symlinked_directories_hiding_nested_features(tmp_path):
    source, manifest = _fixture(tmp_path)
    external = tmp_path / "external-generation"
    external.mkdir()
    (external / "shadow.tf").write_bytes(b"@node\n")
    (source / "linked-generation").symlink_to(external, target_is_directory=True)

    with pytest.raises(DistributionContractError, match="symlink|nested.*feature|feature.*nested"):
        validate_feature_directory(manifest, source)
