from importlib.util import module_from_spec, spec_from_file_location
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

OWN_CONTENT_TEMPLATES = {
    "reading": "{reading_text}",
    "variant_word": "{prefix_utf8}{g_word_utf8}{trailer_utf8}",
    "manuscript": "{ms_abbrev}",
    "resource": "{resource_name}",
    "version_metadata": "{version_title}",
    "ellipsis": "{ellipsis_text}",
    "orphan_reading": "{reading_text}",
    "document_metadata": "{intro_label}",
}


def _config():
    return readYaml(asFile=str(CONFIG), plain=True)


def _app_module():
    spec = spec_from_file_location("pseudepigrapha_tf_browser_app", ROOT / "app" / "app.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_static_type_display_only_contains_universal_corpus_types():
    cfg = _config()

    assert set(cfg["typeDisplay"]) == {"book"}


def test_dynamic_app_has_explicit_policies_for_all_technical_anchor_types():
    module = _app_module()
    policies = module.TYPE_POLICIES

    assert set(policies) == TECHNICAL_TYPES
    assert policies["div"].get("base") is not True
    assert policies["unit"].get("base") is not True
    for node_type in TECHNICAL_TYPES:
        assert policies[node_type].get("hidden") is True, node_type

    for node_type, template in OWN_CONTENT_TEMPLATES.items():
        assert policies[node_type].get("base") is True, node_type
        assert policies[node_type].get("template") == template, node_type

    assert policies["manuscript"]["label"] == "{ms_abbrev}"
    assert policies["resource"]["label"] == "{resource_name}"
    assert policies["version_metadata"]["label"] == "{version_title}"
    assert policies["document_metadata"]["label"] == "{intro_label}"


def test_plain_custom_hook_matches_own_content_templates():
    module = _app_module()

    assert set(module.OWN_CONTENT_TYPES) == set(OWN_CONTENT_TEMPLATES)
    assert not ({"div", "unit"} & set(module.OWN_CONTENT_TYPES))


def test_app_surfaces_version_identity_on_book_nodes():
    cfg = _config()
    book_features = set(cfg["typeDisplay"]["book"]["features"].split())

    assert {"version_title", "version_kind", "language"} <= book_features


def test_app_does_not_claim_unpublished_remote_tf_data_or_single_writing_system():
    cfg = _config()
    provenance = cfg["provenanceSpec"]

    # Text-Fabric composes provenance paths from strings; an unquoted YAML
    # 0.1 becomes a float and crashes advanced-app startup in TF 13.1.0.
    assert provenance["version"] == "0.1"
    assert not ({"org", "repo", "relative"} & set(provenance))
    assert not ({"webBase", "webUrl", "webUrlLex"} & set(provenance))
    assert "writing" not in cfg
