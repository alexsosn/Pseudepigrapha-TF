from collections import Counter
from types import SimpleNamespace

from pseudepigrapha_tf.apparatus import Apparatus


class Feature:
    def __init__(self, values):
        self.values = values

    def v(self, node):
        return self.values.get(node)


class OtypeFeature(Feature):
    def s(self, kind):
        return tuple(node for node, value in self.values.items() if value == kind)


class Edge:
    def __init__(self, forward):
        self.forward = forward
        self.inverse = {}
        self.t_calls = Counter()
        for source, targets in forward.items():
            for target in targets:
                self.inverse.setdefault(target, []).append(source)

    def f(self, node):
        return tuple(self.forward.get(node, ()))

    def t(self, node):
        self.t_calls[node] += 1
        return tuple(self.inverse.get(node, ()))


class Locality:
    def __init__(self):
        self.d_calls = Counter()

    def d(self, node, otype=None):
        self.d_calls[(node, otype)] += 1
        if otype == "word":
            return {1: (101,), 2: (201,)}.get(node, ())
        if otype == "unit":
            return {1000: (10,)}.get(node, ())
        return ()

    def u(self, node, otype=None):
        if (node, otype) == (1000, "book"):
            return (1,)
        return ()


class Text:
    def __init__(self):
        self.section_calls = Counter()

    def sectionFromNode(self, node):
        self.section_calls[node] += 1
        return {
            101: ("Work__A", "1", "1"),
            201: ("Work__B", "1", "1"),
        }[node]

    def nodeFromSection(self, reference):
        if reference == ("Work__A", "1", "1"):
            return 1000
        return None


def work_passage_api():
    F = SimpleNamespace(
        otype=OtypeFeature({
            1: "book",
            2: "book",
            10: "unit",
            11: "reading",
            30: "manuscript",
            31: "manuscript",
            32: "manuscript",
        }),
        ocp_book=Feature({1: "Work", 2: "Work"}),
        title=Feature({1: "Work title", 2: "Work title"}),
        version_title=Feature({1: "A", 2: "B"}),
        language=Feature({1: "Greek", 2: "Latin"}),
        author=Feature({1: "Author A", 2: "Author B"}),
        reading_text=Feature({11: "alpha"}),
        source_ref=Feature({10: "1:1"}),
        unit_id=Feature({10: "1"}),
        is_primary=Feature({11: 1}),
        ms_abbrev=Feature({30: "A", 31: "B", 32: "X"}),
        undefined_manuscript=Feature({30: 0, 31: 0, 32: 1}),
        ms_language=Feature({30: "Greek", 31: "Latin", 32: "Greek"}),
        ms_name=Feature({30: "Witness A", 31: "Witness B", 32: "Citation only"}),
        ms_show=Feature({30: "yes", 31: "yes", 32: ""}),
    )
    E = SimpleNamespace(
        reading_of=Edge({11: {10}}),
        witness=Edge({11: {32}}),
        manuscript_of=Edge({30: {1}, 32: {1}, 31: {2}}),
    )
    return SimpleNamespace(F=F, E=E, L=Locality(), T=Text())


def test_work_passage_resolves_each_textual_version_and_witness_inventory_once():
    api = work_passage_api()
    result = Apparatus(api).work_passage("Work", "1", "1")

    assert result["title"] == "Work title"
    assert set(result["versions"]) == {"Work__A", "Work__B"}

    available = result["versions"]["Work__A"]
    assert available["status"] == "available"
    assert set(available["witnesses"]) == {"A", "X"}
    assert available["witnesses"]["X"]["declared"] is False
    assert set(available["witnesses"]["X"]) == {
        "node", "abbrev", "declared", "language", "name", "show"
    }
    nested_x = available["passage"]["witnesses"]["X"]
    assert nested_x["status"] if "status" in nested_x else nested_x["segments"][0]["status"] == "reading"
    assert available["witnesses"]["X"] is not nested_x

    absent = result["versions"]["Work__B"]
    assert absent["status"] == "not_present"
    assert absent["passage"] is None
    assert set(absent["witnesses"]) == {"B"}

    assert api.L.d_calls[(1, "word")] == 1
    assert api.L.d_calls[(2, "word")] == 1
    assert api.T.section_calls == Counter({101: 1, 201: 1})
    assert api.E.manuscript_of.t_calls == Counter({1: 1, 2: 1})


def test_work_passage_outer_witness_metadata_does_not_alias_nested_passage_state():
    api = work_passage_api()
    result = Apparatus(api).work_passage("Work", "1", "1")
    outer = result["versions"]["Work__A"]["witnesses"]["X"]
    inner = result["versions"]["Work__A"]["passage"]["witnesses"]["X"]

    outer["name"] = "changed by caller"
    assert inner["name"] == "Citation only"
    assert "segments" not in outer
    assert "segments" in inner
