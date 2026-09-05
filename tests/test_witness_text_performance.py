from collections import Counter
from types import SimpleNamespace

import pytest

from pseudepigrapha_tf.apparatus import Apparatus


class Feature:
    def __init__(self, values):
        self.values = values

    def v(self, node):
        return self.values.get(node)


class OtypeFeature(Feature):
    def s(self, kind):
        assert kind == "unit"
        return (10, 20, 30, 40)


class Edge:
    def __init__(self, forward):
        self.forward = {source: tuple(targets) for source, targets in forward.items()}
        self.inverse = {}
        self.f_calls = Counter()
        self.t_calls = Counter()
        for source, targets in self.forward.items():
            for target in targets:
                self.inverse.setdefault(target, []).append(source)

    def f(self, node):
        self.f_calls[node] += 1
        return tuple(self.forward.get(node, ()))

    def t(self, node):
        self.t_calls[node] += 1
        return tuple(self.inverse.get(node, ()))


def witness_text_api(*, duplicate=False, owner_mode="normal"):
    # Requested manuscript 100 cites reading 11 (text), 21 (explicit omission),
    # and 41 (text). Reading 31 belongs to another witness and must never be
    # scanned by the optimized global path.
    reading_of = {
        11: (10,),
        21: (20,),
        31: (30,),
        41: (40,),
    }
    if duplicate:
        reading_of[12] = (10,)
    if owner_mode == "missing":
        reading_of[41] = ()
    elif owner_mode == "multiple":
        reading_of[41] = (40, 30)

    witness = {
        11: (100,),
        21: (100,),
        31: (200,),
        41: (100,),
    }
    if duplicate:
        witness[12] = (100,)

    reading_nodes = {11: "reading", 21: "reading", 31: "reading", 41: "reading"}
    if duplicate:
        reading_nodes[12] = "reading"
    F = SimpleNamespace(
        otype=OtypeFeature(reading_nodes),
        reading_text=Feature({11: "alpha", 12: "alt", 21: "", 31: "other", 41: "omega"}),
    )
    E = SimpleNamespace(
        reading_of=Edge(reading_of),
        witness=Edge(witness),
    )
    return SimpleNamespace(F=F, E=E)


def test_global_witness_text_uses_direct_reverse_edges_once():
    api = witness_text_api()
    assert Apparatus(api).witness_text(100) == "alpha omega"

    assert api.E.witness.t_calls == Counter({100: 1})
    assert api.E.reading_of.f_calls == Counter({11: 1, 21: 1, 41: 1})
    assert api.E.reading_of.t_calls == Counter()
    assert api.E.witness.f_calls == Counter()


def test_global_witness_text_rejects_two_readings_for_same_unit():
    api = witness_text_api(duplicate=True)
    with pytest.raises(ValueError, match=r"manuscript 100 has multiple readings at unit 10"):
        Apparatus(api).witness_text(100)


def test_global_witness_text_requires_exactly_one_unit_per_cited_reading():
    for owner_mode, expected in (
        ("missing", r"reading 41 has no reading_of unit"),
        ("multiple", r"reading 41 has multiple reading_of units"),
    ):
        api = witness_text_api(owner_mode=owner_mode)
        with pytest.raises(ValueError, match=expected):
            Apparatus(api).witness_text(100)


def test_global_witness_text_missing_edge_features_fail_clearly():
    for missing in ("witness", "reading_of"):
        api = witness_text_api()
        delattr(api.E, missing)
        with pytest.raises(ValueError, match=missing):
            Apparatus(api).witness_text(100)


def test_explicit_units_preserve_caller_order_and_duplicates():
    api = witness_text_api()
    assert Apparatus(api).witness_text(100, units=(40, 10, 40, 20)) == "omega alpha omega"
