from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import warnings
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    feature_directory_identity,
    stage_distribution_assets,
    validate_distribution,
)
from distribution_support import canonical_otype_payload, canonical_report_provenance


RELEASE_COMMIT = "b" * 40
RELEASE_TAG = "v0.1.1-test"
REPO_ROOT = "alexsosn/Pseudepigrapha-TF"


def _materialized(tmp_path: Path) -> Path:
    source = tmp_path / "tf" / "0.1"
    source.mkdir(parents=True)
    (source / "otype.tf").write_bytes(canonical_otype_payload())
    (source / "book.tf").write_bytes(b"@node\n@valueType=str\n2\t1En__Ethiopic\n")
    (source / "oslots.tf").write_bytes(b"@edge\n2\t1\n")
    (source / "conversion-report.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "failed_checks": [],
                "semantic_checks": {"probe": True},
                "text_fabric": feature_directory_identity(source),
                "provenance": canonical_report_provenance(),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return source


def _app(tmp_path: Path) -> Path:
    app = tmp_path / "app"
    (app / "static").mkdir(parents=True)
    (app / "config.yaml").write_text(
        'apiVersion: 3\nprovenanceSpec:\n  version: "0.1"\n',
        encoding="utf-8",
    )
    (app / "app.py").write_text("VALUE = 'app'\n", encoding="utf-8")
    (app / "static" / "display.css").write_text("body {}\n", encoding="utf-8")
    return app


def _stage(tmp_path: Path):
    source = _materialized(tmp_path)
    app = _app(tmp_path)
    assets = stage_distribution_assets(
        source,
        tmp_path / "release-assets",
        release_tag=RELEASE_TAG,
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
        app_directory=app,
    )
    return source, app, assets


def _rewrite_express(
    assets: dict[str, Path],
    *,
    replace: dict[str, bytes] | None = None,
    remove: tuple[str, ...] = (),
    add: tuple[tuple[str | ZipInfo, bytes], ...] = (),
) -> dict:
    """Rewrite complete.zip and rebind its manifest record for structural attacks."""

    replace = replace or {}
    express = assets["express"]
    with ZipFile(express) as zf:
        members = [(info, zf.read(info)) for info in zf.infolist()]

    with ZipFile(express, "w", compression=ZIP_DEFLATED) as zf:
        for info, payload in members:
            if info.filename in remove:
                continue
            zf.writestr(info, replace.get(info.filename, payload))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            for name, payload in add:
                zf.writestr(name, payload)

    manifest = json.loads(assets["manifest"].read_text(encoding="utf-8"))
    payload = express.read_bytes()
    manifest["assets"]["express"] = {
        "name": "complete.zip",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    return manifest


def _validate(assets: dict[str, Path], manifest: dict) -> None:
    validate_distribution(
        manifest,
        assets["tf"],
        assets["report"],
        express_archive=assets["express"],
        expected_release_tag=RELEASE_TAG,
        expected_release_commit=RELEASE_COMMIT,
        expected_converter_version="0.1.0",
        expected_data_version="0.1",
    )


def test_release_staging_builds_manifest_bound_text_fabric_complete_zip(tmp_path):
    source, app, assets = _stage(tmp_path)
    destination = tmp_path / "release-assets"

    assert set(path.name for path in destination.iterdir()) == {
        "tf-0.1.zip",
        "complete.zip",
        "conversion-report.json",
        "dataset-manifest.json",
    }
    assert assets["express"] == destination / "complete.zip"

    marker = f"{RELEASE_TAG}\n{RELEASE_COMMIT}\n".encode("utf-8")
    expected_names = [
        f"{REPO_ROOT}/app/__checkout__.txt",
        f"{REPO_ROOT}/app/app.py",
        f"{REPO_ROOT}/app/config.yaml",
        f"{REPO_ROOT}/app/static/display.css",
        f"{REPO_ROOT}/tf/0.1/__checkout__.txt",
        f"{REPO_ROOT}/tf/0.1/book.tf",
        f"{REPO_ROOT}/tf/0.1/oslots.tf",
        f"{REPO_ROOT}/tf/0.1/otype.tf",
    ]
    with ZipFile(assets["express"]) as zf:
        assert zf.namelist() == expected_names
        assert zf.read(f"{REPO_ROOT}/app/__checkout__.txt") == marker
        assert zf.read(f"{REPO_ROOT}/tf/0.1/__checkout__.txt") == marker
        for name in ("app.py", "config.yaml"):
            assert zf.read(f"{REPO_ROOT}/app/{name}") == (app / name).read_bytes()
        for name in ("book.tf", "oslots.tf", "otype.tf"):
            assert zf.read(f"{REPO_ROOT}/tf/0.1/{name}") == (source / name).read_bytes()

    manifest = json.loads(assets["manifest"].read_text(encoding="utf-8"))
    express = assets["express"].read_bytes()
    assert manifest["assets"]["express"] == {
        "name": "complete.zip",
        "bytes": len(express),
        "sha256": hashlib.sha256(express).hexdigest(),
    }
    assert _validate(assets, manifest) is None


def test_complete_zip_is_deterministic_for_same_inputs(tmp_path):
    source = _materialized(tmp_path / "a")
    app = _app(tmp_path / "a")
    first = stage_distribution_assets(
        source,
        tmp_path / "release-a",
        release_tag=RELEASE_TAG,
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
        app_directory=app,
    )["express"].read_bytes()

    source2 = _materialized(tmp_path / "b")
    app2 = _app(tmp_path / "b")
    second = stage_distribution_assets(
        source2,
        tmp_path / "release-b",
        release_tag=RELEASE_TAG,
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
        app_directory=app2,
    )["express"].read_bytes()

    assert first == second


def test_complete_zip_tamper_is_rejected_by_distribution_validation(tmp_path):
    _, _, assets = _stage(tmp_path)
    manifest = json.loads(assets["manifest"].read_text(encoding="utf-8"))
    assets["express"].write_bytes(assets["express"].read_bytes() + b"tamper")

    with pytest.raises(DistributionContractError, match="express|complete"):
        _validate(assets, manifest)


def test_complete_zip_wrong_checkout_marker_fails_even_when_manifest_hash_matches(tmp_path):
    _, _, assets = _stage(tmp_path)
    marker_name = f"{REPO_ROOT}/app/__checkout__.txt"
    manifest = _rewrite_express(
        assets,
        replace={marker_name: f"v9.9.9\n{'c' * 40}\n".encode("utf-8")},
    )

    with pytest.raises(DistributionContractError, match="checkout|marker|release|commit"):
        _validate(assets, manifest)


def test_complete_zip_missing_checkout_marker_fails_even_when_manifest_hash_matches(tmp_path):
    _, _, assets = _stage(tmp_path)
    manifest = _rewrite_express(
        assets,
        remove=(f"{REPO_ROOT}/tf/0.1/__checkout__.txt",),
    )

    with pytest.raises(DistributionContractError, match="checkout|marker|missing"):
        _validate(assets, manifest)


def test_complete_zip_feature_divergence_fails_even_when_manifest_hash_matches(tmp_path):
    _, _, assets = _stage(tmp_path)
    feature_name = f"{REPO_ROOT}/tf/0.1/book.tf"
    manifest = _rewrite_express(
        assets,
        replace={feature_name: b"@node\n1\tDIFFERENT\n"},
    )

    with pytest.raises(DistributionContractError, match="feature|native|express|Text-Fabric"):
        _validate(assets, manifest)


@pytest.mark.parametrize(
    "extra_name",
    [
        "../escape",
        "other/repository/app/rogue.py",
        f"{REPO_ROOT}/tf/0.1/nested/rogue.tf",
    ],
    ids=["traversal", "wrong-root", "nested-data-garbage"],
)
def test_complete_zip_rejects_unsafe_or_unexpected_member_roots(tmp_path, extra_name):
    _, _, assets = _stage(tmp_path)
    manifest = _rewrite_express(assets, add=((extra_name, b"rogue"),))

    with pytest.raises(DistributionContractError, match="path|root|member|express|nested|traversal"):
        _validate(assets, manifest)


def test_complete_zip_rejects_duplicate_members(tmp_path):
    _, _, assets = _stage(tmp_path)
    duplicate = f"{REPO_ROOT}/app/app.py"
    manifest = _rewrite_express(assets, add=((duplicate, b"second copy"),))

    with pytest.raises(DistributionContractError, match="duplicate|member|express"):
        _validate(assets, manifest)


def test_complete_zip_rejects_symlink_members(tmp_path):
    _, _, assets = _stage(tmp_path)
    link = ZipInfo(f"{REPO_ROOT}/app/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    manifest = _rewrite_express(assets, add=((link, b"config.yaml"),))

    with pytest.raises(DistributionContractError, match="symlink|member|express"):
        _validate(assets, manifest)


def test_release_workflows_require_complete_zip_transport():
    root = Path(__file__).parents[1]
    build = (root / ".github/workflows/build-corpus-release-assets.yml").read_text(encoding="utf-8")
    publish = (root / ".github/workflows/publish-corpus-release.yml").read_text(encoding="utf-8")

    assert "complete.zip" in build
    assert "complete.zip" in publish
    assert "assets['express']" in build or 'assets["express"]' in build
