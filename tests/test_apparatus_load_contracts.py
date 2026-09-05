from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.fabric import Fabric

from pseudepigrapha_tf import Apparatus
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


def _load(tmp_path, features: str):
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    output = tmp_path / "tf"
    assert write_tf(data, output)
    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = TF.load(features, silent="deep")
    assert api is not None
    return api


def _unit(api):
    return next(iter(api.F.otype.s("unit")))


def _manuscript(api):
    return next(iter(api.F.otype.s("manuscript")))


def test_unit_readings_names_missing_reading_of_edge(tmp_path):
    api = _load(tmp_path, "reading_text is_primary witness")
    with pytest.raises(ValueError, match="reading_of"):
        Apparatus(api).unit_readings(_unit(api))


def test_witness_reading_names_missing_witness_edge(tmp_path):
    api = _load(tmp_path, "reading_of reading_text is_primary")
    with pytest.raises(ValueError, match="witness"):
        Apparatus(api).witness_reading(_unit(api), _manuscript(api))


def test_witness_state_names_missing_unit_id_instead_of_using_node_id(tmp_path):
    api = _load(tmp_path, "reading_text reading_of witness")
    with pytest.raises(ValueError, match="unit_id"):
        Apparatus(api).witness_state(_unit(api), _manuscript(api))


def test_apparatus_names_missing_is_primary_feature(tmp_path):
    api = _load(tmp_path, "reading_of reading_text witness")
    with pytest.raises(ValueError, match="is_primary"):
        Apparatus(api).apparatus(_unit(api))


def test_apparatus_names_missing_witness_edge(tmp_path):
    api = _load(tmp_path, "reading_of reading_text is_primary")
    with pytest.raises(ValueError, match="witness"):
        Apparatus(api).apparatus(_unit(api))


def test_passage_rejects_missing_is_primary_instead_of_silently_marking_false(tmp_path):
    api = _load(
        tmp_path,
        "reading_text ms_abbrev undefined_manuscript unit_id "
        "reading_of witness manuscript_of",
    )
    with pytest.raises(ValueError, match="is_primary"):
        Apparatus(api).passage("Sample", "1", "2")


def test_passage_names_missing_witness_edge(tmp_path):
    api = _load(
        tmp_path,
        "reading_text is_primary ms_abbrev undefined_manuscript unit_id "
        "reading_of manuscript_of",
    )
    with pytest.raises(ValueError, match="witness"):
        Apparatus(api).passage("Sample", "1", "2")


def test_passage_ms_abbrev_is_auto_loaded_by_manuscript_default_format(tmp_path):
    api = _load(
        tmp_path,
        "reading_text is_primary undefined_manuscript unit_id "
        "reading_of witness manuscript_of",
    )
    # Text-Fabric compiles fmt:manuscript-default={ms_abbrev}, so generated
    # corpora expose this format dependency even when it is omitted above.
    assert getattr(api.F, "ms_abbrev", None) is not None
    passage = Apparatus(api).passage("Sample", "1", "2")
    assert set(passage["witnesses"]) == {"A", "B", "C"}


def test_passage_names_missing_unit_id_instead_of_using_node_ids(tmp_path):
    api = _load(
        tmp_path,
        "reading_text is_primary ms_abbrev undefined_manuscript "
        "reading_of witness manuscript_of",
    )
    with pytest.raises(ValueError, match="unit_id"):
        Apparatus(api).passage("Sample", "1", "2")


def test_passage_does_not_require_optional_display_metadata(tmp_path):
    api = _load(
        tmp_path,
        "reading_text is_primary ms_abbrev undefined_manuscript unit_id "
        "reading_of witness manuscript_of",
    )
    passage = Apparatus(api).passage("Sample", "1", "2")
    assert passage["units"][0]["unit"] == "1"
    assert set(passage["witnesses"]) == {"A", "B", "C"}
    assert passage["source_refs"] == ()
    assert [reading["primary"] for reading in passage["units"][0]["readings"]] == [True, False]
    assert all(record["language"] == "" for record in passage["witnesses"].values())
    assert all(record["name"] == "" for record in passage["witnesses"].values())
    assert all(record["show"] == "" for record in passage["witnesses"].values())


def test_work_passage_available_section_names_missing_is_primary(tmp_path):
    api = _load(
        tmp_path,
        "ocp_book reading_text ms_abbrev undefined_manuscript unit_id "
        "reading_of witness manuscript_of",
    )
    with pytest.raises(ValueError, match="is_primary"):
        Apparatus(api).work_passage("Sample", "1", "2")


def test_work_passage_available_section_names_missing_witness(tmp_path):
    api = _load(
        tmp_path,
        "ocp_book reading_text is_primary ms_abbrev undefined_manuscript unit_id "
        "reading_of manuscript_of",
    )
    with pytest.raises(ValueError, match="witness"):
        Apparatus(api).work_passage("Sample", "1", "2")


def test_work_passage_available_section_names_missing_unit_id(tmp_path):
    api = _load(
        tmp_path,
        "ocp_book reading_text is_primary ms_abbrev undefined_manuscript "
        "reading_of witness manuscript_of",
    )
    with pytest.raises(ValueError, match="unit_id"):
        Apparatus(api).work_passage("Sample", "1", "2")


def test_work_passage_absent_section_does_not_require_passage_only_features(tmp_path):
    api = _load(tmp_path, "ocp_book ms_abbrev undefined_manuscript manuscript_of")
    result = Apparatus(api).work_passage("Sample", "99", "1")
    assert result["versions"]["Sample"]["status"] == "not_present"
    assert set(result["versions"]["Sample"]["witnesses"]) == {"A", "B", "C"}
    assert result["versions"]["Sample"]["passage"] is None
