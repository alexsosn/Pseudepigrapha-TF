from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.fabric import Fabric

from pseudepigrapha_tf import Apparatus
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"
BASE_FEATURES = (
    "reading_text ms_abbrev resource_name source_ref is_primary "
    "prefix_utf8 g_word_utf8 trailer_utf8 boundary_utf8 version_title"
)
PASSAGE_FEATURES = (
    "ms_language ms_name ms_show undefined_manuscript unit_id "
    "reading_of witness manuscript_of"
)
WORK_PASSAGE_FEATURES = f"{PASSAGE_FEATURES} book ocp_book title language author"
METADATA_WORK_PASSAGE_FEATURES = f"{WORK_PASSAGE_FEATURES} version_id"


def _load(data, tmp_path, extra_features=""):
    output = tmp_path / "tf"
    assert write_tf(data, output)
    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    features = f"{BASE_FEATURES} {extra_features}".strip()
    return TF.load(features, silent="deep")


def test_node_type_default_formats_prevent_misleading_text(tmp_path):
    api = _load(build_tf_data([parse_file(FIXTURES / "sample.xml")]), tmp_path)
    assert api is not None
    alternative = next(
        node for node in api.F.otype.s("reading")
        if api.F.is_primary.v(node) != 1 and api.F.reading_text.v(node)
    )
    assert api.T.text(alternative) == api.F.reading_text.v(alternative)
    manuscript = next(node for node in api.F.otype.s("manuscript") if api.F.ms_abbrev.v(node) == "A")
    assert api.T.text(manuscript) == "A"


def test_deep_source_reference_has_truthful_three_level_tf_address(tmp_path):
    api = _load(build_tf_data([parse_file(FIXTURES / "three_divisions.xml")]), tmp_path)
    assert api is not None
    assert tuple(api.T.sectionTypes) == ("book", "chapter", "verse")
    unit = next(node for node in api.F.otype.s("unit") if api.F.source_ref.v(node) == "9.4b.1")
    assert api.T.sectionFromNode(unit)[1:] == ("9.4b", "1")


def test_duplicate_source_sections_remain_individually_addressable(tmp_path):
    api = _load(build_tf_data([parse_file(FIXTURES / "duplicate_sections.xml")]), tmp_path)
    assert api is not None

    first = api.T.nodeFromSection(("Dup", "10", "4"))
    second = api.T.nodeFromSection(("Dup", "10", "4~2"))
    assert first is not None
    assert second is not None
    assert first != second
    assert api.F.source_ref.v(first) == "10:4"
    assert api.F.source_ref.v(second) == "10:4"


def test_metadata_only_version_has_nonmisleading_default_text(tmp_path):
    api = _load(build_tf_data([parse_file(FIXTURES / "metadata_only_version.xml")]), tmp_path)
    assert api is not None
    metadata = next(iter(api.F.otype.s("version_metadata")))
    assert api.T.text(metadata) == "Coptic"
    assert len(api.F.otype.s("book")) == 1


def test_empty_source_division_reloads_without_fabricated_section(tmp_path):
    api = _load(
        build_tf_data([parse_file(FIXTURES / "empty_division.xml")]),
        tmp_path,
        "div_fragment is_empty_div",
    )
    assert api is not None

    assert api.T.nodeFromSection(("EmptyDiv", "1", "1")) is not None
    assert api.T.nodeFromSection(("EmptyDiv", "1", "2")) is None
    empty_div = next(
        node for node in api.F.otype.s("div")
        if api.F.source_ref.v(node) == "1:2"
    )
    assert api.F.div_fragment.v(empty_div) == "empty-upstream"
    assert api.F.is_empty_div.v(empty_div) == 1
    assert len(api.E.oslots.f(empty_div)) == 1


def test_passage_returns_all_witnesses_with_explicit_coverage_states(tmp_path):
    api = _load(
        build_tf_data([parse_file(FIXTURES / "sample.xml")]),
        tmp_path,
        PASSAGE_FEATURES,
    )
    assert api is not None

    passage = Apparatus(api).passage("Sample", "1", "2")
    assert passage["reference"] == ("Sample", "1", "2")
    assert passage["source_refs"] == ("1:2",)
    assert len(passage["units"]) == 1
    assert [reading["text"] for reading in passage["units"][0]["readings"]] == ["", "πλήρης"]

    witnesses = passage["witnesses"]
    assert set(witnesses) == {"A", "B", "C"}

    assert witnesses["A"]["declared"] is True
    assert witnesses["A"]["segments"] == (
        {"unit": "1", "unit_node": passage["units"][0]["node"], "status": "omission", "reading": passage["units"][0]["readings"][0]["node"], "text": ""},
    )
    assert witnesses["A"]["complete"] is True
    assert witnesses["A"]["text"] == ""

    assert witnesses["B"]["segments"][0]["status"] == "reading"
    assert witnesses["B"]["segments"][0]["text"] == "πλήρης"
    assert witnesses["B"]["complete"] is True
    assert witnesses["B"]["text"] == "πλήρης"

    assert witnesses["C"]["segments"][0]["status"] == "unattested"
    assert witnesses["C"]["complete"] is False
    assert witnesses["C"]["text"] is None
    assert witnesses["C"]["attested_text"] == ""


def test_work_passage_returns_every_textual_version(tmp_path):
    api = _load(
        build_tf_data([parse_file(FIXTURES / "multiple_versions.xml")]),
        tmp_path,
        WORK_PASSAGE_FEATURES,
    )
    assert api is not None

    result = Apparatus(api).work_passage("Multi", "1", "1")
    assert result["work"] == "Multi"
    assert result["reference"] == ("1", "1")
    assert result["title"] == "Multi-version work"
    assert set(result["versions"]) == {"Multi__Syriac", "Multi__Greek"}
    assert result["metadata_only_versions"] == {}

    syriac = result["versions"]["Multi__Syriac"]
    assert syriac["title"] == "Syriac"
    assert syriac["language"] == "Syriac"
    assert syriac["status"] == "available"
    assert syriac["passage"]["witnesses"]["S"]["text"] == "ܐ ܒ"

    greek = result["versions"]["Multi__Greek"]
    assert greek["title"] == "Greek"
    assert greek["language"] == "Greek"
    assert greek["status"] == "available"
    assert greek["passage"]["witnesses"]["G"]["text"] == "α β"

    absent = Apparatus(api).work_passage("Multi", "99", "1")
    assert set(absent["versions"]) == {"Multi__Syriac", "Multi__Greek"}
    assert {version["status"] for version in absent["versions"].values()} == {"not_present"}
    assert all(version["passage"] is None for version in absent["versions"].values())


def test_work_passage_preserves_metadata_only_versions(tmp_path):
    api = _load(
        build_tf_data([parse_file(FIXTURES / "metadata_only_version.xml")]),
        tmp_path,
        METADATA_WORK_PASSAGE_FEATURES,
    )
    assert api is not None

    result = Apparatus(api).work_passage("Meta", "1", "1")
    assert set(result["versions"]) == {"Meta__Greek"}
    assert result["versions"]["Meta__Greek"]["status"] == "available"

    assert set(result["metadata_only_versions"]) == {"Meta__Coptic"}
    coptic = result["metadata_only_versions"]["Meta__Coptic"]
    assert coptic["title"] == "Coptic"
    assert coptic["language"] == "Coptic"
    assert coptic["status"] == "metadata_only"
    assert set(coptic["witnesses"]) == {"Coptic"}
    assert coptic["witnesses"]["Coptic"]["name"] == "P. Köln Inv. Nr. 3221"


def test_passage_distinguishes_declared_and_citation_only_witnesses(tmp_path):
    data = build_tf_data([parse_file(FIXTURES / "undeclared_witness.xml")])
    assert any("reading cites undeclared manuscript 'X'" in warning for warning in data.warnings)
    api = _load(data, tmp_path, WORK_PASSAGE_FEATURES)
    assert api is not None

    A = Apparatus(api)
    passage = A.passage("Undeclared", "1", "1")
    witnesses = passage["witnesses"]

    assert set(witnesses) == {"A", "X"}
    assert witnesses["A"]["declared"] is True
    assert witnesses["X"]["declared"] is False
    assert witnesses["X"]["segments"][0]["status"] == "reading"
    assert witnesses["X"]["text"] == "alpha"

    work = A.work_passage("Undeclared", "1", "1")
    version = work["versions"]["Undeclared"]
    assert set(version["witnesses"]) == {"A", "X"}
    assert version["witnesses"]["X"]["declared"] is False
    assert version["passage"]["witnesses"]["X"]["text"] == "alpha"
