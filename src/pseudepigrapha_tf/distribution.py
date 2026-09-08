from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from tempfile import mkdtemp
from typing import Any, Mapping
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile


SCHEMA_VERSION = 1
REPORT_NAME = "conversion-report.json"
MANIFEST_NAME = "dataset-manifest.json"


class DistributionContractError(ValueError):
    """Raised when a canonical corpus distribution fails closed validation."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_record(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "name": path.name,
        "bytes": len(payload),
        "sha256": _sha256_bytes(payload),
    }


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DistributionContractError(f"{label} must be a JSON object")
    return value


def _require_nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DistributionContractError(f"{label} must be a non-empty string")
    return value


def _load_report(path: Path) -> dict[str, Any]:
    if path.name != REPORT_NAME:
        raise DistributionContractError(
            f"report filename must be {REPORT_NAME!r}, got {path.name!r}"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DistributionContractError(f"invalid conversion report: {exc}") from exc
    return dict(_require_mapping(value, "conversion report"))


def _validate_report_audit(report: Mapping[str, Any]) -> None:
    """Require the report's success marker to agree with its semantic evidence."""

    if report.get("status") != "ok":
        raise DistributionContractError(
            f"conversion report status must be 'ok', got {report.get('status')!r}"
        )

    failed_checks = report.get("failed_checks")
    if not isinstance(failed_checks, list):
        raise DistributionContractError("report failed_checks must be a JSON array")
    if failed_checks:
        raise DistributionContractError(
            f"report failed_checks must be empty for publication, got {failed_checks!r}"
        )

    semantic_checks = _require_mapping(report.get("semantic_checks"), "report semantic_checks")
    if not semantic_checks:
        raise DistributionContractError("report semantic_checks must be non-empty")
    failed_semantic = sorted(
        str(name) for name, value in semantic_checks.items() if value is not True
    )
    if failed_semantic:
        raise DistributionContractError(
            "report semantic_checks must all be exactly true; failed: "
            + ", ".join(failed_semantic)
        )


def _report_identity(report: Mapping[str, Any], *, converter_version: str) -> dict[str, Any]:
    _validate_report_audit(report)

    provenance = _require_mapping(report.get("provenance"), "report provenance")
    if provenance.get("source_identity_status") != "verified":
        raise DistributionContractError(
            "report source identity status must be 'verified'"
        )
    if provenance.get("content_license_status") != "verified":
        raise DistributionContractError(
            "report content license status must be 'verified'"
        )

    report_converter = _require_nonempty_string(
        provenance.get("converter_version"), "report converter version"
    )
    if report_converter != converter_version:
        raise DistributionContractError(
            f"converter version mismatch: report has {report_converter!r}, publication has {converter_version!r}"
        )

    upstream_repository = _require_nonempty_string(
        provenance.get("upstream_repository"), "report upstream repository"
    )
    upstream_commit = _require_nonempty_string(
        provenance.get("upstream_commit"), "report upstream commit"
    )

    required_provenance = (
        "source_identity_status",
        "content_license_status",
        "content_license",
        "converter_software_license",
        "upstream_software_license",
    )
    manifest_provenance: dict[str, str] = {}
    for key in required_provenance:
        manifest_provenance[key] = _require_nonempty_string(
            provenance.get(key), f"report provenance {key}"
        )

    # Keep additional immutable provenance evidence when the report exposes it,
    # but never accept these values separately from the publication caller.
    for key in ("upstream_license_commit", "content_license_source"):
        value = provenance.get(key)
        if value is not None:
            manifest_provenance[key] = _require_nonempty_string(
                value, f"report provenance {key}"
            )

    return {
        "upstream_repository": upstream_repository,
        "upstream_commit": upstream_commit,
        "provenance": manifest_provenance,
    }


def _feature_records(archive: Path) -> list[dict[str, Any]]:
    try:
        with ZipFile(archive) as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            if not infos:
                raise DistributionContractError("TF archive contains no feature files")
            if len(set(names)) != len(names):
                raise DistributionContractError("TF archive contains duplicate feature filenames")

            records: list[dict[str, Any]] = []
            for info in infos:
                name = info.filename
                if info.is_dir() or "/" in name or "\\" in name or not name.endswith(".tf"):
                    raise DistributionContractError(
                        f"TF archive contains non-feature or non-top-level entry {name!r}"
                    )
                payload = zf.read(info)
                records.append(
                    {
                        "name": name,
                        "bytes": len(payload),
                        "sha256": _sha256_bytes(payload),
                    }
                )
    except DistributionContractError:
        raise
    except (OSError, BadZipFile, RuntimeError) as exc:
        raise DistributionContractError(f"invalid TF archive: {exc}") from exc

    return sorted(records, key=lambda item: item["name"])


def _directory_feature_records(directory: Path) -> list[dict[str, Any]]:
    if not directory.is_dir():
        raise DistributionContractError(f"missing extracted TF directory: {directory}")

    nested = [
        path
        for path in directory.rglob("*.tf")
        if path.parent != directory
    ]
    if nested:
        raise DistributionContractError(
            "extracted TF directory contains nested feature files: "
            + ", ".join(str(path.relative_to(directory)) for path in sorted(nested))
        )

    features = sorted(path for path in directory.glob("*.tf") if path.is_file())
    if not features:
        raise DistributionContractError("extracted TF directory contains no feature files")
    if any(path.is_symlink() for path in features):
        raise DistributionContractError("extracted TF directory contains symlinked feature files")

    try:
        return [_file_record(path) for path in features]
    except OSError as exc:
        raise DistributionContractError(f"could not read extracted TF feature: {exc}") from exc


def _feature_set_sha256(records: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(payload)


def canonical_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    """Serialize a schema-v1 manifest deterministically for release publication."""

    return (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def build_distribution_manifest(
    tf_archive: str | Path,
    report_path: str | Path,
    *,
    release_tag: str,
    release_commit: str,
    converter_version: str,
    data_version: str,
) -> dict[str, Any]:
    """Build a deterministic manifest binding one native TF archive to its report."""

    archive = Path(tf_archive)
    report_file = Path(report_path)
    release_tag = _require_nonempty_string(release_tag, "release tag")
    release_commit = _require_nonempty_string(release_commit, "release commit")
    converter_version = _require_nonempty_string(converter_version, "converter version")
    data_version = _require_nonempty_string(data_version, "Text-Fabric data version")

    expected_archive_name = f"tf-{data_version}.zip"
    if archive.name != expected_archive_name:
        raise DistributionContractError(
            f"TF archive filename must be {expected_archive_name!r}, got {archive.name!r}"
        )
    if not archive.is_file():
        raise DistributionContractError(f"missing TF archive: {archive}")
    if not report_file.is_file():
        raise DistributionContractError(f"missing conversion report: {report_file}")

    report = _load_report(report_file)
    identity = _report_identity(report, converter_version=converter_version)
    features = _feature_records(archive)

    return {
        "schema_version": SCHEMA_VERSION,
        "release": {
            "tag": release_tag,
            "commit": release_commit,
        },
        "converter": {"version": converter_version},
        "text_fabric": {
            "data_version": data_version,
            "feature_count": len(features),
            "features": features,
            "feature_set_sha256": _feature_set_sha256(features),
        },
        "upstream": {
            "repository": identity["upstream_repository"],
            "commit": identity["upstream_commit"],
        },
        "assets": {
            "tf": _file_record(archive),
            "report": _file_record(report_file),
        },
        "audit": {"status": report["status"]},
        "provenance": identity["provenance"],
    }


def _manifest_publication_identity(manifest: Mapping[str, Any]) -> tuple[str, str, str, str]:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise DistributionContractError(
            f"unsupported manifest schema version {manifest.get('schema_version')!r}"
        )
    release = _require_mapping(manifest.get("release"), "manifest release")
    converter = _require_mapping(manifest.get("converter"), "manifest converter")
    text_fabric = _require_mapping(manifest.get("text_fabric"), "manifest text_fabric")
    return (
        _require_nonempty_string(release.get("tag"), "manifest release tag"),
        _require_nonempty_string(release.get("commit"), "manifest release commit"),
        _require_nonempty_string(converter.get("version"), "manifest converter version"),
        _require_nonempty_string(text_fabric.get("data_version"), "manifest data version"),
    )


def _manifest_feature_records(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    text_fabric = _require_mapping(manifest.get("text_fabric"), "manifest text_fabric")
    raw_records = text_fabric.get("features")
    if not isinstance(raw_records, list) or not raw_records:
        raise DistributionContractError("manifest text_fabric features must be a non-empty JSON array")

    records: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, raw in enumerate(raw_records):
        record = _require_mapping(raw, f"manifest feature record {index}")
        name = _require_nonempty_string(record.get("name"), f"manifest feature record {index} name")
        if "/" in name or "\\" in name or not name.endswith(".tf"):
            raise DistributionContractError(f"manifest feature name is not a top-level .tf file: {name!r}")
        if name in names:
            raise DistributionContractError(f"manifest contains duplicate feature record {name!r}")
        names.add(name)

        byte_count = record.get("bytes")
        if type(byte_count) is not int or byte_count < 0:
            raise DistributionContractError(f"manifest feature {name!r} has invalid byte size")
        sha256 = record.get("sha256")
        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or any(char not in "0123456789abcdef" for char in sha256)
        ):
            raise DistributionContractError(f"manifest feature {name!r} has invalid sha256")
        records.append({"name": name, "bytes": byte_count, "sha256": sha256})

    if records != sorted(records, key=lambda item: item["name"]):
        raise DistributionContractError("manifest feature records are not canonically sorted")
    if text_fabric.get("feature_count") != len(records):
        raise DistributionContractError("manifest feature count does not match feature records")
    if text_fabric.get("feature_set_sha256") != _feature_set_sha256(records):
        raise DistributionContractError("manifest feature-set sha256 does not match feature records")
    return records


def validate_feature_directory(
    manifest: Mapping[str, Any],
    tf_directory: str | Path,
) -> None:
    """Fail closed unless extracted top-level .tf bytes match the manifest exactly."""

    manifest = _require_mapping(manifest, "dataset manifest")
    _manifest_publication_identity(manifest)
    expected = _manifest_feature_records(manifest)
    actual = _directory_feature_records(Path(tf_directory))
    if actual != expected:
        raise DistributionContractError(
            "extracted Text-Fabric feature set does not match dataset manifest"
        )


def validate_distribution(
    manifest: Mapping[str, Any],
    tf_archive: str | Path,
    report_path: str | Path,
    *,
    expected_release_tag: str | None = None,
    expected_release_commit: str | None = None,
    expected_converter_version: str | None = None,
    expected_data_version: str | None = None,
) -> None:
    """Fail closed unless archive, report and manifest form one exact release unit."""

    manifest = _require_mapping(manifest, "dataset manifest")
    release_tag, release_commit, converter_version, data_version = _manifest_publication_identity(manifest)

    if expected_release_tag is not None and release_tag != expected_release_tag:
        raise DistributionContractError(
            f"release tag mismatch: manifest has {release_tag!r}, expected {expected_release_tag!r}"
        )
    if expected_release_commit is not None and release_commit != expected_release_commit:
        raise DistributionContractError(
            f"release commit mismatch: manifest has {release_commit!r}, expected {expected_release_commit!r}"
        )
    if expected_converter_version is not None and converter_version != expected_converter_version:
        raise DistributionContractError(
            f"converter version mismatch: manifest has {converter_version!r}, expected {expected_converter_version!r}"
        )
    if expected_data_version is not None and data_version != expected_data_version:
        raise DistributionContractError(
            f"data version mismatch: manifest has {data_version!r}, expected {expected_data_version!r}"
        )

    archive = Path(tf_archive)
    report_file = Path(report_path)
    rebuilt = build_distribution_manifest(
        archive,
        report_file,
        release_tag=release_tag,
        release_commit=release_commit,
        converter_version=converter_version,
        data_version=data_version,
    )

    # Compare the manifest structurally after all referenced bytes and report
    # provenance have been re-derived. This catches asset, feature-set, upstream,
    # audit, and license/provenance tampering without trusting duplicated fields.
    if dict(manifest) != rebuilt:
        upstream = _require_mapping(manifest.get("upstream"), "manifest upstream")
        if upstream.get("repository") != rebuilt["upstream"]["repository"]:
            raise DistributionContractError("upstream repository mismatch between manifest and report")
        if upstream.get("commit") != rebuilt["upstream"]["commit"]:
            raise DistributionContractError("upstream commit mismatch between manifest and report")

        assets = _require_mapping(manifest.get("assets"), "manifest assets")
        tf_asset = _require_mapping(assets.get("tf"), "manifest TF asset")
        report_asset = _require_mapping(assets.get("report"), "manifest report asset")
        if tf_asset.get("name") != rebuilt["assets"]["tf"]["name"]:
            raise DistributionContractError("TF archive filename mismatch")
        if tf_asset.get("sha256") != rebuilt["assets"]["tf"]["sha256"]:
            raise DistributionContractError("TF archive sha256 mismatch")
        if tf_asset.get("bytes") != rebuilt["assets"]["tf"]["bytes"]:
            raise DistributionContractError("TF archive byte-size mismatch")
        if report_asset.get("name") != rebuilt["assets"]["report"]["name"]:
            raise DistributionContractError("report filename mismatch")
        if report_asset.get("sha256") != rebuilt["assets"]["report"]["sha256"]:
            raise DistributionContractError("report sha256 mismatch")
        if report_asset.get("bytes") != rebuilt["assets"]["report"]["bytes"]:
            raise DistributionContractError("report byte-size mismatch")

        text_fabric = _require_mapping(manifest.get("text_fabric"), "manifest text_fabric")
        if text_fabric.get("features") != rebuilt["text_fabric"]["features"]:
            raise DistributionContractError("Text-Fabric feature records mismatch")
        if text_fabric.get("feature_set_sha256") != rebuilt["text_fabric"]["feature_set_sha256"]:
            raise DistributionContractError("Text-Fabric feature-set sha256 mismatch")

        raise DistributionContractError(
            "dataset manifest does not match archive/report-derived release identity"
        )


def stage_distribution_assets(
    tf_directory: str | Path,
    destination: str | Path,
    *,
    release_tag: str,
    release_commit: str,
    converter_version: str,
    data_version: str,
) -> dict[str, Path]:
    """Atomically stage the native TF archive, report and validated manifest."""

    source = Path(tf_directory)
    destination = Path(destination)
    if not source.is_dir():
        raise DistributionContractError(f"missing materialized TF directory: {source}")
    if destination.exists():
        raise DistributionContractError(
            f"release destination already exists; refusing to mix generations: {destination}"
        )

    report_source = source / REPORT_NAME
    if not report_source.is_file():
        raise DistributionContractError(f"missing conversion report: {report_source}")

    # Reject an invalid report before creating release-visible output. This is
    # intentionally the same provenance gate used by manifest construction.
    report = _load_report(report_source)
    _report_identity(report, converter_version=converter_version)

    features = sorted(path for path in source.glob("*.tf") if path.is_file())
    if not features:
        raise DistributionContractError("materialized TF directory contains no feature files")

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        mkdtemp(
            prefix=".pseudepigrapha-tf-release-",
            dir=str(destination.parent),
        )
    )
    archive = stage / f"tf-{data_version}.zip"
    staged_report = stage / REPORT_NAME
    staged_manifest = stage / MANIFEST_NAME

    try:
        # Text-Fabric 13.1 tf-zip writes sorted top-level .tf files with
        # ZIP_DEFLATED and excludes non-feature files such as the report.
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
            for feature in features:
                zf.write(feature, arcname=feature.name)
        shutil.copyfile(report_source, staged_report)

        manifest = build_distribution_manifest(
            archive,
            staged_report,
            release_tag=release_tag,
            release_commit=release_commit,
            converter_version=converter_version,
            data_version=data_version,
        )
        staged_manifest.write_bytes(canonical_manifest_bytes(manifest))
        validate_distribution(
            manifest,
            archive,
            staged_report,
            expected_release_tag=release_tag,
            expected_release_commit=release_commit,
            expected_converter_version=converter_version,
            expected_data_version=data_version,
        )

        os.replace(stage, destination)
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise

    return {
        "tf": destination / archive.name,
        "report": destination / REPORT_NAME,
        "manifest": destination / MANIFEST_NAME,
    }
