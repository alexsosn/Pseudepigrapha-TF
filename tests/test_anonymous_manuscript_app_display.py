from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.advanced.app import findApp

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def test_anonymous_manuscript_pretty_uses_preserved_name_without_anchor_text(tmp_path: Path):
    book = parse_file(FIXTURES / "sample.xml")
    version = book.versions[0]
    named = version.manuscripts
    anonymous_name = "<Anonymous & witness>"
    version.manuscripts = (
        *named,
        replace(
            named[0],
            abbrev="   ",
            name=anonymous_name,
            name_xml="&lt;Anonymous &amp; witness&gt;",
        ),
    )

    output = tmp_path / "tf"
    assert write_tf(build_tf_data([book]), output)
    app = findApp(
        f"app:{ROOT / 'app'}",
        "",
        None,
        "github",
        False,
        version="0.1",
        locations=[str(output)],
        modules=[""],
        silent="deep",
    )
    assert app is not None and app.api is not None
    api = app.api

    anonymous = next(
        node
        for node in api.F.otype.s("manuscript")
        if not str(api.F.ms_abbrev.v(node) or "").strip()
        and api.F.ms_name.v(node) == anonymous_name
    )
    anchor = api.T.text(api.E.oslots.s(anonymous)[0])
    assert anchor

    html = app.pretty(anonymous, hideTypes=False, _asString=True)

    assert "&lt;Anonymous &amp; witness&gt;" in html, html
    assert anonymous_name not in html, html
    assert anchor not in html, html
