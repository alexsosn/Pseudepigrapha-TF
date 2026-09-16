from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.fabric import Fabric

from pseudepigrapha_tf import Apparatus
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf


@pytest.mark.parametrize("operation", ["passage", "work_passage"])
def test_unaddressable_manuscript_metadata_does_not_break_keyed_witness_inventory(
    tmp_path: Path, operation: str
):
    book = parse_file(Path(__file__).parent / "fixtures" / "sample.xml")
    version = book.versions[0]
    named = version.manuscripts
    version.manuscripts = (
        *named,
        replace(named[0], abbrev="   ", name="Anonymous first", name_xml="Anonymous first"),
        replace(named[0], abbrev="   ", name="Anonymous second", name_xml="Anonymous second"),
    )
    output = tmp_path / "tf"
    assert write_tf(build_tf_data([book]), output)

    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = TF.load(" ".join(Apparatus.WORK_PASSAGE_FEATURES), silent="deep")
    assert api is not False and api is not None
    assert TF.load("ms_name", add=True, silent="deep")
    manuscripts = tuple(api.F.otype.s("manuscript"))
    # TF returns None for the intentionally blank, preserved source values.
    anonymous = tuple(
        node for node in manuscripts if not str(api.F.ms_abbrev.v(node) or "").strip()
    )
    assert len(manuscripts) == len(named) + 2
    assert len(anonymous) == 2
    assert {api.F.ms_name.v(node) for node in anonymous} == {
        "Anonymous first", "Anonymous second"
    }
    assert all(not api.E.witness.t(node) for node in anonymous)

    helper = Apparatus(api)
    result = getattr(helper, operation)("Sample", "1", "2")
    witnesses = (
        result["witnesses"] if operation == "passage"
        else result["versions"]["Sample"]["witnesses"]
    )
    assert set(witnesses) == {"A", "B", "C"}
    assert all(record["abbrev"] for record in witnesses.values())
