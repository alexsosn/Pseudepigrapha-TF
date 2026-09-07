from __future__ import annotations

from pathlib import Path

import pytest

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_bytes
from pseudepigrapha_tf.writer import write_tf


def _book(*versions: str) -> bytes:
    return (
        '<?xml version="1.0"?>\n<book filename="Marked" title="Marked">\n'
        + "".join(versions)
        + "\n</book>\n"
    ).encode("utf-8")


def _version(*, title: str, language: str, manuscript: str, text: str, generated: bool = False) -> str:
    marker = "OCP-Trans" if generated else manuscript
    unit_id = ("fr_" if generated else "") + "1"
    return f'''
  <version title="{title}" author="Editor" language="{language}">
    <divisions>
      <division label="Chapter" delimiter=":"/>
      <division label="Verse"/>
    </divisions>
    <manuscripts>
      <ms abbrev="{marker}" language="{language}" show="yes"><name>{marker}</name></ms>
    </manuscripts>
    <text>
      <div number="1"><div number="1">
        <unit id="{unit_id}"><reading option="0" mss="{marker} ">{text}</reading></unit>
      </div></div>
    </text>
  </version>
'''


def _generated_data():
    book = parse_bytes(
        _book(
            _version(title="Greek", language="Greek", manuscript="G", text="alpha"),
            _version(
                title="Greek (French)",
                language="French",
                manuscript="ignored",
                text="traduction",
                generated=True,
            ),
        ),
        source_path="Marked.xml",
    )
    return build_tf_data([book])


def test_generated_graph_declares_layer_in_generic_metadata() -> None:
    data = _generated_data()

    assert data.metadata[""]["generatedTranslationLayer"] == "1"


def test_source_only_graph_does_not_declare_generated_layer() -> None:
    book = parse_bytes(
        _book(_version(title="Greek", language="Greek", manuscript="G", text="alpha")),
        source_path="Marked.xml",
    )
    data = build_tf_data([book])

    assert "generatedTranslationLayer" not in data.metadata[""]


def test_generated_layer_marker_survives_tf_reload_without_provenance_features(tmp_path: Path) -> None:
    pytest.importorskip("tf")
    from tf.fabric import Fabric

    output = tmp_path / "tf"
    assert write_tf(_generated_data(), output)

    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = TF.load("reading_text", silent="deep")
    assert api is not False and not isinstance(api, bool)
    assert getattr(api.F, "version_kind", None) is None
    assert getattr(api.F, "synthetic_witness", None) is None
    assert api.TF.features["otype"].metaData["generatedTranslationLayer"] == "1"
