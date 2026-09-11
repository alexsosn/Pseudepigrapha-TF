from __future__ import annotations

from html import escape
from pathlib import Path
import sys
from urllib.parse import quote

from tf.fabric import Fabric

from pseudepigrapha_tf.comparison import (
    build_passage_comparison,
    render_passage_comparison,
)
from pseudepigrapha_tf.release_identity import TF_DATA_VERSION
from pseudepigrapha_tf.web import load_local_comparison_web_app
from pinned_classification_acceptance import verify as verify_classifications
from pinned_translation_acceptance import verify as verify_translations


FEATURES = (
    "reading_text ms_abbrev ms_language ms_name ms_show undefined_manuscript "
    "synthetic_witness source_ref is_primary unit_id unit_index "
    "prefix_utf8 g_word_utf8 trailer_utf8 boundary_utf8 version_title version_id "
    "version_kind generated_language generation_marker generation_method generation_model "
    "is_metadata_only ocp_book title language author reading_of witness manuscript_of "
    "translation_of translation_unit_of"
)


def _version(model: dict[str, object], version_id: str) -> dict[str, object]:
    return next(
        record
        for record in model["versions"]
        if isinstance(record, dict) and record.get("id") == version_id
    )


def _witness(version: dict[str, object], siglum: str) -> dict[str, object]:
    return next(
        record
        for record in version["witnesses"]
        if isinstance(record, dict) and record.get("abbrev") == siglum
    )


def verify(tf_dir: Path) -> None:
    TF = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep")
    api = TF.load(FEATURES, silent="deep")
    assert api is not None

    model = build_passage_comparison(
        api,
        "1En",
        "1",
        "2",
        selected_versions=("1En__Ethiopic", "1En__Greek"),
        selected_witnesses={"1En__Ethiopic": ("p", "Bertalotto")},
    )

    source_choices = tuple(choice["id"] for choice in model["version_choices"])
    assert {"1En__Ethiopic", "1En__Qumran_Aramaic", "1En__Latin_Fragments", "1En__Greek"} == set(source_choices)
    assert all("translation" not in version_id.lower() for version_id in source_choices)

    ethiopic = _version(model, "1En__Ethiopic")
    assert ethiopic["status"] == "available"
    assert [row["abbrev"] for row in ethiopic["witnesses"]] == ["p", "Bertalotto"]

    p = _witness(ethiopic, "p")
    bertalotto = _witness(ethiopic, "Bertalotto")
    p_segments = tuple((segment["status"], segment.get("text")) for segment in p["segments"])
    bertalotto_segments = tuple(
        (segment["status"], segment.get("text")) for segment in bertalotto["segments"]
    )
    assert p_segments != bertalotto_segments
    assert any(left != right for left, right in zip(p_segments, bertalotto_segments, strict=True))

    translations = tuple(ethiopic["translations"])
    assert {row["language"] for row in translations} >= {"English", "French"}
    assert all(row["source_id"] == "1En__Ethiopic" for row in translations)
    available = tuple(row for row in translations if row["status"] == "available")
    assert available
    assert all(row["units"] for row in available)
    for row in available:
        assert all(unit["source_unit_id"] for unit in row["units"])
        assert all("source_text" in unit and "translation_text" in unit for unit in row["units"])

    html = render_passage_comparison(model)
    ethiopic_start = html.index('data-version-id="1En__Ethiopic"')
    greek_start = html.index('data-version-id="1En__Greek"')
    first_translation = available[0]
    translation_text = escape(first_translation["text"], quote=True)
    assert translation_text
    translation_pos = html.index(translation_text)
    assert ethiopic_start < translation_pos < greek_start
    assert f'data-translation-id="{first_translation["id"]}"' in html
    assert f'data-version-id="{first_translation["id"]}"' not in html

    # Duplicate source citations are exposed as distinct TF sections. Generated
    # translations are aligned occurrence-by-occurrence, so the real web route
    # must use those alignment edges rather than assuming that the generated
    # section label selects the same duplicate occurrence as the source label.
    flask_app = load_local_comparison_web_app(
        tf_dir,
        Path("app"),
        version=TF_DATA_VERSION,
        silent="deep",
    )
    client = flask_app.test_client()
    first = client.get("/compare?work=4Ezra&chapter=10&verse=4")
    first_html = first.get_data(as_text=True)
    assert first.status_code == 200, first_html
    assert 'data-version-id="4Ezra__Syriac"' in first_html
    assert 'data-translation-id="4Ezra__Syriac__translation__English"' in first_html

    second = client.get(
        "/compare?work=4Ezra&chapter=10&verse=" + quote("4~2")
    )
    second_html = second.get_data(as_text=True)
    assert second.status_code == 200, second_html
    assert 'data-version-id="4Ezra__Syriac"' in second_html

    # Exhaustively close raw-source -> serialized graph -> public translation
    # API parity on this same full-corpus materialization.
    verify_translations(api, Path('/tmp/ocp/static/docs'))

    # Close the scholarly-metadata API parity gap on this same pinned
    # full-corpus materialization rather than launching a second conversion.
    verify_classifications(tf_dir)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: pinned_comparison_acceptance.py TF_DIR")
    verify(Path(sys.argv[1]))
