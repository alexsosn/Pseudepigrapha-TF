"""Browser work-chooser contracts: source-backed titles and stable work IDs."""

from __future__ import annotations

from html import escape
from types import SimpleNamespace

from pseudepigrapha_tf import comparison, web


class Feature:
    def __init__(self, values):
        self.values = dict(values)

    def v(self, node):
        return self.values.get(node)


class BookType:
    def __init__(self, nodes):
        self.nodes = tuple(nodes)

    def s(self, kind):
        assert kind == "book"
        return self.nodes


def work_api(*, with_title=True):
    book_nodes = tuple(range(1, 10))
    features = {
        "otype": BookType(book_nodes),
        "ocp_book": Feature({
            1: "1En", 2: "1En", 3: "1En",
            4: "TJob", 5: "Disputed", 6: "Disputed",
            7: 'Unsafe<&"', 8: "", 9: "TranslationOnly",
        }),
        "version_kind": Feature({
            1: "source", 2: "source", 3: "generated_translation",
            4: "source", 5: "source", 6: "source", 7: "source",
            8: "source", 9: "generated_translation",
        }),
    }
    if with_title:
        features["title"] = Feature({
            1: "Book of Enoch", 2: "Book of Enoch", 3: "Spurious generated title",
            4: "", 5: "First conflicting title", 6: "Second conflicting title",
            7: '<script onload="x">', 8: "Missing work id",
            9: "Generated only",
        })
    return SimpleNamespace(F=SimpleNamespace(**features))


def test_comparison_work_options_use_only_unambiguous_source_titles():
    api = work_api()
    assert web.list_comparison_work_options(api) == (
        ("1En", "Book of Enoch (1En)"),
        ("Disputed", "Disputed"),
        ("TJob", "TJob"),
        ('Unsafe<&"', '<script onload="x"> (Unsafe<&")'),
    )


def test_existing_list_comparison_works_still_returns_stable_ids():
    api = work_api()
    assert web.list_comparison_works(api) == (
        "1En", "Disputed", "TJob", 'Unsafe<&"',
    )
    assert web.list_comparison_work_options(work_api(with_title=False)) == tuple(
        (work, work) for work in web.list_comparison_works(api)
    )


def test_landing_escapes_display_title_and_work_id_independently():
    html = web._landing_html(work_api())
    work = 'Unsafe<&"'
    label = '<script onload="x"> (Unsafe<&")'
    assert '<option value="1En">Book of Enoch (1En)</option>' in html
    assert f'<option value="{escape(work, quote=True)}">{escape(label, quote=True)}</option>' in html
    assert "<script" not in html
    assert '<option value="TranslationOnly">' not in html
    assert '<option value="">' not in html.replace('<option value="">Choose a work</option>', '')


def test_open_comparison_provides_unfiltered_return_to_work_chooser():
    model = {
        "work": "1En",
        "title": "Book of Enoch",
        "chapter": "1",
        "verse": "2",
        "version_choices": (),
        "versions": (),
        "metadata_only_versions": (),
    }
    html = comparison.render_passage_comparison(model)
    nav = html.split('<nav class="comparison-nav">', 1)[1].split("</nav>", 1)[0]

    assert '<a href="/compare">Choose another work</a>' in nav
    assert 'href="/compare?' not in nav
    assert '<a href="/">Text-Fabric browser</a>' in nav
    assert '<input type="hidden" name="work" value="1En">' in html
