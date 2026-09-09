from pathlib import Path


def test_release_revalidation_supplies_exact_app_checkout():
    root = Path(__file__).parents[1]
    build = (root / ".github/workflows/build-corpus-release-assets.yml").read_text(encoding="utf-8")
    publish = (root / ".github/workflows/publish-corpus-release.yml").read_text(encoding="utf-8")
    tests = (root / ".github/workflows/test.yml").read_text(encoding="utf-8")

    assert "app_directory=app_directory" in build
    assert publish.count("app_directory=Path('app')") >= 3
    assert "app_directory=Path('app')" in tests
