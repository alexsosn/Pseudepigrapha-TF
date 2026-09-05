from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.fabric import Fabric

from pseudepigrapha_tf import Apparatus
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name, tmp_path):
    data = build_tf_data([parse_file(FIXTURES / name)])
    output = tmp_path / name.replace(".xml", "-tf")
    assert write_tf(data, output)
    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = TF.load("reading_text ms_abbrev reading_of witness", silent="deep")
    assert api is not None
    return api


def _manuscript(api, abbrev):
    return next(
        node
        for node in api.F.otype.s("manuscript")
        if api.F.ms_abbrev.v(node) == abbrev
    )


def test_global_witness_text_uses_real_tf_reverse_edges_and_hides_omission(tmp_path):
    api = _load_fixture("sample.xml", tmp_path)
    manuscript_a = _manuscript(api, "A")

    # A has the non-empty Heading reading followed by an explicit omission at
    # 1:2. The default/global path must use real TF witness.t()/reading_of.f(),
    # preserve corpus unit order, and not render the omission as text.
    assert Apparatus(api).witness_text(manuscript_a) == "λόγος θεοῦ"


def test_global_witness_text_ignores_intentionally_ownerless_orphan_readings(tmp_path):
    api = _load_fixture("orphan_reading.xml", tmp_path)
    A = Apparatus(api)

    # A owns two ordinary unit readings and must reconstruct normally.
    assert A.witness_text(_manuscript(api, "A")) == "alpha omega"

    # B and citation-only X occur only on the preserved direct-div
    # orphan_reading. That evidence deliberately has no reading_of unit and was
    # never part of witness_text()'s unit reconstruction before this optimization.
    assert A.witness_text(_manuscript(api, "B")) == ""
    assert A.witness_text(_manuscript(api, "X")) == ""
