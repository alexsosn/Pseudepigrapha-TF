from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    assert count == 1, f"{path}: expected one replacement, found {count}"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Keep report parsing/equality and canonical profile authenticity as separate
# invariants. Representation mismatch diagnostics from #110 should win before
# #113 judges the now-agreed profile itself.
path = Path("src/pseudepigrapha_tf/distribution.py")
text = path.read_text(encoding="utf-8")
old = '''    generic_provenance = {
        serialized_key: serialized_provenance[report_key]
        for serialized_key, report_key in REPORT_PROVENANCE_FIELDS
        if report_key in serialized_provenance
    }
    if not corpus_license_provenance_is_consistent(generic_provenance):
        raise DistributionContractError(
            "report provenance does not match a canonical verified source/license profile"
        )

    return {
'''
new = '''    return {
'''
assert text.count(old) == 1, text.count(old)
text = text.replace(old, new, 1)
anchor = '''    return {
        "upstream_repository": upstream_repository,
        "upstream_commit": upstream_commit,
        "provenance": manifest_provenance,
        "serialized_provenance": serialized_provenance,
    }


def _feature_records'''
replacement = '''    return {
        "upstream_repository": upstream_repository,
        "upstream_commit": upstream_commit,
        "provenance": manifest_provenance,
        "serialized_provenance": serialized_provenance,
    }


def _validate_canonical_provenance_profile(identity: Mapping[str, Any]) -> None:
    """Require an agreed report/TF profile to be true for its source tuple."""

    serialized_provenance = _require_mapping(
        identity.get("serialized_provenance"), "report-derived serialized provenance"
    )
    generic_provenance = {
        serialized_key: serialized_provenance[report_key]
        for serialized_key, report_key in REPORT_PROVENANCE_FIELDS
        if report_key in serialized_provenance
    }
    if not corpus_license_provenance_is_consistent(generic_provenance):
        raise DistributionContractError(
            "report provenance does not match a canonical verified source/license profile"
        )


def _feature_records'''
assert text.count(anchor) == 1, text.count(anchor)
text = text.replace(anchor, replacement, 1)
call = '''    _validate_serialized_identity(
        archive,
        identity=identity,
        converter_version=converter_version,
        data_version=data_version,
    )
'''
assert text.count(call) == 1, text.count(call)
text = text.replace(call, call + "    _validate_canonical_provenance_profile(identity)\n", 1)
path.write_text(text, encoding="utf-8")

Path("tests/__init__.py").write_text("", encoding="utf-8")
Path("tests/distribution_test_support.py").write_text(
    '''from __future__ import annotations

from pseudepigrapha_tf.provenance import (
    OCP_PIN,
    OCP_REPOSITORY,
    corpus_license_metadata,
    report_provenance,
)

CONVERTER_VERSION = "0.1.0"
DATA_VERSION = "0.1"


def canonical_generic(*, overrides: dict[str, str] | None = None) -> dict[str, str]:
    generic = {
        "upstreamRepository": OCP_REPOSITORY,
        "upstreamCommit": OCP_PIN,
        "converterVersion": CONVERTER_VERSION,
        **corpus_license_metadata(
            OCP_REPOSITORY,
            OCP_PIN,
            source_identity_verified=True,
        ),
    }
    if overrides:
        generic.update(overrides)
    return generic


def canonical_report_provenance(*, overrides: dict[str, str] | None = None) -> dict[str, str]:
    provenance = report_provenance(canonical_generic())
    if overrides:
        provenance.update(overrides)
    return provenance


def canonical_otype_payload(
    *,
    generic_overrides: dict[str, str] | None = None,
    extra_metadata: dict[str, str] | None = None,
    data_version: str = DATA_VERSION,
) -> bytes:
    metadata = {
        **canonical_generic(overrides=generic_overrides),
        "valueType": "str",
        "version": data_version,
        **(extra_metadata or {}),
    }
    lines = ["@node", *(f"@{key}={value}" for key, value in sorted(metadata.items())), ""]
    return ("\\n".join(lines) + "\\n1\\tword\\n").encode("utf-8")
''',
    encoding="utf-8",
)

support_import = '''from tests.distribution_test_support import (
    canonical_otype_payload,
    canonical_report_provenance,
)
'''

# directory validation
p = "tests/test_distribution_directory_validation.py"
replace_once(p, ")\n\n\nUPSTREAM_REPOSITORY =", ")\n" + support_import + "\nUPSTREAM_REPOSITORY =")
text = Path(p).read_text(encoding="utf-8")
start = text.index("FEATURES = {")
end = text.index("\n}\n\n\ndef _fixture", start) + 2
text = text[:start] + '''FEATURES = {
    "book.tf": b"@node\\n1\\t1En__Ethiopic\\n",
    "otype.tf": canonical_otype_payload(),
    "oslots.tf": b"@edge\\n2\\t1\\n",
}''' + text[end:]
old_prov = '''                "provenance": {
                    "upstream_repository": UPSTREAM_REPOSITORY,
                    "upstream_commit": UPSTREAM_COMMIT,
                    "converter_version": "0.1.0",
                    "source_identity_status": "verified",
                    "content_license_status": "verified",
                    "content_license": "CC-BY-4.0",
                    "converter_software_license": "MIT",
                    "upstream_software_license": "GPL-3.0",
                },'''
assert text.count(old_prov) == 1
text = text.replace(old_prov, '                "provenance": canonical_report_provenance(),', 1)
Path(p).write_text(text, encoding="utf-8")

# feature-set tests
p = "tests/test_distribution_feature_set.py"
replace_once(p, "import pytest\n\n\nUPSTREAM_REPOSITORY", "import pytest\n\n" + support_import + "\nUPSTREAM_REPOSITORY")
text = Path(p).read_text(encoding="utf-8")
start = text.index("FEATURES = {")
end = text.index("\n}\n\n\ndef _distribution", start) + 2
text = text[:start] + '''FEATURES = {
    "book.tf": b"@node\\n1\\t1En__Ethiopic\\n",
    "otype.tf": canonical_otype_payload(),
}''' + text[end:]
assert text.count(old_prov) == 1
text = text.replace(old_prov, '                "provenance": canonical_report_provenance(),', 1)
Path(p).write_text(text, encoding="utf-8")

# manifest tests
p = "tests/test_distribution_manifest.py"
replace_once(p, ")\n\n\nUPSTREAM_REPOSITORY =", ")\n" + support_import + "\nUPSTREAM_REPOSITORY =")
text = Path(p).read_text(encoding="utf-8")
old = '''        "provenance": {
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": UPSTREAM_COMMIT,
            "converter_version": "0.1.0",
            "source_identity_status": source_status,
            "content_license_status": license_status,
            "content_license": "CC-BY-4.0",
            "converter_software_license": "MIT",
            "upstream_software_license": "GPL-3.0",
            "upstream_license_commit": "8c8c2c55a2c55ba4b23ac506956f98dcc25045b2",
            "content_license_source": f"{UPSTREAM_REPOSITORY}/blob/{UPSTREAM_COMMIT}/LICENSE.CC-BY-4.0",
        },'''
new = '''        "provenance": canonical_report_provenance(
            overrides={
                "source_identity_status": source_status,
                "content_license_status": license_status,
            }
        ),'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
old_line = '''        zf.writestr("otype.tf", '@node\\n@contentLicense=CC-BY-4.0\\n@contentLicenseSource=https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/LICENSE.CC-BY-4.0\\n@contentLicenseStatus=verified\\n@converterSoftwareLicense=MIT\\n@converterVersion=0.1.0\\n@sourceIdentityStatus=verified\\n@upstreamCommit=c939dcbacad78c5d18d2c4282cad23c47e19ac07\\n@upstreamLicenseCommit=8c8c2c55a2c55ba4b23ac506956f98dcc25045b2\\n@upstreamRepository=https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha\\n@upstreamSoftwareLicense=GPL-3.0\\n@valueType=str\\n@version=0.1\\n\\n1\\tword\\n')'''
assert text.count(old_line) == 1
text = text.replace(old_line, '        zf.writestr("otype.tf", canonical_otype_payload())', 1)
Path(p).write_text(text, encoding="utf-8")

# provenance-closure tests
p = "tests/test_distribution_provenance_closure.py"
replace_once(p, ")\n\n\nUPSTREAM_REPOSITORY =", ")\n" + support_import + "\nUPSTREAM_REPOSITORY =")
text = Path(p).read_text(encoding="utf-8")
start = text.index("def _otype_payload(")
end = text.index("\n\n\ndef _feature_identity", start)
text = text[:start] + '''def _otype_payload(extra_metadata: dict[str, str] | None = None) -> bytes:
    return canonical_otype_payload(extra_metadata=extra_metadata)
''' + text[end:]
old = '''        "provenance": {
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": UPSTREAM_COMMIT,
            "converter_version": "0.1.0",
            "source_identity_status": "verified",
            "content_license_status": "verified",
            "content_license": "CC-BY-4.0",
            "converter_software_license": "MIT",
            "upstream_software_license": "GPL-3.0",
            **(extra_report_provenance or {}),
        },'''
new = '''        "provenance": canonical_report_provenance(
            overrides=extra_report_provenance
        ),'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
Path(p).write_text(text, encoding="utf-8")

# report-feature binding tests
p = "tests/test_distribution_report_feature_binding.py"
replace_once(
    p,
    "from pseudepigrapha_tf.distribution import DistributionContractError, build_distribution_manifest\n",
    "from pseudepigrapha_tf.distribution import DistributionContractError, build_distribution_manifest\n"
    "from tests.distribution_test_support import canonical_report_provenance\n",
)
text = Path(p).read_text(encoding="utf-8")
old = '''        "provenance": {
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": UPSTREAM_COMMIT,
            "converter_version": "0.1.0",
            "source_identity_status": "verified",
            "content_license_status": "verified",
            "content_license": "CC-BY-4.0",
            "converter_software_license": "MIT",
            "upstream_software_license": "GPL-3.0",
        },'''
assert text.count(old) == 1
text = text.replace(old, '        "provenance": canonical_report_provenance(),', 1)
Path(p).write_text(text, encoding="utf-8")

# serialized-identity tests
p = "tests/test_distribution_serialized_identity.py"
replace_once(p, ")\n\n\nUPSTREAM_REPOSITORY =", ")\n" + support_import + "\nUPSTREAM_REPOSITORY =")
text = Path(p).read_text(encoding="utf-8")
start = text.index("def _otype_payload(")
end = text.index("\n\n\ndef _feature_identity", start)
text = text[:start] + '''def _otype_payload(
    *,
    upstream_repository: str = UPSTREAM_REPOSITORY,
    upstream_commit: str = UPSTREAM_COMMIT,
    converter_version: str = "0.1.0",
    data_version: str = "0.1",
    source_identity_status: str = "verified",
    content_license_status: str = "verified",
    content_license: str = "CC-BY-4.0",
    extra_metadata: dict[str, str] | None = None,
) -> bytes:
    return canonical_otype_payload(
        generic_overrides={
            "upstreamRepository": upstream_repository,
            "upstreamCommit": upstream_commit,
            "converterVersion": converter_version,
            "sourceIdentityStatus": source_identity_status,
            "contentLicenseStatus": content_license_status,
            "contentLicense": content_license,
        },
        extra_metadata=extra_metadata,
        data_version=data_version,
    )
''' + text[end:]
old = '''        "provenance": {
            "upstream_repository": upstream_repository,
            "upstream_commit": upstream_commit,
            "converter_version": converter_version,
            "source_identity_status": source_identity_status,
            "content_license_status": content_license_status,
            "content_license": content_license,
            "converter_software_license": "MIT",
            "upstream_software_license": "GPL-3.0",
            **(extra_provenance or {}),
        },'''
new = '''        "provenance": canonical_report_provenance(
            overrides={
                "upstream_repository": upstream_repository,
                "upstream_commit": upstream_commit,
                "converter_version": converter_version,
                "source_identity_status": source_identity_status,
                "content_license_status": content_license_status,
                "content_license": content_license,
                **(extra_provenance or {}),
            }
        ),'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
Path(p).write_text(text, encoding="utf-8")

# staging tests
p = "tests/test_distribution_staging.py"
replace_once(p, ")\n\n\nUPSTREAM_REPOSITORY =", ")\n" + support_import + "\nUPSTREAM_REPOSITORY =")
text = Path(p).read_text(encoding="utf-8")
old_line = '''    (source / "otype.tf").write_bytes(b'@node\\n@contentLicense=CC-BY-4.0\\n@contentLicenseStatus=verified\\n@converterSoftwareLicense=MIT\\n@converterVersion=0.1.0\\n@sourceIdentityStatus=verified\\n@upstreamCommit=c939dcbacad78c5d18d2c4282cad23c47e19ac07\\n@upstreamRepository=https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha\\n@upstreamSoftwareLicense=GPL-3.0\\n@valueType=str\\n@version=0.1\\n\\n1\\tword\\n')'''
assert text.count(old_line) == 1
text = text.replace(old_line, '    (source / "otype.tf").write_bytes(canonical_otype_payload())', 1)
assert text.count(old_prov) == 1
text = text.replace(old_prov, '                "provenance": canonical_report_provenance(),', 1)
Path(p).write_text(text, encoding="utf-8")

# TF metadata-binding tests
p = "tests/test_distribution_tf_metadata_binding.py"
replace_once(p, ")\n\n\nUPSTREAM_REPOSITORY =", ")\n" + support_import + "\nUPSTREAM_REPOSITORY =")
text = Path(p).read_text(encoding="utf-8")
start = text.index("def _otype(")
end = text.index("\n\n\ndef _fixture", start)
text = text[:start] + '''def _otype(
    *,
    upstream_commit: str = UPSTREAM_COMMIT,
    data_version: str = "0.1",
    converter_version: str = "0.1.0",
    content_license: str = "CC-BY-4.0",
) -> bytes:
    return canonical_otype_payload(
        generic_overrides={
            "upstreamCommit": upstream_commit,
            "converterVersion": converter_version,
            "contentLicense": content_license,
        },
        data_version=data_version,
    )
''' + text[end:]
old = '''                "provenance": {
                    "upstream_repository": UPSTREAM_REPOSITORY,
                    "upstream_commit": report_commit,
                    "converter_version": "0.1.0",
                    "source_identity_status": "verified",
                    "content_license_status": "verified",
                    "content_license": "CC-BY-4.0",
                    "converter_software_license": "MIT",
                    "upstream_software_license": "GPL-3.0",
                },'''
new = '''                "provenance": canonical_report_provenance(
                    overrides={"upstream_commit": report_commit}
                ),'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
Path(p).write_text(text, encoding="utf-8")

# Explicitly pin validation ordering in the #113 focused suite.
p = "tests/test_distribution_provenance_profile_authenticity.py"
text = Path(p).read_text(encoding="utf-8")
old = '''def _build_candidate(
    tmp_path: Path,
    generic: dict[str, str],
    *,
    extra_serialized_metadata: dict[str, str] | None = None,
):
'''
new = '''def _build_candidate(
    tmp_path: Path,
    generic: dict[str, str],
    *,
    report_generic: dict[str, str] | None = None,
    extra_serialized_metadata: dict[str, str] | None = None,
):
'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
old = '        "provenance": report_provenance(generic),\n'
assert text.count(old) == 1
text = text.replace(old, '        "provenance": report_provenance(report_generic or generic),\n', 1)
text += '''

def test_representation_mismatch_is_reported_before_profile_authenticity(tmp_path):
    serialized = _canonical_generic()
    report = dict(serialized)
    report["upstreamCommit"] = "f" * 40

    with pytest.raises(
        DistributionContractError,
        match="serialized Text-Fabric upstream commit mismatch",
    ):
        _build_candidate(tmp_path, serialized, report_generic=report)
'''
Path(p).write_text(text, encoding="utf-8")
