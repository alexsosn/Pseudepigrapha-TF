from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
from tempfile import mkdtemp
from typing import Any, Mapping
from zipfile import BadZipFile, ZipFile

from . import _distribution_native as _native
from ._distribution_native import *  # noqa: F401,F403 - preserve the established public surface


EXPRESS_NAME = "complete.zip"
DEFAULT_REPOSITORY_OWNER = "alexsosn"
DEFAULT_REPOSITORY_NAME = "Pseudepigrapha-TF"
_EXPRESS_CHECKOUT_NAME = "__checkout__.txt"
_EXPRESS_EXCLUDE = {
    ".DS_Store",
    ".tf",
    "__pycache__",
    "_local",
    "_temp",
    ".ipynb_checkpoints",
}


def _require_repository_component(value: object, label: str) -> str:
    value = _native._require_nonempty_string(value, label)
    if (
        value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or "\n" in value
        or "\r" in value
    ):
        raise DistributionContractError(f"{label} must be one safe path component")
    return value


def _checkout_marker(release_tag: str, release_commit: str) -> bytes:
    release_tag = _native._require_nonempty_string(release_tag, "release tag")
    if any(char in release_tag for char in ("\x00", "\n", "\r")):
        raise DistributionContractError("release tag cannot contain control line separators")
    release_commit = _native._require_git_sha(release_commit, "release commit")
    return f"{release_tag}\n{release_commit}\n".encode("utf-8")


def _safe_relative_parts(path: str, label: str) -> tuple[str, ...]:
    if not path or "\x00" in path or "\\" in path or path.startswith("/"):
        raise DistributionContractError(f"{label} contains an unsafe path {path!r}")
    parts = tuple(path.split("/"))
    if any(part in {"", ".", ".."} for part in parts):
        raise DistributionContractError(f"{label} contains path traversal or empty components: {path!r}")
    return parts


def _collect_app_payloads(app_directory: Path) -> dict[str, bytes]:
    if app_directory.is_symlink():
        raise DistributionContractError(f"Text-Fabric app directory must not be a symlink: {app_directory}")
    if not app_directory.is_dir():
        raise DistributionContractError(f"missing Text-Fabric app directory: {app_directory}")

    entries = list(app_directory.rglob("*"))
    symlinks = sorted(path for path in entries if path.is_symlink())
    if symlinks:
        raise DistributionContractError(
            "Text-Fabric app directory contains symlinked entries: "
            + ", ".join(str(path.relative_to(app_directory)) for path in symlinks)
        )

    payloads: dict[str, bytes] = {}
    try:
        for path in sorted(entries, key=lambda item: item.relative_to(app_directory).as_posix()):
            relative = path.relative_to(app_directory).as_posix()
            parts = _safe_relative_parts(relative, "Text-Fabric app entry")
            if any(part in _EXPRESS_EXCLUDE for part in parts):
                continue
            if path.is_dir():
                continue
            if not path.is_file():
                raise DistributionContractError(f"Text-Fabric app entry is not a regular file: {relative}")
            if relative == _EXPRESS_CHECKOUT_NAME:
                continue
            payloads[relative] = path.read_bytes()
    except OSError as exc:
        raise DistributionContractError(f"could not read Text-Fabric app files: {exc}") from exc

    if "config.yaml" not in payloads:
        raise DistributionContractError("Text-Fabric app directory is missing required config.yaml")
    return payloads


def _native_feature_payloads(tf_archive: Path) -> dict[str, bytes]:
    records = _native._feature_records(tf_archive)
    try:
        with ZipFile(tf_archive) as zf:
            return {record["name"]: zf.read(record["name"]) for record in records}
    except (OSError, BadZipFile, RuntimeError, KeyError) as exc:
        raise DistributionContractError(f"could not read native Text-Fabric feature bytes: {exc}") from exc


def _build_express_archive(
    express_archive: Path,
    native_archive: Path,
    app_directory: Path,
    *,
    release_tag: str,
    release_commit: str,
    data_version: str,
    repository_owner: str,
    repository_name: str,
) -> None:
    data_version = _native._require_data_version(data_version)
    repository_owner = _require_repository_component(repository_owner, "repository owner")
    repository_name = _require_repository_component(repository_name, "repository name")
    marker = _checkout_marker(release_tag, release_commit)
    app_payloads = _collect_app_payloads(app_directory)
    feature_payloads = _native_feature_payloads(native_archive)

    root = f"{repository_owner}/{repository_name}"
    app_root = f"{root}/app"
    data_root = f"{root}/tf/{data_version}"
    members: dict[str, bytes] = {
        f"{app_root}/{_EXPRESS_CHECKOUT_NAME}": marker,
        f"{data_root}/{_EXPRESS_CHECKOUT_NAME}": marker,
    }
    members.update({f"{app_root}/{name}": payload for name, payload in app_payloads.items()})
    members.update({f"{data_root}/{name}": payload for name, payload in feature_payloads.items()})

    try:
        with ZipFile(express_archive, "w") as zf:
            for name in sorted(members):
                zf.writestr(_native._canonical_zip_info(name), members[name])
    except (OSError, RuntimeError) as exc:
        raise DistributionContractError(f"could not build Text-Fabric express archive: {exc}") from exc


def _validate_express_member(info: Any) -> tuple[str, ...]:
    name = info.filename
    parts = _safe_relative_parts(name, "Text-Fabric express member")
    if info.is_dir():
        raise DistributionContractError(f"Text-Fabric express archive contains a directory member: {name!r}")
    if info.create_system == 3:
        mode = (info.external_attr >> 16) & 0xFFFF
        kind = stat.S_IFMT(mode)
        if stat.S_ISLNK(mode):
            raise DistributionContractError(f"Text-Fabric express archive contains a symlink member: {name!r}")
        if kind not in {0, stat.S_IFREG}:
            raise DistributionContractError(f"Text-Fabric express archive contains a special member: {name!r}")
    return parts


def _validate_express_archive(
    express_archive: str | Path,
    native_archive: str | Path,
    *,
    release_tag: str,
    release_commit: str,
    data_version: str,
    repository_owner: str,
    repository_name: str,
) -> dict[str, bytes]:
    express_archive = Path(express_archive)
    native_archive = Path(native_archive)
    if express_archive.name != EXPRESS_NAME:
        raise DistributionContractError(
            f"Text-Fabric express archive filename must be {EXPRESS_NAME!r}, got {express_archive.name!r}"
        )
    if not express_archive.is_file():
        raise DistributionContractError(f"missing Text-Fabric express archive: {express_archive}")

    data_version = _native._require_data_version(data_version)
    repository_owner = _require_repository_component(repository_owner, "repository owner")
    repository_name = _require_repository_component(repository_name, "repository name")
    marker = _checkout_marker(release_tag, release_commit)
    feature_payloads = _native_feature_payloads(native_archive)

    root = f"{repository_owner}/{repository_name}"
    app_prefix = f"{root}/app/"
    data_prefix = f"{root}/tf/{data_version}/"
    app_payloads: dict[str, bytes] = {}
    data_payloads: dict[str, bytes] = {}

    try:
        with ZipFile(express_archive) as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            if not infos:
                raise DistributionContractError("Text-Fabric express archive contains no members")
            if len(set(names)) != len(names):
                raise DistributionContractError("Text-Fabric express archive contains duplicate members")
            if names != sorted(names):
                raise DistributionContractError("Text-Fabric express archive members are not canonically sorted")

            for info in infos:
                _validate_express_member(info)
                name = info.filename
                payload = zf.read(info)
                if name.startswith(app_prefix):
                    relative = name[len(app_prefix):]
                    parts = _safe_relative_parts(relative, "Text-Fabric app member")
                    if any(part in _EXPRESS_EXCLUDE for part in parts):
                        raise DistributionContractError(
                            f"Text-Fabric express archive contains excluded app member {name!r}"
                        )
                    app_payloads[relative] = payload
                elif name.startswith(data_prefix):
                    relative = name[len(data_prefix):]
                    parts = _safe_relative_parts(relative, "Text-Fabric data member")
                    if len(parts) != 1:
                        raise DistributionContractError(
                            f"Text-Fabric express data member must be top-level within the version: {name!r}"
                        )
                    data_payloads[relative] = payload
                else:
                    raise DistributionContractError(
                        f"Text-Fabric express member is outside the expected repository roots: {name!r}"
                    )
    except DistributionContractError:
        raise
    except (OSError, BadZipFile, RuntimeError, KeyError) as exc:
        raise DistributionContractError(f"invalid Text-Fabric express archive: {exc}") from exc

    app_marker = app_payloads.pop(_EXPRESS_CHECKOUT_NAME, None)
    data_marker = data_payloads.pop(_EXPRESS_CHECKOUT_NAME, None)
    if app_marker is None or data_marker is None:
        raise DistributionContractError("Text-Fabric express archive is missing required checkout marker")
    if app_marker != marker or data_marker != marker:
        raise DistributionContractError("Text-Fabric express checkout marker does not match release tag/commit")
    if "config.yaml" not in app_payloads:
        raise DistributionContractError("Text-Fabric express app is missing config.yaml")

    if set(data_payloads) != set(feature_payloads):
        missing = sorted(set(feature_payloads) - set(data_payloads))
        extra = sorted(set(data_payloads) - set(feature_payloads))
        raise DistributionContractError(
            f"Text-Fabric express feature member set differs from native archive; missing={missing}, extra={extra}"
        )
    for name, native_payload in feature_payloads.items():
        if data_payloads[name] != native_payload:
            raise DistributionContractError(
                f"Text-Fabric express feature {name!r} differs from native archive bytes"
            )
    return app_payloads


def _validate_express_app_identity(
    app_payloads: Mapping[str, bytes],
    app_directory: str | Path,
) -> None:
    expected = _collect_app_payloads(Path(app_directory))
    actual_names = set(app_payloads)
    expected_names = set(expected)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise DistributionContractError(
            "Text-Fabric express app member set differs from exact app directory; "
            f"missing={missing}, extra={extra}"
        )
    for name, expected_payload in expected.items():
        if app_payloads[name] != expected_payload:
            raise DistributionContractError(
                f"Text-Fabric express app payload {name!r} differs from exact app directory"
            )


def build_distribution_manifest(
    tf_archive: str | Path,
    report_path: str | Path,
    *,
    release_tag: str,
    release_commit: str,
    converter_version: str,
    data_version: str,
    express_archive: str | Path | None = None,
    app_directory: str | Path | None = None,
    repository_owner: str = DEFAULT_REPOSITORY_OWNER,
    repository_name: str = DEFAULT_REPOSITORY_NAME,
) -> dict[str, Any]:
    """Build the native manifest and bind optional express bytes to exact app identity."""

    manifest = _native.build_distribution_manifest(
        tf_archive,
        report_path,
        release_tag=release_tag,
        release_commit=release_commit,
        converter_version=converter_version,
        data_version=data_version,
    )
    if express_archive is not None:
        app_payloads = _validate_express_archive(
            express_archive,
            tf_archive,
            release_tag=release_tag,
            release_commit=release_commit,
            data_version=data_version,
            repository_owner=repository_owner,
            repository_name=repository_name,
        )
        if app_directory is None:
            raise DistributionContractError(
                "Text-Fabric express app manifest binding requires an exact app directory identity"
            )
        _validate_express_app_identity(app_payloads, app_directory)
        manifest["assets"]["express"] = _native._file_record(Path(express_archive))
    return manifest


def validate_distribution(
    manifest: Mapping[str, Any],
    tf_archive: str | Path,
    report_path: str | Path,
    *,
    express_archive: str | Path | None = None,
    app_directory: str | Path | None = None,
    repository_owner: str = DEFAULT_REPOSITORY_OWNER,
    repository_name: str = DEFAULT_REPOSITORY_NAME,
    expected_release_tag: str | None = None,
    expected_release_commit: str | None = None,
    expected_converter_version: str | None = None,
    expected_data_version: str | None = None,
) -> None:
    """Validate native closure plus complete.zip against its exact app checkout."""

    manifest = _native._require_mapping(manifest, "dataset manifest")
    release_tag, release_commit, converter_version, data_version = _native._manifest_publication_identity(manifest)
    assets = _native._require_mapping(manifest.get("assets"), "manifest assets")
    manifest_has_express = "express" in assets
    supplied_express = express_archive is not None
    if manifest_has_express != supplied_express:
        raise DistributionContractError(
            "dataset manifest and validation call disagree about Text-Fabric express transport"
        )

    native_manifest = dict(manifest)
    native_assets = dict(assets)
    native_assets.pop("express", None)
    native_manifest["assets"] = native_assets
    _native.validate_distribution(
        native_manifest,
        tf_archive,
        report_path,
        expected_release_tag=expected_release_tag,
        expected_release_commit=expected_release_commit,
        expected_converter_version=expected_converter_version,
        expected_data_version=expected_data_version,
    )

    if express_archive is None:
        return

    app_payloads = _validate_express_archive(
        express_archive,
        tf_archive,
        release_tag=release_tag,
        release_commit=release_commit,
        data_version=data_version,
        repository_owner=repository_owner,
        repository_name=repository_name,
    )
    if app_directory is None:
        raise DistributionContractError(
            "Text-Fabric express app validation requires an exact app directory identity"
        )
    _validate_express_app_identity(app_payloads, app_directory)

    actual = _native._file_record(Path(express_archive))
    expected = dict(_native._require_mapping(assets.get("express"), "manifest express asset"))
    if expected != actual:
        if expected.get("name") != actual["name"]:
            raise DistributionContractError("Text-Fabric express archive filename mismatch")
        if expected.get("sha256") != actual["sha256"]:
            raise DistributionContractError("Text-Fabric express archive sha256 mismatch")
        if expected.get("bytes") != actual["bytes"]:
            raise DistributionContractError("Text-Fabric express archive byte-size mismatch")
        raise DistributionContractError("Text-Fabric express asset record mismatch")


def stage_distribution_assets(
    tf_directory: str | Path,
    destination: str | Path,
    *,
    release_tag: str,
    release_commit: str,
    converter_version: str,
    data_version: str,
    app_directory: str | Path | None = None,
    repository_owner: str = DEFAULT_REPOSITORY_OWNER,
    repository_name: str = DEFAULT_REPOSITORY_NAME,
) -> dict[str, Path]:
    """Atomically stage native assets and, when requested, complete.zip transport."""

    if app_directory is None:
        return _native.stage_distribution_assets(
            tf_directory,
            destination,
            release_tag=release_tag,
            release_commit=release_commit,
            converter_version=converter_version,
            data_version=data_version,
        )

    destination = Path(destination)
    if destination.exists():
        raise DistributionContractError(
            f"release destination already exists; refusing to mix generations: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    outer_stage = Path(
        mkdtemp(
            prefix=".pseudepigrapha-tf-express-release-",
            dir=str(destination.parent),
        )
    )
    generation = outer_stage / "generation"

    try:
        native_assets = _native.stage_distribution_assets(
            tf_directory,
            generation,
            release_tag=release_tag,
            release_commit=release_commit,
            converter_version=converter_version,
            data_version=data_version,
        )
        express = generation / EXPRESS_NAME
        _build_express_archive(
            express,
            native_assets["tf"],
            Path(app_directory),
            release_tag=release_tag,
            release_commit=release_commit,
            data_version=data_version,
            repository_owner=repository_owner,
            repository_name=repository_name,
        )
        manifest = build_distribution_manifest(
            native_assets["tf"],
            native_assets["report"],
            release_tag=release_tag,
            release_commit=release_commit,
            converter_version=converter_version,
            data_version=data_version,
            express_archive=express,
            app_directory=app_directory,
            repository_owner=repository_owner,
            repository_name=repository_name,
        )
        native_assets["manifest"].write_bytes(_native.canonical_manifest_bytes(manifest))
        validate_distribution(
            manifest,
            native_assets["tf"],
            native_assets["report"],
            express_archive=express,
            app_directory=app_directory,
            repository_owner=repository_owner,
            repository_name=repository_name,
            expected_release_tag=release_tag,
            expected_release_commit=release_commit,
            expected_converter_version=converter_version,
            expected_data_version=data_version,
        )
        os.replace(generation, destination)
    except BaseException:
        if outer_stage.exists():
            shutil.rmtree(outer_stage, ignore_errors=True)
        raise
    else:
        if outer_stage.exists():
            shutil.rmtree(outer_stage, ignore_errors=True)

    return {
        "tf": destination / f"tf-{_native._require_data_version(data_version)}.zip",
        "express": destination / EXPRESS_NAME,
        "report": destination / _native.REPORT_NAME,
        "manifest": destination / _native.MANIFEST_NAME,
    }
