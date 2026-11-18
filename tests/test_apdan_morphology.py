"""Fail-closed ApDan TEI → native TF word overlay, without default publication."""
from __future__ import annotations

from pathlib import Path
import json

import pytest
from tf.fabric import Fabric

from pseudepigrapha_tf import build_tf_data
from pseudepigrapha_tf.apdan_morphology import (
    align_apdan_morphology,
    write_apdan_morphology_module,
)
from pseudepigrapha_tf.parser import parse_bytes
from pseudepigrapha_tf.writer import write_tf


SOURCE = """<book filename="ApDan" title="Apocalypse of Daniel">
  <version title="Greek" author="Heiser and Penner" language="Greek">
    <divisions><division label="Chapter" delimiter="."/><division label="Verse"/></divisions>
    <manuscripts>
      <ms abbrev="Heiser-Penner" language="Greek" show="yes"><name>Editor</name></ms>
    </manuscripts>
    <text><div number="2">
      <div number="1"><unit id="0"><reading option="0" mss="Heiser-Penner">Καὶ λόγος.</reading></unit></div>
      <div number="2"><unit id="1"><reading option="0" mss="Heiser-Penner">Ζωή·</reading></unit></div>
    </div></text>
  </version>
</book>"""

TEI = """<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ApDan">
  <teiHeader>
    <fileDesc>
      <publicationStmt>
        <availability status="restricted">
          <licence target="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</licence>
        </availability>
      </publicationStmt>
    </fileDesc>
  </teiHeader>
  <text xml:lang="grc"><body><div type="chapter" n="2" xml:id="ApDan.2">
    <head>Chapter 2</head>
    <ab type="verse" n="2.1" xml:id="ApDan.2.1">
      <w lemma="καί" pos="conj" msd="C">Καὶ</w>
      <w lemma="λόγος" pos="noun" msd="NNSM">λόγος</w><pc>.</pc>
    </ab>
    <ab type="verse" n="2.2" xml:id="ApDan.2.2">
      <w lemma="ζωή" pos="noun" msd="NNSF">Ζωή</w><pc>·</pc>
    </ab>
  </div></body></text>
</TEI>"""


@pytest.fixture
def corpus(tmp_path):
    source = SOURCE.encode("utf-8")
    model = parse_bytes(source, source_path="ApDan.xml")
    tf_dir = tmp_path / "base-tf"
    assert write_tf(build_tf_data([model]), tf_dir)
    api = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep").load(
        "ocp_book version_title source_file source_sha256 source_ref g_word_utf8 version_kind",
        silent="deep",
    )
    assert api is not None
    return tf_dir, api


def test_apdan_exact_word_morphology_is_on_existing_native_tf_slots(corpus):
    tf_dir, api = corpus
    aligned = align_apdan_morphology(api, SOURCE.encode(), TEI.encode())
    assert aligned.summary["verses"] == 2
    assert aligned.summary["words"] == 3
    assert aligned.summary["punctuation_elements"] == 2
    assert aligned.summary["source_declared_license"] == "CC-BY-NC-4.0"
    assert aligned.summary["source_declared_availability"] == "restricted"
    assert aligned.summary["redistribution_permission"] == "not_attested"
    slots = sorted(aligned.features["apdan_tei_lemma"])
    assert len(slots) == 3
    assert [api.F.g_word_utf8.v(slot) for slot in slots] == ["Καὶ", "λόγος.", "Ζωή·"]
    assert [aligned.features["apdan_tei_lemma"][slot] for slot in slots] == [
        "καί", "λόγος", "ζωή"
    ]
    assert [aligned.features["apdan_tei_pos"][slot] for slot in slots] == [
        "conj", "noun", "noun"
    ]
    assert [aligned.features["apdan_tei_msd"][slot] for slot in slots] == [
        "C", "NNSM", "NNSF"
    ]
    assert not any(path.name.startswith("apdan_tei_") for path in tf_dir.glob("*.tf"))


@pytest.mark.parametrize(
    ("old", "new", "match"),
    [
        ('xml:id="ApDan"', 'xml:id="Other"', "identity"),
        ('status="restricted"', 'status="free"', "restricted|license"),
        ("by-nc/4.0/", "by/4.0/", "CC BY-NC|license"),
        ('lemma="λόγος"', 'lemma=""', "empty|lemma"),
        ('pos="conj"', 'pos=""', "empty|pos"),
        ('msd="NNSM"', 'msd=""', "empty|msd"),
        ('>λόγος</w>', '>ἄλλος</w>', "word|surface|mismatch"),
        ('n="2.2" xml:id="ApDan.2.2"', 'n="2.1" xml:id="ApDan.2.2"', "duplicate|verse"),
        ('<w lemma="ζωή" pos="noun" msd="NNSF">Ζωή</w>', "", "word|missing|count"),
        ('<w lemma="λόγος" pos="noun" msd="NNSM">λόγος</w>', '<w lemma="λόγος" pos="noun" msd="NNSM">λόγος</w><w lemma="λόγος" pos="noun" msd="NNSM">λόγος</w>', "word|count"),
        ('<pc>.</pc>', '<foobar>.</foobar>', "unexpected|element|punctuation"),
    ],
)
def test_apdan_bad_tei_fails_closed(corpus, old, new, match):
    _, api = corpus
    assert old in TEI
    with pytest.raises(ValueError, match=match):
        align_apdan_morphology(api, SOURCE.encode(), TEI.replace(old, new).encode())


def test_apdan_source_bytes_must_match_tf_book_provenance(corpus):
    _, api = corpus
    bad_source = SOURCE.replace("Καὶ λόγος.", "Καὶ ἀλήθεια.")
    with pytest.raises(ValueError, match="sha256|source"):
        align_apdan_morphology(api, bad_source.encode(), TEI.encode())


def test_apdan_module_requires_noncommercial_consent_and_isolation(corpus, tmp_path):
    tf_dir, api = corpus
    aligned = align_apdan_morphology(api, SOURCE.encode(), TEI.encode())
    overlay_dir = tmp_path / "private-cc-by-nc"
    with pytest.raises(ValueError, match="noncommercial|CC BY-NC|opt-in"):
        write_apdan_morphology_module(
            aligned, base_tf_directory=tf_dir, output=overlay_dir, accept_noncommercial=False
        )
    assert not overlay_dir.exists()
    with pytest.raises(ValueError, match="outside|separate|base"):
        write_apdan_morphology_module(
            aligned, base_tf_directory=tf_dir, output=tf_dir / "private",
            accept_noncommercial=True,
        )
    assert write_apdan_morphology_module(
        aligned, base_tf_directory=tf_dir, output=overlay_dir,
        accept_noncommercial=True,
    )
    assert (overlay_dir / "apdan_tei_lemma.tf").is_file()
    assert (overlay_dir / "apdan_tei_pos.tf").is_file()
    assert (overlay_dir / "apdan_tei_msd.tf").is_file()
    assert not (tf_dir / "apdan_tei_lemma.tf").exists()
    loaded = Fabric(
        locations=[str(tf_dir), str(overlay_dir)], modules=[""], silent="deep"
    ).load(
        "apdan_tei_lemma apdan_tei_pos apdan_tei_msd", silent="deep"
    )
    assert loaded is not None
    slot = min(aligned.features["apdan_tei_lemma"])
    assert loaded.F.apdan_tei_lemma.v(slot) == "καί"
    assert loaded.F.apdan_tei_pos.v(slot) == "conj"
    assert loaded.F.apdan_tei_msd.v(slot) == "C"
    md = loaded.TF.features["apdan_tei_lemma"].metaData
    assert md["sourceDeclaredLicense"] == "CC-BY-NC-4.0"
    assert md["sourceDeclaredAvailability"] == "restricted"
    assert md["redistributionPermission"] == "not_attested"


def test_researcher_cli_audits_without_distributing_annotation(corpus, tmp_path, capsys):
    from pseudepigrapha_tf.cli import main

    base, _ = corpus
    raw = tmp_path / "ApDan.xml"
    raw.write_text(SOURCE, encoding="utf-8")
    tei = tmp_path / "ApDan_TEI.xml"
    tei.write_text(TEI, encoding="utf-8")
    assert main(["apdan-morph", str(base), str(raw), str(tei)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["verses"] == 2 and report["words"] == 3
    assert report["source_declared_license"] == "CC-BY-NC-4.0"
    assert not any(p.name.startswith("apdan_tei_") for p in tmp_path.rglob("*.tf"))
    with pytest.raises(ValueError, match="noncommercial|--accept-noncommercial"):
        main([
            "apdan-morph", str(base), str(raw), str(tei),
            "--output", str(tmp_path / "morph"),
        ])
    assert not (tmp_path / "morph").exists()
