from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.fabric import Fabric

from pseudepigrapha_tf.graph import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


def _load(data, tmp_path):
    output = tmp_path / "tf"
    assert write_tf(data, output)
    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    return TF.load(
        "reading_text ms_abbrev resource_name source_ref is_primary "
        "prefix_utf8 g_word_utf8 trailer_utf8 boundary_utf8",
        silent="deep",
    )


def test_node_type_default_formats_prevent_misleading_text(tmp_path):
    api = _load(build_tf_data([parse_file(FIXTURES / "sample.xml")]), tmp_path)
    assert api is not None
    alternative = next(
        node for node in api.F.otype.s("reading")
        if api.F.is_primary.v(node) != 1 and api.F.reading_text.v(node)
    )
    assert api.T.text(alternative) == api.F.reading_text.v(alternative)
    manuscript = next(node for node in api.F.otype.s("manuscript") if api.F.ms_abbrev.v(node) == "A")
    assert api.T.text(manuscript) == "A"


def test_deep_source_reference_has_truthful_three_level_tf_address(tmp_path):
    api = _load(build_tf_data([parse_file(FIXTURES / "three_divisions.xml")]), tmp_path)
    assert api is not None
    unit = next(node for node in api.F.otype.s("unit") if api.F.source_ref.v(node) == "9.4b.1")
    assert api.T.sectionFromNode(unit)[1:] == ("9.4b", "1")
