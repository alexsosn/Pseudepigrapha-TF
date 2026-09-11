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


def _get(client, url: str, expected_status: int = 200) -> str:
    response = client.get(url)
    body = response.get_data(as_text=True)
    assert response.status_code == expected_status, body
    return body


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

    flask_app = load_local_comparison_web_app(
        tf_dir,
        Path("app"),
        version=TF_DATA_VERSION,
        silent="deep",
    )
    client = flask_app.test_client()

    # Real route: ordinary passage, large witness inventory, metadata-only
    # sibling version, and Previous/Next navigation all coexist without
    # fabricating Coptic text.
    tjob = _get(client, "/compare?work=TJob&chapter=1&verse=1")
    assert 'class="metadata-only-versions"' in tjob
    assert "Coptic" in tjob
    assert tjob.count('type="checkbox" name="witness.') >= 10
    assert 'class="state-omission"' in tjob
    assert 'rel="prev"' in tjob and 'rel="next"' in tjob
    assert "technical anchor" not in tjob.lower()
    assert "oslots" not in tjob.lower()

    # Representative multi-version/witness/translation workflow through the
    # actual Flask route, preserving distinct missing-evidence states and exact
    # generated-to-source nesting.
    enoch = _get(
        client,
        "/compare?work=1En&chapter=1&verse=2"
        "&version=1En__Ethiopic&version=1En__Greek"
        "&witness.1En__Ethiopic=p&witness.1En__Ethiopic=Bertalotto",
    )
    assert 'class="state-omission"' in enoch
    assert 'class="state-unattested"' in enoch
    assert enoch.count('type="checkbox" name="witness.') >= 10
    assert 'rel="prev"' in enoch and 'rel="next"' in enoch
    enoch_ethiopic = enoch.index('data-version-id="1En__Ethiopic"')
    enoch_translation = enoch.index('data-translation-id=', enoch_ethiopic)
    enoch_greek = enoch.index('data-version-id="1En__Greek"')
    assert enoch_ethiopic < enoch_translation < enoch_greek

    # PssSol has both a normal high-witness passage and a genuine source
    # ambiguity at 1:5. The latter must remain a readable fail-closed 400 rather
    # than silently choosing one of two readings for the same manuscript/unit.
    psssol = _get(client, "/compare?work=PssSol&chapter=1&verse=0")
    assert psssol.count('type="checkbox" name="witness.') >= 10
    assert 'class="state-omission"' in psssol
    assert 'class="state-unattested"' in psssol
    ambiguous = _get(client, "/compare?work=PssSol&chapter=1&verse=5", 400)
    assert 'class="comparison-error"' in ambiguous
    assert "multiple readings at unit" in ambiguous

    # Aristob carries the upstream <elipsis/> structural anomaly and deep
    # section references. The comparison remains passage-centered; a sibling
    # source version may simply be not present here.
    aristob = _get(
        client,
        "/compare?work=Aristob&chapter=" + quote("7:32") + "&verse=13",
    )
    assert 'class="state-not-present"' in aristob
    assert "oslots" not in aristob.lower()

    # Duplicate source citations are distinct TF sections. Generated
    # translations must follow exact translation_unit_of occurrence edges, not
    # assume that independently assigned generated/source section suffixes match.
    first = _get(client, "/compare?work=4Ezra&chapter=10&verse=4")
    assert 'data-version-id="4Ezra__Syriac"' in first
    assert 'data-translation-id="4Ezra__Syriac__translation__English"' in first

    second = _get(
        client,
        "/compare?work=4Ezra&chapter=10&verse=" + quote("4~2"),
    )
    assert 'data-version-id="4Ezra__Syriac"' in second
    assert 'rel="prev"' in second or 'rel="next"' in second

    # Keep the already-working narrow-layout contract stable without adding a
    # frontend framework or visual redesign.
    css = Path("app/static/comparison.css").read_text()
    assert "@media (max-width: 760px)" in css
    assert "min-width: 0" in css
    assert "overflow-wrap: anywhere" in css
    assert "flex-wrap: wrap" in css

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
