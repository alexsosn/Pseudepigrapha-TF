from pathlib import Path


def test_readme_documents_first_class_generated_translation_api() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Until those versions receive first-class provenance/alignment semantics" not in readme
    assert "from pseudepigrapha_tf import Apparatus, Translations" in readme
    assert "Translations(api)" in readme
    assert ".versions(" in readme
    assert ".aligned_units(" in readme
    assert ".passage(" in readme
    assert "OCP-Trans" in readme
    assert "synthetic" in readme.lower()
    assert "generatedTranslationLayer" in readme
