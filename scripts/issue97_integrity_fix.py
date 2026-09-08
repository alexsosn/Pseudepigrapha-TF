from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one target, found {text.count(old)}")
    return text.replace(old, new, 1)


def patch_distribution() -> None:
    path = ROOT / "src" / "pseudepigrapha_tf" / "distribution.py"
    text = path.read_text(encoding="utf-8")

    old = '''def _require_nonempty_string(value: object, label: str) -> str:\n    if not isinstance(value, str) or not value.strip():\n        raise DistributionContractError(f"{label} must be a non-empty string")\n    return value\n\n\n'''
    new = old + '''def _require_git_sha(value: object, label: str) -> str:\n    value = _require_nonempty_string(value, label)\n    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):\n        raise DistributionContractError(\n            f"{label} must be a 40-character lowercase hexadecimal Git SHA"\n        )\n    return value\n\n\n'''
    text = replace_once(text, old, new, "git sha helper")

    old = '''    upstream_commit = _require_nonempty_string(\n        provenance.get("upstream_commit"), "report upstream commit"\n    )\n'''
    new = '''    upstream_commit = _require_git_sha(\n        provenance.get("upstream_commit"), "report upstream commit"\n    )\n'''
    text = replace_once(text, old, new, "upstream sha")

    old = '''def _feature_set_sha256(records: list[dict[str, Any]]) -> str:\n    payload = json.dumps(\n        records,\n        ensure_ascii=False,\n        sort_keys=True,\n        separators=(",", ":"),\n    ).encode("utf-8")\n    return _sha256_bytes(payload)\n\n\n'''
    new = old + '''def _feature_identity(records: list[dict[str, Any]]) -> dict[str, Any]:\n    return {\n        "feature_count": len(records),\n        "features": records,\n        "feature_set_sha256": _feature_set_sha256(records),\n    }\n\n\ndef feature_directory_identity(directory: str | Path) -> dict[str, Any]:\n    """Return normalized identity for one materialized top-level TF feature set."""\n\n    return _feature_identity(_directory_feature_records(Path(directory)))\n\n\ndef _report_feature_identity(report: Mapping[str, Any]) -> dict[str, Any]:\n    raw = _require_mapping(report.get("text_fabric"), "report Text-Fabric feature identity")\n    raw_features = raw.get("features")\n    if not isinstance(raw_features, list) or not raw_features:\n        raise DistributionContractError(\n            "report Text-Fabric feature identity must contain a non-empty features array"\n        )\n    records: list[dict[str, Any]] = []\n    names: set[str] = set()\n    for index, item in enumerate(raw_features):\n        record = _require_mapping(item, f"report feature record {index}")\n        name = _require_nonempty_string(record.get("name"), f"report feature record {index} name")\n        if "/" in name or "\\\\" in name or not name.endswith(".tf") or name in names:\n            raise DistributionContractError(f"report feature record has invalid name {name!r}")\n        names.add(name)\n        byte_count = record.get("bytes")\n        sha256 = record.get("sha256")\n        if type(byte_count) is not int or byte_count < 0:\n            raise DistributionContractError(f"report feature {name!r} has invalid byte size")\n        if (\n            not isinstance(sha256, str)\n            or len(sha256) != 64\n            or any(char not in "0123456789abcdef" for char in sha256)\n        ):\n            raise DistributionContractError(f"report feature {name!r} has invalid sha256")\n        records.append({"name": name, "bytes": byte_count, "sha256": sha256})\n    if records != sorted(records, key=lambda item: item["name"]):\n        raise DistributionContractError("report feature records are not canonically sorted")\n    identity = _feature_identity(records)\n    if raw.get("feature_count") != identity["feature_count"]:\n        raise DistributionContractError("report feature count does not match feature records")\n    if raw.get("feature_set_sha256") != identity["feature_set_sha256"]:\n        raise DistributionContractError("report feature-set sha256 does not match feature records")\n    return identity\n\n\n'''
    text = replace_once(text, old, new, "feature identity helpers")

    old = '''    release_commit = _require_nonempty_string(release_commit, "release commit")\n'''
    new = '''    release_commit = _require_git_sha(release_commit, "release commit")\n'''
    text = replace_once(text, old, new, "release sha builder")

    old = '''    report = _load_report(report_file)\n    identity = _report_identity(report, converter_version=converter_version)\n    features = _feature_records(archive)\n\n    return {\n'''
    new = '''    report = _load_report(report_file)\n    identity = _report_identity(report, converter_version=converter_version)\n    features = _feature_records(archive)\n    feature_identity = _feature_identity(features)\n    report_feature_identity = _report_feature_identity(report)\n    if report_feature_identity != feature_identity:\n        raise DistributionContractError(\n            "report Text-Fabric feature identity does not match serialized feature bytes"\n        )\n\n    return {\n'''
    text = replace_once(text, old, new, "report feature binding")

    old = '''        "text_fabric": {\n            "data_version": data_version,\n            "feature_count": len(features),\n            "features": features,\n            "feature_set_sha256": _feature_set_sha256(features),\n        },\n'''
    new = '''        "text_fabric": {\n            "data_version": data_version,\n            **feature_identity,\n        },\n'''
    text = replace_once(text, old, new, "manifest feature identity")

    old = '''        _require_nonempty_string(release.get("commit"), "manifest release commit"),\n'''
    new = '''        _require_git_sha(release.get("commit"), "manifest release commit"),\n'''
    text = replace_once(text, old, new, "manifest release sha")

    old = '''    # Reject an invalid report before creating release-visible output. This is\n    # intentionally the same provenance gate used by manifest construction.\n    report = _load_report(report_source)\n    _report_identity(report, converter_version=converter_version)\n\n    features = sorted(path for path in source.glob("*.tf") if path.is_file())\n    if not features:\n        raise DistributionContractError("materialized TF directory contains no feature files")\n\n'''
    new = '''    # Reject an invalid report and unsafe materialized feature layout before\n    # creating release-visible output. The same normalized feature set is used\n    # for report binding, archive construction, and extracted verification.\n    report = _load_report(report_source)\n    _report_identity(report, converter_version=converter_version)\n    source_records = _directory_feature_records(source)\n    source_identity = _feature_identity(source_records)\n    if _report_feature_identity(report) != source_identity:\n        raise DistributionContractError(\n            "report Text-Fabric feature identity does not match materialized feature bytes"\n        )\n    features = [source / record["name"] for record in source_records]\n\n'''
    text = replace_once(text, old, new, "staging preflight")

    path.write_text(text, encoding="utf-8")


def patch_cli() -> None:
    path = ROOT / "src" / "pseudepigrapha_tf" / "cli.py"
    text = path.read_text(encoding="utf-8")
    old = '''from .conversion import build_tf_data\n'''
    new = old + '''from .distribution import feature_directory_identity\n'''
    text = replace_once(text, old, new, "cli distribution import")

    old = '''        if not _write_prevalidated_tf(data, args.output):\n            raise SystemExit("Text-Fabric refused the generated dataset")\n        stage_started = _stage("write_text_fabric", stage_started)\n        staged_report.replace(publication_path)\n'''
    new = '''        if not _write_prevalidated_tf(data, args.output):\n            raise SystemExit("Text-Fabric refused the generated dataset")\n        stage_started = _stage("write_text_fabric", stage_started)\n        report["text_fabric"] = feature_directory_identity(args.output)\n        write_conversion_report(report, staged_report)\n        staged_report.replace(publication_path)\n'''
    text = replace_once(text, old, new, "cli report binding")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_distribution()
    patch_cli()
