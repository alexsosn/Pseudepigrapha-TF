from pathlib import Path

path = Path("src/pseudepigrapha_tf/distribution.py")
text = path.read_text(encoding="utf-8")

old_import = "from .provenance import REPORT_PROVENANCE_FIELDS, report_provenance\n"
new_import = """from .provenance import (\n    REPORT_PROVENANCE_FIELDS,\n    corpus_license_provenance_is_consistent,\n    report_provenance,\n)\n"""
if text.count(old_import) != 1:
    raise SystemExit("expected exactly one provenance import")
text = text.replace(old_import, new_import, 1)

needle = """    serialized_provenance: dict[str, str] = {}\n    for _serialized_key, report_key in REPORT_PROVENANCE_FIELDS:\n        value = provenance.get(report_key)\n        if value is not None:\n            serialized_provenance[report_key] = _require_nonempty_string(\n                value, f\"report provenance {report_key}\"\n            )\n\n    return {\n"""
replacement = """    serialized_provenance: dict[str, str] = {}\n    for _serialized_key, report_key in REPORT_PROVENANCE_FIELDS:\n        value = provenance.get(report_key)\n        if value is not None:\n            serialized_provenance[report_key] = _require_nonempty_string(\n                value, f\"report provenance {report_key}\"\n            )\n\n    generic_provenance = {\n        serialized_key: serialized_provenance[report_key]\n        for serialized_key, report_key in REPORT_PROVENANCE_FIELDS\n        if report_key in serialized_provenance\n    }\n    if not corpus_license_provenance_is_consistent(generic_provenance):\n        raise DistributionContractError(\n            \"report provenance does not match a canonical verified source/license profile\"\n        )\n\n    return {\n"""
if text.count(needle) != 1:
    raise SystemExit("expected exactly one serialized provenance block")
text = text.replace(needle, replacement, 1)
path.write_text(text, encoding="utf-8")
