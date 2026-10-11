"""Untrusted complete.zip app entries must be hashed with bounded reads (#190)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_STORED, ZipFile

import pytest

from pseudepigrapha_tf import distribution
from pseudepigrapha_tf import _distribution_native as native
from test_express_streaming import (
    REPO_ROOT, _fixtures, _historical_express, _validation_arguments,
)


def _identity(name: str, body: bytes) -> dict[str, object]:
    return {
        "name": name, "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def _forbid_express_app_reads(original):
    def guard(self, member, *args, **kwargs):
        name = member.filename if hasattr(member, "filename") else member
        if f"{REPO_ROOT}/app/" in str(name):
            raise AssertionError("full complete.zip app member read is forbidden")
        return original(self, member, *args, **kwargs)
    return guard


def test_complete_zip_app_members_stream_and_return_content_identities(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    large = (b"tracked source app code\n" * 58_000) + b"final app byte"
    (app / "large-resource.txt").write_bytes(large)
    members[f"{REPO_ROOT}/app/large-resource.txt"] = large
    express = tmp_path / "complete.zip"
    _historical_express(express, members)

    original_read = ZipFile.read
    with patch.object(ZipFile, "read", _forbid_express_app_reads(original_read)):
        records = distribution._validate_express_archive(
            express, **_validation_arguments(native_zip, app)
        )

    assert records["large-resource.txt"] == _identity("large-resource.txt", large)
    assert records["config.yaml"] == _identity(
        "config.yaml", (app / "config.yaml").read_bytes()
    )
    assert sorted(records) == ["app.py", "config.yaml", "large-resource.txt"]


def test_exact_app_checkout_validation_uses_streaming_files_not_full_buffers(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    large = b"large resource\n" * 85_000
    (app / "large-resource.txt").write_bytes(large)
    members[f"{REPO_ROOT}/app/large-resource.txt"] = large
    express = tmp_path / "complete.zip"
    _historical_express(express, members)

    records = distribution._validate_express_archive(
        express, **_validation_arguments(native_zip, app)
    )
    with patch.object(
        Path, "read_bytes",
        side_effect=AssertionError("whole tracked app file read is forbidden"),
    ):
        assert distribution._validate_express_app_identity(records, app) is None

    # Same-size source substitution must not pass a mere size+filename check.
    (app / "large-resource.txt").write_bytes(b"X" + large[1:])
    with pytest.raises(distribution.DistributionContractError, match="payload"):
        distribution._validate_express_app_identity(records, app)


def test_express_checkout_markers_are_read_without_zipfile_read(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    express = tmp_path / "complete.zip"
    _historical_express(express, members)
    original_read = ZipFile.read
    with patch.object(ZipFile, "read", _forbid_express_app_reads(original_read)):
        records = distribution._validate_express_archive(
            express, **_validation_arguments(native_zip, app)
        )
    assert "config.yaml" in records


def test_malformed_giant_app_checkout_marker_fails_closed_before_buffering(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    members[f"{REPO_ROOT}/app/__checkout__.txt"] = b"X" * (1_048_576 + 1)
    express = tmp_path / "complete.zip"
    _historical_express(express, members)
    original_read = ZipFile.read
    with patch.object(ZipFile, "read", _forbid_express_app_reads(original_read)):
        with pytest.raises(distribution.DistributionContractError, match="checkout marker"):
            distribution._validate_express_archive(
                express, **_validation_arguments(native_zip, app)
            )


def test_corrupted_stored_app_member_still_fails_crc(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    target = f"{REPO_ROOT}/app/app.py"
    payload = b"APP_CRC_UNIQUE_DATA_TO_CORRUPT_123456789"
    members[target] = payload
    express = tmp_path / "complete.zip"
    with ZipFile(express, "w") as zf:
        for name, data in sorted(members.items()):
            info = native._canonical_zip_info(name)
            info.compress_type = ZIP_STORED
            zf.writestr(info, data)

    archive = express.read_bytes()
    assert archive.count(payload) == 1
    express.write_bytes(
        archive.replace(payload, b"BAD_CRC_UNIQUE_DATA_TO_CORRUPT_123456789", 1)
    )

    with pytest.raises(distribution.DistributionContractError, match="CRC|invalid"):
        distribution._validate_express_archive(
            express, **_validation_arguments(native_zip, app)
        )
