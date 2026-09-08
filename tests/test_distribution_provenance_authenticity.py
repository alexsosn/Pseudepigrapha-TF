from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    build_distribution_manifest,
)
from pseudepigrapha_tf.provenance import (
    OCP_PIN,
    OCP_REPOSITORY,
    corpus_license_metadata,
    report_provenance,
)


CONVERTER_VERSION = "0.2.0"
DATA_VERSION = "0.2"
RELEASE_COMMIT = "d" * 40


def _canonical_generic() -> dict[str, str]:
    return {
        "upstreamRepository": OCP_REPOSITORY,
        "upstreamCommit": OCP_PIN,
        "converterVersion": CONVERTER_VERSION,
        **corpus_license_metadata(
            OCP_REPOSITORY,
            OCP_PIN,
            source_identity_verified=True,
        ),
    }


def _otype_payload(
    generic: dict[str, str],
    *,
    extra_metadata: dict[str, str] | None = None,
) -> bytes:
    metadata = {
        **generic,
        "valueType": "str",
        "version": DATA_VERSION,
        **(extra_metadata or {}),
    }
    lines = ["@node", *(f"@{key}={value}" for key, value in sorted(metadata.items())), ""]
    return ("\n".join(lines) + "\n1\tword\n").encode("utf-8")


def _feature_identity(features: dict[str, bytes]) -> dict[str, object]:
    records = [
        {
            "name": name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for name, payload in sorted(features.items())
    ]
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return {
        "feature_count": len(records),
        "features": records,
        "feature_set_sha256": hashlib.sha256(payload).hexdigest(),
    }


def _build_candidate(
    tmp_path: Path,
    generic: dict[str, str],
    *,
    extra_serialized_metadata: dict[str, str] | None = None,
):
    features = {
        "otype.tf": _otype_payload(generic, extra_metadata=extra_serialized_metadata),
        "oslots.tf": b"@edge\n@valueType=str\n\n2\t1\n",
    }
    archive = tmp_path / f"tf-{DATA_VERSION}.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        for name, payload in sorted(features.items()):
            zf.writestr(name, payload)

    report = {
        "status": "ok",
        "failed_checks": [],
        "semantic_checks": {"probe": True},
        "text_fabric": _feature_identity(features),
        "provenance": report_provenance(generic),
    }
    report_path = tmp_path / "conversion-report.json"
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")

    return build_distribution_manifest(
        archive,
        report_path,
        release_tag="v0.2.0-test",
        release_commit=RELEASE_COMMIT,
        converter_version=CONVERTER_VERSION,
        data_version=DATA_VERSION,
    )


@pytest.mark.parametrize(
    "serialized_key",
    [
        "contentLicense",
        "contentLicenseUrl",
        "contentLicenseSource",
        "contentLicenseScope",
        "converterSoftwareLicense",
        "upstreamSoftwareLicense",
        "upstreamLicenseCommit",
        "contentAttribution",
        "contentCitation",
    ],
)
def test_manifest_rejects_mutually_agreeing_false_verified_profile_value(
    tmp_path,
    serialized_key,
):
    generic = _canonical_generic()
    generic[serialized_key] = f"forged-{serialized_key}"

    with pytest.raises(
        DistributionContractError,
        match="canonical|profile|provenance|license|source",
    ):
        _build_candidate(tmp_path, generic)


@pytest.mark.parametrize(
    "serialized_key",
    [
        "contentLicenseUrl",
        "contentLicenseSource",
        "contentLicenseScope",
        "upstreamLicenseCommit",
        "contentAttribution",
        "contentCitation",
    ],
)
def test_manifest_rejects_mutually_agreeing_missing_verified_profile_evidence(
    tmp_path,
    serialized_key,
):
    generic = _canonical_generic()
    del generic[serialized_key]

    with pytest.raises(
        DistributionContractError,
        match="canonical|profile|provenance|license|source",
    ):
        _build_candidate(tmp_path, generic)


def test_manifest_rejects_unresearched_source_with_forged_verified_license_profile(tmp_path):
    generic = _canonical_generic()
    generic["upstreamRepository"] = "https://example.invalid/unresearched"
    generic["upstreamCommit"] = "f" * 40

    with pytest.raises(
        DistributionContractError,
        match="canonical|profile|provenance|license|source",
    ):
        _build_candidate(tmp_path, generic)


def test_manifest_accepts_exact_canonical_verified_profile(tmp_path):
    manifest = _build_candidate(tmp_path, _canonical_generic())

    assert manifest["upstream"]["repository"] == OCP_REPOSITORY
    assert manifest["upstream"]["commit"] == OCP_PIN
    assert manifest["provenance"]["content_license"] == "CC-BY-4.0"


def test_manifest_ignores_noncanonical_text_fabric_metadata_for_profile_truth(tmp_path):
    manifest = _build_candidate(
        tmp_path,
        _canonical_generic(),
        extra_serialized_metadata={"writtenBy": "Text-Fabric"},
    )

    assert manifest["upstream"]["commit"] == OCP_PIN
