#!/usr/bin/env python3
"""Inventory OCP generated translations and structural source-version alignment."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from pseudepigrapha_tf.source_versions import (
    GeneratedTranslationClassificationError,
    is_generated_translation_version,
)

UnitSignature = tuple[tuple[tuple[str, ...], str], ...]


def _units(version: ET.Element) -> list[dict[str, object]]:
    text = version.find("text")
    if text is None:
        return []
    result: list[dict[str, object]] = []

    def walk(node: ET.Element, path: tuple[str, ...]) -> None:
        for child in node:
            tag = child.tag.lower()
            if tag in {"div", "chapter", "verse"}:
                number = (
                    child.get("number")
                    or child.get("reference")
                    or child.get("n")
                    or str(len(path) + 1)
                )
                walk(child, (*path, number))
            elif tag == "unit":
                result.append({"path": path, "id": child.get("id", "")})

    walk(text, ())
    return result


def _source_signature(version: ET.Element) -> UnitSignature:
    return tuple((tuple(unit["path"]), str(unit["id"])) for unit in _units(version))


def _translation_signature(version: ET.Element) -> UnitSignature:
    language = (version.get("language") or "").lower()
    prefix = "en_" if language == "english" else "fr_" if language == "french" else ""
    result: list[tuple[tuple[str, ...], str]] = []
    for unit in _units(version):
        unit_id = str(unit["id"])
        source_id = unit_id[len(prefix) :] if prefix and unit_id.startswith(prefix) else unit_id
        result.append((tuple(unit["path"]), source_id))
    return tuple(result)


def _version_record(index: int, version: ET.Element) -> dict[str, object]:
    readings = list(version.iter("reading"))
    return {
        "index": index,
        "title": version.get("title", ""),
        "language": version.get("language", ""),
        "fragment": version.get("fragment", ""),
        "units": len(_units(version)),
        "readings": len(readings),
        "empty_readings": sum(1 for reading in readings if not "".join(reading.itertext()).strip()),
    }


def _signature_drift(generated: UnitSignature, source: UnitSignature) -> dict[str, object]:
    generated_counts = Counter(generated)
    source_counts = Counter(source)
    common = sum((generated_counts & source_counts).values())
    missing = list((source_counts - generated_counts).elements())
    extra = list((generated_counts - source_counts).elements())
    first_mismatch = None
    for position, (generated_item, source_item) in enumerate(zip(generated, source, strict=False)):
        if generated_item != source_item:
            first_mismatch = {
                "position": position,
                "generated": generated_item,
                "source": source_item,
            }
            break
    if first_mismatch is None and len(generated) != len(source):
        first_mismatch = {
            "position": min(len(generated), len(source)),
            "generated": generated[min(len(generated), len(source))] if len(generated) > len(source) else None,
            "source": source[min(len(generated), len(source))] if len(source) > len(generated) else None,
        }
    return {
        "generated_units": len(generated),
        "source_units": len(source),
        "common_identities": common,
        "missing_from_generated_count": len(missing),
        "extra_in_generated_count": len(extra),
        "missing_from_generated_sample": missing[:5],
        "extra_in_generated_sample": extra[:5],
        "first_mismatch": first_mismatch,
    }


def inventory(source_dir: Path) -> dict[str, object]:
    files: list[dict[str, object]] = []
    language_counts: Counter[str] = Counter()
    language_unit_counts: Counter[str] = Counter()
    genuine_modern_versions: list[dict[str, object]] = []
    ambiguous: list[dict[str, object]] = []
    unmatched: list[dict[str, object]] = []
    generated_total = 0
    generated_units = 0
    generated_empty_readings = 0
    generated_documents: set[str] = set()
    source_versions_total = 0

    xml_paths = sorted(
        path for path in source_dir.glob("*.xml") if not path.name.startswith(".") and path.read_bytes().strip()
    )
    for xml_path in xml_paths:
        root = ET.fromstring(xml_path.read_bytes())
        versions = list(root.findall("version"))
        generated: list[tuple[int, ET.Element]] = []
        sources: list[tuple[int, ET.Element]] = []
        for index, version in enumerate(versions):
            try:
                is_generated = is_generated_translation_version(version)
            except GeneratedTranslationClassificationError as exc:
                raise RuntimeError(f"{xml_path.name}: {exc}") from exc
            if is_generated:
                generated.append((index, version))
            else:
                sources.append((index, version))
                if (version.get("language") or "").lower() in {"english", "french"}:
                    genuine_modern_versions.append(
                        {"file": xml_path.name, **_version_record(index, version)}
                    )

        source_versions_total += len(sources)
        source_signatures: dict[UnitSignature, list[tuple[int, ET.Element]]] = {}
        for pair in sources:
            source_signatures.setdefault(_source_signature(pair[1]), []).append(pair)

        generated_records: list[dict[str, object]] = []
        for index, version in generated:
            target = version.get("language", "")
            signature = _translation_signature(version)
            candidates = source_signatures.get(signature, [])
            record: dict[str, object] = {
                "file": xml_path.name,
                **_version_record(index, version),
                "candidate_sources": [
                    {
                        "index": source_index,
                        "title": source.get("title", ""),
                        "language": source.get("language", ""),
                        "fragment": source.get("fragment", ""),
                    }
                    for source_index, source in candidates
                ],
            }
            if len(candidates) == 0:
                nearest = []
                for source_index, source in sources:
                    drift = _signature_drift(signature, _source_signature(source))
                    nearest.append(
                        {
                            "index": source_index,
                            "title": source.get("title", ""),
                            "language": source.get("language", ""),
                            "fragment": source.get("fragment", ""),
                            **drift,
                        }
                    )
                nearest.sort(
                    key=lambda item: (
                        -int(item["common_identities"]),
                        int(item["missing_from_generated_count"]) + int(item["extra_in_generated_count"]),
                        int(item["index"]),
                    )
                )
                record["nearest_sources"] = nearest[:3]
                unmatched.append(record)
            elif len(candidates) > 1:
                ambiguous.append(record)
            generated_records.append(record)
            generated_total += 1
            generated_documents.add(xml_path.name)
            language_counts[target] += 1
            units = len(signature)
            language_unit_counts[target] += units
            generated_units += units
            readings = list(version.iter("reading"))
            generated_empty_readings += sum(
                1 for reading in readings if not "".join(reading.itertext()).strip()
            )

        files.append(
            {
                "file": xml_path.name,
                "source_versions": [_version_record(index, version) for index, version in sources],
                "generated_versions": generated_records,
            }
        )

    return {
        "nonempty_xml_documents": len(xml_paths),
        "source_versions": source_versions_total,
        "generated_documents": len(generated_documents),
        "generated_versions": generated_total,
        "generated_units": generated_units,
        "generated_empty_readings": generated_empty_readings,
        "generated_versions_by_language": dict(sorted(language_counts.items())),
        "generated_units_by_language": dict(sorted(language_unit_counts.items())),
        "genuine_non_generated_english_french_versions": genuine_modern_versions,
        "unmatched_generated_versions": unmatched,
        "ambiguous_generated_versions": ambiguous,
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: inspect_generated_translations.py PATH/TO/static/docs")
    print(json.dumps(inventory(Path(args[0])), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
