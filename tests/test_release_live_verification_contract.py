from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLISH_WORKFLOW = ROOT / ".github" / "workflows" / "publish-corpus-release.yml"
VERIFY_WORKFLOW = ROOT / ".github" / "workflows" / "verify-published-corpus-release.yml"
TF_GITHUB_EXTRA = "text-fabric[github]>=13.1,<14"
EXPRESS_STEP = "Fresh-cache express complete.zip load then network-blocked local reload"
EXPRESS_HOME = "/tmp/pseudepigrapha-tf-express-live-home"


def _publish_live_block() -> str:
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    marker = "  verify-live:"
    assert marker in text, "publisher live-verification job is missing"
    return text.split(marker, 1)[1]


def test_publisher_live_verifier_provisions_github_backend_before_remote_use():
    live = _publish_live_block()

    install = live.index(TF_GITHUB_EXTRA)
    remote_use = live.index("from tf.app import use")

    assert install < remote_use
    assert "checkout=release_tag" in live
    assert "checkout=\"local\"" in live or "checkout='local'" in live
    assert "socket.create_connection" in live
    assert "socket.socket.connect" in live


def test_github_verifier_dependency_does_not_leak_into_normal_package_runtime():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = [str(dep).lower() for dep in project["project"]["dependencies"]]

    assert "text-fabric>=13.1,<14" in dependencies
    assert all("text-fabric[github]" not in dep for dep in dependencies)
    assert all("pygithub" not in dep for dep in dependencies)


def test_published_release_verifier_is_read_only_and_bound_to_explicit_identity():
    assert VERIFY_WORKFLOW.is_file(), "read-only published-release verifier is missing"
    text = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "release_tag:" in text
    assert "release_commit:" in text
    assert "permissions:" in text
    assert "contents: read" in text
    assert "contents: write" not in text

    for destructive in (
        "gh release create",
        "gh release edit",
        "gh release upload",
        "gh release delete",
        "git tag -f",
        "git push --force",
    ):
        assert destructive not in text

    assert "refs/tags/$RELEASE_TAG" in text
    assert "^{commit}" in text
    assert 'test "$TAG_COMMIT" = "$RELEASE_COMMIT"' in text
    assert "gh release download" in text
    assert "validate_distribution" in text


def test_published_release_verifier_provisions_github_backend_and_checks_offline_reload():
    text = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    install = text.index(TF_GITHUB_EXTRA)
    remote_use = text.index("from tf.app import use")

    assert install < remote_use
    assert "checkout=release_tag" in text
    assert "checkout=\"local\"" in text or "checkout='local'" in text
    assert "socket.create_connection" in text
    assert "socket.socket.connect" in text
    assert "network access attempted" in text
    assert "dataset-manifest.json" in text


def test_published_release_verifier_derives_release_identity_instead_of_freezing_v020():
    text = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "manifest['converter']['version']" in text
    assert "manifest['text_fabric']['data_version']" in text
    assert "manifest['upstream']['commit']" in text
    assert "manifest['provenance']['content_license']" in text
    assert "expected_converter_version=converter_version" in text
    assert "expected_data_version=data_version" in text
    assert "local_app.api.F.otype.maxSlot == fresh_max_slot" in text
    assert "expected_converter_version='0.2.0'" not in text
    assert "expected_data_version='0.2'" not in text
    assert "922922" not in text


def test_published_release_verifier_binds_express_check_to_requested_latest_release():
    text = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "releases/latest" in text
    assert "LATEST_RELEASE_TAG" in text
    assert 'test "$LATEST_RELEASE_TAG" = "$RELEASE_TAG"' in text


def test_published_release_verifier_exercises_stock_complete_zip_express_path():
    text = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert EXPRESS_STEP in text
    express = text.split(EXPRESS_STEP, 1)[1]
    assert EXPRESS_HOME in express

    # Plain repository use with no app/data checkout spec is what makes
    # Text-Fabric 13.1 enter Checkout.downloadComplete().
    plain_use = express.index("'alexsosn/Pseudepigrapha-TF'")
    network_block = express.index("socket.create_connection")
    local_reload = express.index("'alexsosn/Pseudepigrapha-TF:local'")

    assert plain_use < network_block < local_reload
    assert "checkout=release_tag" not in express[:network_block]
    assert "checkout='latest'" not in express[:network_block]
    assert 'checkout="latest"' not in express[:network_block]
    assert "checkout=\"local\"" in express or "checkout='local'" in express

    # A plain use() can fall back to ordinary GitHub acquisition after a failed
    # express attempt. Instrument Text-Fabric's own path and require success so
    # fallback cannot make a broken complete.zip look healthy.
    assert "Checkout.downloadComplete" in express
    assert "download_complete_results" in express
    assert "assert download_complete_results" in express
    assert "all(download_complete_results)" in express


def test_published_release_express_gate_checks_manifest_identity_and_keeps_tagged_gate():
    text = VERIFY_WORKFLOW.read_text(encoding="utf-8")
    express = text.split(EXPRESS_STEP, 1)[1]

    # Keep the exact-tag path as a separate immutable-release gate.
    assert "f'alexsosn/Pseudepigrapha-TF:{release_tag}'" in text
    assert "checkout=release_tag" in text

    # The new express path must prove it loaded the same generation that was
    # already cryptographically validated from the public release assets.
    for fragment in (
        "expected_data_version",
        "expected_converter_version",
        "expected_upstream",
        "expected_source_status",
        "expected_license_status",
        "expected_license",
        "generic['version']",
        "generic['converterVersion']",
        "generic['upstreamCommit']",
        "generic['sourceIdentityStatus']",
        "generic['contentLicenseStatus']",
        "generic['contentLicense']",
        "fresh_max_slot",
    ):
        assert fragment in express
