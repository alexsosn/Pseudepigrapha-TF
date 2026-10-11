"""Bounded otype header reading must preserve full UTF-8 and CRC integrity (#194)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from pseudepigrapha_tf import _distribution_native as native


def _archive(tmp_path: Path, data: bytes, *, compression=ZIP_DEFLATED) -> Path:
    path = tmp_path / "tf-1.0.zip"
    with ZipFile(path, "w", compression=compression) as zf:
        zf.writestr("otype.tf", data)
    return path


def test_metadata_header_streams_without_entire_otype_zip_member(tmp_path):
    header = (
        "@node\r\n"
        "@version=1.0\r\n"
        "@upstreamCommit=abc123\r\n"
        "@writtenBy=Πᾶυλος\r\n"
        "@writtenBy=second-generic-value\r\n"
        "\r\n"
    ).encode("utf-8")
    body = ("1\tλέξη\n" * 300_000).encode("utf-8")
    archive = _archive(tmp_path, header + body)
    assert len(body) > 1_048_576

    # Eager whole-member allocation must be impossible for this call.
    with patch.object(ZipFile, "read", side_effect=AssertionError("whole ZIP member read forbidden")):
        metadata = native._serialized_otype_metadata(archive)
    assert metadata == {
        "version": "1.0",
        "upstreamCommit": "abc123",
        "writtenBy": "Πᾶυλος",
    }


def test_oversized_header_line_fails_closed_instead_of_allocating_full_string(tmp_path):
    body = b"@node\n@writtenBy=" + b"x" * (1024 * 1024 + 1) + b"\n\n1\tword\n"
    archive = _archive(tmp_path, body)
    with pytest.raises(native.DistributionContractError, match=r"otype.*header.*line.*limit|metadata.*line.*long"):
        native._serialized_otype_metadata(archive)


def test_bad_utf8_after_blank_header_is_still_rejected(tmp_path):
    archive = _archive(tmp_path, b"@node\n@version=1.0\n\n1\tword\n\xff\xfe")
    with pytest.raises(native.DistributionContractError, match="valid UTF-8"):
        native._serialized_otype_metadata(archive)


def test_crc_corruption_after_blank_header_is_still_rejected(tmp_path):
    payload = b"@node\n@version=1.0\n\n1\tUNCHANGED_UNIQUE_CRC_PAYLOAD\n"
    archive = _archive(tmp_path, payload, compression=ZIP_STORED)
    raw = archive.read_bytes()
    assert raw.count(b"UNCHANGED_UNIQUE_CRC_PAYLOAD") == 1
    archive.write_bytes(raw.replace(
        b"UNCHANGED_UNIQUE_CRC_PAYLOAD",
        b"CHANGEDXX_UNIQUE_CRC_PAYLOAD",
        1,
    ))
    with pytest.raises(native.DistributionContractError, match="could not read|CRC|archive"):
        native._serialized_otype_metadata(archive)


def test_unicode_line_separator_in_header_keeps_existing_splitlines_behavior(tmp_path):
    data = ("@node\u2028@version=1.0\u2028\u20281\tword\n").encode("utf-8")
    archive = _archive(tmp_path, data)
    assert native._serialized_otype_metadata(archive)["version"] == "1.0"
