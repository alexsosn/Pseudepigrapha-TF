from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pseudepigrapha_tf import build_tf_data
from pseudepigrapha_tf.feature_docs import render_feature_docs, serialized_feature_contract
from pseudepigrapha_tf.parser import parse_file


FIXTURE = Path(__file__).parent / "fixtures" / "sample.xml"


def _data():
    return build_tf_data([parse_file(FIXTURE)])


def test_global_edge_page_does_not_depend_on_fixture_serialization_presence():
    absent = _data()
    absent.edge_features.pop("resource_of", None)
    present = deepcopy(absent)
    present.edge_features["resource_of"] = {}

    absent_page = render_feature_docs(absent)["resource_of.md"]
    present_page = render_feature_docs(present)["resource_of.md"]

    assert absent_page == present_page
    assert "**Supported by converter:** yes" in present_page


def test_programmatic_contract_still_reports_actual_fixture_serialization():
    absent = _data()
    absent.edge_features.pop("resource_of", None)
    present = deepcopy(absent)
    present.edge_features["resource_of"] = {}

    assert serialized_feature_contract(absent, include_supported=True)["edge"]["resource_of"]["serialized"] is False
    assert serialized_feature_contract(present, include_supported=True)["edge"]["resource_of"]["serialized"] is True
