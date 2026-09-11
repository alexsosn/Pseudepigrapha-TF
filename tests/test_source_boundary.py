from __future__ import annotations

from pathlib import Path

import pytest

from pseudepigrapha_tf.source import validate_source_boundary


def _write_supported_layout(root: Path) -> None:
    (root / "Demo.xml").write_text("<book filename=\"Demo\" title=\"Demo\"></book>", encoding="utf-8")
    (root / "intros.json").write_text("{}", encoding="utf-8")
    (root / "grammateus.dtd").write_text("<!ELEMENT book ANY>", encoding="utf-8")
    (root / "tags").write_text("!_TAG_FILE_FORMAT\t2\n", encoding="utf-8")
    (root / ".TJob.xml.un~").write_text("editor backup", encoding="utf-8")
    (root / "backups").mkdir()
    (root / "backups" / "old.xml.bak").write_text("backup", encoding="utf-8")
    (root / "drafts").mkdir()
    (root / "drafts" / "Draft.xml").write_text("draft", encoding="utf-8")


def test_source_boundary_accepts_published_inputs_and_reviewed_non_corpus_artifacts(
    tmp_path: Path,
) -> None:
    _write_supported_layout(tmp_path)

    validate_source_boundary(tmp_path)


@pytest.mark.parametrize(
    "filename",
    [
        "metadata.json",
        "metadata.CSV",
        "metadata.yaml",
        "metadata.YML",
        "corpus.sqlite",
        "corpus.db",
        "metadata.tsv",
        "new-export",
    ],
)
def test_source_boundary_rejects_unknown_root_level_material(
    tmp_path: Path,
    filename: str,
) -> None:
    _write_supported_layout(tmp_path)
    (tmp_path / filename).write_text("unexpected", encoding="utf-8")

    with pytest.raises(ValueError, match="unreviewed OCP source material"):
        validate_source_boundary(tmp_path)


def test_source_boundary_rejects_unreviewed_nested_directory(tmp_path: Path) -> None:
    _write_supported_layout(tmp_path)
    extra = tmp_path / "exports"
    extra.mkdir()
    (extra / "metadata.JSON").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="unreviewed OCP source material.*exports"):
        validate_source_boundary(tmp_path)


def test_source_boundary_rejects_xml_with_case_variant_extension(tmp_path: Path) -> None:
    _write_supported_layout(tmp_path)
    (tmp_path / "Extra.XML").write_text("<book/>", encoding="utf-8")

    with pytest.raises(ValueError, match="Extra\\.XML"):
        validate_source_boundary(tmp_path)
