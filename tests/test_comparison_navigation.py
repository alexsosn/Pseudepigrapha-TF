from __future__ import annotations

from types import SimpleNamespace

import pytest

from pseudepigrapha_tf import comparison


class Feature:
    def __init__(self, values):
        self.values = values

    def v(self, node):
        return self.values.get(node)


class OtypeFeature(Feature):
    def s(self, kind):
        return tuple(node for node, value in self.values.items() if value == kind)


class Locality:
    def __init__(self):
        self.descendants = {
            1: (101, 102, 103),
            2: (201, 203),
            3: (301, 302, 303),
        }

    def d(self, node, otype=None):
        assert otype == "verse"
        return self.descendants.get(node, ())


class Text:
    SECTIONS = {
        1: ("Work__A",),
        2: ("Work__B",),
        3: ("Work__A__translation__English",),
        101: ("Work__A", "1", "1"),
        102: ("Work__A", "1", "2"),
        103: ("Work__A", "2", "1"),
        201: ("Work__B", "1", "1"),
        203: ("Work__B", "2", "1"),
        301: ("Work__A__translation__English", "1", "1"),
        302: ("Work__A__translation__English", "1", "2"),
        303: ("Work__A__translation__English", "2", "1"),
    }

    def sectionFromNode(self, node):
        return self.SECTIONS[node]


def navigation_api():
    return SimpleNamespace(
        F=SimpleNamespace(
            otype=OtypeFeature(
                {
                    1: "book",
                    2: "book",
                    3: "book",
                    101: "verse",
                    102: "verse",
                    103: "verse",
                    201: "verse",
                    203: "verse",
                    301: "verse",
                    302: "verse",
                    303: "verse",
                }
            ),
            ocp_book=Feature({1: "Work", 2: "Work", 3: "Work"}),
            version_kind=Feature(
                {1: "source", 2: "source", 3: "generated_translation"}
            ),
        ),
        L=Locality(),
        T=Text(),
    )


def test_passage_neighbors_skip_preferred_version_without_current_passage_and_ignore_generated():
    nav = comparison.passage_neighbors(
        navigation_api(),
        "Work",
        "1",
        "2",
        preferred_versions=("Work__B", "Work__A"),
    )

    assert nav == {
        "context_version": "Work__A",
        "previous": ("1", "1"),
        "next": ("2", "1"),
    }


def test_passage_neighbors_at_edges_return_none_without_crossing_to_another_version():
    first = comparison.passage_neighbors(
        navigation_api(),
        "Work",
        "1",
        "1",
        preferred_versions=("Work__A",),
    )
    last = comparison.passage_neighbors(
        navigation_api(),
        "Work",
        "2",
        "1",
        preferred_versions=("Work__A",),
    )

    assert first["previous"] is None
    assert first["next"] == ("1", "2")
    assert last["previous"] == ("1", "2")
    assert last["next"] is None


def _render_model():
    return {
        "work": "Work",
        "title": "Work title",
        "chapter": "1",
        "verse": "2",
        "reference": ("1", "2"),
        "navigation": {
            "context_version": "Work__A",
            "previous": ("1", "1"),
            "next": ("2", "1"),
        },
        "version_choices": (
            {
                "id": "Work__A",
                "title": "A",
                "language": "Greek",
                "author": "",
                "status": "available",
                "selected": True,
            },
            {
                "id": "Work__B",
                "title": "B",
                "language": "Syriac",
                "author": "",
                "status": "available",
                "selected": True,
            },
        ),
        "versions": (
            {
                "id": "Work__A",
                "title": "A",
                "language": "Greek",
                "author": "",
                "status": "available",
                "primary_segments": (
                    {"unit": "1", "status": "reading", "text": "alpha"},
                ),
                "witness_choices": (
                    {
                        "abbrev": "A 1",
                        "name": "Codex A",
                        "language": "Greek",
                        "declared": True,
                        "show": "yes",
                        "selected": True,
                    },
                    {
                        "abbrev": "B&2",
                        "name": "Codex B",
                        "language": "Greek",
                        "declared": True,
                        "show": "yes",
                        "selected": False,
                    },
                ),
                "witnesses": (),
                "translations": (),
            },
            {
                "id": "Work__B",
                "title": "B",
                "language": "Syriac",
                "author": "",
                "status": "available",
                "primary_segments": (
                    {"unit": "1", "status": "reading", "text": "beta"},
                ),
                "witness_choices": (
                    {
                        "abbrev": "S",
                        "name": "Syriac witness",
                        "language": "Syriac",
                        "declared": True,
                        "show": "yes",
                        "selected": True,
                    },
                ),
                "witnesses": (),
                "translations": (),
            },
        ),
        "metadata_only_versions": (),
    }


def test_renderer_navigation_preserves_selected_versions_and_witnesses():
    html = comparison.render_passage_comparison(_render_model())

    assert 'class="passage-navigation"' in html
    assert '>Previous<' in html
    assert '>Next<' in html
    assert "chapter=1" in html and "verse=1" in html
    assert "chapter=2" in html and "verse=1" in html
    assert html.count("version=Work__A") >= 2
    assert html.count("version=Work__B") >= 2
    assert "witness.Work__A=A+1" in html
    assert "witness.Work__B=S" in html
    assert "B%262" not in html


def test_witness_selector_inputs_are_associated_with_the_comparison_submit_form():
    html = comparison.render_passage_comparison(_render_model())

    assert '<form id="comparison-controls"' in html
    assert 'name="witness.Work__A" value="A 1" checked form="comparison-controls"' in html
    assert 'name="witness.Work__B" value="S" checked form="comparison-controls"' in html


def test_comparison_href_rejects_navigation_to_empty_work_or_section():
    with pytest.raises(ValueError, match="work, chapter, and verse"):
        comparison.comparison_href("", "1", "2")


def test_navigation_index_reuses_work_and_verse_topology_between_passages():
    api = navigation_api()
    calls = {"books": 0, "verse_descendants": 0, "sections": 0}
    original_books = api.F.otype.s
    original_descendants = api.L.d
    original_section = api.T.sectionFromNode

    def books(kind):
        calls["books"] += 1
        return original_books(kind)

    def descendants(node, otype=None):
        calls["verse_descendants"] += 1
        return original_descendants(node, otype=otype)

    def section(node):
        calls["sections"] += 1
        return original_section(node)

    api.F.otype.s = books
    api.L.d = descendants
    api.T.sectionFromNode = section
    navigator = comparison.PassageNavigator(api)

    first = navigator.neighbors("Work", "1", "2", preferred_versions=("Work__B", "Work__A"))
    counts_after_first = dict(calls)
    second = navigator.neighbors("Work", "2", "1", preferred_versions=("Work__A",))

    assert first == {"context_version": "Work__A", "previous": ("1", "1"), "next": ("2", "1")}
    assert second == {"context_version": "Work__A", "previous": ("1", "2"), "next": None}
    assert calls == counts_after_first
    assert calls["books"] == 1
    assert calls["verse_descendants"] == 2
    # Both source versions are resolved once; generated translation is excluded.
    assert calls["sections"] == 2 + 2 + 3


def test_navigation_indexes_do_not_share_state_between_different_tf_apis():
    first_api = navigation_api()
    second_api = navigation_api()
    for node in (1, 2, 3):
        second_api.F.ocp_book.values[node] = "Other"

    first = comparison.PassageNavigator(first_api)
    second = comparison.PassageNavigator(second_api)
    assert first.neighbors("Work", 1, 2)["context_version"] == "Work__A"
    with pytest.raises(KeyError, match="no source versions"):
        second.neighbors("Work", 1, 2)
    assert second.neighbors("Other", 1, 2)["context_version"] == "Work__A"


def test_navigation_cache_rejects_duplicate_address_only_when_requested():
    api = navigation_api()
    api.L.descendants[1] = (101, 102, 102, 103)
    navigator = comparison.PassageNavigator(api)

    # Duplicate unrelated addresses historically do not invalidate this request.
    first = navigator.neighbors("Work", 1, 1, preferred_versions=("Work__A",))
    assert first["next"] == ("1", "2")
    with pytest.raises(ValueError, match="duplicate TF passage address"):
        navigator.neighbors("Work", 1, 2, preferred_versions=("Work__A",))


def test_navigation_cache_fails_closed_on_foreign_verse_section():
    api = navigation_api()
    api.T.SECTIONS = {
        **api.T.SECTIONS,
        102: ("Wrong__Book", "1", "2"),
    }
    navigator = comparison.PassageNavigator(api)
    with pytest.raises(ValueError, match="belongs to section"):
        navigator.neighbors("Work", 1, 1, preferred_versions=("Work__A",))


def test_open_comparison_can_jump_to_another_passage_in_same_selection_form():
    html = comparison.render_passage_comparison(_render_model())
    form = html.split('<form id="comparison-controls"', 1)[1].split("</form>", 1)[0]

    assert 'type="hidden" name="work" value="Work"' in form
    assert '<label>Chapter <input name="chapter" value="1" required></label>' in form
    assert '<label>Verse <input name="verse" value="2" required></label>' in form
    assert 'type="hidden" name="chapter"' not in form
    assert 'type="hidden" name="verse"' not in form
    assert 'name="version" value="Work__A" checked' in form
    assert 'name="version" value="Work__B" checked' in form
    # Witness controls in cards still target this same GET form.
    assert 'name="witness.Work__A" value="A 1" checked form="comparison-controls"' in html


def test_comparison_jump_section_values_are_html_attribute_escaped():
    model = _render_model()
    model["chapter"] = '1" onfocus="alert(1)'
    model["verse"] = "<verse>"

    html = comparison.render_passage_comparison(model)
    form = html.split('<form id="comparison-controls"', 1)[1].split("</form>", 1)[0]

    assert 'name="chapter" value="1&quot; onfocus=&quot;alert(1)" required' in form
    assert 'name="verse" value="&lt;verse&gt;" required' in form
    assert 'name="chapter" value="1" onfocus="' not in form
