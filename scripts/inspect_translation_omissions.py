#!/usr/bin/env python3
"""Check omission markers and generator bare-unit-id collisions on an exact OCP snapshot."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

from pseudepigrapha_tf.source_versions import is_generated_translation_version

Identity = tuple[tuple[str, ...], str]


def units(version: ET.Element, *, generated: bool = False) -> list[tuple[Identity, str, str]]:
    text = version.find("text")
    if text is None:
        return []
    language = (version.get("language") or "").lower()
    prefix = "en_" if generated and language == "english" else "fr_" if generated and language == "french" else ""
    result: list[tuple[Identity, str, str]] = []

    def walk(node: ET.Element, path: tuple[str, ...]) -> None:
        for child in node:
            tag = child.tag.lower()
            if tag in {"div", "chapter", "verse"}:
                number = child.get("number") or child.get("reference") or child.get("n") or str(len(path) + 1)
                walk(child, (*path, number))
            elif tag == "unit":
                unit_id = child.get("id", "")
                source_id = unit_id[len(prefix):] if prefix and unit_id.startswith(prefix) else unit_id
                reading = child.find("reading[@option='0']")
                if reading is None:
                    reading = child.find("reading")
                value = "".join(reading.itertext()) if reading is not None else ""
                result.append(((path, source_id), source_id, value))

    walk(text, ())
    return result


def version_key(rows: list[tuple[Identity, str, str]]) -> frozenset[tuple[Identity, int]]:
    return frozenset(Counter(identity for identity, _, _ in rows).items())


def marker(language: str, value: str) -> bool:
    stripped = value.strip()
    if language == "English":
        return stripped == "[...]"
    if language == "French":
        return stripped == ""
    raise ValueError(language)


def inventory(source_dir: Path) -> dict[str, object]:
    by_language = {
        "English": Counter(),
        "French": Counter(),
    }
    mismatches: list[dict[str, object]] = []
    ambiguous_omission_groups: list[dict[str, object]] = []
    collision_versions: list[dict[str, object]] = []

    for xml_path in sorted(source_dir.glob("*.xml")):
        if xml_path.name.startswith(".") or not xml_path.read_bytes().strip():
            continue
        root = ET.fromstring(xml_path.read_bytes())
        versions = list(root.findall("version"))
        source_versions = [(i, version, units(version)) for i, version in enumerate(versions) if not is_generated_translation_version(version)]
        source_by_key: dict[frozenset[tuple[Identity, int]], list[tuple[int, ET.Element, list[tuple[Identity, str, str]]]]] = defaultdict(list)
        for source in source_versions:
            source_by_key[version_key(source[2])].append(source)

        for generated_index, generated in enumerate(versions):
            if not is_generated_translation_version(generated):
                continue
            language = generated.get("language", "")
            generated_rows = units(generated, generated=True)
            candidates = source_by_key.get(version_key(generated_rows), [])
            if len(candidates) != 1:
                raise RuntimeError(
                    f"{xml_path.name} generated index {generated_index}: expected one source candidate, got {len(candidates)}"
                )
            source_index, source, source_rows = candidates[0]

            source_groups: dict[Identity, list[str]] = defaultdict(list)
            generated_groups: dict[Identity, list[str]] = defaultdict(list)
            for identity, _, value in source_rows:
                source_groups[identity].append(value)
            for identity, _, value in generated_rows:
                generated_groups[identity].append(value)

            counts = by_language[language]
            counts["versions"] += 1
            counts["units"] += len(generated_rows)
            counts["source_empty_units"] += sum(1 for _, _, value in source_rows if not value.strip())
            counts["observed_omission_markers"] += sum(1 for _, _, value in generated_rows if marker(language, value))

            for identity in sorted(source_groups, key=repr):
                source_states = sorted(not value.strip() for value in source_groups[identity])
                generated_states = sorted(marker(language, value) for value in generated_groups[identity])
                if source_states != generated_states:
                    record = {
                        "file": xml_path.name,
                        "generated_index": generated_index,
                        "generated_title": generated.get("title", ""),
                        "language": language,
                        "source_index": source_index,
                        "source_title": source.get("title", ""),
                        "identity": identity,
                        "source_empty_states": source_states,
                        "generated_marker_states": generated_states,
                        "source_texts": source_groups[identity],
                        "generated_texts": generated_groups[identity],
                    }
                    mismatches.append(record)
                    if len(source_states) > 1 or len(generated_states) > 1:
                        ambiguous_omission_groups.append(record)

            bare_groups: dict[str, list[tuple[Identity, str]]] = defaultdict(list)
            for identity, bare_id, value in generated_rows:
                bare_groups[bare_id].append((identity, value))
            collisions = {bare_id: rows for bare_id, rows in bare_groups.items() if len(rows) > 1}
            if collisions:
                counts["collision_versions"] += 1
                counts["collision_groups"] += len(collisions)
                counts["collision_unit_occurrences"] += sum(len(rows) for rows in collisions.values())
                collision_versions.append(
                    {
                        "file": xml_path.name,
                        "generated_index": generated_index,
                        "language": language,
                        "source_index": source_index,
                        "source_title": source.get("title", ""),
                        "groups": [
                            {
                                "source_unit_id": bare_id,
                                "occurrences": len(rows),
                                "identities": [identity for identity, _ in rows],
                                "all_generated_text_equal": len({value for _, value in rows}) == 1,
                                "marker_occurrences": sum(1 for _, value in rows if marker(language, value)),
                            }
                            for bare_id, rows in sorted(collisions.items())
                        ],
                    }
                )

    return {
        "by_language": {language: dict(sorted(counts.items())) for language, counts in by_language.items()},
        "omission_mismatches": mismatches,
        "ambiguous_omission_groups": ambiguous_omission_groups,
        "collision_versions": collision_versions,
        "collision_version_count": len(collision_versions),
        "collision_group_count": sum(len(record["groups"]) for record in collision_versions),
        "collision_unit_occurrence_count": sum(
            sum(group["occurrences"] for group in record["groups"]) for record in collision_versions
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: inspect_translation_omissions.py PATH/TO/static/docs")
    print(json.dumps(inventory(Path(args[0])), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
