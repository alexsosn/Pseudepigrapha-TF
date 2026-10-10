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
    def __init__(self, verse_owners=(1,)):
        self.d_calls = Counter()
        self.verse_owners = tuple(verse_owners)

    def d(self, node, otype=None):
        self.d_calls[(node, otype)] += 1
        if otype == "word":
            return {1: (101,), 2: (201,)}.get(node, ())
        if otype == "unit":
            return {1000: (10,)}.get(node, ())
        return ()

    def u(self, node, otype=None):
        if (node, otype) == (1000, "book"):
            return self.verse_owners
        return ()


class Text:
    def __init__(self, *, bad_book_heading=False):
        self.section_calls = Counter()
        self.bad_book_heading = bad_book_heading

    def sectionFromNode(self, node):
        self.section_calls[node] += 1
        if node == 1 and self.bad_book_heading:
            return ()
        return {
            1: ("Work__A",),
            2: ("Work__B",),
            101: ("Work__A", "1", "1"),
            201: ("Work__B", "1", "1"),
        }[node]

    def nodeFromSection(self, reference):
        if reference == ("Work__A", "1", "1"):
            return 1000
        return None


def work_passage_api(*, verse_owners=(1,), bad_book_heading=False):
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
    return SimpleNamespace(
        F=F,
        E=E,
        L=Locality(verse_owners),
        T=Text(bad_book_heading=bad_book_heading),
    )


def test_work_passage_resolves_each_textual_version_without_word_traversal():
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
    assert nested_x["segments"][0]["status"] == "reading"
    assert available["witnesses"]["X"] is not nested_x

    absent = result["versions"]["Work__B"]
    assert absent["status"] == "not_present"
    assert absent["passage"] is None
    assert set(absent["witnesses"]) == {"B"}

    assert api.L.d_calls[(1, "word")] == 0
    assert api.L.d_calls[(2, "word")] == 0
    assert api.T.section_calls == Counter({1: 1, 2: 1})
    assert api.E.manuscript_of.t_calls == Counter({1: 1, 2: 1})


def test_work_passage_rejects_missing_direct_book_heading():
    api = work_passage_api(bad_book_heading=True)
    with pytest.raises(
        ValueError,
        match=r"cannot resolve TF book section id for textual OCP version node 1",
    ):
        Apparatus(api).work_passage("Work", "1", "1")


def test_work_passage_outer_witness_metadata_does_not_alias_nested_passage_state():
    api = work_passage_api()
    result = Apparatus(api).work_passage("Work", "1", "1")
    outer = result["versions"]["Work__A"]["witnesses"]["X"]
    inner = result["versions"]["Work__A"]["passage"]["witnesses"]["X"]

    outer["name"] = "changed by caller"
    assert inner["name"] == "Citation only"
    assert "segments" not in outer
    assert "segments" in inner


def test_public_passage_still_rejects_multiple_containing_books():
    api = work_passage_api(verse_owners=(1, 2))

    with pytest.raises(
        ValueError,
        match=r"expected one containing book for \('Work__A', '1', '1'\), found \(1, 2\)",
    ):
        Apparatus(api).passage("Work__A", "1", "1")


def test_work_passage_uses_actual_owner_witnesses_for_mismatched_section_owner():
    api = work_passage_api(verse_owners=(2,))
    result = Apparatus(api).work_passage("Work", "1", "1")

    version = result["versions"]["Work__A"]
    assert set(version["witnesses"]) == {"A", "X"}
    assert set(version["passage"]["witnesses"]) == {"B"}
    assert api.E.manuscript_of.t_calls == Counter({1: 1, 2: 2})


def test_repeated_work_passages_reuse_version_inventory_and_book_ids():
    api = work_passage_api()
    counts = Counter()
    original = api.F.otype.s

    def counted_nodes(kind):
        counts[kind] += 1
        return original(kind)

    api.F.otype.s = counted_nodes
    apparatus = Apparatus(api)

    first = apparatus.work_passage("Work", "1", "1")
    second = apparatus.work_passage("Work", 1, 2)

    assert list(first["versions"]) == list(second["versions"]) == ["Work__A", "Work__B"]
    assert second["reference"] == ("1", "2")
    assert counts == Counter({"book": 1, "version_metadata": 1})
    assert api.T.section_calls == Counter({1: 1, 2: 1})


def test_distinct_works_share_inventory_but_resolve_only_requested_book_ids():
    api = work_passage_api()
    api.F.ocp_book.values[2] = "Other"
    api.T.bad_book_heading = True
    counts = Counter()
    original = api.F.otype.s

    def counted_nodes(kind):
        counts[kind] += 1
        return original(kind)

    api.F.otype.s = counted_nodes
    apparatus = Apparatus(api)

    with pytest.raises(
        ValueError,
        match="cannot resolve TF book section id for textual OCP version node 1",
    ):
        apparatus.work_passage("Work", 1, 1)

    # The failed Work lookup must not poison the otherwise valid Other work.
    other = apparatus.work_passage("Other", 1, 1)
    assert list(other["versions"]) == ["Work__B"]
    assert api.T.section_calls == Counter({1: 1, 2: 1})
    assert counts == Counter({"book": 1, "version_metadata": 1})


def test_version_cache_preserves_generated_exclusion_and_metadata_only_ordering():
    api = work_passage_api()
    api.F.otype.values.update({3: "book", 40: "version_metadata", 41: "version_metadata"})
    api.F.ocp_book.values.update({3: "Work", 40: "Work", 41: "Work"})
    api.F.version_kind = Feature({3: "generated_translation"})
    api.F.version_id = Feature({40: "Work__Z", 41: "Work__C"})
    apparatus = Apparatus(api)

    first = apparatus.work_passage("Work", 1, 1)
    second = apparatus.work_passage("Work", 2, 2)

    for result in (first, second):
        assert list(result["versions"]) == ["Work__A", "Work__B"]
        assert list(result["metadata_only_versions"]) == ["Work__C", "Work__Z"]
        assert all(
            record["status"] == "metadata_only"
            for record in result["metadata_only_versions"].values()
        )
    # A generated book must never have its section resolved by the apparatus.
    assert api.T.section_calls == Counter({1: 1, 2: 1})


def test_missing_work_reuses_inventory_without_caching_failed_results():
    api = work_passage_api()
    counts = Counter()
    original = api.F.otype.s

    def counted_nodes(kind):
        counts[kind] += 1
        return original(kind)

    api.F.otype.s = counted_nodes
    apparatus = Apparatus(api)
    for _ in range(2):
        with pytest.raises(KeyError, match="OCP work not found"):
            apparatus.work_passage("Absent", 1, 1)

    assert counts == Counter({"book": 1, "version_metadata": 1})
    assert api.T.section_calls == Counter()
