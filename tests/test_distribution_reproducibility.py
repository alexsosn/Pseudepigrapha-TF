from __future__ import annotations

import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from pseudepigrapha_tf.distribution import (
    feature_directory_identity,
    stage_distribution_assets,
    validate_distribution,
)
from pseudepigrapha_tf.provenance import (
    OCP_PIN,
    OCP_REPOSITORY,
    corpus_license_metadata,
    report_provenance,
)


RELEASE_COMMIT = "b" * 40
RELEASE_TAG = "v0.2.0-repro-test"
CONVERTER_VERSION = "0.2.0"
DATA_VERSION = "0.2"
FIXED_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)
FIXED_ZIP_MODE = 0o100644


def _materialized(root: Path, *, book_payload: bytes = b"@node\n@valueType=str\n2\t1En__Ethiopic\n") -> Path:
    root.mkdir(parents=True)
    generic = {
        "version": DATA_VERSION,
        "upstreamRepository": OCP_REPOSITORY,
        "upstreamCommit": OCP_PIN,
        "converterVersion": CONVERTER_VERSION,
    }
    generic.update(
        corpus_license_metadata(
            OCP_REPOSITORY,
            OCP_PIN,
            source_identity_verified=True,
        )
    )

    otype_header = ["@node", *(f"@{key}={value}" for key, value in sorted(generic.items()))]
    (root / "otype.tf").write_bytes(
        ("\n".join(otype_header) + "\n@valueType=str\n\n1\tword\n").encode("utf-8")
    )
    (root / "book.tf").write_bytes(book_payload)
    (root / "oslots.tf").write_bytes(b"@edge\n2\t1\n")

    report = {
        "status": "ok",
        "failed_checks": [],
        "semantic_checks": {"probe": True},
        "text_fabric": feature_directory_identity(root),
        "provenance": report_provenance(generic),
    }
    (root / "conversion-report.json").write_text(
        json.dumps(report, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return root


def _stage(source: Path, destination: Path) -> dict[str, Path]:
    return stage_distribution_assets(
        source,
        destination,
        release_tag=RELEASE_TAG,
        release_commit=RELEASE_COMMIT,
        converter_version=CONVERTER_VERSION,
        data_version=DATA_VERSION,
    )


def _manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_staging_is_bit_reproducible_across_source_mtime_and_mode_changes(tmp_path):
    first = _materialized(tmp_path / "first")
    second = _materialized(tmp_path / "second")

    first_time = 946684800  # 2000-01-01 UTC
    second_time = 1609459200  # 2021-01-01 UTC
    for name in ("book.tf", "oslots.tf", "otype.tf"):
        os.utime(first / name, (first_time, first_time))
        os.utime(second / name, (second_time, second_time))
        os.chmod(first / name, 0o600)
        os.chmod(second / name, 0o755)

    first_assets = _stage(first, tmp_path / "first-assets")
    second_assets = _stage(second, tmp_path / "second-assets")

    assert first_assets["tf"].read_bytes() == second_assets["tf"].read_bytes()
    assert first_assets["manifest"].read_bytes() == second_assets["manifest"].read_bytes()

    first_manifest = _manifest(first_assets["manifest"])
    second_manifest = _manifest(second_assets["manifest"])
    assert first_manifest["assets"]["tf"]["sha256"] == second_manifest["assets"]["tf"]["sha256"]


def test_staged_zip_members_use_explicit_normalized_metadata(tmp_path):
    source = _materialized(tmp_path / "source")
    for name in ("book.tf", "oslots.tf", "otype.tf"):
        os.utime(source / name, (1609459200, 1609459200))
        os.chmod(source / name, 0o755)

    assets = _stage(source, tmp_path / "assets")

    with ZipFile(assets["tf"]) as zf:
        assert zf.namelist() == ["book.tf", "oslots.tf", "otype.tf"]
        for info in zf.infolist():
            assert info.date_time == FIXED_ZIP_DATETIME
            assert info.create_system == 3
            assert info.external_attr >> 16 == FIXED_ZIP_MODE
            assert info.compress_type == ZIP_DEFLATED
            assert info.extra == b""
            assert info.comment == b""


def test_feature_byte_change_still_changes_archive_and_manifest_identity(tmp_path):
    first = _materialized(tmp_path / "first")
    second = _materialized(
        tmp_path / "second",
        book_payload=b"@node\n@valueType=str\n2\tDIFFERENT\n",
    )

    first_assets = _stage(first, tmp_path / "first-assets")
    second_assets = _stage(second, tmp_path / "second-assets")
    first_manifest = _manifest(first_assets["manifest"])
    second_manifest = _manifest(second_assets["manifest"])

    assert first_assets["tf"].read_bytes() != second_assets["tf"].read_bytes()
    assert first_manifest["assets"]["tf"]["sha256"] != second_manifest["assets"]["tf"]["sha256"]
    assert first_manifest["text_fabric"]["feature_set_sha256"] != second_manifest["text_fabric"]["feature_set_sha256"]

    assert validate_distribution(
        first_manifest,
        first_assets["tf"],
        first_assets["report"],
        expected_release_tag=RELEASE_TAG,
        expected_release_commit=RELEASE_COMMIT,
        expected_converter_version=CONVERTER_VERSION,
        expected_data_version=DATA_VERSION,
    ) is None
    assert validate_distribution(
        second_manifest,
        second_assets["tf"],
        second_assets["report"],
        expected_release_tag=RELEASE_TAG,
        expected_release_commit=RELEASE_COMMIT,
        expected_converter_version=CONVERTER_VERSION,
        expected_data_version=DATA_VERSION,
    ) is None
