from __future__ import annotations

from collections.abc import Mapping, MutableMapping


OCP_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
OCP_PIN = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
OCP_LICENSE_COMMIT = "8c8c2c55a2c55ba4b23ac506956f98dcc25045b2"
CONVERTER_SOFTWARE_LICENSE = "MIT"
OCP_SOFTWARE_LICENSE = "GPL-3.0"
OCP_CONTENT_LICENSE = "CC-BY-4.0"
OCP_CONTENT_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
OCP_CONTENT_LICENSE_SOURCE = f"{OCP_REPOSITORY}/blob/{OCP_PIN}/LICENSE.CC-BY-4.0"
OCP_CONTENT_LICENSE_SCOPE = "OCP text editions and TEI XML files under static/docs/"
OCP_CONTENT_ATTRIBUTION = (
    "Online Critical Pseudepigrapha (OCP) and the individual editor named in each "
    "document's header/public metadata."
)
OCP_CONTENT_CITATION = (
    "Ian W. Scott and Ken M. Penner, eds. The Online Critical Pseudepigrapha. "
    "Atlanta: Society of Biblical Literature / Online: pseudepigrapha.org."
)

_VERIFIED_ONLY_KEYS = frozenset(
    {
        "contentLicense",
        "contentLicenseUrl",
        "contentLicenseSource",
        "contentLicenseScope",
        "upstreamSoftwareLicense",
        "upstreamLicenseCommit",
        "contentAttribution",
        "contentCitation",
    }
)
_PROFILE_KEYS = frozenset(
    {
        "converterSoftwareLicense",
        "contentLicenseStatus",
        "contentLicenseDiagnostic",
        "sourceIdentityStatus",
        "sourceIdentityDiagnostic",
        *_VERIFIED_ONLY_KEYS,
    }
)


def corpus_license_metadata(
    repository: str,
    commit: str,
    *,
    source_identity_verified: bool = True,
) -> dict[str, str]:
    """Return the researched license profile for one exact source tuple.

    A caller that has independent access to the source checkout can set
    ``source_identity_verified=False`` so a recorded pin cannot by itself create
    a verified license assertion.
    """

    base = {"converterSoftwareLicense": CONVERTER_SOFTWARE_LICENSE}
    if source_identity_verified and repository == OCP_REPOSITORY and commit == OCP_PIN:
        return {
            **base,
            "contentLicenseStatus": "verified",
            "contentLicense": OCP_CONTENT_LICENSE,
            "contentLicenseUrl": OCP_CONTENT_LICENSE_URL,
            "contentLicenseSource": OCP_CONTENT_LICENSE_SOURCE,
            "contentLicenseScope": OCP_CONTENT_LICENSE_SCOPE,
            "upstreamSoftwareLicense": OCP_SOFTWARE_LICENSE,
            "upstreamLicenseCommit": OCP_LICENSE_COMMIT,
            "contentAttribution": OCP_CONTENT_ATTRIBUTION,
            "contentCitation": OCP_CONTENT_CITATION,
        }

    if not source_identity_verified:
        diagnostic = (
            "recorded upstream commit/source tree was not independently verified: "
            f"upstreamRepository={repository!r}, upstreamCommit={commit!r}"
        )
    else:
        diagnostic = (
            "no verified corpus-license profile for "
            f"upstreamRepository={repository!r}, upstreamCommit={commit!r}"
        )
    return {
        **base,
        "contentLicenseStatus": "unverified",
        "contentLicenseDiagnostic": diagnostic,
    }


def attest_corpus_license_source_identity(
    generic: MutableMapping[str, str],
    detected_commit: str,
    *,
    source_tree_clean: bool = True,
) -> None:
    """Rebuild license metadata from independently detected checkout identity.

    The recorded upstream commit remains useful provenance even when explicitly
    overridden, but an override or dirty source tree cannot make a checkout look
    like the researched source pin.
    """

    repository = str(generic.get("upstreamRepository", ""))
    recorded_commit = str(generic.get("upstreamCommit", ""))
    commit_matches = bool(detected_commit) and detected_commit == recorded_commit
    identity_verified = commit_matches and source_tree_clean

    for key in _PROFILE_KEYS:
        generic.pop(key, None)
    generic.update(
        corpus_license_metadata(
            repository,
            recorded_commit,
            source_identity_verified=identity_verified,
        )
    )
    generic["sourceIdentityStatus"] = "verified" if identity_verified else "unverified"
    if not identity_verified:
        reasons: list[str] = []
        if not commit_matches:
            reasons.append(
                "recorded upstream commit does not match an independently detected source checkout "
                f"(recorded={recorded_commit!r}, detected={detected_commit!r})"
            )
        if not source_tree_clean:
            reasons.append("supplied source directory has tracked, untracked, or ignored filesystem changes")
        generic["sourceIdentityDiagnostic"] = "; ".join(reasons)


def corpus_license_provenance_is_consistent(generic: Mapping[str, object]) -> bool:
    """Check that a graph neither drops nor overclaims its source license profile."""

    repository = str(generic.get("upstreamRepository", ""))
    commit = str(generic.get("upstreamCommit", ""))
    identity_status = generic.get("sourceIdentityStatus")
    if identity_status not in (None, "verified", "unverified"):
        return False
    source_identity_verified = identity_status != "unverified"
    expected = corpus_license_metadata(
        repository,
        commit,
        source_identity_verified=source_identity_verified,
    )

    if any(generic.get(key) != value for key, value in expected.items()):
        return False
    if expected["contentLicenseStatus"] == "unverified":
        if any(key in generic for key in _VERIFIED_ONLY_KEYS):
            return False
    elif "contentLicenseDiagnostic" in generic:
        return False

    if identity_status == "verified" and "sourceIdentityDiagnostic" in generic:
        return False
    if identity_status == "unverified" and not generic.get("sourceIdentityDiagnostic"):
        return False
    return True


def report_provenance(generic: Mapping[str, object]) -> dict[str, str]:
    """Project the graph's canonical generic provenance into report field names."""

    mapping = (
        ("upstreamRepository", "upstream_repository"),
        ("upstreamCommit", "upstream_commit"),
        ("converterVersion", "converter_version"),
        ("sourceIdentityStatus", "source_identity_status"),
        ("sourceIdentityDiagnostic", "source_identity_diagnostic"),
        ("contentLicenseStatus", "content_license_status"),
        ("contentLicense", "content_license"),
        ("contentLicenseUrl", "content_license_url"),
        ("contentLicenseSource", "content_license_source"),
        ("contentLicenseScope", "content_license_scope"),
        ("converterSoftwareLicense", "converter_software_license"),
        ("upstreamSoftwareLicense", "upstream_software_license"),
        ("upstreamLicenseCommit", "upstream_license_commit"),
        ("contentAttribution", "content_attribution"),
        ("contentCitation", "content_citation"),
        ("contentLicenseDiagnostic", "content_license_diagnostic"),
    )
    return {
        target: str(generic[source])
        for source, target in mapping
        if source in generic
    }
