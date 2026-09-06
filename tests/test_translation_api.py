from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

from pseudepigrapha_tf import Apparatus, Translations


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
        self.forward = {source: set(targets) for source, targets in forward.items()}
        self.inverse = {}
        for source, targets in self.forward.items():
            for target in targets:
                self.inverse.setdefault(target, set()).add(source)

    def f(self, node):
        return tuple(sorted(self.forward.get(node, ())))

    def t(self, node):
        return tuple(sorted(self.inverse.get(node, ())))


class Locality:
    def d(self, node, otype=None):
        assert otype == "unit"
        return {
            1: (10,),
            2: (20,),
            100: (20,),
        }.get(node, ())

    def u(self, node, otype=None):
        assert otype == "book"
        return {100: (2,)}.get(node, ())


class Text:
    def sectionFromNode(self, node):
        return {1: ("Demo",), 2: ("Demo__translation__French",)}.get(node)

    def nodeFromSection(self, reference):
        if tuple(reference) == ("Demo__translation__French", "1", "1"):
            return 100
        return None


def translation_api():
    F = SimpleNamespace(
        otype=OtypeFeature(
            {
                1: "book",
                2: "book",
                10: "unit",
                20: "unit",
                30: "reading",
                40: "reading",
                50: "manuscript",
                51: "manuscript",
            }
        ),
        book=Feature({1: "Demo", 2: "Demo__translation__French"}),
        ocp_book=Feature({1: "Demo", 2: "Demo"}),
        version_title=Feature({1: "Greek", 2: "Greek (French)"}),
        version_kind=Feature({1: "source", 2: "generated_translation", 10: "source", 20: "generated_translation"}),
        language=Feature({1: "Greek", 2: "French"}),
        generated_language=Feature({2: "French"}),
        generation_method=Feature({2: "llm"}),
        generation_model=Feature({2: "openrouter/google/gemini-3.7-flash"}),
        generation_marker=Feature({2: "OCP-Trans"}),
        unit_id=Feature({10: "1", 20: "fr_1"}),
        source_ref=Feature({10: "1:1", 20: "1:1"}),
        unit_index=Feature({10: 1, 20: 1}),
        reading_text=Feature({30: "λόγος", 40: "mot"}),
        is_primary=Feature({30: 1, 40: 1}),
        ms_abbrev=Feature({50: "A", 51: "OCP-Trans"}),
        synthetic_witness=Feature({51: 1}),
        undefined_manuscript=Feature({50: 0, 51: 0}),
        ms_language=Feature({50: "Greek", 51: "French"}),
        ms_name=Feature({50: "A", 51: "OCP French Translation"}),
        ms_show=Feature({50: "yes", 51: "yes"}),
    )
    E = SimpleNamespace(
        translation_of=Edge({2: {1}}),
        translation_unit_of=Edge({20: {10}}),
        reading_of=Edge({30: {10}, 40: {20}}),
        manuscript_of=Edge({50: {1}, 51: {2}}),
        witness=Edge({30: {50}, 40: {51}}),
    )
    return SimpleNamespace(F=F, E=E, L=Locality(), T=Text())


def test_translations_lists_generated_versions_with_explicit_source_and_provenance():
    records = Translations(translation_api()).versions(work="Demo", language="French")

    assert records == (
        {
            "node": 2,
            "id": "Demo__translation__French",
            "work": "Demo",
            "title": "Greek (French)",
            "language": "French",
            "source_node": 1,
            "source_id": "Demo",
            "generation_marker": "OCP-Trans",
            "generation_method": "llm",
            "generation_model": "openrouter/google/gemini-3.7-flash",
        },
    )


def test_translations_returns_occurrence_aligned_source_and_translation_text():
    helper = Translations(translation_api())

    assert helper.source_version(2) == 1
    assert helper.aligned_units(2) == (
        {
            "translation_unit": 20,
            "source_unit": 10,
            "translation_unit_id": "fr_1",
            "source_unit_id": "1",
            "source_ref": "1:1",
            "translation_text": "mot",
            "source_text": "λόγος",
        },
    )
    assert helper.passage("Demo__translation__French", "1", "1")["units"] == helper.aligned_units(2)


def test_apparatus_default_witness_view_excludes_synthetic_translation_witness():
    api = translation_api()
    # This directly exercises the witness collection used by passage/work_passage;
    # the synthetic provenance node remains in TF but is not historical evidence.
    witnesses = Apparatus(api)._witnesses(2)

    assert "OCP-Trans" not in witnesses
