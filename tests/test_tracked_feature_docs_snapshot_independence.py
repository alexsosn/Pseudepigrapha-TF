from __future__ import annotations

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
