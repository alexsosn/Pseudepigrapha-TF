from pathlib import Path


path = Path("src/pseudepigrapha_tf/distribution.py")
text = path.read_text(encoding="utf-8")
old = '''    for report_key, expected_value in expected_provenance.items():
        label = report_key.replace("_", " ")
        actual = serialized_provenance.get(report_key)
        if actual is None:
            raise DistributionContractError(
                f"serialized Text-Fabric identity is missing {label} metadata"
            )
        if actual != expected_value:
            raise DistributionContractError(
                f"serialized Text-Fabric {label} mismatch: {actual!r} != {expected_value!r}"
            )

    actual_data_version = metadata.get("version")
'''
new = '''    for report_key, expected_value in expected_provenance.items():
        label = report_key.replace("_", " ")
        actual = serialized_provenance.get(report_key)
        if actual is None:
            raise DistributionContractError(
                f"serialized Text-Fabric identity is missing {label} metadata"
            )
        if actual != expected_value:
            raise DistributionContractError(
                f"serialized Text-Fabric {label} mismatch: {actual!r} != {expected_value!r}"
            )

    unexpected_provenance = sorted(
        set(serialized_provenance) - set(expected_provenance)
    )
    if unexpected_provenance:
        raise DistributionContractError(
            "serialized Text-Fabric identity contains provenance absent from the "
            "conversion report: " + ", ".join(unexpected_provenance)
        )

    actual_data_version = metadata.get("version")
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected one serialized-provenance validation block, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
