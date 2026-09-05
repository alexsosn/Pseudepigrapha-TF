from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.fabric import Fabric

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


def test_real_tf_resolves_generated_book_nodes_directly(tmp_path):
    data = build_tf_data([parse_file(FIXTURES / "multiple_versions.xml")])
    output = tmp_path / "tf"
    assert write_tf(data, output)

    api = Fabric(locations=[str(output)], modules=[""], silent="deep").load(
        "book", silent="deep"
    )
    assert api is not None

    book_nodes = tuple(api.F.otype.s("book"))
    assert len(book_nodes) == 2
    assert {api.T.sectionFromNode(node)[0] for node in book_nodes} == {
        "Multi__Syriac",
        "Multi__Greek",
    }
