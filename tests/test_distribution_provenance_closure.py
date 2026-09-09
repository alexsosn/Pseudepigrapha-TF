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
from pseudepigrapha_tf.provenance import corpus_license_metadata, report_provenance

UPSTREAM_REPOSITORY = (
    "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
)
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
RELEASE_COMMIT = "d" * 40

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



def _otype_payload(extra_metadata: dict[str, str] | None = None) -> bytes:
    metadata = {**_canonical_generic(), **(extra_metadata or {})}
    metadata.update({"valueType": "str", "version": "0.1"})
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
    *,
    extra_serialized_metadata: dict[str, str] | None = None,
    extra_report_provenance: dict[str, str] | None = None,
    omit_report_provenance: tuple[str, ...] = (),
):
    features = {
        "otype.tf": _otype_payload(extra_serialized_metadata),
        "oslots.tf": b"@edge\n@valueType=str\n\n2\t1\n",
    }
    archive = tmp_path / "tf-0.1.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        for name, payload in sorted(features.items()):
            zf.writestr(name, payload)

    report = {
        "status": "ok",
        "failed_checks": [],
        "semantic_checks": {"probe": True},
        "text_fabric": _feature_identity(features),
        "provenance": {
            **report_provenance(_canonical_generic()),
            **(extra_report_provenance or {}),
        },
    }
    for key in omit_report_provenance:
        report["provenance"].pop(key, None)
    report_path = tmp_path / "conversion-report.json"
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")

    return build_distribution_manifest(
        archive,
        report_path,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
    )


def test_manifest_rejects_serialized_identity_diagnostic_omitted_from_report(tmp_path):
    with pytest.raises(
        DistributionContractError,
        match="unexpected|source.*identity.*diagnostic|serialized.*provenance",
    ):
        _build_candidate(
            tmp_path,
            extra_serialized_metadata={
                "sourceIdentityDiagnostic": "serialized identity claims extra diagnostic"
            },
        )


def test_manifest_rejects_serialized_optional_provenance_omitted_from_report(tmp_path):
    with pytest.raises(
        DistributionContractError,
        match="unexpected|license.*url|serialized.*provenance",
    ):
        _build_candidate(
            tmp_path,
            extra_serialized_metadata={
                "contentLicenseUrl": "https://creativecommons.org/licenses/by/4.0/"
            },
            omit_report_provenance=("content_license_url",),
        )


@pytest.mark.parametrize(
    ("serialized_key", "report_key", "diagnostic"),
    [
        (
            "sourceIdentityDiagnostic",
            "source_identity_diagnostic",
            "verified source identity cannot carry a failure diagnostic",
        ),
        (
            "contentLicenseDiagnostic",
            "content_license_diagnostic",
            "verified content license cannot carry a failure diagnostic",
        ),
    ],
)
def test_manifest_rejects_matching_diagnostic_for_verified_provenance(
    tmp_path,
    serialized_key,
    report_key,
    diagnostic,
):
    with pytest.raises(
        DistributionContractError,
        match="diagnostic|verified|provenance",
    ):
        _build_candidate(
            tmp_path,
            extra_serialized_metadata={serialized_key: diagnostic},
            extra_report_provenance={report_key: diagnostic},
        )


def test_manifest_allows_unbound_noncanonical_text_fabric_metadata(tmp_path):
    manifest = _build_candidate(
        tmp_path,
        extra_serialized_metadata={"writtenBy": "Text-Fabric"},
    )

    assert manifest["upstream"]["commit"] == UPSTREAM_COMMIT
    assert manifest["provenance"]["source_identity_status"] == "verified"
