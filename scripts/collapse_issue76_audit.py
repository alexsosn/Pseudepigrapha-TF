from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "pseudepigrapha_tf"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


audit_core = PKG / "audit_core.py"
semantic_core = PKG / "semantic_audit_core.py"
audit = audit_core.read_text(encoding="utf-8")
semantic = semantic_core.read_text(encoding="utf-8")

audit = replace_once(
    audit,
    "import re\nfrom pathlib import Path\n",
    "import re\nfrom collections import Counter\nfrom pathlib import Path\n",
    label="audit Counter import",
)

raw_identity_helper = r'''
def _raw_translation_unit_identities(
    version: ET.Element,
    *,
    generated: bool,
) -> tuple[tuple[tuple[str, ...], str], ...]:
    """Return raw structural unit identities for independent translation mapping."""

    text = version.find("text")
    if text is None:
        return ()

    prefix = ""
    if generated:
        language = (version.get("language") or "").strip().lower()
        prefix = f"{language[:2]}_" if language else ""

    result: list[tuple[tuple[str, ...], str]] = []

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
                    unit_id = unit_id[len(prefix):]
                result.append((path, unit_id))

    walk(text, ())
    return tuple(result)


'''
audit = replace_once(
    audit,
    "def _raw_inventory(source_dir: Path) -> dict:\n",
    raw_identity_helper + "def _raw_inventory(source_dir: Path) -> dict:\n",
    label="audit raw identity helper",
)
audit = replace_once(
    audit,
    '        "ellipses": [], "orphan_readings": [], "excluded_generated_translation_versions": [],\n',
    '        "ellipses": [], "orphan_readings": [], "excluded_generated_translation_versions": [],\n'
    '        "generated_translations": [], "generated_translation_mapping_failures": [],\n',
    label="audit generated inventory keys",
)

branch_start = audit.index('        if versions:\n', audit.index('    for path in sorted(source_dir.glob("*.xml")):'))
branch_end_marker = '        else:\n            version_title = root.get("language", "") or "Default"\n'
branch_end = audit.index(branch_end_marker, branch_start)

modern_branch = r'''        if versions:
            classified_versions: list[tuple[ET.Element, bool]] = []
            source_versions: list[ET.Element] = []
            for version in versions:
                try:
                    generated = is_generated_translation_version(version)
                except GeneratedTranslationClassificationError as exc:
                    raise InvalidSourceError(f"{path.name}: {exc}") from exc
                classified_versions.append((version, generated))
                if not generated:
                    source_versions.append(version)

            source_signatures = [
                Counter(_raw_translation_unit_identities(version, generated=False))
                for version in source_versions
            ]

            for version, generated in classified_versions:
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
                    "version_kind": "generated_translation" if generated else "source",
                })

                if generated:
                    identities = _raw_translation_unit_identities(version, generated=True)
                    signature = Counter(identities)
                    candidates = [
                        source
                        for source, source_signature in zip(
                            source_versions, source_signatures, strict=True
                        )
                        if source_signature == signature
                    ]
                    common = {
                        "ocp_book": ocp_book,
                        "version_title": version_title,
                        "language": version.get("language", ""),
                        "source_file": path.name,
                    }
                    if len(candidates) != 1:
                        inventory["generated_translation_mapping_failures"].append({
                            **common,
                            "candidate_count": len(candidates),
                        })
                    else:
                        source = candidates[0]
                        inventory["generated_translations"].append({
                            **common,
                            "marker": GENERATED_TRANSLATION_MARKER,
                            "source_version_title": source.get("title", ""),
                            "source_version_language": source.get("language", ""),
                            "unit_count": len(identities),
                            "aligned_unit_count": len(identities),
                        })

                if is_wrapped_legacy_version(version):
                    specs = (DivisionSpec("Chapter", ":"), DivisionSpec("Verse", ""))
                else:
                    divisions = version.find("divisions")
                    specs = tuple(
                        DivisionSpec(
                            d.get("label", ""),
                            d.get("delimiter", d.get("Delimiter", "")),
                            _plain_text(d),
                        )
                        for d in (
                            divisions.findall("division")
                            if divisions is not None
                            else []
                        )
                    )
                add_specs(ocp_book, version_title, specs)
                add_manuscripts(version, ocp_book, version_title)
                add_resources(version, ocp_book, version_title)
                text = version.find("text")
                if text is not None:
                    if is_wrapped_legacy_version(version):
                        add_legacy_text(text, ocp_book, version_title, specs)
                    else:
                        for div in text.findall("div"):
                            walk_div(div, ocp_book, version_title, specs, ())
'''
audit = audit[:branch_start] + modern_branch + audit[branch_end:]

audit = replace_once(
    audit,
    '                "source_sha256": source_sha256,\n            })\n            specs = (DivisionSpec("Chapter", ":"), DivisionSpec("Verse", ""))\n',
    '                "source_sha256": source_sha256,\n'
    '                "version_kind": "source",\n'
    '            })\n'
    '            specs = (DivisionSpec("Chapter", ":"), DivisionSpec("Verse", ""))\n',
    label="audit legacy version kind",
)
audit = replace_once(
    audit,
    '            "source_sha256": _feature(data, "source_sha256", node),\n        })\n',
    '            "source_sha256": _feature(data, "source_sha256", node),\n'
    '            "version_kind": _feature(data, "version_kind", node, "source"),\n'
    '        })\n',
    label="audit graph version kind",
)

semantic = replace_once(
    semantic,
    '                "source_sha256": base._feature(data, "source_sha256", node),\n',
    '                "source_sha256": base._feature(data, "source_sha256", node),\n'
    '                "version_kind": base._feature(data, "version_kind", node, "source"),\n',
    label="semantic metadata version kind",
)

semantic_helpers = r'''
def _graph_generated_translation_inventory(
    data: TFData,
    node_index: dict[str, list[int]],
) -> list[dict]:
    """Project generated/source alignment independently from graph provenance."""

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
        source_version_id = (
            str(version_id.get(source_book, "")) if source_book is not None else ""
        )
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
        seen_targets: set[int] = set()
        for unit in generated_units:
            unit_targets = translation_unit_of.get(unit, set())
            if len(unit_targets) != 1 or source_book is None:
                continue
            target = next(iter(unit_targets))
            generated_id = str(base._feature(data, "unit_id", unit))
            if prefix and generated_id.startswith(prefix):
                generated_id = generated_id[len(prefix):]
            if (
                target not in seen_targets
                and version_kind.get(target) == "source"
                and str(version_id.get(target, "")) == source_version_id
                and str(base._feature(data, "source_ref", unit))
                == str(base._feature(data, "source_ref", target))
                and generated_id == str(base._feature(data, "unit_id", target))
            ):
                aligned += 1
                seen_targets.add(target)

        records.append({
            "ocp_book": base._feature(data, "ocp_book", book),
            "version_title": base._feature(data, "version_title", book),
            "language": language,
            "source_file": base._feature(data, "source_file", book),
            "marker": base._feature(data, "generation_marker", book),
            "source_version_title": (
                base._feature(data, "version_title", source_book)
                if source_book is not None
                else ""
            ),
            "source_version_language": (
                base._feature(data, "language", source_book)
                if source_book is not None
                else ""
            ),
            "unit_count": len(generated_units),
            "aligned_unit_count": aligned,
        })
    return records


def _generated_provenance_features_ok(
    data: TFData,
    node_index: dict[str, list[int]],
) -> bool:
    generated_books = [
        node
        for node in node_index.get("book", [])
        if base._feature(data, "version_kind", node) == "generated_translation"
    ]
    return all(
        base._feature(data, "generation_marker", node) == "OCP-Trans"
        and base._feature(data, "generation_method", node) == "llm"
        and base._feature(data, "generation_model", node)
        == "openrouter/google/gemini-3.7-flash"
        for node in generated_books
    )


'''
semantic = replace_once(
    semantic,
    'def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:\n',
    semantic_helpers
    + 'def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:\n',
    label="semantic generated helpers",
)

semantic = replace_once(
    semantic,
    '    raw_excluded_translations = raw["excluded_generated_translation_versions"]\n',
    '    raw_excluded_translations = raw["excluded_generated_translation_versions"]\n'
    '    raw_generated_translations = raw["generated_translations"]\n'
    '    raw_generated_mapping_failures = raw["generated_translation_mapping_failures"]\n',
    label="semantic raw generated inventories",
)
semantic = replace_once(
    semantic,
    '    graph_missing_unit_ids = _graph_missing_unit_id_inventory(data, node_index)\n',
    '    graph_missing_unit_ids = _graph_missing_unit_id_inventory(data, node_index)\n'
    '    graph_generated_translations = _graph_generated_translation_inventory(data, node_index)\n',
    label="semantic graph generated inventory",
)
semantic = replace_once(
    semantic,
    '    section_address_collisions = _section_address_collisions_from_records(section_address_records)\n\n    checks = {\n',
    '    section_address_collisions = _section_address_collisions_from_records(section_address_records)\n'
    '    generated_alignment_ok = (\n'
    '        not raw_generated_mapping_failures\n'
    '        and base._canonical(raw_generated_translations)\n'
    '        == base._canonical(graph_generated_translations)\n'
    '    )\n'
    '    generated_provenance_ok = (\n'
    '        generated_alignment_ok\n'
    '        and _generated_provenance_features_ok(data, node_index)\n'
    '    )\n\n'
    '    checks = {\n',
    label="semantic generated check inputs",
)
semantic = replace_once(
    semantic,
    '        "generated_translation_exclusions": base._canonical(raw_excluded_translations)\n        == base._canonical(model_excluded_translations),\n',
    '        "generated_translation_exclusions": base._canonical(raw_excluded_translations)\n'
    '        == base._canonical(model_excluded_translations),\n'
    '        "generated_translation_alignment": generated_alignment_ok,\n'
    '        "generated_translation_provenance": generated_provenance_ok,\n',
    label="semantic generated checks",
)
semantic = replace_once(
    semantic,
    '        "excluded_generated_translation_versions": len(raw_excluded_translations),\n',
    '        "excluded_generated_translation_versions": len(raw_excluded_translations),\n'
    '        "generated_translation_versions": len(raw_generated_translations),\n'
    '        "generated_translation_units": sum(\n'
    '            int(record["unit_count"]) for record in raw_generated_translations\n'
    '        ),\n',
    label="semantic source generated counts",
)
semantic = replace_once(
    semantic,
    '        "witness_edges": sum(\n            len(targets) for targets in data.edge_features.get("witness", {}).values()\n        ),\n    }\n\n    generic = data.metadata.get("", {})\n',
    '        "witness_edges": sum(\n'
    '            len(targets) for targets in data.edge_features.get("witness", {}).values()\n'
    '        ),\n'
    '        "generated_translation_versions": len(graph_generated_translations),\n'
    '        "generated_translation_units": sum(\n'
    '            int(record["unit_count"]) for record in graph_generated_translations\n'
    '        ),\n'
    '        "translation_of_edges": sum(\n'
    '            len(targets) for targets in data.edge_features.get("translation_of", {}).values()\n'
    '        ),\n'
    '        "translation_unit_of_edges": sum(\n'
    '            len(targets)\n'
    '            for targets in data.edge_features.get("translation_unit_of", {}).values()\n'
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
    '    generated_units = sum(\n'
    '        int(record["unit_count"]) for record in raw_generated_translations\n'
    '    )\n'
    '    aligned_units = sum(\n'
    '        int(record["aligned_unit_count"]) for record in raw_generated_translations\n'
    '    )\n\n'
    '    generic = data.metadata.get("", {})\n',
    label="semantic graph generated counts",
)
semantic = replace_once(
    semantic,
    '            "excluded_generated_translation_versions": raw_excluded_translations,\n        },\n',
    '            "excluded_generated_translation_versions": raw_excluded_translations,\n'
    '            "generated_translation_mapping_failures": raw_generated_mapping_failures,\n'
    '        },\n',
    label="semantic generated diagnostics",
)
semantic = replace_once(
    semantic,
    '        "source_sha256": source_hashes,\n        "provenance": {\n',
    '        "source_sha256": source_hashes,\n'
    '        "generated_translations": {\n'
    '            "by_language": by_language,\n'
    '            "versions": len(raw_generated_translations),\n'
    '            "units": generated_units,\n'
    '            "aligned_units": aligned_units,\n'
    '            "alignment_coverage": aligned_units / generated_units if generated_units else 1.0,\n'
    '        },\n'
    '        "provenance": {\n',
    label="semantic generated report section",
)

(PKG / "audit.py").write_text(audit, encoding="utf-8")
(PKG / "semantic_audit.py").write_text(semantic, encoding="utf-8")
audit_core.unlink()
semantic_core.unlink()
