from __future__ import annotations

import pseudepigrapha_tf.graph as graph
from pseudepigrapha_tf.model import Book, DivisionSpec, Reading, Token, Unit, Version


def _reading(option: str, count: int) -> Reading:
    tokens = tuple(Token(text=f"w{option}_{index}") for index in range(count))
    return Reading(
        option=option,
        witnesses=(),
        mss_raw="",
        linebreak="",
        indent="",
        text=" ".join(token.text for token in tokens),
        content_xml="",
        tokens=tokens,
    )


def test_add_unit_builds_source_reference_once_independent_of_token_count(monkeypatch) -> None:
    book = Book(filename="Perf", title="Performance", text_structure="", versions=())
    version = Version(
        title="Greek",
        author="",
        language="grc",
        fragment="",
        divisions=(DivisionSpec("Chapter", ":"), DivisionSpec("Verse", "")),
        resources=(),
        manuscripts=(),
        divs=(),
    )
    unit = Unit(
        unit_id="u1",
        group="0",
        parallel="",
        linebreak="",
        readings=(_reading("0", 5), _reading("1", 7)),
    )
    builder = graph._Builder()
    calls = 0
    original = graph._ref_features

    def counted(path, specs):
        nonlocal calls
        calls += 1
        return original(path, specs)

    monkeypatch.setattr(graph, "_ref_features", counted)
    graph._add_unit(
        builder,
        book,
        version,
        "book:1:version:1",
        unit,
        1,
        {},
        ("1", "2"),
        version.divisions,
        "book:1:version:1:div:2",
        [],
    )

    # Source-reference construction is a unit-level operation. Growing primary
    # or variant token counts must not cause another _ref_features() call.
    assert calls == 1

    expected_ref = "1:2"
    expected_parts = '["1", "2"]'
    primary_slots = range(1, 6)
    for slot in primary_slots:
        assert builder.slot_features["source_ref"][slot] == expected_ref
        assert builder.slot_features["source_ref_parts"][slot] == expected_parts

    relevant = [
        obj
        for obj in builder.objects
        if obj.kind in {"unit", "reading", "variant_word"}
    ]
    assert [obj.kind for obj in relevant].count("unit") == 1
    assert [obj.kind for obj in relevant].count("reading") == 2
    assert [obj.kind for obj in relevant].count("variant_word") == 7
    for obj in relevant:
        assert obj.features["source_ref"] == expected_ref
        assert obj.features["source_ref_parts"] == expected_parts
