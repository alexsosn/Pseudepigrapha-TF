from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.fabric import Fabric

from pseudepigrapha_tf import Apparatus
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


def test_global_witness_text_uses_real_tf_reverse_edges_and_hides_omission(tmp_path):
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    output = tmp_path / "tf"
    assert write_tf(data, output)

    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = TF.load("reading_text ms_abbrev reading_of witness", silent="deep")
    assert api is not None

    manuscript_a = next(
        node
        for node in api.F.otype.s("manuscript")
        if api.F.ms_abbrev.v(node) == "A"
    )

    # A has the non-empty Heading reading followed by an explicit omission at
    # 1:2. The default/global path must use real TF witness.t()/reading_of.f(),
    # preserve corpus unit order, and not render the omission as text.
    assert Apparatus(api).witness_text(manuscript_a) == "λόγος θεοῦ"
