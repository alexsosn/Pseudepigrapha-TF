from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.advanced.app import findApp

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def _materialize(tmp_path):
    output = tmp_path / "tf"
    assert write_tf(build_tf_data([parse_file(FIXTURES / "sample.xml")]), output)
    return output


def _find_local_app(output, *, version=None):
    return findApp(
        f"app:{ROOT / 'app'}",
        "",
        None,
        "github",
        False,
        version=version,
        locations=[str(output)],
        modules=[""],
        silent="deep",
    )


def _load_app_for_rendering(tmp_path):
    app = _find_local_app(_materialize(tmp_path), version="0.1")
    assert app is not None
    assert app.api is not None
    return app


def test_local_app_loads_materialized_tf_without_remote_distribution_contract(tmp_path):
    app = _find_local_app(_materialize(tmp_path))

    assert app is not None
    assert app.api is not None
    assert app.api.T.nodeFromSection(("Sample", "1", "Heading")) is not None


def test_pretty_alternative_reading_does_not_render_primary_anchor_text(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    alternative = next(
        node
        for node in api.F.otype.s("reading")
        if api.F.source_ref.v(node) == "1:Heading" and api.F.is_primary.v(node) != 1
    )

    html = app.pretty(alternative, _asString=True)

    assert "κυρίου" in html, html
    assert "θεοῦ" not in html, html


def test_pretty_manuscript_uses_manuscript_identity_not_anchor_text(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    manuscript = next(
        node for node in api.F.otype.s("manuscript") if api.F.ms_abbrev.v(node) == "A"
    )

    html = app.pretty(manuscript, _asString=True)

    assert "A" in html, html
    assert "λόγος" not in html, html
    assert "θεοῦ" not in html, html


def test_pretty_resource_uses_resource_identity_not_anchor_text(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    resource = next(
        node
        for node in api.F.otype.s("resource")
        if api.F.resource_name.v(node) == "Edition"
    )

    html = app.pretty(resource, _asString=True)

    assert "Edition" in html, html
    assert "λόγος" not in html, html


def test_hidden_technical_type_remains_directly_inspectable(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    manuscript = next(
        node for node in api.F.otype.s("manuscript") if api.F.ms_abbrev.v(node) == "A"
    )

    html = app.pretty(manuscript, hideTypes=False, _asString=True)

    assert "A" in html, html
