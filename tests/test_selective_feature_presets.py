from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.fabric import Fabric

from pseudepigrapha_tf import Apparatus, Translations
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_bytes, parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


EXPECTED_TRANSLATION_FEATURES = (
    "book",
    "ocp_book",
    "version_title",
    "version_kind",
    "language",
    "generated_language",
    "generation_marker",
    "generation_method",
    "generation_model",
    "unit_id",
    "unit_index",
    "source_ref",
    "reading_text",
    "is_primary",
    "translation_of",
    "translation_unit_of",
    "reading_of",
)

EXPECTED_PASSAGE_FEATURES = (
    "reading_text",
    "is_primary",
    "ms_abbrev",
    "undefined_manuscript",
    "unit_id",
    "version_kind",
    "synthetic_witness",
    "reading_of",
    "witness",
    "manuscript_of",
)

EXPECTED_WORK_PASSAGE_FEATURES = (
    "ocp_book",
    "version_id",
    *EXPECTED_PASSAGE_FEATURES,
)


def _load(data, output: Path, features: tuple[str, ...]):
    assert write_tf(data, output)
    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = TF.load(" ".join(features), silent="deep")
    assert api is not None and api is not False
    return api


def _source_data():
    return build_tf_data([parse_file(FIXTURES / "sample.xml")])


def _generated_data():
    xml = b'''<?xml version="1.0"?>
<book filename="Marked" title="Marked">
  <version title="Greek" author="Editor" language="Greek">
    <divisions><division label="Chapter" delimiter=":"/><division label="Verse"/></divisions>
    <manuscripts><ms abbrev="G" language="Greek" show="yes"><name>G</name></ms></manuscripts>
    <text><div number="1"><div number="1"><unit id="1"><reading option="0" mss="G ">alpha</reading></unit></div></div></text>
  </version>
  <version title="Greek (French)" author="Editor" language="French">
    <divisions><division label="Chapter" delimiter=":"/><division label="Verse"/></divisions>
    <manuscripts><ms abbrev="OCP-Trans" language="French" show="yes"><name>OCP-Trans</name></ms></manuscripts>
    <text><div number="1"><div number="1"><unit id="fr_1"><reading option="0" mss="OCP-Trans ">traduction</reading></unit></div></div></text>
  </version>
</book>
'''
    return build_tf_data([parse_bytes(xml, source_path="Marked.xml")])


def test_public_feature_presets_freeze_documented_contracts():
    assert Translations.REQUIRED_FEATURES == EXPECTED_TRANSLATION_FEATURES
    assert Apparatus.PASSAGE_FEATURES == EXPECTED_PASSAGE_FEATURES
    assert Apparatus.WORK_PASSAGE_FEATURES == EXPECTED_WORK_PASSAGE_FEATURES
    assert isinstance(Translations.REQUIRED_FEATURES, tuple)
    assert isinstance(Apparatus.PASSAGE_FEATURES, tuple)
    assert isinstance(Apparatus.WORK_PASSAGE_FEATURES, tuple)


def test_apparatus_passage_preset_loads_raw_fabric_fixture(tmp_path):
    api = _load(_source_data(), tmp_path / "passage", Apparatus.PASSAGE_FEATURES)

    passage = Apparatus(api).passage("Sample", "1", "2")

    assert passage["units"][0]["unit"] == "1"
    assert set(passage["witnesses"]) == {"A", "B", "C"}


def test_apparatus_work_passage_preset_loads_raw_fabric_fixture(tmp_path):
    api = _load(_source_data(), tmp_path / "work", Apparatus.WORK_PASSAGE_FEATURES)

    result = Apparatus(api).work_passage("Sample", "1", "2")

    assert result["versions"]["Sample"]["status"] == "available"


def test_apparatus_preset_preserves_generated_layer_fail_closed_safety(tmp_path):
    api = _load(_generated_data(), tmp_path / "generated-apparatus", Apparatus.PASSAGE_FEATURES)
    generated_book = next(
        node
        for node in api.F.otype.s("book")
        if api.F.version_kind.v(node) == "generated_translation"
    )
    generated_id = api.T.sectionFromNode(generated_book)[0]

    with pytest.raises(ValueError, match="generated translation"):
        Apparatus(api).passage(generated_id, "1", "1")


def test_apparatus_preset_does_not_weaken_missing_feature_errors(tmp_path):
    features = tuple(name for name in Apparatus.PASSAGE_FEATURES if name != "is_primary")
    api = _load(_source_data(), tmp_path / "missing-required", features)

    with pytest.raises(ValueError, match="is_primary"):
        Apparatus(api).passage("Sample", "1", "2")


def test_translation_preset_supports_documented_raw_fabric_workflow(tmp_path):
    api = _load(_generated_data(), tmp_path / "translations", Translations.REQUIRED_FEATURES)
    helper = Translations(api)

    versions = helper.versions(work="Marked", language="French")
    assert len(versions) == 1
    generated_book = versions[0]["node"]
    aligned = helper.aligned_units(generated_book)
    passage = helper.passage(versions[0]["id"], "1", "1")

    assert len(aligned) == 1
    assert aligned[0]["translation_text"] == "traduction"
    assert aligned[0]["source_text"] == "alpha"
    assert passage["units"] == aligned
