from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from . import audit as base
from .graph import TFData
from .model import DivisionSpec
from .source_versions import is_wrapped_legacy_version


def _reading_signature(reading: ET.Element, index: int, primary_index: int) -> dict[str, object]:
    return {
        "reading_index": index + 1,
        "option": reading.get("option", ""),
        "mss": reading.get("mss", "").strip(),
        "linebreak": reading.get("linebreak", ""),
        "indent": reading.get("indent", ""),
        "text": base._plain_text(reading),
        "xml": base._inner_xml(reading),
        "primary": index == primary_index,
    }


def _raw_unit_occurrences(source_dir: Path) -> list[dict[str, object]]:
    """Read unit→reading occurrence ownership directly from upstream XML."""

    records: list[dict[str, object]] = []

    def add_textual_version(
        *,
        path: Path,
        ocp_book: str,
        version: ET.Element,
        version_title: str,
        language: str,
        version_kind: str,
        specs: tuple[DivisionSpec, ...],
        legacy: bool,
    ) -> None:
        text = version.find("text") if version.tag == "version" else version.find("text")
        if text is None:
            return

        unit_index = 0

        def add_unit(unit: ET.Element, source_path: tuple[str, ...]) -> None:
            nonlocal unit_index
            unit_index += 1
            readings = unit.findall("reading")
            primary_index = next(
                (i for i, reading in enumerate(readings) if reading.get("option", "") == "0"),
                0,
            )
            records.append(
                {
                    "source_file": path.name,
                    "ocp_book": ocp_book,
                    "version_title": version_title,
                    "language": language,
                    "version_kind": version_kind,
                    "unit_index": unit_index,
                    "source_ref": base._reference(source_path, specs),
                    "unit_id": unit.get("id", ""),
                    "readings": [
                        _reading_signature(reading, index, primary_index)
                        for index, reading in enumerate(readings)
                    ],
                }
            )

        if legacy:
            for chapter in text.findall("chapter"):
                chapter_path = (chapter.get("number", ""),)
                for verse in chapter.findall("verse"):
                    verse_path = (*chapter_path, verse.get("reference", ""))
                    for unit in verse.findall("unit"):
                        add_unit(unit, verse_path)
            return

        def walk_div(div: ET.Element, parent_path: tuple[str, ...]) -> None:
            source_path = (*parent_path, div.get("number", ""))
            for child in list(div):
                if child.tag == "div":
                    walk_div(child, source_path)
                elif child.tag == "unit":
                    add_unit(child, source_path)

        for div in text.findall("div"):
            walk_div(div, ())

    for path in sorted(source_dir.glob("*.xml")):
        data = path.read_bytes()
        if path.name.startswith(".") or not data.strip():
            continue
        root = ET.fromstring(data)
        ocp_book = root.get("filename", "")
        versions = root.findall("version")
        if versions:
            for version in versions:
                generated = base._audit_is_generated_translation_version(version)
                version_title = version.get("title", "")
                language = version.get("language", "")
                legacy = is_wrapped_legacy_version(version)
                if legacy:
                    specs = (DivisionSpec("Chapter", ":"), DivisionSpec("Verse", ""))
                else:
                    divisions = version.find("divisions")
                    specs = tuple(
                        DivisionSpec(
                            division.get("label", ""),
                            division.get("delimiter", division.get("Delimiter", "")),
                            base._plain_text(division),
                        )
                        for division in (
                            divisions.findall("division") if divisions is not None else []
                        )
                    )
                add_textual_version(
                    path=path,
                    ocp_book=ocp_book,
                    version=version,
                    version_title=version_title,
                    language=language,
                    version_kind="generated_translation" if generated else "source",
                    specs=specs,
                    legacy=legacy,
                )
        else:
            specs = (DivisionSpec("Chapter", ":"), DivisionSpec("Verse", ""))
            add_textual_version(
                path=path,
                ocp_book=ocp_book,
                version=root,
                version_title=root.get("language", "") or "Default",
                language=root.get("language", ""),
                version_kind="source",
                specs=specs,
                legacy=True,
            )

    return records


def _graph_reading_signature(data: TFData, reading: int) -> dict[str, object]:
    return {
        "reading_index": base._feature(data, "reading_index", reading, 0),
        "option": base._feature(data, "reading_option_source", reading),
        "mss": base._feature(data, "mss", reading),
        "linebreak": base._feature(data, "linebreak", reading),
        "indent": base._feature(data, "indent", reading),
        "text": base._feature(data, "reading_text", reading),
        "xml": base._feature(data, "reading_xml", reading),
        "primary": base._feature(data, "is_primary", reading, 0) == 1,
    }


def _graph_unit_occurrences(
    data: TFData,
    node_index: dict[str, list[int]],
) -> list[dict[str, object]] | None:
    """Project unit occurrences using actual reading_of ownership edges."""

    version_ids = data.node_features.get("version_id", {})
    books_by_version: dict[str, dict[str, str]] = {}
    for book in node_index.get("book", []):
        version_id = str(version_ids.get(book, ""))
        if not version_id or version_id in books_by_version:
            return None
        books_by_version[version_id] = {
            "source_file": str(base._feature(data, "source_file", book)),
            "ocp_book": str(base._feature(data, "ocp_book", book)),
            "version_title": str(base._feature(data, "version_title", book)),
            "language": str(base._feature(data, "language", book)),
            "version_kind": str(base._feature(data, "version_kind", book, "source")),
        }

    units = set(node_index.get("unit", []))
    readings_by_unit: dict[int, list[int]] = {unit: [] for unit in units}
    reading_of = data.edge_features.get("reading_of", {})
    for reading in node_index.get("reading", []):
        targets = reading_of.get(reading, set())
        if len(targets) != 1:
            return None
        unit = next(iter(targets))
        if unit not in units:
            return None
        readings_by_unit[unit].append(reading)

    records: list[dict[str, object]] = []
    for unit in units:
        version_id = str(version_ids.get(unit, ""))
        metadata = books_by_version.get(version_id)
        if metadata is None:
            return None
        try:
            unit_index = int(base._feature(data, "unit_index", unit, 0))
        except (TypeError, ValueError):
            return None
        readings = sorted(
            readings_by_unit[unit],
            key=lambda reading: (
                int(base._feature(data, "reading_index", reading, 0)),
                reading,
            ),
        )
        records.append(
            {
                **metadata,
                "unit_index": unit_index,
                "source_ref": str(base._feature(data, "source_ref", unit)),
                "unit_id": str(base._feature(data, "unit_id", unit)),
                "readings": [_graph_reading_signature(data, reading) for reading in readings],
            }
        )
    return records


def reading_occurrence_ownership_ok(
    source_dir: str | Path,
    data: TFData,
    node_index: dict[str, list[int]],
) -> bool:
    """Verify source-order unit→reading ownership independently from the parser model."""

    raw = _raw_unit_occurrences(Path(source_dir))
    graph = _graph_unit_occurrences(data, node_index)
    if graph is None:
        return False
    return base._canonical(raw) == base._canonical(graph)
