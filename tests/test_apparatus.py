from types import SimpleNamespace

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
        for source, targets in forward.items():
            for target in targets:
                self.inverse.setdefault(target, []).append(source)

    def f(self, node):
        return tuple(self.forward.get(node, ()))

    def t(self, node):
        return tuple(self.inverse.get(node, ()))


def fake_api():
    F = SimpleNamespace(
        otype=Feature({10: "unit", 11: "reading", 12: "reading", 13: "variant_word", 20: "manuscript"}),
        reading_text=Feature({11: "alpha", 12: "beta"}),
        g_word_utf8=Feature({13: "beta"}),
        prefix_utf8=Feature({13: ""}),
        trailer_utf8=Feature({13: ""}),
        ms_abbrev=Feature({20: "B"}),
        is_primary=Feature({11: 1}),
    )
    E = SimpleNamespace(
        reading_of=Edge({11: {10}, 12: {10}}),
        variant_word_of=Edge({13: {12}}),
        witness=Edge({11: {20}, 12: {20}}),
    )
    return SimpleNamespace(F=F, E=E)


def test_apparatus_helpers_hide_edge_joining_details():
    apparatus = Apparatus(fake_api())
    assert apparatus.unit_readings(10) == (11, 12)
    assert apparatus.reading_text(12) == "beta"
    assert apparatus.reading_tokens(12) == (13,)
    assert apparatus.witness_reading(10, 20) == 12
    assert apparatus.apparatus(10) == (
        {"reading": 11, "text": "alpha", "primary": True, "witnesses": (20,)},
        {"reading": 12, "text": "beta", "primary": False, "witnesses": (20,)},
    )
