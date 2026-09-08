from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pseudepigrapha_tf
from pseudepigrapha_tf import cli
from pseudepigrapha_tf.conversion import build_tf_data as build_conversion_tf_data
from pseudepigrapha_tf.graph import build_tf_data as build_graph_tf_data
from pseudepigrapha_tf.parser import parse_file


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
EXPECTED_PACKAGE_VERSION = "0.2.0"
EXPECTED_DATA_VERSION = "0.2"
EXPECTED_RELEASE_TAG = "v0.2.0"
EXPECTED_TF_ASSET = "tf-0.2.zip"
PUBLISH_WORKFLOW = ROOT / ".github" / "workflows" / "publish-corpus-release.yml"


def _app_data_version() -> str:
    text = (ROOT / "app" / "config.yaml").read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^provenanceSpec:\s*$.*?^\s+version:\s*[\"']?([^\"'\s#]+)",
        text,
    )
    assert match is not None, "app/config.yaml provenanceSpec.version is missing"
    return match.group(1)


def test_frozen_release_identity_is_consistent_across_owned_surfaces():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    materializer = json.loads((ROOT / "agora.materializer.json").read_text(encoding="utf-8"))
    cli_args = cli._parser().parse_args(["convert", "source"])

    assert project["project"]["version"] == EXPECTED_PACKAGE_VERSION
    assert pseudepigrapha_tf.__version__ == EXPECTED_PACKAGE_VERSION
    assert materializer["plugin"]["version"] == EXPECTED_PACKAGE_VERSION
    assert _app_data_version() == EXPECTED_DATA_VERSION
    assert cli_args.output == Path(f"tf/{EXPECTED_DATA_VERSION}")
    assert f"v{project['project']['version']}" == EXPECTED_RELEASE_TAG
    assert f"tf-{_app_data_version()}.zip" == EXPECTED_TF_ASSET


def test_serialized_tf_data_version_matches_frozen_release_identity_by_default():
    data = build_graph_tf_data([parse_file(FIXTURES / "sample.xml")])

    assert data.metadata[""]["version"] == EXPECTED_DATA_VERSION
    assert data.metadata[""]["converterVersion"] == EXPECTED_PACKAGE_VERSION


def test_public_conversion_builder_defaults_match_frozen_release_identity():
    data = build_conversion_tf_data([parse_file(FIXTURES / "sample.xml")])

    assert data.metadata[""]["version"] == EXPECTED_DATA_VERSION
    assert data.metadata[""]["converterVersion"] == EXPECTED_PACKAGE_VERSION


def test_release_publisher_is_explicit_delegated_and_no_clobber():
    assert PUBLISH_WORKFLOW.is_file(), "permanent corpus release publisher is missing"
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "release_tag:" in text
    assert "release_commit:" in text
    assert "uses: ./.github/workflows/build-corpus-release-assets.yml" in text
    assert "release_tag: ${{ inputs.release_tag }}" in text
    assert "release_commit: ${{ inputs.release_commit }}" in text
    assert "actions/download-artifact@v4" in text
    assert "pseudepigrapha-tf-corpus-release-candidate" in text
    assert "gh release view" in text
    assert "gh release create" in text
    assert "--verify-tag" in text
    assert "--clobber" not in text
    assert "git push --force" not in text
    assert "git tag -f" not in text


def test_release_publisher_binds_workflow_revision_to_requested_release_commit():
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "preflight:" in text
    assert 'GITHUB_SHA: ${{ github.sha }}' in text
    assert 'RELEASE_COMMIT: ${{ inputs.release_commit }}' in text
    assert 'test "$GITHUB_SHA" = "$RELEASE_COMMIT"' in text

    build = text.index("  build:")
    publish = text.index("  publish:")
    build_block = text[build:publish]
    assert "needs: preflight" in build_block


def test_release_stays_draft_until_canonical_asset_set_is_verified():
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    create = text.index('gh release create "$RELEASE_TAG"')
    verify = text.index("Verify published asset-name set")
    promote = text.index('gh release edit "$RELEASE_TAG"')

    assert create < verify < promote
    assert "--draft" in text[create:verify]
    assert "isDraft" in text[verify:promote]
    assert "release['isDraft']" in text[verify:promote]
    assert "--draft=false" in text[promote:]


def test_draft_release_bytes_are_revalidated_before_public_promotion():
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    create = text.index('gh release create "$RELEASE_TAG"')
    draft_validation = text.index("Download and validate draft release bytes")
    promote = text.index('gh release edit "$RELEASE_TAG"')
    validation_block = text[draft_validation:promote]

    assert create < draft_validation < promote
    assert 'gh release download "$RELEASE_TAG"' in validation_block
    assert "validate_distribution" in validation_block
    assert "expected_release_tag=os.environ['RELEASE_TAG']" in validation_block
    assert "expected_release_commit=os.environ['RELEASE_COMMIT']" in validation_block
    assert "expected_converter_version='0.2.0'" in validation_block
    assert "expected_data_version='0.2'" in validation_block


def test_release_publisher_exports_exact_canonical_asset_generation():
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    for asset in (
        "tf-${DATA_VERSION}.zip",
        "conversion-report.json",
        "dataset-manifest.json",
    ):
        assert asset in text
    assert "validate_distribution" in text


def test_release_publisher_verifies_fresh_remote_and_network_blocked_local_tf_loads():
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "from tf.app import use" in text
    assert "checkout=release_tag" in text
    assert "checkout=\"local\"" in text or "checkout='local'" in text
    assert "socket" in text
    assert "network" in text.lower()
    assert "converterVersion" in text
    assert "upstreamCommit" in text
    assert "contentLicenseStatus" in text
    assert "dataset-manifest.json" in text
