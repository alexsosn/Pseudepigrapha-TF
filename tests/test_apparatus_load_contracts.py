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


def test_reading_text_names_missing_feature(tmp_path):
    api = _load(tmp_path, "reading_of witness is_primary")
    unit = _unit(api)
    reading = next(iter(api.E.reading_of.t(unit)))
    with pytest.raises(ValueError, match="reading_text"):
        Apparatus(api).reading_text(reading)


def test_witness_reading_names_missing_witness_edge(tmp_path):
    api = _load(tmp_path, "reading_of reading_text is_primary")
    with pytest.raises(ValueError, match="witness"):
        Apparatus(api).witness_reading(_unit(api), _manuscript(api))


def test_apparatus_names_missing_is_primary_feature(tmp_path):
    api = _load(tmp_path, "reading_of reading_text witness")
    with pytest.raises(ValueError, match="is_primary"):
        Apparatus(api).apparatus(_unit(api))


def test_passage_rejects_missing_is_primary_instead_of_silently_marking_false(tmp_path):
    api = _load(
        tmp_path,
        "reading_text ms_abbrev undefined_manuscript unit_id "
        "reading_of witness manuscript_of",
    )
    with pytest.raises(ValueError, match="is_primary"):
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
