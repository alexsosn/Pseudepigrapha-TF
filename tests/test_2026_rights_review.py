"""2026 source/edition rights evidence must fail closed, not certify copyright."""
from __future__ import annotations

from pathlib import Path

import pytest

from pseudepigrapha_tf.rights_review import (
    classify_root_document,
    classify_tei_mirror,
    build_2026_rights_evidence,
)


COMPACT = """<?xml version="1.0"?>
<book filename="CithDavid.xml" title="Citharismus">
  <version id="Latin" title="Latin Text" lang="lat">
    <divisions><division id="1" title="Text" type="section"/></divisions>
    <manuscripts><manuscript id="Phill" name="Codex"/></manuscripts>
    <text><div number="1"><unit id="1.1"><reading option="base" mss="Phill">Verbum.</reading></unit></div></text>
  </version>
  <version id="English" title="English Translation" lang="eng">
    <divisions><division id="1" title="Text" type="section"/></divisions>
    <manuscripts><manuscript id="Eng" name="English Translation"/></manuscripts>
    <text><div number="1"><unit id="1.1"><reading option="base" mss="Eng">Word.</reading></unit></div></text>
  </version>
</book>"""
INTRO = {
    "title": "Citharismus",
    "fields": {
        "status": "<p>Latin text with parallel English translation.</p>",
        "bibliography": "James 1893",
    },
}
TEI = """<TEI xmlns="http://www.tei-c.org/ns/1.0"
  xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:id="ApDan">
  <teiHeader><fileDesc><publicationStmt>
    <availability status="restricted">
      <licence target="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</licence>
    </availability>
  </publicationStmt></fileDesc></teiHeader>
  <text><body><div type="chapter" n="2"><ab type="verse" n="2.1">
    <w lemma="λόγος" pos="noun" msd="NNSM">λόγος</w>
  </ab></div></body></text>
</TEI>"""
MIRROR = """<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc>
    <titleStmt><respStmt>
      <resp>TEI P5 conversion from OCP Grammateus XML</resp>
    </respStmt></titleStmt>
    <publicationStmt><availability status="free">
      <licence target="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</licence>
    </availability></publicationStmt>
  </fileDesc></teiHeader>
  <text><body><ab>Text</ab></body></text>
</TEI>"""


def test_compact_english_is_flagged_for_rights_review_and_not_relicensed():
    result = classify_root_document(
        "CithDavid.xml", COMPACT.encode("utf-8"), INTRO
    )
    assert result["source_kind"] == "compact_parallel_english"
    assert result["core_candidate"] is True
    assert result["version_ids"] == ["Latin", "English"]
    assert result["translation_credit"] == "not_declared"
    assert result["per_work_copyright_field"] == "absent"
    assert result["rights_review_required"] is True
    assert len(result["sha256"]) == 64
    assert len(result["git_blob_sha1"]) == 40
    assert "license" not in result  # license assertions are captured separately


@pytest.mark.parametrize(
    ("xml", "metadata", "message"),
    [
        (COMPACT.replace('id="English"', 'id="Greek"'), INTRO, "English|translation|identity"),
        (COMPACT.replace('lang="eng"', 'lang="lat"'), INTRO, "English|language"),
        (COMPACT.replace('mss="Eng"', 'mss="Phantom"'), INTRO, "witness|manuscript"),
        (COMPACT.replace('id="1.1"', 'id="1.2"', 1), INTRO, "alignment|unit"),
        (COMPACT, None, "metadata"),
    ],
)
def test_compact_rights_source_identity_fails_closed(xml, metadata, message):
    with pytest.raises(ValueError, match=message):
        classify_root_document("CithDavid.xml", xml.encode(), metadata)



def test_general_2026_text_has_repo_wide_license_claim_not_independent_clearance():
    source = b'<book filename="Other" title="Other"><version title="Greek"/></book>'
    result = classify_root_document("Other.xml", source, None)
    assert result["source_kind"] == "grammateus_text"
    assert result["core_candidate"] is True
    # No per-edition permission or translator/editor claim may be inferred
    # from the source-wide README license badge.
    assert result["rights_review_required"] is True
    assert "license" not in result
    assert result["public_metadata_present"] is False
    assert result["per_work_copyright_html"] is None


def test_standard_metadata_preserves_literal_editor_citation_and_copyright():
    source = b'<book filename="ApDan" title="ApDan"><version title="Greek"/></book>'
    record = {
        "editor": "Source-declared Editor",
        "citation": "<p>Source citation</p>",
        "fields": {"copyright": "<p>Public domain.</p>"},
    }
    result = classify_root_document("ApDan.xml", source, record)
    assert result["source_kind"] == "grammateus_text"
    assert result["public_metadata_present"] is True
    assert result["intro_editor"] == "Source-declared Editor"
    assert result["intro_citation_html"] == "<p>Source citation</p>"
    assert result["per_work_copyright_html"] == "<p>Public domain.</p>"
    assert result["rights_review_required"] is True


def test_restricted_morphology_is_excluded_from_public_core():
    result = classify_root_document("ApDan_TEI.xml", TEI.encode(), None)
    assert result["source_kind"] == "restricted_tei_morphology"
    assert result["core_candidate"] is False
    assert result["source_declared_license"] == "CC-BY-NC-4.0"
    assert result["source_declared_availability"] == "restricted"
    assert result["rights_review_required"] is True


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        (TEI.replace('status="restricted"', 'status="free"'), "restricted"),
        (TEI.replace("by-nc/4.0/", "by/4.0/"), "CC BY-NC|license"),
        (TEI.replace('xml:id="ApDan"', 'xml:id="Other"'), "identity"),
    ],
)
def test_restricted_tei_fail_closed_on_license_and_identity(corrupt, message):
    with pytest.raises(ValueError, match=message):
        classify_root_document("ApDan_TEI.xml", corrupt.encode(), None)


def test_mirror_has_source_conversion_evidence_without_claiming_new_edition():
    result = classify_tei_mirror("CithDavid.xml", MIRROR.encode())
    assert result["source_kind"] == "derived_grammateus_tei_mirror"
    assert result["core_candidate"] is False
    assert result["source_declared_license"] == "CC-BY-4.0"
    assert result["rights_review_required"] is False


@pytest.mark.parametrize(
    "bad", [
        MIRROR.replace("TEI P5 conversion from OCP Grammateus XML", "My new edition"),
        MIRROR.replace("by/4.0/", "by-nc/4.0/"),
    ],
)
def test_mirror_unknown_provenance_or_rights_fails_closed(bad):
    with pytest.raises(ValueError, match="mirror|license|conversion"):
        classify_tei_mirror("CithDavid.xml", bad.encode())


def test_inventory_cannot_attest_missing_or_unreviewed_source(tmp_path):
    root = tmp_path / "ocp"
    docs = root / "static" / "docs"
    docs.mkdir(parents=True)
    (docs / "CithDavid.xml").write_text(COMPACT)
    with pytest.raises(ValueError, match="67|README|license|source"):
        build_2026_rights_evidence(root)
