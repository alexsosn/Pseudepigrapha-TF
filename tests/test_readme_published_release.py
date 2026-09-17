from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def _browse_and_compare_section() -> str:
    text = README.read_text(encoding="utf-8")
    start = text.index("## Browse and compare")
    end = text.index("## Resource expectations", start)
    return text[start:end]


def test_local_comparison_example_uses_matching_published_release_identity():
    section = _browse_and_compare_section()

    assert "releases/download/v0.2.0/tf-0.2.zip" in section
    assert "--branch v0.2.0" in section
    assert "/tmp/pseudepigrapha-tf/0.2" in section
    assert "--version 0.2" in section
    assert "releases/download/v1.0.0/tf-1.0.zip" not in section
    assert "--branch v1.0.0" not in section
