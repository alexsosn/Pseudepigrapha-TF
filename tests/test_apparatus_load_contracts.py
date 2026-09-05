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


def test_passage_does_not_require_optional_display_metadata(tmp_path):
    api = _load(
        tmp_path,
        "reading_text is_primary undefined_manuscript "
        "reading_of witness manuscript_of",
    )
    passage = Apparatus(api).passage("Sample", "1", "2")
    assert len(passage["units"]) == 1
    assert [reading["primary"] for reading in passage["units"][0]["readings"]] == [True, False]


def test_work_passage_available_section_names_missing_is_primary(tmp_path):
    api = _load(
        tmp_path,
        "ocp_book reading_text undefined_manuscript "
        "reading_of witness manuscript_of",
    )
    with pytest.raises(ValueError, match="is_primary"):
        Apparatus(api).work_passage("Sample", "1", "2")


def test_work_passage_available_section_names_missing_witness(tmp_path):
    api = _load(
        tmp_path,
        "ocp_book reading_text is_primary undefined_manuscript "
        "reading_of manuscript_of",
    )
    with pytest.raises(ValueError, match="witness"):
        Apparatus(api).work_passage("Sample", "1", "2")


def test_work_passage_absent_section_does_not_require_passage_only_features(tmp_path):
    api = _load(tmp_path, "ocp_book undefined_manuscript manuscript_of")
    result = Apparatus(api).work_passage("Sample", "99", "1")
    assert result["versions"]["Sample"]["status"] == "not_present"
    assert result["versions"]["Sample"]["passage"] is None
