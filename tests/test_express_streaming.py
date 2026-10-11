"""Express complete.zip streams native corpus features without losing exact parity."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from pseudepigrapha_tf import distribution
from pseudepigrapha_tf import _distribution_native as native


RELEASE_TAG = "v0.1.1-test"
RELEASE_COMMIT = "b" * 40
REPO_ROOT = "alexsosn/Pseudepigrapha-TF"


def _fixtures(tmp_path: Path):
    data = b"@edge\n" + b"1\t2\n" * 280_000 + b"3\t4\n"
    otype = b"@node\n@valueType=str\n\n1\tword\n"
    app = tmp_path / "app"
    app.mkdir()
    (app / "config.yaml").write_bytes(b"apiVersion: 3\n")
    (app / "app.py").write_bytes(b"CODE = 1\n")
    native_zip = tmp_path / "tf-0.1.zip"
    with ZipFile(native_zip, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr(native._canonical_zip_info("oslots.tf"), data)
        zf.writestr(native._canonical_zip_info("otype.tf"), otype)
    marker = f'{RELEASE_TAG}\n{RELEASE_COMMIT}\n'.encode()
    members = {
        f"{REPO_ROOT}/app/__checkout__.txt": marker,
        f"{REPO_ROOT}/app/config.yaml": (app / "config.yaml").read_bytes(),
        f"{REPO_ROOT}/app/app.py": (app / "app.py").read_bytes(),
        f"{REPO_ROOT}/tf/0.1/__checkout__.txt": marker,
        f"{REPO_ROOT}/tf/0.1/oslots.tf": data,
        f"{REPO_ROOT}/tf/0.1/otype.tf": otype,
    }
    return native_zip, app, members


def _historical_express(path: Path, members: dict[str, bytes]) -> None:
    with ZipFile(path, "w") as zf:
        for name in sorted(members):
            zf.writestr(native._canonical_zip_info(name), members[name])


def _arguments(native_zip: Path, app: Path) -> dict:
    return {
        "native_archive": native_zip,
        "app_directory": app,
        "release_tag": RELEASE_TAG,
        "release_commit": RELEASE_COMMIT,
        "data_version": "0.1",
        "repository_owner": "alexsosn",
        "repository_name": "Pseudepigrapha-TF",
    }


def _validation_arguments(native_zip: Path, app: Path) -> dict:
    # The validator takes native_archive and repository identifiers, but
    # unlike the builder it deliberately does not accept app_directory.
    args = _arguments(native_zip, app)
    del args["app_directory"]
    return args


def _deny_native_feature_payloads(*args, **kwargs):
    raise AssertionError("entire native feature payload dictionary is forbidden")


def _no_tf_member_read(original):
    def checked(self, member, *args, **kwargs):
        name = member.filename if hasattr(member, "filename") else member
        if str(name).endswith(".tf"):
            raise AssertionError("whole TF ZIP member read is forbidden")
        return original(self, member, *args, **kwargs)
    return checked


def test_streaming_express_builder_is_identical_to_historical_complete_zip(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    golden = tmp_path / "historical.zip"
    output = tmp_path / "complete.zip"
    _historical_express(golden, members)
    original = ZipFile.read
    with (
        patch.object(distribution, "_native_feature_payloads", side_effect=_deny_native_feature_payloads),
        patch.object(ZipFile, "read", _no_tf_member_read(original)),
    ):
        distribution._build_express_archive(output, **_arguments(native_zip, app))
    assert golden.read_bytes() == output.read_bytes()
    with ZipFile(output) as zf:
        assert zf.namelist() == sorted(members)
        for info in zf.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.create_system == 3
            assert info.external_attr >> 16 == 0o100644
            assert info.extra == b'' and info.comment == b''
        assert sha256(zf.read(f'{REPO_ROOT}/tf/0.1/oslots.tf')).digest() == sha256(members[f'{REPO_ROOT}/tf/0.1/oslots.tf']).digest()


def test_streaming_express_validator_checks_feature_bytes_without_payload_dicts(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    express = tmp_path / "complete.zip"
    _historical_express(express, members)
    original = ZipFile.read
    with (
        patch.object(distribution, "_native_feature_payloads", side_effect=_deny_native_feature_payloads),
        patch.object(ZipFile, "read", _no_tf_member_read(original)),
    ):
        app_payloads = distribution._validate_express_archive(
            express, **_validation_arguments(native_zip, app)
        )
    assert app_payloads["config.yaml"] == {
        "name": "config.yaml", "bytes": len(b"apiVersion: 3\n"),
        "sha256": sha256(b"apiVersion: 3\n").hexdigest(),
    }
    assert app_payloads["app.py"] == {
        "name": "app.py", "bytes": len(b"CODE = 1\n"),
        "sha256": sha256(b"CODE = 1\n").hexdigest(),
    }


def test_express_validator_rejects_same_length_feature_substitution(tmp_path):
    native_zip, app, members = _fixtures(tmp_path)
    express = tmp_path / "complete.zip"
    name = f'{REPO_ROOT}/tf/0.1/oslots.tf'
    original = members[name]
    members[name] = original.replace(b"1\t2", b"9\t8", 1)
    assert len(members[name]) == len(original)
    _historical_express(express, members)
    with pytest.raises(distribution.DistributionContractError, match="differs from native archive bytes"):
        distribution._validate_express_archive(express, **_validation_arguments(native_zip, app))

