from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

pytest.importorskip("tf")
from tf.advanced.app import findApp

from pseudepigrapha_tf import web
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


class FakeTfApp:
    def __init__(self):
        self.api = object()


def _materialize(tmp_path):
    output = tmp_path / "tf"
    books = [parse_file(FIXTURES / "sample.xml")]
    assert write_tf(build_tf_data(books), output)
    return output


def _find_local_app(output):
    return findApp(
        f"app:{ROOT / 'app'}",
        "",
        None,
        "github",
        True,
        version="0.1",
        locations=[str(output)],
        modules=[""],
        silent="deep",
    )


def test_register_compare_route_parses_version_and_per_version_witness_selection(monkeypatch):
    flask_app = Flask(__name__)

    @flask_app.get("/")
    def root():
        return "root"

    captured = {}

    def fake_build(api, work, chapter, verse, *, selected_versions=None, selected_witnesses=None):
        captured.update(
            api=api,
            work=work,
            chapter=chapter,
            verse=verse,
            selected_versions=tuple(selected_versions or ()),
            selected_witnesses={key: tuple(value) for key, value in (selected_witnesses or {}).items()},
        )
        return {"work": work, "chapter": chapter, "verse": verse}

    monkeypatch.setattr(web, "build_passage_comparison", fake_build)
    monkeypatch.setattr(web, "render_passage_comparison", lambda model: "<main>comparison</main>")

    tf_app = FakeTfApp()
    web.register_comparison_route(flask_app, tf_app)
    client = flask_app.test_client()
    response = client.get(
        "/compare?work=Work&chapter=1&verse=2"
        "&version=Work__Greek&version=Work__Latin"
        "&witness.Work__Greek=A&witness.Work__Greek=B"
        "&witness.Work__Latin=L"
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "<main>comparison</main>"
    assert captured == {
        "api": tf_app.api,
        "work": "Work",
        "chapter": "1",
        "verse": "2",
        "selected_versions": ("Work__Greek", "Work__Latin"),
        "selected_witnesses": {
            "Work__Greek": ("A", "B"),
            "Work__Latin": ("L",),
        },
    }
    assert client.get("/").get_data(as_text=True) == "root"


def test_compare_route_landing_lists_source_works_without_requiring_a_technical_node(monkeypatch):
    flask_app = Flask(__name__)
    tf_app = FakeTfApp()
    monkeypatch.setattr(web, "list_comparison_works", lambda api: ("1En", "2Bar"))

    web.register_comparison_route(flask_app, tf_app)
    response = flask_app.test_client().get("/compare")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "1En" in html
    assert "2Bar" in html
    assert 'name="work"' in html
    assert 'name="chapter"' in html
    assert 'name="verse"' in html


def test_compare_route_returns_safe_400_for_invalid_selection(monkeypatch):
    flask_app = Flask(__name__)
    tf_app = FakeTfApp()

    def invalid(*args, **kwargs):
        raise ValueError("unknown source version: <script>alert(1)</script>")

    monkeypatch.setattr(web, "build_passage_comparison", invalid)
    web.register_comparison_route(flask_app, tf_app)
    response = flask_app.test_client().get("/compare?work=Work&chapter=1&verse=2&version=bad")
    html = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "unknown source version" in html
    assert "&lt;script&gt;" in html
    assert "<script>" not in html


def test_stock_tf_browser_and_compare_route_coexist_on_one_flask_app(tmp_path):
    tf_app = _find_local_app(_materialize(tmp_path))
    assert tf_app is not None and tf_app.api is not None

    flask_app = web.create_comparison_web_app(tf_app, app_name="pseudepigrapha-test")
    client = flask_app.test_client()

    root = client.get("/")
    assert root.status_code == 200, root.get_data(as_text=True)

    # Sample 1:2 is an unambiguous apparatus locus: A explicitly omits and B
    # supplies a reading. The Heading fixture deliberately cites B on two
    # competing readings and must remain a fail-closed error below.
    comparison = client.get("/compare?work=Sample&chapter=1&verse=2")
    html = comparison.get_data(as_text=True)
    assert comparison.status_code == 200, html
    assert 'class="comparison-page"' in html
    assert 'class="source-version-card"' in html
    assert 'class="state-omission"' in html
    assert "Sample" in html

    css_response = client.get("/data/static/comparison.css")
    try:
        css = css_response.get_data(as_text=True)
    finally:
        css_response.close()
    assert ".version-grid" in css
    assert ".source-version-card" in css
    assert "@media" in css


def test_real_tf_ambiguous_witness_assignment_fails_closed_in_comparison_route(tmp_path):
    tf_app = _find_local_app(_materialize(tmp_path))
    flask_app = web.create_comparison_web_app(tf_app, app_name="pseudepigrapha-test")

    response = flask_app.test_client().get("/compare?work=Sample&chapter=1&verse=Heading")
    html = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "multiple readings at unit" in html
    assert "manuscript 5" in html


def test_local_loader_reuses_tracked_app_and_materialized_tf(tmp_path):
    output = _materialize(tmp_path)
    flask_app = web.load_local_comparison_web_app(
        output,
        ROOT / "app",
        version="0.1",
        silent="deep",
    )
    client = flask_app.test_client()
    root = client.get("/")
    assert root.status_code == 200, root.get_data(as_text=True)

    response = client.get("/compare?work=Sample&chapter=1&verse=2")
    html = response.get_data(as_text=True)
    assert response.status_code == 200, html
    assert "Sample" in html
