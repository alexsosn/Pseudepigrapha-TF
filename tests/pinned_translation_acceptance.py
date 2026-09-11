from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pseudepigrapha_tf import Translations
from pseudepigrapha_tf import audit


def _language_map(records):
    by_source: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for record in records:
        by_source[
            (
                str(record["ocp_book"]),
                str(record["source_version_title"]),
                str(record["source_version_language"]),
            )
        ].add(str(record["language"]))
    return {key: tuple(sorted(values)) for key, values in sorted(by_source.items())}


def verify(api, source_dir: Path) -> None:
    raw = audit._raw_inventory(source_dir)
    assert raw["generated_translation_mapping_failures"] == []

    expected_versions = tuple(raw["generated_translations"])
    assert len(expected_versions) == 231
    assert sum(int(record["unit_count"]) for record in expected_versions) == 54143

    translations = Translations(api)
    actual_versions = translations.versions()
    assert len(actual_versions) == len(expected_versions)

    aligned_by_book: dict[int, tuple[dict[str, object], ...]] = {}
    actual_inventory: list[tuple[object, ...]] = []
    api_generated_units: set[int] = set()
    actual_languages: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    for record in actual_versions:
        book_node = int(record["node"])
        source_node = int(record["source_node"])
        aligned = translations.aligned_units(book_node)
        aligned_by_book[book_node] = aligned

        source_title = str(api.F.version_title.v(source_node) or "")
        source_language = str(api.F.language.v(source_node) or "")
        actual_inventory.append(
            (
                str(record["work"]),
                str(record["title"]),
                str(record["language"]),
                str(record["generation_marker"]),
                source_title,
                source_language,
                len(aligned),
            )
        )
        actual_languages[(str(record["work"]), source_title, source_language)].add(
            str(record["language"])
        )

        assert record["generation_marker"] == "OCP-Trans"
        assert record["generation_method"] == "llm"
        assert record["generation_model"] == "openrouter/google/gemini-3.7-flash"
        assert api.F.version_kind.v(source_node) == "source"
        assert aligned, record["id"]

        source_units: list[int] = []
        for row in aligned:
            generated_unit = int(row["translation_unit"])
            source_unit = int(row["source_unit"])
            api_generated_units.add(generated_unit)
            source_units.append(source_unit)

            targets = tuple(api.E.translation_unit_of.f(generated_unit))
            assert targets == (source_unit,), (record["id"], generated_unit, targets, source_unit)
            assert api.F.version_kind.v(generated_unit) == "generated_translation"
            assert api.F.version_kind.v(source_unit) == "source"
            assert row["translation_unit_id"] == str(api.F.unit_id.v(generated_unit) or "")
            assert row["source_unit_id"] == str(api.F.unit_id.v(source_unit) or "")
            assert row["source_ref"] == str(api.F.source_ref.v(source_unit) or "")

        # Occurrence identity must survive the public API even where source
        # refs/unit ids repeat: one generated occurrence cannot collapse onto
        # another occurrence's source unit.
        assert len(set(source_units)) == len(source_units), record["id"]

        # Exercise the passage-facing API on every generated version, not one
        # convenient sample. The first aligned occurrence is sufficient to
        # prove section resolution and source association for that book while
        # aligned_units() above exhaustively checks every unit.
        first = aligned[0]
        section = api.T.sectionFromNode(int(first["translation_unit"]))
        assert section and len(section) == 3, (record["id"], section)
        assert str(section[0]) == str(record["id"]), (record["id"], section)
        passage = translations.passage(str(record["id"]), str(section[1]), str(section[2]))
        assert int(passage["source_book_node"]) == source_node
        passage_pairs = {
            (int(unit["translation_unit"]), int(unit["source_unit"]))
            for unit in passage["units"]
        }
        assert (
            int(first["translation_unit"]),
            int(first["source_unit"]),
        ) in passage_pairs, record["id"]

    expected_inventory = sorted(
        (
            str(record["ocp_book"]),
            str(record["version_title"]),
            str(record["language"]),
            str(record["marker"]),
            str(record["source_version_title"]),
            str(record["source_version_language"]),
            int(record["unit_count"]),
        )
        for record in expected_versions
    )
    assert sorted(actual_inventory) == expected_inventory

    graph_generated_units = {
        node
        for node in api.F.otype.s("unit")
        if api.F.version_kind.v(node) == "generated_translation"
    }
    assert len(graph_generated_units) == 54143
    assert api_generated_units == graph_generated_units

    expected_languages = _language_map(expected_versions)
    normalized_actual_languages = {
        key: tuple(sorted(values)) for key, values in sorted(actual_languages.items())
    }
    assert normalized_actual_languages == expected_languages

    # Make the absence/fallback assertion non-vacuous for the exact pinned
    # corpus: at least one source version genuinely lacks one target language.
    all_languages = {language for values in expected_languages.values() for language in values}
    missing = {
        key: tuple(sorted(all_languages - set(values)))
        for key, values in expected_languages.items()
        if set(values) != all_languages
    }
    assert missing
