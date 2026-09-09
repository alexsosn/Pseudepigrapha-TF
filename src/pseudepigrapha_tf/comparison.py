from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from html import escape
from typing import Any
from urllib.parse import urlencode

from .apparatus import Apparatus
from .translations import Translations

DEFAULT_VERSION_LIMIT = 2
DEFAULT_WITNESS_LIMIT = 4


def _unique_strings(values: Iterable[object]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return tuple(result)


def comparison_href(
    work: object,
    chapter: object,
    verse: object,
    *,
    selected_versions: Iterable[object] = (),
    selected_witnesses: Mapping[str, Iterable[object]] | None = None,
) -> str:
    """Build a deterministic comparison URL while preserving selection state."""

    work_text = str(work).strip()
    chapter_text = str(chapter).strip()
    verse_text = str(verse).strip()
    if not (work_text and chapter_text and verse_text):
        raise ValueError("work, chapter, and verse are required for comparison navigation")

    versions = _unique_strings(selected_versions)
    pairs: list[tuple[str, str]] = [
        ("work", work_text),
        ("chapter", chapter_text),
        ("verse", verse_text),
    ]
    pairs.extend(("version", version_id) for version_id in versions)

    if selected_witnesses is not None:
        for version_id in versions:
            if version_id not in selected_witnesses:
                continue
            key = f"witness.{version_id}"
            witnesses = _unique_strings(selected_witnesses[version_id])
            if witnesses:
                pairs.extend((key, witness) for witness in witnesses)
            else:
                pairs.append((key, ""))

    return f"/compare?{urlencode(pairs)}"


def passage_neighbors(
    api: Any,
    work: object,
    chapter: object,
    verse: object,
    *,
    preferred_versions: Iterable[object] = (),
) -> dict[str, object]:
    """Resolve previous/next passage from one real source-version section topology.

    Generated translations never participate. Preferred source versions are tried
    first, but a preferred version that lacks the current passage is skipped in
    favor of another source version of the same OCP work that actually contains it.
    """

    work_text = str(work)
    chapter_text = str(chapter)
    verse_text = str(verse)

    otype = getattr(api.F, "otype", None)
    books_for_type = getattr(otype, "s", None) if otype is not None else None
    ocp_book = getattr(api.F, "ocp_book", None)
    if books_for_type is None or ocp_book is None:
        raise ValueError("otype and ocp_book features must be loaded for passage navigation")

    version_kind = getattr(api.F, "version_kind", None)
    source_books: dict[str, int] = {}
    for book_node in books_for_type("book"):
        if str(ocp_book.v(book_node) or "") != work_text:
            continue
        if version_kind is not None and version_kind.v(book_node) == "generated_translation":
            continue
        section = api.T.sectionFromNode(book_node)
        if not section or not section[0]:
            raise ValueError(f"cannot resolve TF source-version section id for book node {book_node}")
        version_id = str(section[0])
        if version_id in source_books:
            raise ValueError(f"duplicate source-version section id for navigation: {version_id!r}")
        source_books[version_id] = book_node

    if not source_books:
        raise KeyError(f"OCP work has no source versions in loaded Text-Fabric data: {work_text!r}")

    preferred = tuple(
        version_id
        for version_id in _unique_strings(preferred_versions)
        if version_id in source_books
    )
    candidates = preferred + tuple(
        version_id for version_id in source_books if version_id not in preferred
    )

    for version_id in candidates:
        book_node = source_books[version_id]
        verse_nodes = tuple(api.L.d(book_node, otype="verse"))
        verse_index = getattr(api.F, "verse_index", None)
        if verse_index is not None:
            verse_nodes = tuple(
                sorted(verse_nodes, key=lambda node: (verse_index.v(node) or 0, node))
            )

        sections: list[tuple[str, str]] = []
        current_positions: list[int] = []
        for index, verse_node in enumerate(verse_nodes):
            section = api.T.sectionFromNode(verse_node)
            if not section or len(section) < 3:
                raise ValueError(f"cannot resolve TF passage section for verse node {verse_node}")
            if str(section[0]) != version_id:
                raise ValueError(
                    f"verse node {verse_node} belongs to section {section[0]!r}, expected {version_id!r}"
                )
            section_pair = (str(section[1]), str(section[2]))
            sections.append(section_pair)
            if section_pair == (chapter_text, verse_text):
                current_positions.append(index)

        if not current_positions:
            continue
        if len(current_positions) != 1:
            raise ValueError(
                f"source version {version_id!r} has duplicate TF passage address "
                f"{(chapter_text, verse_text)!r}"
            )

        current = current_positions[0]
        return {
            "context_version": version_id,
            "previous": sections[current - 1] if current > 0 else None,
            "next": sections[current + 1] if current + 1 < len(sections) else None,
        }

    return {"context_version": None, "previous": None, "next": None}


def _showable_witness(record: Mapping[str, object]) -> bool:
    if record.get("declared") is False:
        return False
    show = str(record.get("show", "")).strip().lower()
    return show not in {"0", "false", "hide", "hidden", "no", "off"}


def _primary_segments(passage: Mapping[str, object]) -> tuple[dict[str, object], ...]:
    result: list[dict[str, object]] = []
    for unit in passage.get("units", ()):
        unit_record = unit if isinstance(unit, Mapping) else {}
        readings = tuple(
            reading
            for reading in unit_record.get("readings", ())
            if isinstance(reading, Mapping) and reading.get("primary") is True
        )
        if len(readings) != 1:
            raise ValueError(
                f"apparatus unit {unit_record.get('unit')!r} has {len(readings)} primary readings; "
                "expected exactly 1"
            )
        reading = readings[0]
        text = str(reading.get("text") or "")
        omission = bool(reading.get("omission")) or text == ""
        result.append(
            {
                "unit": str(unit_record.get("unit", "")),
                "status": "omission" if omission else "reading",
                "text": text,
            }
        )
    return tuple(result)


def _joined_reading_text(segments: Iterable[Mapping[str, object]]) -> str:
    return " ".join(
        text
        for segment in segments
        if str(segment.get("status")) == "reading"
        and (text := str(segment.get("text") or ""))
    )


def _witness_view(record: Mapping[str, object]) -> dict[str, object]:
    segments = tuple(
        dict(segment)
        for segment in record.get("segments", ())
        if isinstance(segment, Mapping)
    )
    for segment in segments:
        segment["unit"] = str(segment.get("unit", ""))
        segment["status"] = str(segment.get("status", ""))
        if segment["status"] not in {"reading", "omission", "unattested"}:
            raise ValueError(f"unknown witness segment state: {segment['status']!r}")
        text = segment.get("text")
        segment["text"] = None if text is None else str(text)
    return {
        "node": record.get("node"),
        "abbrev": str(record.get("abbrev", "")),
        "declared": bool(record.get("declared", True)),
        "language": str(record.get("language", "")),
        "name": str(record.get("name", "")),
        "show": str(record.get("show", "")),
        "segments": segments,
        "coverage": dict(record.get("coverage", {})),
        "complete": bool(record.get("complete", False)),
    }


def _selected_witness_ids(
    version_id: str,
    witnesses: Mapping[str, Mapping[str, object]],
    selected_witnesses: Mapping[str, Iterable[str]] | None,
) -> tuple[str, ...]:
    if selected_witnesses is not None and version_id in selected_witnesses:
        requested = _unique_strings(selected_witnesses[version_id])
        unknown = tuple(siglum for siglum in requested if siglum not in witnesses)
        if unknown:
            raise ValueError(
                f"unknown witness for source version {version_id!r}: {', '.join(unknown)}"
            )
        return requested

    ordered = tuple(witnesses)
    preferred = tuple(siglum for siglum in ordered if _showable_witness(witnesses[siglum]))
    fallback = tuple(siglum for siglum in ordered if siglum not in preferred)
    return (preferred + fallback)[:DEFAULT_WITNESS_LIMIT]


def _translation_view(
    translations: Translations,
    record: Mapping[str, object],
    chapter: str,
    verse: str,
    *,
    expected_source_units: frozenset[object] | None = None,
    source_passage_present: bool = True,
) -> dict[str, object]:
    generated_id = str(record.get("id", ""))
    base = {
        "node": record.get("node"),
        "id": generated_id,
        "title": str(record.get("title", "")),
        "language": str(record.get("language", "")),
        "source_node": record.get("source_node"),
        "source_id": str(record.get("source_id", "")),
        "generation_marker": str(record.get("generation_marker", "")),
        "generation_method": str(record.get("generation_method", "")),
        "generation_model": str(record.get("generation_model", "")),
    }
    try:
        passage = translations.passage(generated_id, chapter, verse)
    except KeyError:
        return {
            **base,
            "status": "not_present",
            "units": (),
            "text": "",
        }

    if not source_passage_present:
    raise ValueError(
        f"generated translation {generated_id!r} has a passage but source passage is not present"
    )

    source_book_node = passage.get("source_book_node")
    expected_source_node = record.get("source_node")
    if (
        expected_source_node is not None
        and source_book_node is not None
        and source_book_node != expected_source_node
    ):
        raise ValueError(
            f"generated translation {generated_id!r} passage points to source node "
            f"{source_book_node}, expected {expected_source_node}"
        )

    units = tuple(
        dict(unit) for unit in passage.get("units", ()) if isinstance(unit, Mapping)
    )
    if expected_source_units is not None:
        for unit in units:
            source_unit = unit.get("source_unit")
            if source_unit not in expected_source_units:
                raise ValueError(
                    f"generated translation {generated_id!r} source unit {source_unit!r} "
                    "is outside requested source passage"
                )
    text = " ".join(
        chunk
        for unit in units
        if (chunk := str(unit.get("translation_text") or ""))
    )
    return {
        **base,
        "status": "available",
        "units": units,
        "text": text,
    }


def build_passage_comparison(
    api: Any,
    work: str,
    chapter: str | int,
    verse: str | int,
    *,
    selected_versions: Iterable[str] | None = None,
    selected_witnesses: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, object]:
    """Build a verse-centered comparison from public apparatus/translation APIs.

    Historical witness semantics come exclusively from :class:`Apparatus` and
    generated translation ownership/alignment exclusively from
    :class:`Translations`. Technical ``oslots`` anchors are never consulted.
    """

    work = str(work)
    chapter = str(chapter)
    verse = str(verse)

    apparatus = Apparatus(api)
    translations = Translations(api)
    work_passage = apparatus.work_passage(work, chapter, verse)

    source_versions = work_passage.get("versions", {})
    if not isinstance(source_versions, Mapping):
        raise ValueError("Apparatus.work_passage() returned invalid versions mapping")

    source_ids = tuple(str(version_id) for version_id in source_versions)
    if selected_versions is None:
        available = tuple(
            version_id
            for version_id in source_ids
            if isinstance(source_versions[version_id], Mapping)
            and source_versions[version_id].get("status") == "available"
        )
        unavailable = tuple(
            version_id for version_id in source_ids if version_id not in available
        )
        selected_ids = (available + unavailable)[:DEFAULT_VERSION_LIMIT]
    else:
        selected_ids = _unique_strings(selected_versions)
        unknown = tuple(
            version_id for version_id in selected_ids if version_id not in source_versions
        )
        if unknown:
            raise ValueError(f"unknown source version: {', '.join(unknown)}")

    if selected_witnesses is not None:
        unknown_witness_versions = tuple(
            str(version_id)
            for version_id in selected_witnesses
            if str(version_id) not in source_versions
        )
        if unknown_witness_versions:
            raise ValueError(
                "witness selection targets unknown source version: "
                + ", ".join(unknown_witness_versions)
            )

    generated = tuple(translations.versions(work=work))
    generated_by_source: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for record in generated:
        if not isinstance(record, Mapping):
            raise ValueError("Translations.versions() returned a non-mapping record")
        source_id = str(record.get("source_id", ""))
        if source_id not in source_versions:
            raise ValueError(
                f"generated translation {record.get('id')!r} targets unknown source version {source_id!r}"
            )
        generated_by_source[source_id].append(record)

    version_choices: list[dict[str, object]] = []
    for version_id in source_ids:
        record = source_versions[version_id]
        if not isinstance(record, Mapping):
            raise ValueError(f"source version {version_id!r} is not a mapping")
        version_choices.append(
            {
                "id": version_id,
                "title": str(record.get("title", "")),
                "language": str(record.get("language", "")),
                "author": str(record.get("author", "")),
                "status": str(record.get("status", "")),
                "selected": version_id in selected_ids,
            }
        )

    selected_records: list[dict[str, object]] = []
    for version_id in selected_ids:
        source_record = source_versions[version_id]
        if not isinstance(source_record, Mapping):
            raise ValueError(f"source version {version_id!r} is not a mapping")
        status = str(source_record.get("status", ""))
        if status not in {"available", "not_present"}:
            raise ValueError(
                f"unknown source passage status for {version_id!r}: {status!r}"
            )

        passage = source_record.get("passage")
        primary_segments: tuple[dict[str, object], ...] = ()
        primary_text = ""
        witness_choices: tuple[dict[str, object], ...] = ()
        witness_rows: tuple[dict[str, object], ...] = ()
        expected_source_units: frozenset[object] | None = None

        if status == "available":
            if not isinstance(passage, Mapping):
                raise ValueError(
                    f"available source version {version_id!r} has no passage mapping"
                )
            primary_segments = _primary_segments(passage)
            primary_text = _joined_reading_text(primary_segments)
            source_units = tuple(
                unit for unit in passage.get("units", ()) if isinstance(unit, Mapping)
            )
            expected_source_units = frozenset(
                unit.get("node") for unit in source_units if unit.get("node") is not None
            )

            raw_witnesses = passage.get("witnesses", {})
            if not isinstance(raw_witnesses, Mapping):
                raise ValueError(
                    f"source version {version_id!r} has invalid witness mapping"
                )
            witness_map: dict[str, Mapping[str, object]] = {
                str(siglum): record
                for siglum, record in raw_witnesses.items()
                if isinstance(record, Mapping)
            }
            selected_sigla = _selected_witness_ids(
                version_id,
                witness_map,
                selected_witnesses,
            )
            witness_choices = tuple(
                {
                    "abbrev": siglum,
                    "name": str(witness_map[siglum].get("name", "")),
                    "language": str(witness_map[siglum].get("language", "")),
                    "declared": bool(witness_map[siglum].get("declared", True)),
                    "show": str(witness_map[siglum].get("show", "")),
                    "selected": siglum in selected_sigla,
                }
                for siglum in witness_map
            )
            witness_rows = tuple(
                _witness_view(witness_map[siglum]) for siglum in selected_sigla
            )
        else:
            raw_witnesses = source_record.get("witnesses", {})
            if not isinstance(raw_witnesses, Mapping):
                raise ValueError(
                    f"source version {version_id!r} has invalid witness mapping"
                )
            witness_map = {
                str(siglum): record
                for siglum, record in raw_witnesses.items()
                if isinstance(record, Mapping)
            }
            selected_sigla = _selected_witness_ids(
                version_id,
                witness_map,
                selected_witnesses,
            )
            witness_choices = tuple(
                {
                    "abbrev": siglum,
                    "name": str(witness_map[siglum].get("name", "")),
                    "language": str(witness_map[siglum].get("language", "")),
                    "declared": bool(witness_map[siglum].get("declared", True)),
                    "show": str(witness_map[siglum].get("show", "")),
                    "selected": siglum in selected_sigla,
                }
                for siglum in witness_map
            )

        translation_rows = tuple(
            _translation_view(
                translations,
                record,
                chapter,
                verse,
                expected_source_units=expected_source_units,
                source_passage_present=status == "available",
            )
            for record in generated_by_source.get(version_id, ())
        )

        selected_records.append(
            {
                "node": source_record.get("node"),
                "id": version_id,
                "title": str(source_record.get("title", "")),
                "language": str(source_record.get("language", "")),
                "author": str(source_record.get("author", "")),
                "status": status,
                "primary_segments": primary_segments,
                "primary_text": primary_text,
                "witness_choices": witness_choices,
                "witnesses": witness_rows,
                "translations": translation_rows,
            }
        )

    metadata_only = work_passage.get("metadata_only_versions", {})
    if not isinstance(metadata_only, Mapping):
        raise ValueError(
            "Apparatus.work_passage() returned invalid metadata-only versions mapping"
        )
    metadata_records = tuple(
        {
            "node": record.get("node"),
            "id": str(version_id),
            "title": str(record.get("title", "")),
            "language": str(record.get("language", "")),
            "author": str(record.get("author", "")),
            "status": "metadata_only",
        }
        for version_id, record in metadata_only.items()
        if isinstance(record, Mapping)
    )

    return {
        "work": work,
        "title": str(work_passage.get("title", "")),
        "chapter": chapter,
        "verse": verse,
        "reference": (chapter, verse),
        "version_choices": tuple(version_choices),
        "versions": tuple(selected_records),
        "metadata_only_versions": metadata_records,
    }


def _h(value: object) -> str:
    return escape(str(value), quote=True)


def _render_text_segments(segments: Iterable[Mapping[str, object]]) -> str:
    chunks: list[str] = []
    for segment in segments:
        status = str(segment.get("status", ""))
        text = segment.get("text")
        if status == "reading":
            chunks.append(f'<span class="state-reading">{_h(text or "")}</span>')
        elif status == "omission":
            chunks.append('<span class="state-omission">[omission]</span>')
        elif status == "unattested":
            chunks.append('<span class="state-unattested">[unattested]</span>')
        else:
            raise ValueError(f"unknown presentation segment state: {status!r}")
    return " ".join(chunks)


def _render_translation(
    record: Mapping[str, object], *, open_by_default: bool
) -> str:
    language = str(record.get("language", ""))
    title = str(record.get("title", ""))
    model = str(record.get("generation_model", ""))
    summary_parts = [part for part in (language, title) if part]
    summary = " — ".join(summary_parts) or str(record.get("id", "translation"))
    open_attr = " open" if open_by_default else ""
    if record.get("status") == "not_present":
        body = '<p class="state-not-present">not present</p>'
    else:
        body = f'<div class="translation-text">{_h(record.get("text", ""))}</div>'
    provenance = " · ".join(
        part
        for part in (
            str(record.get("generation_marker", "")),
            str(record.get("generation_method", "")),
            model,
        )
        if part
    )
    provenance_html = (
        f'<div class="translation-provenance">{_h(provenance)}</div>'
        if provenance
        else ""
    )
    return (
        f'<details class="translation-block" data-translation-id="{_h(record.get("id", ""))}"{open_attr}>'
        f'<summary>{_h(summary)}</summary>{body}{provenance_html}</details>'
    )


def _render_witness(record: Mapping[str, object]) -> str:
    label = str(record.get("abbrev", ""))
    name = str(record.get("name", ""))
    language = str(record.get("language", ""))
    identity = " — ".join(part for part in (label, name, language) if part)
    completeness = "complete" if record.get("complete") else "partial coverage"
    return (
        f'<article class="witness-row" data-witness="{_h(label)}">'
        f'<h4>{_h(identity)}</h4>'
        f'<div class="witness-text">{_render_text_segments(record.get("segments", ()))}</div>'
        f'<div class="witness-coverage">{_h(completeness)}</div>'
        "</article>"
    )


def _render_version_card(record: Mapping[str, object]) -> str:
    version_id = str(record.get("id", ""))
    title = str(record.get("title", "")) or version_id
    language = str(record.get("language", ""))
    author = str(record.get("author", ""))
    heading = " — ".join(part for part in (title, language) if part)
    parts = [
        f'<section class="source-version-card" data-version-id="{_h(version_id)}">',
        f'<h2>{_h(heading)}</h2>',
    ]
    if author:
        parts.append(f'<div class="source-author">{_h(author)}</div>')

    if record.get("status") == "not_present":
        parts.append('<p class="state-not-present">not present</p>')
    else:
        parts.extend(
            (
                '<section class="source-passage"><h3>Source text</h3>',
                f'<div class="source-text">{_render_text_segments(record.get("primary_segments", ()))}</div>',
                "</section>",
            )
        )

    translations = tuple(record.get("translations", ()))
    if translations:
        parts.append('<section class="translations"><h3>Translations</h3>')
        parts.extend(
            _render_translation(translation, open_by_default=index == 0)
            for index, translation in enumerate(translations)
        )
        parts.append("</section>")

    witness_choices = tuple(record.get("witness_choices", ()))
    if witness_choices:
        parts.append(
            f'<input type="hidden" name="witness.{_h(version_id)}" value="" '
            'form="comparison-controls">'
        )
        parts.append(
            '<details class="witness-selector"><summary>Choose witnesses</summary>'
        )
        for choice in witness_choices:
            checked = " checked" if choice.get("selected") else ""
            siglum = str(choice.get("abbrev", ""))
            parts.append(
                f'<label><input type="checkbox" name="witness.{_h(version_id)}" '
                f'value="{_h(siglum)}"{checked} form="comparison-controls"> {_h(siglum)}</label>'
            )
        parts.append("</details>")

    witnesses = tuple(record.get("witnesses", ()))
    if witnesses:
        parts.append('<section class="witness-comparison"><h3>Manuscripts</h3>')
        parts.extend(_render_witness(witness) for witness in witnesses)
        parts.append("</section>")

    parts.append("</section>")
    return "".join(parts)


def _selected_render_state(
    model: Mapping[str, object],
) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    selected_versions = tuple(
        str(choice.get("id", ""))
        for choice in model.get("version_choices", ())
        if isinstance(choice, Mapping) and choice.get("selected")
    )
    selected_witnesses: dict[str, tuple[str, ...]] = {}
    for version in model.get("versions", ()):
        if not isinstance(version, Mapping):
            continue
        version_id = str(version.get("id", ""))
        choices = tuple(
            choice
            for choice in version.get("witness_choices", ())
            if isinstance(choice, Mapping)
        )
        if not choices:
            continue
        selected_witnesses[version_id] = tuple(
            str(choice.get("abbrev", ""))
            for choice in choices
            if choice.get("selected")
        )
    return selected_versions, selected_witnesses


def render_passage_comparison(model: Mapping[str, object]) -> str:
    """Render a passage-comparison model as deterministic escaped HTML."""

    work = str(model.get("work", ""))
    chapter = str(model.get("chapter", ""))
    verse = str(model.get("verse", ""))
    title = str(model.get("title", "")) or work
    selected_versions, selected_witnesses = _selected_render_state(model)

    parts = [
        '<!doctype html><html><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{_h(title)} {_h(chapter)}:{_h(verse)}</title>',
        '<link rel="stylesheet" href="/data/static/comparison.css">',
        '</head><body><main class="comparison-page">',
        '<nav class="comparison-nav"><a href="/">Text-Fabric browser</a></nav>',
        f'<header><h1>{_h(title)}</h1><div class="passage-reference">{_h(chapter)}:{_h(verse)}</div></header>',
    ]

    navigation = model.get("navigation")
    if isinstance(navigation, Mapping):
        previous = navigation.get("previous")
        following = navigation.get("next")
        if previous is not None or following is not None:
            parts.append('<nav class="passage-navigation">')
            if previous is not None:
                prev_chapter, prev_verse = previous
                href = comparison_href(
                    work,
                    prev_chapter,
                    prev_verse,
                    selected_versions=selected_versions,
                    selected_witnesses=selected_witnesses,
                )
                parts.append(f'<a rel="prev" href="{_h(href)}">Previous</a>')
            if following is not None:
                next_chapter, next_verse = following
                href = comparison_href(
                    work,
                    next_chapter,
                    next_verse,
                    selected_versions=selected_versions,
                    selected_witnesses=selected_witnesses,
                )
                parts.append(f'<a rel="next" href="{_h(href)}">Next</a>')
            parts.append("</nav>")

    parts.extend(
        (
            '<form id="comparison-controls" class="comparison-controls" action="/compare" method="get">',
            f'<input type="hidden" name="work" value="{_h(work)}">',
            f'<input type="hidden" name="chapter" value="{_h(chapter)}">',
            f'<input type="hidden" name="verse" value="{_h(verse)}">',
            '<fieldset><legend>Source versions</legend>',
        )
    )

    for choice in model.get("version_choices", ()):
        checked = " checked" if choice.get("selected") else ""
        choice_id = str(choice.get("id", ""))
        choice_title = str(choice.get("title", "")) or choice_id
        choice_language = str(choice.get("language", ""))
        label = " — ".join(
            part for part in (choice_title, choice_language) if part
        )
        parts.append(
            f'<label><input type="checkbox" name="version" value="{_h(choice_id)}"{checked}> '
            f'{_h(label)}</label>'
        )
    parts.extend(
        (
            '</fieldset><button type="submit">Compare</button></form>',
            '<div class="version-grid">',
        )
    )

    parts.extend(
        _render_version_card(version) for version in model.get("versions", ())
    )
    parts.append("</div>")

    metadata_only = tuple(model.get("metadata_only_versions", ()))
    if metadata_only:
        parts.append(
            '<aside class="metadata-only-versions"><h2>Metadata-only versions</h2><ul>'
        )
        for record in metadata_only:
            label = " — ".join(
                part
                for part in (
                    str(record.get("title", "")) or str(record.get("id", "")),
                    str(record.get("language", "")),
                )
                if part
            )
            parts.append(f'<li>{_h(label)}</li>')
        parts.append("</ul></aside>")

    parts.append("</main></body></html>")
    return "".join(parts)
