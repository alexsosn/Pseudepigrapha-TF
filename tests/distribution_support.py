from __future__ import annotations

from collections.abc import Iterable, Mapping

from pseudepigrapha_tf.provenance import (
    OCP_PIN,
    OCP_REPOSITORY,
    corpus_license_metadata,
    report_provenance,
)


SYNTHETIC_CONVERTER_VERSION = "0.1.0"
SYNTHETIC_DATA_VERSION = "0.1"


def canonical_generic(
    *,
    overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return a fresh complete verified OCP generic-metadata baseline."""

    generic = {
        "upstreamRepository": OCP_REPOSITORY,
        "upstreamCommit": OCP_PIN,
        "converterVersion": SYNTHETIC_CONVERTER_VERSION,
        **corpus_license_metadata(
            OCP_REPOSITORY,
            OCP_PIN,
            source_identity_verified=True,
        ),
    }
    if overrides:
        generic.update(overrides)
    return generic


def canonical_report_provenance(
    *,
    overrides: Mapping[str, str] | None = None,
    omit: Iterable[str] = (),
) -> dict[str, str]:
    """Return a fresh canonical report projection with explicit test mutations."""

    provenance = report_provenance(canonical_generic())
    if overrides:
        provenance.update(overrides)
    for key in omit:
        provenance.pop(key)
    return provenance


def canonical_otype_payload(
    *,
    generic_overrides: Mapping[str, str] | None = None,
    extra_metadata: Mapping[str, str] | None = None,
    data_version: str = SYNTHETIC_DATA_VERSION,
) -> bytes:
    """Serialize a minimal otype.tf carrying the complete canonical baseline."""

    metadata = {
        **canonical_generic(overrides=generic_overrides),
        "valueType": "str",
        "version": data_version,
        **(extra_metadata or {}),
    }
    lines = ["@node", *(f"@{key}={value}" for key, value in sorted(metadata.items())), ""]
    return ("\n".join(lines) + "\n1\tword\n").encode("utf-8")
