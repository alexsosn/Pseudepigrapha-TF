"""Chunked release-hash identity with exact ZIP/member and CRC contracts (#184)."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from pseudepigrapha_tf import _distribution_native as native


def _payload(n: int) -> bytes:
    return (b"reproducible-text-fabric-data-" * (n // 30 + 1))[:n]


def _record(name: str, payload: bytes) -> dict[str, object]:
    return {"name": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def test_file_record_streams_instead_of_reading_whole_file(tmp_path: Path):
    data = _payload(1_048_576 + 41)
    source = tmp_path / "text-fabric-data.zip"
    source.write_bytes(data)

    # Deliberately fail the old complete-file read path.
    with patch.object(Path, "read_bytes", side_effect=AssertionError("full Path.read_bytes is forbidden")):
        record = native._file_record(source)
    assert record == _record(source.name, data)


@pytest.mark.parametrize("compression", [ZIP_STORED, ZIP_DEFLATED])
def test_tf_member_identities_are_streamed_with_crc(compression, tmp_path: Path):
    oslots = _payload(1_048_576 + 131)
    otype = b"@node\n@valueType=str\n\n1\tword\n"
    zip_file = tmp_path / "tf-1.0.zip"
    with ZipFile(zip_file, "w", compression=compression) as zf:
        # Write deliberately unsorted input to assert canonical sorting.
        zf.writestr("oslots.tf", oslots)
        zf.writestr("otype.tf", otype)

    # ZipFile.read allocates a whole member; incremental open/read must suffice.
    with patch.object(ZipFile, "read", side_effect=AssertionError("full ZipFile.read is forbidden")):
        records = native._feature_records(zip_file)
    assert records == [_record("oslots.tf", oslots), _record("otype.tf", otype)]


def test_corrupted_stored_zip_member_still_fails_crc(tmp_path: Path):
    source_data = b"UNIQUE_PAYLOAD_TO_CORRUPT_123456789"
    zip_file = tmp_path / "tf-1.0.zip"
    with ZipFile(zip_file, "w", compression=ZIP_STORED) as zf:
        zf.writestr("otype.tf", source_data)
    binary = zip_file.read_bytes()
    assert binary.count(source_data) == 1
    zip_file.write_bytes(binary.replace(source_data, b"BROKEN_PAYLOAD_TO_CORRUPT_123456789", 1))

    with pytest.raises(native.DistributionContractError, match=r"invalid TF archive|CRC"):
        native._feature_records(zip_file)


def test_internal_hash_reads_are_bounded():
    source = _payload(1_048_576 + 73)

    class GuardedReader(io.BytesIO):
        calls: list[int]

        def __init__(self, data: bytes):
            super().__init__(data)
            self.calls = []

        def read(self, size: int = -1) -> bytes:
            assert 0 < size <= 1_048_576, "stream must request bounded positive-size chunks"
            self.calls.append(size)
            return super().read(size)

    stream = GuardedReader(source)
    assert native._hash_stream_record("otype.tf", stream) == _record("otype.tf", source)
    assert len(stream.calls) >= 2
