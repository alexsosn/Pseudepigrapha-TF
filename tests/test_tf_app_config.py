from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.core.files import readYaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "app" / "config.yaml"

TECHNICAL_TYPES = {
    "div",
    "unit",
    "reading",
    "variant_word",
    "manuscript",
    "resource",
    "version_metadata",
    "ellipsis",
    "orphan_reading",
    "document_metadata",
}


def _config():
    return readYaml(asFile=str(CONFIG), plain=True)


def test_app_declares_researcher_facing_text_defaults():
    cfg = _config()
    display = cfg["dataDisplay"]

    assert display["textFormat"] == "text-orig-full"
    assert display["exampleSection"] == "1En__Ethiopic 1:1"
    assert "1En__Ethiopic 1:1" in display["exampleSectionHtml"]


def test_app_routes_general_help_to_tracked_documentation():
    cfg = _config()
    docs = cfg["docs"]

    assert docs["docPage"] == "tf-app"
    assert (ROOT / "docs" / "tf-app.md").is_file()


def test_app_has_explicit_policies_for_all_technical_anchor_types():
    cfg = _config()
    type_display = cfg["typeDisplay"]

    assert TECHNICAL_TYPES <= set(type_display)
    for node_type in TECHNICAL_TYPES:
        assert type_display[node_type].get("hidden") is True, node_type

    assert type_display["variant_word"]["level"] == 0
    assert type_display["manuscript"]["label"] == "{ms_abbrev}"
    assert type_display["resource"]["label"] == "{resource_name}"
    assert type_display["version_metadata"]["label"] == "{version_title}"
    assert type_display["document_metadata"]["label"] == "{intro_label}"


def test_app_surfaces_version_identity_on_book_nodes():
    cfg = _config()
    book_features = set(cfg["typeDisplay"]["book"]["features"].split())

    assert {"version_title", "version_kind", "language"} <= book_features


def test_app_does_not_claim_unpublished_remote_tf_data_or_single_writing_system():
    cfg = _config()
    provenance = cfg["provenanceSpec"]

    assert provenance["version"] == 0.1 or provenance["version"] == "0.1"
    assert not ({"org", "repo", "relative"} & set(provenance))
    assert not ({"webBase", "webUrl", "webUrlLex"} & set(provenance))
    assert "writing" not in cfg
