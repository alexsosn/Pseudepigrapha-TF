from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"expected patch anchor missing: {label}")
    return text.replace(old, new, 1)


def patch_audit() -> None:
    path = Path("src/pseudepigrapha_tf/audit.py")
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "import re\nfrom pathlib import Path\n",
        "import re\nfrom collections import Counter\nfrom pathlib import Path\n",
        label="audit Counter import",
    )

    marker = '''def _canonical(records: list[dict]) -> list[str]:
    return sorted(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)
'''
    helper = marker + '''

def _raw_translation_unit_identities(
    version: ET.Element,
    *,
    generated: bool,
) -> tuple[tuple[tuple[str, ...], str], ...]:
    """Reconstruct source identities directly from XML for audit-only mapping."""

    text = version.find("text")
    if text is None:
        return ()
    prefix = ""
    if generated:
        language = (version.get("language") or "").strip().lower()
        prefix = f"{language[:2]}_" if language else ""

    identities: list[tuple[tuple[str, ...], str]] = []

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
                unit_id = child.get("id", "")
                if generated and prefix and unit_id.startswith(prefix):
                    unit_id = unit_id[len(prefix) :]
                identities.append((path, unit_id))

    walk(text, ())
    return tuple(identities)
'''
    text = replace_once(text, marker, helper, label="raw identity helper")

    text = replace_once(
        text,
        '        "ellipses": [], "orphan_readings": [], "excluded_generated_translation_versions": [],\n    }\n',
        '        "ellipses": [], "orphan_readings": [], "excluded_generated_translation_versions": [],\n'
        '        "generated_translations": [], "generated_translation_mapping_failures": [],\n'
        '    }\n',
        label="raw inventory generated buckets",
    )

    old_loop = '''        if versions:
            for version in versions:
                try:
                    generated = is_generated_translation_version(version)
                except GeneratedTranslationClassificationError as exc:
                    raise InvalidSourceError(f"{path.name}: {exc}") from exc
                if generated:
                    inventory["excluded_generated_translation_versions"].append({
                        "ocp_book": ocp_book,
                        "version_title": version.get("title", ""),
                        "language": version.get("language", ""),
                        "source_file": path.name,
                        "marker": GENERATED_TRANSLATION_MARKER,
                    })
                    continue

                version_title = version.get("title", "")
'''
    new_loop = '''        if versions:
            classified: list[tuple[ET.Element, bool]] = []
            source_versions: list[ET.Element] = []
            for version in versions:
                try:
                    generated = is_generated_translation_version(version)
                except GeneratedTranslationClassificationError as exc:
                    raise InvalidSourceError(f"{path.name}: {exc}") from exc
                classified.append((version, generated))
                if not generated:
                    source_versions.append(version)

            source_signatures = [
                Counter(_raw_translation_unit_identities(version, generated=False))
                for version in source_versions
            ]
            for version, generated in classified:
                if generated:
                    generated_identities = _raw_translation_unit_identities(version, generated=True)
                    generated_signature = Counter(generated_identities)
                    candidates = [
                        candidate
                        for candidate, source_signature in zip(source_versions, source_signatures)
                        if source_signature == generated_signature
                    ]
                    if len(candidates) == 1:
                        source_version = candidates[0]
                        inventory["generated_translations"].append({
                            "ocp_book": ocp_book,
                            "version_title": version.get("title", ""),
                            "language": version.get("language", ""),
                            "source_file": path.name,
                            "marker": GENERATED_TRANSLATION_MARKER,
                            "source_version_title": source_version.get("title", ""),
                            "source_version_language": source_version.get("language", ""),
                            "unit_count": len(generated_identities),
                            "aligned_unit_count": len(generated_identities),
                        })
                    else:
                        inventory["generated_translation_mapping_failures"].append({
                            "ocp_book": ocp_book,
                            "version_title": version.get("title", ""),
                            "language": version.get("language", ""),
                            "source_file": path.name,
                            "candidate_count": len(candidates),
                        })

                version_title = version.get("title", "")
'''
    text = replace_once(text, old_loop, new_loop, label="generated classification loop")

    text = replace_once(
        text,
        '                    "source_file": path.name,\n                    "source_sha256": source_sha256,\n                })\n',
        '                    "source_file": path.name,\n'
        '                    "source_sha256": source_sha256,\n'
        '                    "version_kind": "generated_translation" if generated else "source",\n'
        '                })\n',
        label="modern raw version kind",
    )
    text = replace_once(
        text,
        '                "source_file": path.name,\n                "source_sha256": source_sha256,\n            })\n            specs = (DivisionSpec("Chapter", ":"), DivisionSpec("Verse", ""))\n',
        '                "source_file": path.name,\n'
        '                "source_sha256": source_sha256,\n'
        '                "version_kind": "source",\n'
        '            })\n'
        '            specs = (DivisionSpec("Chapter", ":"), DivisionSpec("Verse", ""))\n',
        label="legacy raw version kind",
    )
    text = replace_once(
        text,
        '            "source_file": _feature(data, "source_file", node),\n            "source_sha256": _feature(data, "source_sha256", node),\n        })\n',
        '            "source_file": _feature(data, "source_file", node),\n'
        '            "source_sha256": _feature(data, "source_sha256", node),\n'
        '            "version_kind": _feature(data, "version_kind", node, "source"),\n'
        '        })\n',
        label="graph version kind",
    )

    path.write_text(text, encoding="utf-8")


def patch_semantic_audit() -> None:
    path = Path("src/pseudepigrapha_tf/semantic_audit.py")
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '                "source_file": base._feature(data, "source_file", node),\n'
        '                "source_sha256": base._feature(data, "source_sha256", node),\n'
        '            }\n',
        '                "source_file": base._feature(data, "source_file", node),\n'
        '                "source_sha256": base._feature(data, "source_sha256", node),\n'
        '                "version_kind": base._feature(data, "version_kind", node, "source"),\n'
        '            }\n',
        label="metadata version kind",
    )

    marker = '''def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:
'''
    helper = '''def _graph_generated_translation_inventory(
    data: TFData,
    node_index: dict[str, list[int]],
) -> list[dict]:
    """Project graph alignment independently for comparison with raw XML evidence."""

    version_kind = data.node_features.get("version_kind", {})
    version_id = data.node_features.get("version_id", {})
    translation_of = data.edge_features.get("translation_of", {})
    translation_unit_of = data.edge_features.get("translation_unit_of", {})
    units_by_version: dict[str, list[int]] = {}
    for unit in node_index.get("unit", []):
        units_by_version.setdefault(str(version_id.get(unit, "")), []).append(unit)

    records: list[dict] = []
    for book in node_index.get("book", []):
        if version_kind.get(book) != "generated_translation":
            continue
        targets = translation_of.get(book, set())
        source_book = next(iter(targets)) if len(targets) == 1 else None
        generated_version_id = str(version_id.get(book, ""))
        source_version_id = str(version_id.get(source_book, "")) if source_book is not None else ""
        language = str(
            base._feature(
                data,
                "generated_language",
                book,
                base._feature(data, "language", book),
            )
        )
        prefix = f"{language.strip().lower()[:2]}_" if language.strip() else ""
        generated_units = units_by_version.get(generated_version_id, [])
        aligned = 0
        for unit in generated_units:
            unit_targets = translation_unit_of.get(unit, set())
            if len(unit_targets) != 1 or source_book is None:
                continue
            target = next(iter(unit_targets))
            generated_id = str(base._feature(data, "unit_id", unit))
            if prefix and generated_id.startswith(prefix):
                generated_id = generated_id[len(prefix) :]
            if (
                version_kind.get(target) == "source"
                and str(version_id.get(target, "")) == source_version_id
                and str(base._feature(data, "source_ref", unit))
                == str(base._feature(data, "source_ref", target))
                and generated_id == str(base._feature(data, "unit_id", target))
            ):
                aligned += 1
        records.append(
            {
                "ocp_book": base._feature(data, "ocp_book", book),
                "version_title": base._feature(data, "version_title", book),
                "language": language,
                "source_file": base._feature(data, "source_file", book),
                "marker": base._feature(data, "generation_marker", book),
                "source_version_title": (
                    base._feature(data, "version_title", source_book) if source_book is not None else ""
                ),
                "source_version_language": (
                    base._feature(data, "language", source_book) if source_book is not None else ""
                ),
                "unit_count": len(generated_units),
                "aligned_unit_count": aligned,
            }
        )
    return records


def _generated_provenance_features_ok(
    data: TFData,
    node_index: dict[str, list[int]],
) -> bool:
    books = [
        node
        for node in node_index.get("book", [])
        if base._feature(data, "version_kind", node) == "generated_translation"
    ]
    return all(
        base._feature(data, "generation_marker", node) == "OCP-Trans"
        and base._feature(data, "generation_method", node) == "llm"
        and base._feature(data, "generation_model", node)
        == "openrouter/google/gemini-3.7-flash"
        for node in books
    )


''' + marker
    text = replace_once(text, marker, helper, label="graph generated inventory helper")

    text = replace_once(
        text,
        '    raw_excluded_translations = raw["excluded_generated_translation_versions"]\n'
        '    graph_ellipses = _graph_ellipsis_inventory(data, node_index)\n',
        '    raw_excluded_translations = raw["excluded_generated_translation_versions"]\n'
        '    raw_generated_translations = raw["generated_translations"]\n'
        '    raw_generated_mapping_failures = raw["generated_translation_mapping_failures"]\n'
        '    graph_generated_translations = _graph_generated_translation_inventory(data, node_index)\n'
        '    graph_ellipses = _graph_ellipsis_inventory(data, node_index)\n',
        label="generated inventories in report",
    )

    text = replace_once(
        text,
        '        "generated_translation_exclusions": base._canonical(raw_excluded_translations)\n'
        '        == base._canonical(model_excluded_translations),\n'
        '        "versions": base._canonical(raw["versions"]) == base._canonical(graph["versions"]),\n',
        '        "generated_translation_exclusions": base._canonical(raw_excluded_translations)\n'
        '        == base._canonical(model_excluded_translations),\n'
        '        "generated_translation_alignment": (\n'
        '            not raw_generated_mapping_failures\n'
        '            and base._canonical(raw_generated_translations)\n'
        '            == base._canonical(graph_generated_translations)\n'
        '        ),\n'
        '        "generated_translation_provenance": (\n'
        '            base._canonical(raw_generated_translations)\n'
        '            == base._canonical(graph_generated_translations)\n'
        '            and _generated_provenance_features_ok(data, node_index)\n'
        '        ),\n'
        '        "versions": base._canonical(raw["versions"]) == base._canonical(graph["versions"]),\n',
        label="generated semantic checks",
    )

    text = replace_once(
        text,
        '        "excluded_generated_translation_versions": len(raw_excluded_translations),\n'
        '        "divisions": len(raw["divs"]),\n',
        '        "excluded_generated_translation_versions": len(raw_excluded_translations),\n'
        '        "generated_translation_versions": len(raw_generated_translations),\n'
        '        "generated_translation_units": sum(\n'
        '            record["unit_count"] for record in raw_generated_translations\n'
        '        ),\n'
        '        "divisions": len(raw["divs"]),\n',
        label="source generated counts",
    )

    text = replace_once(
        text,
        '        "witness_edges": sum(\n'
        '            len(targets) for targets in data.edge_features.get("witness", {}).values()\n'
        '        ),\n'
        '    }\n\n'
        '    generic = data.metadata.get("", {})\n',
        '        "witness_edges": sum(\n'
        '            len(targets) for targets in data.edge_features.get("witness", {}).values()\n'
        '        ),\n'
        '        "generated_translation_versions": len(graph_generated_translations),\n'
        '        "generated_translation_units": sum(\n'
        '            record["unit_count"] for record in graph_generated_translations\n'
        '        ),\n'
        '        "translation_of_edges": sum(\n'
        '            len(targets) for targets in data.edge_features.get("translation_of", {}).values()\n'
        '        ),\n'
        '        "translation_unit_of_edges": sum(\n'
        '            len(targets) for targets in data.edge_features.get("translation_unit_of", {}).values()\n'
        '        ),\n'
        '        "synthetic_witnesses": sum(\n'
        '            1\n'
        '            for node in node_index.get("manuscript", [])\n'
        '            if base._feature(data, "synthetic_witness", node, 0) == 1\n'
        '        ),\n'
        '    }\n\n'
        '    by_language: dict[str, dict[str, int]] = {}\n'
        '    for record in raw_generated_translations:\n'
        '        language = str(record["language"])\n'
        '        summary = by_language.setdefault(language, {"versions": 0, "units": 0})\n'
        '        summary["versions"] += 1\n'
        '        summary["units"] += int(record["unit_count"])\n'
        '    generated_units = sum(record["unit_count"] for record in raw_generated_translations)\n'
        '    aligned_units = sum(record["aligned_unit_count"] for record in raw_generated_translations)\n\n'
        '    generic = data.metadata.get("", {})\n',
        label="graph generated counts and summary",
    )

    text = replace_once(
        text,
        '        "diagnostics": {\n'
        '            "duplicate_section_addresses": section_address_collisions,\n'
        '            "excluded_generated_translation_versions": raw_excluded_translations,\n'
        '        },\n'
        '        "source": source_counts,\n',
        '        "diagnostics": {\n'
        '            "duplicate_section_addresses": section_address_collisions,\n'
        '            "excluded_generated_translation_versions": raw_excluded_translations,\n'
        '            "generated_translation_mapping_failures": raw_generated_mapping_failures,\n'
        '        },\n'
        '        "generated_translations": {\n'
        '            "by_language": by_language,\n'
        '            "versions": len(raw_generated_translations),\n'
        '            "units": generated_units,\n'
        '            "aligned_units": aligned_units,\n'
        '            "alignment_coverage": (aligned_units / generated_units if generated_units else 1.0),\n'
        '        },\n'
        '        "source": source_counts,\n',
        label="generated report payload",
    )

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_audit()
    patch_semantic_audit()
