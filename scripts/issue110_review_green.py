from pathlib import Path


path = Path("src/pseudepigrapha_tf/distribution.py")
text = path.read_text(encoding="utf-8")
old = '''    if provenance.get("content_license_status") != "verified":
        raise DistributionContractError(
            "report content license status must be 'verified'"
        )

    report_converter = _require_nonempty_string(
'''
new = '''    if provenance.get("content_license_status") != "verified":
        raise DistributionContractError(
            "report content license status must be 'verified'"
        )
    if "source_identity_diagnostic" in provenance:
        raise DistributionContractError(
            "verified report source identity must not carry a diagnostic"
        )
    if "content_license_diagnostic" in provenance:
        raise DistributionContractError(
            "verified report content license must not carry a diagnostic"
        )

    report_converter = _require_nonempty_string(
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected one verified-provenance validation block, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
