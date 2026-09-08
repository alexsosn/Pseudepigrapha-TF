from __future__ import annotations

from werkzeug.datastructures import MultiDict

from pseudepigrapha_tf import comparison, web


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


def test_renderer_submits_empty_witness_sentinel_for_each_selectable_source_version():
    model = {
        "work": "Work",
        "title": "Work",
        "chapter": "1",
        "verse": "2",
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
