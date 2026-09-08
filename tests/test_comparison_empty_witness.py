from __future__ import annotations

from inspect import signature
from urllib.parse import parse_qs, urlsplit

from werkzeug.datastructures import MultiDict

from pseudepigrapha_tf import comparison, web
from pseudepigrapha_tf.release_identity import TF_DATA_VERSION


def test_witness_query_distinguishes_explicit_empty_selection_from_no_selection():
    assert web._witness_selection(MultiDict()) is None
    assert web._witness_selection(
        MultiDict([("witness.Work__Greek", "")])
    ) == {"Work__Greek": ()}
    assert web._witness_selection(
        MultiDict(
            [
                ("witness.Work__Greek", ""),
                ("witness.Work__Greek", "A"),
            ]
        )
    ) == {"Work__Greek": ("A",)}


def test_comparison_href_preserves_explicit_empty_witness_selection():
    href = comparison.comparison_href(
        "Work",
        "1",
        "3",
        selected_versions=("Work__Greek",),
        selected_witnesses={"Work__Greek": ()},
    )
    query = parse_qs(urlsplit(href).query, keep_blank_values=True)

    assert query["version"] == ["Work__Greek"]
    assert query["witness.Work__Greek"] == [""]


def test_renderer_submits_and_navigates_explicit_empty_witness_selection():
    model = {
        "work": "Work",
        "title": "Work",
        "chapter": "1",
        "verse": "2",
        "navigation": {
            "context_version": "Work__Greek",
            "previous": None,
            "next": ("1", "3"),
        },
        "version_choices": (
            {
                "id": "Work__Greek",
                "title": "Greek",
                "language": "Greek",
                "author": "",
                "status": "available",
                "selected": True,
            },
        ),
        "versions": (
            {
                "id": "Work__Greek",
                "title": "Greek",
                "language": "Greek",
                "author": "",
                "status": "available",
                "primary_segments": (),
                "witness_choices": (
                    {
                        "abbrev": "A",
                        "name": "Witness A",
                        "language": "Greek",
                        "declared": True,
                        "show": "yes",
                        "selected": False,
                    },
                ),
                "witnesses": (),
                "translations": (),
            },
        ),
        "metadata_only_versions": (),
    }

    html = comparison.render_passage_comparison(model)

    assert (
        '<input type="hidden" name="witness.Work__Greek" value="" '
        'form="comparison-controls">'
    ) in html
    assert (
        'name="witness.Work__Greek" value="A" form="comparison-controls"'
    ) in html
    assert "witness.Work__Greek=" in html


def test_programmatic_browser_defaults_track_authoritative_tf_data_version():
    load_default = signature(web.load_local_comparison_web_app).parameters["version"].default
    run_default = signature(web.run_local_comparison_browser).parameters["version"].default

    assert load_default == TF_DATA_VERSION
    assert run_default == TF_DATA_VERSION
