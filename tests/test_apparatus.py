from collections import Counter
from types import SimpleNamespace

import pytest

from pseudepigrapha_tf.apparatus import Apparatus


class Feature:
    def __init__(self, values):
        self.values = values

    def v(self, node):
        return self.values.get(node)


class Edge:
    def __init__(self, forward):
        self.forward = forward
        self.inverse = {}
        self.f_calls = Counter()
        self.t_calls = Counter()
        for source, targets in forward.items():
            for target in targets:
                self.inverse.setdefault(target, []).append(source)

    def f(self, node):
        self.f_calls[node] += 1
        return tuple(self.forward.get(node, ()))

    def t(self, node):
        self.t_calls[node] += 1
        return tuple(self.inverse.get(node, ()))


def fake_api():
    F = SimpleNamespace(
        otype=Feature({10: "unit", 11: "reading", 12: "reading", 13: "variant_word", 20: "manuscript", 21: "manuscript"}),
        reading_text=Feature({11: "alpha", 12: "beta"}),
        g_word_utf8=Feature({13: "beta"}),
        prefix_utf8=Feature({13: ""}),
        trailer_utf8=Feature({13: ""}),
        ms_abbrev=Feature({20: "B", 21: "A"}),
        is_primary=Feature({11: 1}),
    )
    E = SimpleNamespace(
        reading_of=Edge({11: {10}, 12: {10}}),
        variant_word_of=Edge({13: {12}}),
        witness=Edge({11: {21}, 12: {20}}),
    )
    return SimpleNamespace(F=F, E=E)


def test_apparatus_helpers_hide_edge_joining_details():
    apparatus = Apparatus(fake_api())
    assert apparatus.unit_readings(10) == (11, 12)
    assert apparatus.reading_text(12) == "beta"
    assert apparatus.reading_tokens(12) == (13,)
    assert apparatus.witness_reading(10, 20) == 12
    assert apparatus.apparatus(10) == (
        {"reading": 11, "text": "alpha", "primary": True, "witnesses": (21,)},
        {"reading": 12, "text": "beta", "primary": False, "witnesses": (20,)},
    )


class Locality:
    def d(self, node, otype=None):
        assert (node, otype) == (100, "unit")
        return (10, 20)

    def u(self, node, otype=None):
        assert (node, otype) == (100, "book")
        return (1,)


class Text:
    def nodeFromSection(self, reference):
        return 100 if reference == ("Perf", "1", "1") else None


def passage_api(*, duplicate_witness=False):
    F = SimpleNamespace(
        reading_text=Feature({11: "alpha", 12: "", 21: "beta", 22: "gamma"}),
        source_ref=Feature({10: "1:1", 20: "1:1"}),
        unit_id=Feature({10: "1", 20: "2"}),
        is_primary=Feature({11: 1, 12: 0, 21: 1, 22: 0}),
        ms_abbrev=Feature({30: "A", 31: "B", 32: "C"}),
        undefined_manuscript=Feature({30: 0, 31: 0, 32: 1}),
        ms_language=Feature({30: "Greek", 31: "Greek", 32: "Greek"}),
        ms_name=Feature({30: "A", 31: "B", 32: "Citation only"}),
        ms_show=Feature({30: "yes", 31: "yes", 32: ""}),
    )
    witness_forward = {
        11: {30},
        12: {30 if duplicate_witness else 31},
        21: {30},
        22: {31},
    }
    E = SimpleNamespace(
        reading_of=Edge({11: {10}, 12: {10}, 21: {20}, 22: {20}}),
        witness=Edge(witness_forward),
        manuscript_of=Edge({30: {1}, 31: {1}, 32: {1}}),
    )
    return SimpleNamespace(F=F, E=E, L=Locality(), T=Text())


def test_passage_traverses_each_apparatus_relation_once():
    api = passage_api()
    result = Apparatus(api).passage("Perf", "1", "1")

    assert result["source_refs"] == ("1:1",)
    assert [unit["unit"] for unit in result["units"]] == ["1", "2"]

    witnesses = result["witnesses"]
    assert witnesses["A"]["complete"] is True
    assert witnesses["A"]["text"] == "alpha beta"
    assert [segment["status"] for segment in witnesses["A"]["segments"]] == ["reading", "reading"]

    assert witnesses["B"]["complete"] is True
    assert witnesses["B"]["text"] == "gamma"
    assert [segment["status"] for segment in witnesses["B"]["segments"]] == ["omission", "reading"]

    assert witnesses["C"]["declared"] is False
    assert witnesses["C"]["complete"] is False
    assert witnesses["C"]["text"] is None
    assert witnesses["C"]["attested_text"] == ""
    assert [segment["status"] for segment in witnesses["C"]["segments"]] == ["unattested", "unattested"]

    assert api.E.reading_of.t_calls == Counter({10: 1, 20: 1})
    assert api.E.witness.f_calls == Counter({11: 1, 12: 1, 21: 1, 22: 1})


def test_passage_still_rejects_multiple_readings_for_one_witness():
    api = passage_api(duplicate_witness=True)

    with pytest.raises(ValueError, match=r"manuscript 30 has multiple readings at unit 10"):
        Apparatus(api).passage("Perf", "1", "1")
