from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from distribution_support import canonical_otype_payload, canonical_report_provenance
from pseudepigrapha_tf.distribution import (
    DistributionContractError,
    feature_directory_identity,
    stage_distribution_assets,
    validate_distribution,
)
from pseudepigrapha_tf.express_app_binding import validate_express_app_directory


RELEASE_COMMIT = "b" * 40
RELEASE_TAG = "v0.1.1-test"
REPO_ROOT = "alexsosn/Pseudepigrapha-TF"


def _stage(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
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

    app = tmp_path / "app"
    app.mkdir()
    (app / "config.yaml").write_text(
        'apiVersion: 3\nprovenanceSpec:\n  version: "0.1"\n',
        encoding="utf-8",
    )
    (app / "app.py").write_text("VALUE = 'trusted'\n", encoding="utf-8")

    assets = stage_distribution_assets(
        source,
        tmp_path / "release-assets",
        release_tag=RELEASE_TAG,
        release_commit=RELEASE_COMMIT,
        converter_version="0.1.0",
        data_version="0.1",
        app_directory=app,
    )
    return app, assets


def test_express_app_bytes_are_bound_to_exact_release_checkout(tmp_path):
    app, assets = _stage(tmp_path)
    express = assets["express"]
    app_member = f"{REPO_ROOT}/app/app.py"

    with ZipFile(express) as zf:
        members = [(info, zf.read(info)) for info in zf.infolist()]
    with ZipFile(express, "w", compression=ZIP_DEFLATED) as zf:
        for info, payload in members:
            zf.writestr(info, b"VALUE = 'substituted'\n" if info.filename == app_member else payload)

    manifest = json.loads(assets["manifest"].read_text(encoding="utf-8"))
    payload = express.read_bytes()
    manifest["assets"]["express"] = {
        "name": "complete.zip",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }

    # Structural distribution validation intentionally accepts the coherently
    # rebound outer asset record; the exact checkout is the independent trust
    # source for app bytes.
    assert validate_distribution(
        manifest,
        assets["tf"],
        assets["report"],
        express_archive=express,
        expected_release_tag=RELEASE_TAG,
        expected_release_commit=RELEASE_COMMIT,
        expected_converter_version="0.1.0",
        expected_data_version="0.1",
    ) is None

    with pytest.raises(DistributionContractError, match="app|tracked|checkout|payload"):
        validate_express_app_directory(express, app_directory=app)


def test_release_revalidation_supplies_exact_app_checkout():
    root = Path(__file__).parents[1]
    build = (root / ".github/workflows/build-corpus-release-assets.yml").read_text(encoding="utf-8")
    publish = (root / ".github/workflows/publish-corpus-release.yml").read_text(encoding="utf-8")

    assert "validate_express_app_directory" in build
    assert "app_directory=" in build
    assert publish.count("validate_express_app_directory") >= 3
    assert publish.count("app_directory=") >= 3
