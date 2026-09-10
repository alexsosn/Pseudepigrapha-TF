from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLISH_WORKFLOW = ROOT / ".github" / "workflows" / "publish-corpus-release.yml"


def _workflow() -> str:
    assert PUBLISH_WORKFLOW.is_file(), "permanent corpus release publisher is missing"
    return PUBLISH_WORKFLOW.read_text(encoding="utf-8")


def test_publisher_requires_repository_immutable_release_policy_before_publication():
    text = _workflow()

    # The release workflow may verify repository policy with ordinary read access,
    # but it must never grant itself repository-administration rights to enable it.
    assert "/immutable-releases" in text
    assert '"enabled"' in text or "['enabled']" in text
    assert "Administration" not in text
    assert "administration:" not in text

    policy_check = text.index("/immutable-releases")
    create = text.index('gh release create "$RELEASE_TAG"')
    assert policy_check < create


def test_publication_verifies_exact_release_is_immutable_and_attested():
    text = _workflow()

    promote = text.index('gh release edit "$RELEASE_TAG"')
    after_publish = text[promote:]

    assert "isImmutable" in after_publish or '"immutable"' in after_publish or "['immutable']" in after_publish
    assert "gh release verify" in after_publish
    assert "$RELEASE_TAG" in after_publish
    assert "dataset-manifest.json" in after_publish


def test_immutability_hardening_does_not_add_post_publication_mutation_paths():
    text = _workflow()

    assert "--clobber" not in text
    assert "git push --force" not in text
    assert "git tag -f" not in text
    assert "gh release delete" not in text
