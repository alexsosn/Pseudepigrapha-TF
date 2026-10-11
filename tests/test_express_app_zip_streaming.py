"""Exact-byte canonical express app archive construction without full buffers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from pseudepigrapha_tf import distribution
from test_express_streaming import _arguments, _fixtures, _historical_express, REPO_ROOT
from test_distribution_staging import _materialized


def _large_app_body() -> bytes:
    return b"APP ASSET BINARY PAYLOAD\n" * 53_000 + b"last asset byte"


def test_streamed_tracked_app_members_match_historical_complete_zip_exactly(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    asset = _large_app_body()
    (app / "large-app.bin").write_bytes(asset)
    members[f"{REPO_ROOT}/app/large-app.bin"] = asset
    golden = tmp_path / "historical.zip"
    output = tmp_path / "complete.zip"
    _historical_express(golden, members)

    original_copy = distribution.shutil.copyfileobj
    app_copies = []

    def monitor_copy(source, target, length=0):
        if str(getattr(source, "name", "")).endswith("large-app.bin"):
            app_copies.append(length)
            assert length == 1_048_576, "app asset must be read in bounded chunks"
        return original_copy(source, target, length)

    with (
        patch.object(Path, "read_bytes", side_effect=AssertionError("eager app read forbidden")),
        patch.object(
            distribution, "_collect_app_payloads",
            side_effect=AssertionError("whole app payload dictionary forbidden"),
        ),
        patch.object(distribution.shutil, "copyfileobj", side_effect=monitor_copy),
    ):
        distribution._build_express_archive(output, **_arguments(native_zip, app))

    assert app_copies == [1_048_576]
    assert golden.read_bytes() == output.read_bytes()

    with ZipFile(output) as zf:
        assert zf.namelist() == sorted(members)
        for info in zf.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.create_system == 3
            assert info.external_attr >> 16 == 0o100644
            assert info.extra == b"" and info.comment == b""


def test_app_source_stream_failure_cleans_entire_release_stage(tmp_path):
    source = _materialized(tmp_path)
    app = tmp_path / "tracked-app"
    app.mkdir()
    (app / "config.yaml").write_bytes(b"apiVersion: 3\n")
    (app / "large-app.bin").write_bytes(_large_app_body())
    original_source = {p.name: p.read_bytes() for p in source.iterdir()}
    original_app = {p.name: p.read_bytes() for p in app.iterdir()}
    destination = tmp_path / "published-assets"

    original_copy = distribution.shutil.copyfileobj
    observed_app = []

    def fail_app_stream(source_stream, target_stream, length=0):
        if str(getattr(source_stream, "name", "")).endswith("large-app.bin"):
            observed_app.append(length)
            raise OSError("injected tracked app stream failure")
        return original_copy(source_stream, target_stream, length)

    with patch.object(distribution.shutil, "copyfileobj", side_effect=fail_app_stream):
        with pytest.raises(distribution.DistributionContractError, match="injected tracked app stream failure"):
            distribution.stage_distribution_assets(
                source,
                destination,
                release_tag="v0.1.1-test",
                release_commit="b" * 40,
                converter_version="0.1.0",
                data_version="0.1",
                app_directory=app,
            )

    assert observed_app == [1_048_576]
    assert not destination.exists()
    assert not list(tmp_path.glob(".pseudepigrapha-tf-express-release-*"))
    assert {p.name: p.read_bytes() for p in source.iterdir()} == original_source
    assert {p.name: p.read_bytes() for p in app.iterdir()} == original_app
