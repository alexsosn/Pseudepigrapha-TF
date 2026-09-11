from pathlib import Path


def test_readme_documents_first_class_generated_translation_api() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Until those versions receive first-class provenance/alignment semantics" not in readme
    assert "from pseudepigrapha_tf import Apparatus" in readme
    assert "from pseudepigrapha_tf import Translations" in readme
    assert "T = Translations(app.api)" in readme
    assert "T.versions(" in readme
    assert "T.aligned_units(" in readme
    assert "translation_of" in readme
    assert "translation_unit_of" in readme
    assert "OCP-Trans" in readme
    assert "synthetic" in readme.lower()
