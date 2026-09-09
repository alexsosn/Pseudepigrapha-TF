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
    OCP_CONTENT_LICENSE,
    OCP_CONTENT_LICENSE_URL,
    OCP_LICENSE_COMMIT,
    OCP_PIN,
    OCP_REPOSITORY,
    corpus_license_metadata,
    report_provenance,
)


CONVERTER_VERSION = "0.1.0"
DATA_VERSION = "0.1"
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
    canonical = json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "feature_count": len(records),
        "features": records,
        "feature_set_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def _build_candidate(
    tmp_path: Path,
    generic: dict[str, str],
    *,
    extra_serialized_metadata: dict[str, str] | None = None,
):
    features = {
        "otype.tf": _otype_payload(
            generic,
            extra_metadata=extra_serialized_metadata,
        ),
        "oslots.tf": b"@edge\n@valueType=str\n\n2\t1\n",
    }
    archive = tmp_path / f"tf-{DATA_VERSION}.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        for name, payload in sorted(features.items()):
            zf.writestr(name, payload)

    report = {
        "status": "ok",
        "failed_checks": [],
        # Deliberately hostile boundary: distribution must not trust a forged
        # semantic-check boolean as proof of provenance authenticity.
        "semantic_checks": {
            "probe": True,
            "corpus_license_provenance": True,
        },
        "text_fabric": _feature_identity(features),
        "provenance": report_provenance(generic),
    }
    report_path = tmp_path / "conversion-report.json"
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")

    return build_distribution_manifest(
        archive,
        report_path,
        release_tag="v0.1.1-test",
        release_commit=RELEASE_COMMIT,
        converter_version=CONVERTER_VERSION,
        data_version=DATA_VERSION,
    )


def _wrong_content_license(generic: dict[str, str]) -> None:
    generic["contentLicense"] = "OTHER"


def _wrong_content_license_url(generic: dict[str, str]) -> None:
    generic["contentLicenseUrl"] = "https://example.invalid/license"


def _wrong_content_license_source(generic: dict[str, str]) -> None:
    generic["contentLicenseSource"] = "https://example.invalid/license-source"


def _wrong_content_license_scope(generic: dict[str, str]) -> None:
    generic["contentLicenseScope"] = "different corpus scope"


def _wrong_converter_software_license(generic: dict[str, str]) -> None:
    generic["converterSoftwareLicense"] = "OTHER"


def _wrong_upstream_software_license(generic: dict[str, str]) -> None:
    generic["upstreamSoftwareLicense"] = "OTHER"


def _wrong_upstream_license_commit(generic: dict[str, str]) -> None:
    generic["upstreamLicenseCommit"] = "a" * 40


def _wrong_content_attribution(generic: dict[str, str]) -> None:
    generic["contentAttribution"] = "Incorrect attribution"


def _wrong_content_citation(generic: dict[str, str]) -> None:
    generic["contentCitation"] = "Incorrect citation"


def _omit_required_attribution(generic: dict[str, str]) -> None:
    generic.pop("contentAttribution")


def _omit_required_license_source(generic: dict[str, str]) -> None:
    generic.pop("contentLicenseSource")


def _omit_required_license_scope(generic: dict[str, str]) -> None:
    generic.pop("contentLicenseScope")


def _omit_required_citation(generic: dict[str, str]) -> None:
    generic.pop("contentCitation")


def _unknown_source_claiming_verified_profile(generic: dict[str, str]) -> None:
    generic["upstreamRepository"] = "https://example.invalid/unresearched-corpus"
    generic["upstreamCommit"] = "b" * 40


@pytest.mark.parametrize(
    "mutate",
    [
        _wrong_content_license,
        _wrong_content_license_url,
        _wrong_content_license_source,
        _wrong_content_license_scope,
        _wrong_converter_software_license,
        _wrong_upstream_software_license,
        _wrong_upstream_license_commit,
        _wrong_content_attribution,
        _wrong_content_citation,
        _omit_required_attribution,
        _omit_required_license_source,
        _omit_required_license_scope,
        _omit_required_citation,
        _unknown_source_claiming_verified_profile,
    ],
    ids=[
        "wrong-content-license",
        "wrong-content-license-url",
        "wrong-content-license-source",
        "wrong-content-license-scope",
        "wrong-converter-software-license",
        "wrong-upstream-software-license",
        "wrong-upstream-license-commit",
        "wrong-content-attribution",
        "wrong-content-citation",
        "missing-required-attribution",
        "missing-required-license-source",
        "missing-required-license-scope",
        "missing-required-citation",
        "unknown-source-verified-profile",
    ],
)
def test_manifest_rejects_mutually_agreeing_false_verified_profile(tmp_path, mutate):
    generic = _canonical_generic()
    mutate(generic)

    with pytest.raises(
        DistributionContractError,
        match="provenance|profile|license|source",
    ):
        _build_candidate(tmp_path, generic)


def test_manifest_accepts_exact_canonical_pinned_ocp_profile(tmp_path):
    manifest = _build_candidate(tmp_path, _canonical_generic())

    assert manifest["upstream"]["repository"] == OCP_REPOSITORY
    assert manifest["upstream"]["commit"] == OCP_PIN
    assert manifest["provenance"]["content_license"] == OCP_CONTENT_LICENSE
    assert OCP_CONTENT_LICENSE_URL.startswith("https://")
    assert OCP_LICENSE_COMMIT != OCP_PIN


def test_manifest_still_ignores_noncanonical_text_fabric_metadata(tmp_path):
    manifest = _build_candidate(
        tmp_path,
        _canonical_generic(),
        extra_serialized_metadata={"writtenBy": "Text-Fabric"},
    )

    assert manifest["upstream"]["commit"] == OCP_PIN
