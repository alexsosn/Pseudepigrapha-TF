"""RED-first contract: a one-shot guarded GitHub Actions launcher for 1.1 (#206)."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / ".github" / "workflows" / "launch-v1-1-release.yml"
PUBLISHER = ROOT / ".github" / "workflows" / "publish-corpus-release.yml"


def _launcher() -> str:
    assert LAUNCH.is_file(), "guarded one-shot release workflow not yet implemented"
    return LAUNCH.read_text(encoding="utf-8")


def test_launcher_only_consumes_successful_own_main_push_ci():
    text = _launcher()
    assert "workflow_run:" in text
    assert "workflows: [test]" in text
    assert "types: [completed]" in text
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "github.event.workflow_run.event == 'push'" in text
    assert "github.event.workflow_run.head_branch == 'main'" in text
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in text
    assert "pull_request:" not in text
    assert "schedule:" not in text
    assert "workflow_dispatch:" not in text


def test_launcher_requires_exact_checked_and_still_current_commit():
    text = _launcher()
    assert "github.event.workflow_run.head_sha" in text
    assert "ref: ${{ github.event.workflow_run.head_sha }}" in text
    assert 'git rev-parse HEAD' in text
    assert 'TARGET_COMMIT' in text
    assert 'refs/heads/main' in text
    assert 'test "$CURRENT_MAIN" = "$TARGET_COMMIT"' in text
    assert "pyproject.toml" in text
    assert "app/config.yaml" in text
    assert "v1.1.0" in text
    assert "1.1" in text


def test_launcher_has_scoped_credential_and_never_overwrites_release():
    text = _launcher()
    assert "contents: write" in text
    assert "actions: write" in text
    assert "GITHUB_TOKEN" in text or "GH_TOKEN" in text
    assert "git/ref/tags/" in text
    assert "releases/tags/" in text
    assert "git/refs" in text
    assert "gh api" in text
    assert "gh workflow run publish-corpus-release.yml" in text
    # A draft or incomplete prior release must never be reported as published.
    assert "existing['draft']" in text
    assert "existing['prerelease']" in text
    assert "tf-1.1.zip" in text
    assert "complete.zip" in text
    assert "conversion-report.json" in text
    assert "dataset-manifest.json" in text
    assert '--ref "$RELEASE_TAG"' in text
    assert '-f release_commit="$TARGET_COMMIT"' in text
    assert '-f release_tag="$RELEASE_TAG"' in text
    assert "git tag -f" not in text
    assert "--force" not in text
    assert "--clobber" not in text
    assert "gh release create" not in text
    assert "gh release upload" not in text
    assert "gh release edit" not in text
    assert "gh release delete" not in text
    assert "pip install" not in text
    assert "curl | bash" not in text


def test_actual_immutable_asset_publisher_contract_is_retained():
    _launcher()
    publisher = PUBLISHER.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in publisher
    assert "release_tag:" in publisher
    assert "release_commit:" in publisher
    assert 'test "$GITHUB_SHA" = "$RELEASE_COMMIT"' in publisher
    assert "gh release create" in publisher
    assert "--verify-tag" in publisher
    assert "--draft=false" in publisher
    assert "verify-live:" in publisher
