from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from .graph import TFData
from .model import Book, DivisionSpec
from .parser import InvalidSourceError
from .source_structure import SourceStructureError, validate_source_structure


def _plain_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", "".join(element.itertext()).replace("\u200b", "")).strip()


def _inner_xml(element: ET.Element) -> str:
    chunks = [escape(element.text or "")]
    chunks.extend(ET.tostring(child, encoding="unicode") for child in list(element))
    return "".join(chunks).strip()


def _reference(path: tuple[str, ...], specs: tuple[DivisionSpec, ...]) -> str:
    parts: list[str] = []
    for index, value in enumerate(path):
        parts.append(value)
        if index < len(path) - 1:
            delimiter = specs[index].delimiter if index < len(specs) else "/"
            parts.append(delimiter)
    return "".join(parts)


def _canonical(records: list[dict]) -> list[str]:
    return sorted(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)


def _raw_inventory(source_dir: Path) -> dict:
    inventory = {
        "files": [], "versions": [], "division_specs": [], "divs": [], "units": [],
        "readings": [], "manuscripts": [], "resources": [], "annotated_words": [],
    }

    def add_manuscripts(container: ET.Element, ocp_book: str, version_title: str) -> None:
        manuscripts = container.find("manuscripts")
        if manuscripts is None:
            return
        for ms in manuscripts.findall("ms"):
            name = ms.find("name")
            bibliography = ms.findall("bibliography")
            inventory["manuscripts"].append({
                "ocp_book": ocp_book, "version_title": version_title,
                "abbrev": ms.get("abbrev", ""), "language": ms.get("language", ""),
                "show": ms.get("show", ""), "name": _plain_text(name),
                "name_xml": _inner_xml(name) if name is not None else "",
                "bibliography": [_plain_text(b) for b in bibliography],
                "bibliography_xml": [_inner_xml(b) for b in bibliography],
            })

    def add_resources(container: ET.Element, ocp_book: str, version_title: str) -> None:
        for resources in container.findall("resources"):
            for resource in resources.findall("resource"):
                inventory["resources"].append({
                    "ocp_book": ocp_book, "version_title": version_title,
                    "name": resource.get("name", ""),
                    "info": [_plain_text(i) for i in resource.findall("info")],
                    "url": _plain_text(resource.find("URL")),
                })

    def add_unit(unit: ET.Element, ocp_book: str, version_title: str,
                 path: tuple[str, ...], specs: tuple[DivisionSpec, ...]) -> None:
        source_ref = _reference(path, specs)
        inventory["units"].append({
            "ocp_book": ocp_book, "version_title": version_title, "source_ref": source_ref,
            "unit_id": unit.get("id", ""), "group": unit.get("group", "0"),
            "parallel": unit.get("parallel", ""), "linebreak": unit.get("linebreak", ""),
        })
        readings = unit.findall("reading")
        primary_index = next((i for i, r in enumerate(readings) if r.get("option", "") == "0"), 0)
        for reading_index, reading in enumerate(readings):
            mss = reading.get("mss", "")
            inventory["readings"].append({
                "ocp_book": ocp_book, "version_title": version_title, "source_ref": source_ref,
                "unit_id": unit.get("id", ""), "option": reading.get("option", ""),
                "mss": mss.strip(), "witnesses": sorted(part for part in mss.split() if part),
                "linebreak": reading.get("linebreak", ""), "indent": reading.get("indent", ""),
                "text": _plain_text(reading), "xml": _inner_xml(reading),
                "primary": reading_index == primary_index,
            })
            for word in reading.findall("w"):
                inventory["annotated_words"].append({
                    "ocp_book": ocp_book, "version_title": version_title, "source_ref": source_ref,
                    "unit_id": unit.get("id", ""), "option": reading.get("option", ""),
                    "text": word.text or "", "morph": word.get("morph", ""),
                    "lex": word.get("lex", ""), "style": word.get("style", ""),
                    "lang": word.get("lang", ""),
                })

    def walk_div(div: ET.Element, ocp_book: str, version_title: str,
                 specs: tuple[DivisionSpec, ...], path: tuple[str, ...]) -> None:
        dpath = path + (div.get("number", ""),)
        level = len(dpath)
        inventory["divs"].append({
            "ocp_book": ocp_book, "version_title": version_title,
            "source_ref": _reference(dpath, specs), "number": div.get("number", ""),
            "fragment": div.get("fragment", ""), "level": level,
            "label": specs[level - 1].label if level <= len(specs) else "",
        })
        for child in list(div):
            if child.tag == "div":
                walk_div(child, ocp_book, version_title, specs, dpath)
            elif child.tag == "unit":
                add_unit(child, ocp_book, version_title, dpath, specs)

    for path in sorted(source_dir.glob("*.xml")):
        data = path.read_bytes()
        if path.name.startswith(".") or not data.strip():
            continue
        source_sha256 = hashlib.sha256(data).hexdigest()
        root = ET.fromstring(data)
        versions = root.findall("version")
        is_legacy = not versions and root.find("text/chapter") is not None
        try:
            validate_source_structure(
                root,
                legacy=is_legacy,
                source_path=path.name,
                source_sha256=source_sha256,
            )
        except SourceStructureError as exc:
            raise InvalidSourceError(str(exc)) from exc
        ocp_book = root.get("filename", "")
        inventory["files"].append({"file": path.name, "sha256": source_sha256})
        if versions:
            for version in versions:
                version_title = version.get("title", "")
                inventory["versions"].append({
                    "ocp_book": ocp_book,
                    "title": root.get("title", ""),
                    "text_structure": root.get("textStructure", ""),
                    "version_title": version_title,
                    "author": version.get("author", ""),
                    "language": version.get("language", ""),
                    "fragment": version.get("fragment", ""),
                    "source_file": path.name,
                    "source_sha256": source_sha256,
                })
                divisions = version.find("divisions")
                specs = tuple(
                    DivisionSpec(
                        d.get("label", ""),
                        d.get("delimiter", d.get("Delimiter", "")),
                        _plain_text(d),
                    )
                    for d in (divisions.findall("division") if divisions is not None else [])
                )
                for index, spec in enumerate(specs, 1):
                    inventory["division_specs"].append({
                        "ocp_book": ocp_book, "version_title": version_title, "index": index,
                        "label": spec.label, "delimiter": spec.delimiter, "text": spec.text,
                    })
                add_manuscripts(version, ocp_book, version_title)
                add_resources(version, ocp_book, version_title)
                text = version.find("text")
                if text is not None:
                    for div in text.findall("div"):
                        walk_div(div, ocp_book, version_title, specs, ())
        else:
            version_title = root.get("language", "") or "Default"
            inventory["versions"].append({
                "ocp_book": ocp_book,
                "title": root.get("title", ""),
                "text_structure": root.get("textStructure", ""),
                "version_title": version_title,
                "author": "",
                "language": root.get("language", ""),
                "fragment": "",
                "source_file": path.name,
                "source_sha256": source_sha256,
            })
            specs = (DivisionSpec("Chapter", ":"), DivisionSpec("Verse", ""))
            for index, spec in enumerate(specs, 1):
                inventory["division_specs"].append({
                    "ocp_book": ocp_book, "version_title": version_title, "index": index,
                    "label": spec.label, "delimiter": spec.delimiter, "text": spec.text,
                })
            add_manuscripts(root, ocp_book, version_title)
            add_resources(root, ocp_book, version_title)
            text = root.find("text")
            if text is not None:
                for chapter in text.findall("chapter"):
                    chapter_path = (chapter.get("number", ""),)
                    inventory["divs"].append({
                        "ocp_book": ocp_book, "version_title": version_title,
                        "source_ref": _reference(chapter_path, specs),
                        "number": chapter.get("number", ""), "fragment": chapter.get("fragment", ""),
                        "level": 1, "label": "Chapter",
                    })
                    for verse in chapter.findall("verse"):
                        verse_path = chapter_path + (verse.get("reference", ""),)
                        inventory["divs"].append({
                            "ocp_book": ocp_book, "version_title": version_title,
                            "source_ref": _reference(verse_path, specs),
                            "number": verse.get("reference", ""), "fragment": verse.get("fragment", ""),
                            "level": 2, "label": "Verse",
                        })
                        for unit in verse.findall("unit"):
                            add_unit(unit, ocp_book, version_title, verse_path, specs)
    return inventory


def _nodes(data: TFData, kind: str) -> list[int]:
    return sorted(n for n, value in data.node_features["otype"].items() if value == kind)


def _feature(data: TFData, name: str, node: int, default=""):
    return data.node_features.get(name, {}).get(node, default)


def _graph_inventory(data: TFData) -> dict:
    inventory = {
        "versions": [], "division_specs": [], "divs": [], "units": [], "readings": [],
        "manuscripts": [], "resources": [], "annotated_words": [],
    }
    for node in _nodes(data, "book"):
        ocp_book = _feature(data, "ocp_book", node)
        version_title = _feature(data, "version_title", node)
        inventory["versions"].append({
            "ocp_book": ocp_book,
            "title": _feature(data, "title", node),
            "text_structure": _feature(data, "text_structure", node),
            "version_title": version_title,
            "author": _feature(data, "author", node),
            "language": _feature(data, "language", node),
            "fragment": _feature(data, "version_fragment", node),
            "source_file": _feature(data, "source_file", node),
            "source_sha256": _feature(data, "source_sha256", node),
        })
        labels = json.loads(_feature(data, "division_labels", node, "[]"))
        delimiters = json.loads(_feature(data, "division_delimiters", node, "[]"))
        texts = json.loads(_feature(data, "division_texts", node, "[]"))
        for index, label in enumerate(labels, 1):
            inventory["division_specs"].append({
                "ocp_book": ocp_book, "version_title": version_title, "index": index,
                "label": label, "delimiter": delimiters[index - 1] if index <= len(delimiters) else "",
                "text": texts[index - 1] if index <= len(texts) else "",
            })
    for node in _nodes(data, "div"):
        inventory["divs"].append({
            "ocp_book": _feature(data, "ocp_book", node),
            "version_title": _feature(data, "version_title", node),
            "source_ref": _feature(data, "source_ref", node),
            "number": _feature(data, "div_number", node),
            "fragment": _feature(data, "div_fragment", node),
            "level": _feature(data, "div_level", node, 0),
            "label": _feature(data, "div_label", node),
        })
    for node in _nodes(data, "unit"):
        inventory["units"].append({
            "ocp_book": _feature(data, "ocp_book", node),
            "version_title": _feature(data, "version_title", node),
            "source_ref": _feature(data, "source_ref", node),
            "unit_id": _feature(data, "unit_id", node), "group": _feature(data, "group", node, "0"),
            "parallel": _feature(data, "parallel", node), "linebreak": _feature(data, "unit_linebreak", node),
        })
    witness_edges = data.edge_features.get("witness", {})
    for node in _nodes(data, "reading"):
        witnesses = sorted(_feature(data, "ms_abbrev", target) for target in witness_edges.get(node, set()))
        inventory["readings"].append({
            "ocp_book": _feature(data, "ocp_book", node),
            "version_title": _feature(data, "version_title", node),
            "source_ref": _feature(data, "source_ref", node), "unit_id": _feature(data, "unit_id", node),
            "option": _feature(data, "reading_option_source", node), "mss": _feature(data, "mss", node),
            "witnesses": witnesses, "linebreak": _feature(data, "linebreak", node),
            "indent": _feature(data, "indent", node), "text": _feature(data, "reading_text", node),
            "xml": _feature(data, "reading_xml", node), "primary": _feature(data, "is_primary", node, 0) == 1,
        })
    for node in _nodes(data, "manuscript"):
        if _feature(data, "undefined_manuscript", node, 0) == 1:
            continue
        inventory["manuscripts"].append({
            "ocp_book": _feature(data, "ocp_book", node), "version_title": _feature(data, "version_title", node),
            "abbrev": _feature(data, "ms_abbrev", node), "language": _feature(data, "ms_language", node),
            "show": _feature(data, "ms_show", node), "name": _feature(data, "ms_name", node),
            "name_xml": _feature(data, "ms_name_xml", node),
            "bibliography": json.loads(_feature(data, "bibliography", node, "[]")),
            "bibliography_xml": json.loads(_feature(data, "bibliography_xml", node, "[]")),
        })
    for node in _nodes(data, "resource"):
        inventory["resources"].append({
            "ocp_book": _feature(data, "ocp_book", node), "version_title": _feature(data, "version_title", node),
            "name": _feature(data, "resource_name", node),
            "info": json.loads(_feature(data, "resource_info", node, "[]")),
            "url": _feature(data, "resource_url", node),
        })
    for node in sorted(data.node_features.get("w_annotated", {})):
        inventory["annotated_words"].append({
            "ocp_book": _feature(data, "ocp_book", node), "version_title": _feature(data, "version_title", node),
            "source_ref": _feature(data, "source_ref", node), "unit_id": _feature(data, "unit_id", node),
            "option": _feature(data, "reading_option_source", node), "text": _feature(data, "g_word_utf8", node),
            "morph": _feature(data, "morph", node), "lex": _feature(data, "lex", node),
            "style": _feature(data, "style", node), "lang": _feature(data, "w_lang", node),
        })
    return inventory


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u200b", "")).strip()


def _reconstruction_checks(data: TFData) -> tuple[bool, bool]:
    reading_to_variants: dict[int, list[int]] = {}
    for variant, targets in data.edge_features.get("variant_word_of", {}).items():
        for reading in targets:
            reading_to_variants.setdefault(reading, []).append(variant)
    primary_ok = alternative_ok = True
    for reading in _nodes(data, "reading"):
        expected = _normalize(str(_feature(data, "reading_text", reading)))
        if _feature(data, "is_primary", reading, 0) == 1:
            slots = sorted(data.edge_features["oslots"].get(reading, set()))
            actual = "".join(
                f"{_feature(data, 'prefix_utf8', slot)}{_feature(data, 'g_word_utf8', slot)}{_feature(data, 'trailer_utf8', slot)}"
                for slot in slots if _feature(data, "is_gap", slot, 0) != 1
            )
            primary_ok = primary_ok and _normalize(actual) == expected
        else:
            variants = sorted(reading_to_variants.get(reading, []), key=lambda n: int(_feature(data, "variant_position", n, 0)))
            actual = "".join(
                f"{_feature(data, 'prefix_utf8', node)}{_feature(data, 'g_word_utf8', node)}{_feature(data, 'trailer_utf8', node)}"
                for node in variants
            )
            alternative_ok = alternative_ok and _normalize(actual) == expected
    return primary_ok, alternative_ok


def _parent_linkage_ok(data: TFData) -> bool:
    parent = data.edge_features.get("parent", {})
    div_nodes = set(_nodes(data, "div"))
    for unit in _nodes(data, "unit"):
        targets = parent.get(unit, set())
        if len(targets) != 1:
            return False
        target = next(iter(targets))
        if target not in div_nodes or _feature(data, "source_ref", target) != _feature(data, "source_ref", unit):
            return False
    return True


def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:
    """Return the canonical semantic parity report through the legacy entry point.

    The import is intentionally lazy because :mod:`semantic_audit` imports this
    module for low-level inventory helpers.
    """

    from .semantic_audit import build_conversion_report as semantic_report

    return semantic_report(source_dir, books, data)


def write_conversion_report(report: dict, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
