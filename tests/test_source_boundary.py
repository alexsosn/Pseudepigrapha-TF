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


def _write_mirror(root: Path, name: str = "Demo.xml", marker: str = "TEI P5 conversion from OCP Grammateus XML") -> None:
    directory = root / "tei"
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc>'
        '<titleStmt><respStmt><resp>' + marker + '</resp></respStmt></titleStmt>'
        '</fileDesc></teiHeader><text/></TEI>', encoding="utf-8"
    )


def test_source_boundary_accepts_declared_tei_mirror(tmp_path: Path) -> None:
    _write_supported_layout(tmp_path)
    _write_mirror(tmp_path)
    validate_source_boundary(tmp_path)


@pytest.mark.parametrize("name,marker", [
    ("Unknown.xml", "TEI P5 conversion from OCP Grammateus XML"),
    ("Demo.xml", "Independent edition"),
])
def test_source_boundary_rejects_unrecognized_tei_material(
    tmp_path: Path, name: str, marker: str
) -> None:
    _write_supported_layout(tmp_path)
    _write_mirror(tmp_path, name, marker)
    with pytest.raises(ValueError, match="tei/"):
        validate_source_boundary(tmp_path)


def test_source_boundary_rejects_non_tei_payload_with_morphology_filename(tmp_path: Path) -> None:
    _write_supported_layout(tmp_path)
    (tmp_path / "ApDan_TEI.xml").write_text('<book filename="ApDan_TEI"/>', encoding="utf-8")
    with pytest.raises(ValueError, match="ApDan_TEI"):
        validate_source_boundary(tmp_path)


def test_tei_mirror_symlink_is_not_followed(tmp_path: Path) -> None:
    _write_supported_layout(tmp_path)
    _write_mirror(tmp_path)
    (tmp_path / "tei" / "Demo.xml").unlink()
    (tmp_path / "tei" / "Demo.xml").symlink_to(tmp_path / "Demo.xml")
    with pytest.raises(ValueError, match="tei/Demo.xml"):
        validate_source_boundary(tmp_path)


def test_reviewed_morphology_is_not_a_second_edition(tmp_path: Path, monkeypatch) -> None:
    from pseudepigrapha_tf import apdan_morphology
    from pseudepigrapha_tf.source import excluded_source_layers
    from hashlib import sha256

    (tmp_path / "ApDan.xml").write_text('<book filename="ApDan"/>', encoding="utf-8")
    payload = b'<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ApDan"/>'
    (tmp_path / "ApDan_TEI.xml").write_bytes(payload)
    # The real immutable blob is covered by full upstream acceptance.
    monkeypatch.setattr(apdan_morphology, "CANDIDATE_MORPH_BLOB",
                        apdan_morphology._git_blob_sha(payload))
    assert excluded_source_layers(tmp_path) == [{
        "path": "ApDan_TEI.xml", "kind": "separate_morphology",
        "sha256": sha256(payload).hexdigest(),
    }]
    (tmp_path / "ApDan_TEI.xml").write_bytes(payload + b" ")
    with pytest.raises(ValueError, match="ApDan_TEI"):
        excluded_source_layers(tmp_path)
