from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from pseudepigrapha_tf import comparison


WITNESSES = {
    "A": {
        "node": 31,
        "abbrev": "A",
        "declared": True,
        "language": "Greek",
        "name": "Witness A",
        "show": "yes",
    },
    "B": {
        "node": 32,
        "abbrev": "B",
        "declared": True,
        "language": "Greek",
        "name": "Witness B",
        "show": "yes",
    },
}


class FakeApparatus:
    def __init__(self, api):
        self.api = api

    def work_passage(self, work, chapter, verse):
        return {
            "work": str(work),
            "title": "Work",
            "reference": (str(chapter), str(verse)),
            "versions": {
                "Work__Greek": {
                    "node": 1,
                    "id": "Work__Greek",
                    "title": "Greek",
                    "language": "Greek",
                    "author": "",
                    "status": "not_present",
                    # Version-level inventory remains available even though this
                    # exact passage is absent from the version.
                    "witnesses": WITNESSES,
                    "passage": None,
                },
            },
            "metadata_only_versions": {},
        }


class FakeTranslations:
    def __init__(self, api):
        self.api = api

    def versions(self, *, work=None, language=None):
        return ()


def _build(monkeypatch, selected):
    monkeypatch.setattr(comparison, "Apparatus", FakeApparatus)
    monkeypatch.setattr(comparison, "Translations", FakeTranslations)
    return comparison.build_passage_comparison(
        object(),
        "Work",
        "1",
        "2",
        selected_versions=("Work__Greek",),
        selected_witnesses={"Work__Greek": selected},
    )


def test_not_present_version_retains_explicit_witness_subset_for_navigation(monkeypatch):
    model = _build(monkeypatch, ("B",))
    version = model["versions"][0]

    assert version["status"] == "not_present"
    assert version["witnesses"] == ()
    assert [
        choice["abbrev"]
        for choice in version["witness_choices"]
        if choice["selected"]
    ] == ["B"]

    model["navigation"] = {
        "context_version": "Work__Greek",
        "previous": None,
        "next": ("1", "3"),
    }
    html = comparison.render_passage_comparison(model)
    href_start = html.index('rel="next" href="') + len('rel="next" href="')
    href_end = html.index('"', href_start)
    href = html[href_start:href_end].replace("&amp;", "&")
    query = parse_qs(urlsplit(href).query, keep_blank_values=True)

    assert query["version"] == ["Work__Greek"]
    assert query["witness.Work__Greek"] == ["B"]


def test_not_present_version_retains_explicit_empty_witness_selection(monkeypatch):
    model = _build(monkeypatch, ())
    version = model["versions"][0]

    assert version["witnesses"] == ()
    assert version["witness_choices"]
    assert not any(choice["selected"] for choice in version["witness_choices"])

    model["navigation"] = {
        "context_version": "Work__Greek",
        "previous": None,
        "next": ("1", "3"),
    }
    html = comparison.render_passage_comparison(model)
    assert "witness.Work__Greek=" in html
