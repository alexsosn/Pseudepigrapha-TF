from __future__ import annotations

from collections.abc import Mapping


OCP_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
OCP_PIN = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
OCP_LICENSE_COMMIT = "8c8c2c55a2c55ba4b23ac506956f98dcc25045b2"
CONVERTER_SOFTWARE_LICENSE = "MIT"
OCP_SOFTWARE_LICENSE = "GPL-3.0"
OCP_CONTENT_LICENSE = "CC-BY-4.0"
OCP_CONTENT_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
OCP_CONTENT_LICENSE_SOURCE = (
    f"{OCP_REPOSITORY}/blob/{OCP_PIN}/LICENSE.CC-BY-4.0"
)
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


def corpus_license_metadata(repository: str, commit: str) -> dict[str, str]:
    """Return the researched license profile for one exact source tuple.

    The source repository may still be converted when it is not the supported
    OCP pin, but such a tuple must not inherit the verified CC BY assertion.
    """

    base = {"converterSoftwareLicense": CONVERTER_SOFTWARE_LICENSE}
    if repository == OCP_REPOSITORY and commit == OCP_PIN:
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

    return {
        **base,
        "contentLicenseStatus": "unverified",
        "contentLicenseDiagnostic": (
            "no verified corpus-license profile for "
            f"upstreamRepository={repository!r}, upstreamCommit={commit!r}"
        ),
    }


def corpus_license_provenance_is_consistent(generic: Mapping[str, object]) -> bool:
    """Check that a graph neither drops nor overclaims its source license profile."""

    repository = str(generic.get("upstreamRepository", ""))
    commit = str(generic.get("upstreamCommit", ""))
    expected = corpus_license_metadata(repository, commit)

    if any(generic.get(key) != value for key, value in expected.items()):
        return False
    if expected["contentLicenseStatus"] == "unverified":
        if any(key in generic for key in _VERIFIED_ONLY_KEYS):
            return False
    else:
        if "contentLicenseDiagnostic" in generic:
            return False
    return True


def report_provenance(generic: Mapping[str, object]) -> dict[str, str]:
    """Project the graph's canonical generic provenance into report field names."""

    mapping = (
        ("upstreamRepository", "upstream_repository"),
        ("upstreamCommit", "upstream_commit"),
        ("converterVersion", "converter_version"),
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
