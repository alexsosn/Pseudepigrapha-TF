from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pseudepigrapha_tf import build_tf_data
from pseudepigrapha_tf.feature_docs import render_feature_docs
from pseudepigrapha_tf.parser import parse_file


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample.xml"


def _fixture_data():
    return build_tf_data([parse_file(FIXTURE)])


def test_tracked_reference_does_not_publish_fixture_local_absence_as_corpus_fact():
    pages = render_feature_docs(_fixture_data())

    # These optional layers are deliberately absent from the small synthetic
    # fixture but present in the exact pinned released corpus. Tracked global
    # help must therefore describe support without claiming corpus absence.
    for name in ("intro_title_json", "historical_genres_json"):
        page = pages[f"{name}.md"]
        assert "Serialized in this corpus:" not in page, name
        assert "**Supported by converter:** yes" in page, name

    tracked = (ROOT / "docs" / "features" / "intro_title_json.md").read_text(encoding="utf-8")
    assert "Serialized in this corpus:" not in tracked


def test_global_feature_page_scopes_observation_without_changing_support_claim():
    absent = _fixture_data()
    present = deepcopy(absent)
    node = max(present.node_features["otype"]) + 1
    present.node_features["otype"][node] = "document_metadata"
    present.node_features["intro_title_json"] = {node: '["probe"]'}
    present.edge_features["oslots"][node] = {1}

    absent_page = render_feature_docs(absent)["intro_title_json.md"]
    present_page = render_feature_docs(present)["intro_title_json.md"]

    for page in (absent_page, present_page):
        assert "Serialized in this corpus:" not in page
        assert "**Supported by converter:** yes" in page
        assert "**Supported node types:** `document_metadata`" in page
    assert "**Observed node types in render graph:** none in this render graph" in absent_page
    assert "**Observed node types in render graph:** `document_metadata`" in present_page
