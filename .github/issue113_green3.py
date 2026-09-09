from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement target, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Production: preserve specific archive / serialized-identity diagnostics before
# the final canonical source/license authenticity gate.
replace_once(
    "src/pseudepigrapha_tf/distribution.py",
    '''    generic_provenance = {\n        serialized_key: serialized_provenance[report_key]\n        for serialized_key, report_key in REPORT_PROVENANCE_FIELDS\n        if report_key in serialized_provenance\n    }\n    if not corpus_license_provenance_is_consistent(generic_provenance):\n        raise DistributionContractError(\n            "report provenance does not match a canonical verified source/license profile"\n        )\n\n''',
    '',
)
replace_once(
    "src/pseudepigrapha_tf/distribution.py",
    '''    return {\n        "upstream_repository": upstream_repository,\n        "upstream_commit": upstream_commit,\n        "provenance": manifest_provenance,\n        "serialized_provenance": serialized_provenance,\n    }\n\n\ndef _feature_records(archive: Path) -> list[dict[str, Any]]:\n''',
    '''    return {\n        "upstream_repository": upstream_repository,\n        "upstream_commit": upstream_commit,\n        "provenance": manifest_provenance,\n        "serialized_provenance": serialized_provenance,\n    }\n\n\ndef _validate_canonical_provenance_profile(identity: Mapping[str, Any]) -> None:\n    serialized_provenance = _require_mapping(\n        identity.get("serialized_provenance"), "report-derived serialized provenance"\n    )\n    generic_provenance = {\n        serialized_key: serialized_provenance[report_key]\n        for serialized_key, report_key in REPORT_PROVENANCE_FIELDS\n        if report_key in serialized_provenance\n    }\n    if not corpus_license_provenance_is_consistent(generic_provenance):\n        raise DistributionContractError(\n            "report provenance does not match a canonical verified source/license profile"\n        )\n\n\ndef _feature_records(archive: Path) -> list[dict[str, Any]]:\n''',
)
replace_once(
    "src/pseudepigrapha_tf/distribution.py",
    '''    _validate_serialized_identity(\n        archive,\n        identity=identity,\n        converter_version=converter_version,\n        data_version=data_version,\n    )\n\n    return {\n''',
    '''    _validate_serialized_identity(\n        archive,\n        identity=identity,\n        converter_version=converter_version,\n        data_version=data_version,\n    )\n    _validate_canonical_provenance_profile(identity)\n\n    return {\n''',
)

CANONICAL_IMPORT = "from pseudepigrapha_tf.provenance import corpus_license_metadata, report_provenance\n"
HELPER = '''\n\ndef _canonical_generic() -> dict[str, str]:\n    return {\n        "upstreamRepository": UPSTREAM_REPOSITORY,\n        "upstreamCommit": UPSTREAM_COMMIT,\n        "converterVersion": "0.1.0",\n        **corpus_license_metadata(\n            UPSTREAM_REPOSITORY,\n            UPSTREAM_COMMIT,\n            source_identity_verified=True,\n        ),\n    }\n\n\ndef _canonical_otype_payload() -> bytes:\n    metadata = {**_canonical_generic(), "valueType": "str", "version": "0.1"}\n    lines = ["@node", *(f"@{key}={value}" for key, value in sorted(metadata.items())), ""]\n    return ("\\n".join(lines) + "\\n1\\tword\\n").encode("utf-8")\n'''

# Directory validation fixture.
path = "tests/test_distribution_directory_validation.py"
replace_once(path, ')\n\n\nUPSTREAM_REPOSITORY =', ')\n' + CANONICAL_IMPORT + '\nUPSTREAM_REPOSITORY =')
replace_once(path, 'UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"\nFEATURES = {', 'UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"' + HELPER + '\n\nFEATURES = {')
replace_once(path, '    "otype.tf": b\'@node\\n@contentLicense=CC-BY-4.0\\n@contentLicenseStatus=verified\\n@converterSoftwareLicense=MIT\\n@converterVersion=0.1.0\\n@sourceIdentityStatus=verified\\n@upstreamCommit=c939dcbacad78c5d18d2c4282cad23c47e19ac07\\n@upstreamRepository=https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha\\n@upstreamSoftwareLicense=GPL-3.0\\n@valueType=str\\n@version=0.1\\n\\n1\\tword\\n\',', '    "otype.tf": _canonical_otype_payload(),')
replace_once(path, '''                "provenance": {\n                    "upstream_repository": UPSTREAM_REPOSITORY,\n                    "upstream_commit": UPSTREAM_COMMIT,\n                    "converter_version": "0.1.0",\n                    "source_identity_status": "verified",\n                    "content_license_status": "verified",\n                    "content_license": "CC-BY-4.0",\n                    "converter_software_license": "MIT",\n                    "upstream_software_license": "GPL-3.0",\n                },\n''', '                "provenance": report_provenance(_canonical_generic()),\n')

# Feature-set fixture.
path = "tests/test_distribution_feature_set.py"
replace_once(path, 'import pytest\n\n\nUPSTREAM_REPOSITORY', 'import pytest\n\n' + CANONICAL_IMPORT + '\nUPSTREAM_REPOSITORY')
replace_once(path, 'RELEASE_COMMIT = "a" * 40\nFEATURES = {', 'RELEASE_COMMIT = "a" * 40' + HELPER + '\n\nFEATURES = {')
replace_once(path, '    "otype.tf": b\'@node\\n@contentLicense=CC-BY-4.0\\n@contentLicenseStatus=verified\\n@converterSoftwareLicense=MIT\\n@converterVersion=0.1.0\\n@sourceIdentityStatus=verified\\n@upstreamCommit=c939dcbacad78c5d18d2c4282cad23c47e19ac07\\n@upstreamRepository=https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha\\n@upstreamSoftwareLicense=GPL-3.0\\n@valueType=str\\n@version=0.1\\n\\n1\\tword\\n\',', '    "otype.tf": _canonical_otype_payload(),')
replace_once(path, '''                "provenance": {\n                    "upstream_repository": UPSTREAM_REPOSITORY,\n                    "upstream_commit": UPSTREAM_COMMIT,\n                    "converter_version": "0.1.0",\n                    "source_identity_status": "verified",\n                    "content_license_status": "verified",\n                    "content_license": "CC-BY-4.0",\n                    "converter_software_license": "MIT",\n                    "upstream_software_license": "GPL-3.0",\n                },\n''', '                "provenance": report_provenance(_canonical_generic()),\n')

# Manifest fixture.
path = "tests/test_distribution_manifest.py"
replace_once(path, ')\n\n\nUPSTREAM_REPOSITORY =', ')\n' + CANONICAL_IMPORT + '\nUPSTREAM_REPOSITORY =')
replace_once(path, 'RELEASE_COMMIT = "0123456789abcdef0123456789abcdef01234567"\n\n\ndef _report', 'RELEASE_COMMIT = "0123456789abcdef0123456789abcdef01234567"' + HELPER + '\n\n\ndef _report')
replace_once(path, '''        "provenance": {\n            "upstream_repository": UPSTREAM_REPOSITORY,\n            "upstream_commit": UPSTREAM_COMMIT,\n            "converter_version": "0.1.0",\n            "source_identity_status": source_status,\n            "content_license_status": license_status,\n            "content_license": "CC-BY-4.0",\n            "converter_software_license": "MIT",\n            "upstream_software_license": "GPL-3.0",\n            "upstream_license_commit": "8c8c2c55a2c55ba4b23ac506956f98dcc25045b2",\n            "content_license_source": f"{UPSTREAM_REPOSITORY}/blob/{UPSTREAM_COMMIT}/LICENSE.CC-BY-4.0",\n        },\n''', '''        "provenance": {\n            **report_provenance(_canonical_generic()),\n            "source_identity_status": source_status,\n            "content_license_status": license_status,\n        },\n''')
start = '        zf.writestr("otype.tf", \'@node\\n@contentLicense=CC-BY-4.0\\n@contentLicenseSource=https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/LICENSE.CC-BY-4.0\\n@contentLicenseStatus=verified\\n@converterSoftwareLicense=MIT\\n@converterVersion=0.1.0\\n@sourceIdentityStatus=verified\\n@upstreamCommit=c939dcbacad78c5d18d2c4282cad23c47e19ac07\\n@upstreamLicenseCommit=8c8c2c55a2c55ba4b23ac506956f98dcc25045b2\\n@upstreamRepository=https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha\\n@upstreamSoftwareLicense=GPL-3.0\\n@valueType=str\\n@version=0.1\\n\\n1\\tword\\n\')'
replace_once(path, start, '        zf.writestr("otype.tf", _canonical_otype_payload())')

# Provenance closure fixture: canonical by default; allow one report key to be
# removed when specifically testing representation asymmetry.
path = "tests/test_distribution_provenance_closure.py"
replace_once(path, ')\n\n\nUPSTREAM_REPOSITORY =', ')\n' + CANONICAL_IMPORT + '\nUPSTREAM_REPOSITORY =')
replace_once(path, 'RELEASE_COMMIT = "d" * 40\n\n\ndef _otype_payload', 'RELEASE_COMMIT = "d" * 40' + HELPER + '\n\n\ndef _otype_payload')
replace_once(path, '''def _otype_payload(extra_metadata: dict[str, str] | None = None) -> bytes:\n    metadata = {\n        "contentLicense": "CC-BY-4.0",\n        "contentLicenseStatus": "verified",\n        "converterSoftwareLicense": "MIT",\n        "converterVersion": "0.1.0",\n        "sourceIdentityStatus": "verified",\n        "upstreamCommit": UPSTREAM_COMMIT,\n        "upstreamRepository": UPSTREAM_REPOSITORY,\n        "upstreamSoftwareLicense": "GPL-3.0",\n        "valueType": "str",\n        "version": "0.1",\n        **(extra_metadata or {}),\n    }\n    lines = ["@node", *(f"@{key}={value}" for key, value in sorted(metadata.items())), ""]\n    return ("\\n".join(lines) + "\\n1\\tword\\n").encode("utf-8")\n''', '''def _otype_payload(extra_metadata: dict[str, str] | None = None) -> bytes:\n    metadata = {**_canonical_generic(), **(extra_metadata or {})}\n    metadata.update({"valueType": "str", "version": "0.1"})\n    lines = ["@node", *(f"@{key}={value}" for key, value in sorted(metadata.items())), ""]\n    return ("\\n".join(lines) + "\\n1\\tword\\n").encode("utf-8")\n''')
replace_once(path, '''    extra_report_provenance: dict[str, str] | None = None,\n):\n''', '''    extra_report_provenance: dict[str, str] | None = None,\n    omit_report_provenance: tuple[str, ...] = (),\n):\n''')
replace_once(path, '''        "provenance": {\n            "upstream_repository": UPSTREAM_REPOSITORY,\n            "upstream_commit": UPSTREAM_COMMIT,\n            "converter_version": "0.1.0",\n            "source_identity_status": "verified",\n            "content_license_status": "verified",\n            "content_license": "CC-BY-4.0",\n            "converter_software_license": "MIT",\n            "upstream_software_license": "GPL-3.0",\n            **(extra_report_provenance or {}),\n        },\n    }\n''', '''        "provenance": {\n            **report_provenance(_canonical_generic()),\n            **(extra_report_provenance or {}),\n        },\n    }\n    for key in omit_report_provenance:\n        report["provenance"].pop(key, None)\n''')
replace_once(path, '''        _build_candidate(\n            tmp_path,\n            extra_serialized_metadata={\n                "contentLicenseUrl": "https://creativecommons.org/licenses/by/4.0/"\n            },\n        )\n''', '''        _build_candidate(\n            tmp_path,\n            extra_serialized_metadata={\n                "contentLicenseUrl": "https://creativecommons.org/licenses/by/4.0/"\n            },\n            omit_report_provenance=("content_license_url",),\n        )\n''')

# Staging fixture.
path = "tests/test_distribution_staging.py"
replace_once(path, ')\n\n\nUPSTREAM_REPOSITORY =', ')\n' + CANONICAL_IMPORT + '\nUPSTREAM_REPOSITORY =')
replace_once(path, 'RELEASE_COMMIT = "b" * 40\n\n\ndef _materialized', 'RELEASE_COMMIT = "b" * 40' + HELPER + '\n\n\ndef _materialized')
old_otype = '    (source / "otype.tf").write_bytes(b\'@node\\n@contentLicense=CC-BY-4.0\\n@contentLicenseStatus=verified\\n@converterSoftwareLicense=MIT\\n@converterVersion=0.1.0\\n@sourceIdentityStatus=verified\\n@upstreamCommit=c939dcbacad78c5d18d2c4282cad23c47e19ac07\\n@upstreamRepository=https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha\\n@upstreamSoftwareLicense=GPL-3.0\\n@valueType=str\\n@version=0.1\\n\\n1\\tword\\n\')'
replace_once(path, old_otype, '    (source / "otype.tf").write_bytes(_canonical_otype_payload())')
replace_once(path, '''                "provenance": {\n                    "upstream_repository": UPSTREAM_REPOSITORY,\n                    "upstream_commit": UPSTREAM_COMMIT,\n                    "converter_version": "0.1.0",\n                    "source_identity_status": "verified",\n                    "content_license_status": "verified",\n                    "content_license": "CC-BY-4.0",\n                    "converter_software_license": "MIT",\n                    "upstream_software_license": "GPL-3.0",\n                },\n''', '                "provenance": report_provenance(_canonical_generic()),\n')
