from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "build-corpus-release-assets.yml"
UPSTREAM_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"


def _text() -> str:
    assert WORKFLOW.is_file(), "canonical release-candidate asset workflow is missing"
    return WORKFLOW.read_text(encoding="utf-8")


def test_release_candidate_workflow_is_reusable_and_immutable():
    text = _text()

    assert "workflow_call:" in text
    assert "release_tag:" in text
    assert "release_commit:" in text
    assert "ref: ${{ inputs.release_commit }}" in text
    assert UPSTREAM_COMMIT in text
    assert "--upstream-commit " + UPSTREAM_COMMIT in text
    assert "checkout HEAD" not in text
    assert "upstream HEAD" not in text


def test_release_identity_verification_binds_real_tag_ref_to_requested_commit():
    text = _text()

    assert "refs/tags/$RELEASE_TAG" in text
    assert "^{commit}" in text
    assert 'TAG_COMMIT=' in text
    assert 'test "$TAG_COMMIT" = "$RELEASE_COMMIT"' in text


def test_release_candidate_workflow_builds_and_installs_wheel_not_editable_source():
    text = _text()

    assert "python -m build --wheel" in text
    assert "pip install -e" not in text
    assert "dist/*.whl" in text
    assert "pseudepigrapha-tf convert" in text


def test_release_candidate_workflow_stages_and_exports_only_validated_release_set():
    text = _text()

    assert "stage_distribution_assets" in text
    assert "dataset-manifest.json" in text
    assert "conversion-report.json" in text
    assert "tf-" in text and ".zip" in text
    assert "actions/upload-artifact@" in text
    assert "if-no-files-found: error" in text


def test_infrastructure_workflow_cannot_publish_a_live_github_release():
    text = _text()

    assert "gh release" not in text
    assert "softprops/action-gh-release" not in text
    assert "actions/create-release" not in text
    assert "releases: write" not in text
