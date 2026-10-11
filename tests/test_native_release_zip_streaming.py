"""Native release ZIP construction is bounded and historically byte-compatible (#186)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf import _distribution_native as native
from distribution_support import canonical_otype_payload, canonical_report_provenance


def _features(tmp_path: Path) -> list[Path]:
    source = tmp_path / "features"
    source.mkdir()
    (source / "book.tf").write_bytes(b"@node\n@valueType=str\n2\t1En__Ethiopic\n")
    (source / "oslots.tf").write_bytes(
        b"@edge\n" + b"1\t2\n" * 270_000 + b"3\t4\n"
    )
    (source / "otype.tf").write_bytes(canonical_otype_payload())
    return sorted(source.glob("*.tf"))


def _old_canonical_zip(archive: Path, features: list[Path]) -> None:
    """Historic writestr implementation, frozen independently of the helper."""
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
        for feature in features:
            zf.writestr(native._canonical_zip_info(feature.name), feature.read_bytes())


def test_stream_writer_matches_historical_archive_bytes_without_full_file_reads(tmp_path):
    features = _features(tmp_path)
    old_archive = tmp_path / "old.zip"
    streamed_archive = tmp_path / "new.zip"
    _old_canonical_zip(old_archive, features)

    original_copy = native.shutil.copyfileobj
    observed_lengths = []

    def bounded_copy(source, dest, length=0):
        observed_lengths.append(length)
        assert length == 1_048_576, "release ZIP writer must request fixed 1 MiB chunks"
        return original_copy(source, dest, length)

    for i, feature in enumerate(features):
        os.utime(feature, (946684800 + i, 946684800 + i))
        os.chmod(feature, 0o600 if i % 2 else 0o755)

    # Old writer would use Path.read_bytes; new writer must not.
    with (
        patch.object(Path, "read_bytes", side_effect=AssertionError("full source-file read forbidden")),
        patch.object(native.shutil, "copyfileobj", side_effect=bounded_copy),
    ):
        native._write_native_feature_archive(streamed_archive, features)

    assert observed_lengths == [1_048_576] * len(features)
    assert old_archive.read_bytes() == streamed_archive.read_bytes()
    with ZipFile(streamed_archive) as zf:
        assert zf.namelist() == [feature.name for feature in features]
        for info in zf.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == ZIP_DEFLATED
            assert info.create_system == 3
            assert info.external_attr >> 16 == 0o100644
            assert info.extra == b"" and info.comment == b""


def test_mid_member_stream_error_cleans_staged_release_without_touching_source(tmp_path):
    source = tmp_path / "tf"
    source.mkdir()
    (source / "otype.tf").write_bytes(canonical_otype_payload())
    (source / "book.tf").write_bytes(b"@node\n@valueType=str\n2\t1En__Ethiopic\n")
    (source / "oslots.tf").write_bytes(b"@edge\n2\t1\n")
    report = {
        "status": "ok",
        "failed_checks": [],
        "semantic_checks": {"probe": True},
        "text_fabric": native.feature_directory_identity(source),
        "provenance": canonical_report_provenance(),
    }
    (source / "conversion-report.json").write_text(
        json.dumps(report, sort_keys=True) + "\n", encoding="utf-8"
    )
    original = {file.name: file.read_bytes() for file in source.iterdir()}
    destination = tmp_path / "release-output"

    def fail_copy(source_stream, dest_stream, length=0):
        assert length == 1_048_576
        raise OSError("simulated source read error after ZIP member opened")

    with patch.object(native.shutil, "copyfileobj", side_effect=fail_copy):
        with pytest.raises(OSError, match="simulated source read error"):
            native.stage_distribution_assets(
                source,
                destination,
                release_tag="v0.1-test",
                release_commit="b" * 40,
                converter_version="0.1.0",
                data_version="0.1",
            )

    assert not destination.exists()
    assert {file.name: file.read_bytes() for file in source.iterdir()} == original
    assert not list(tmp_path.glob(".pseudepigrapha-tf-release-*"))
