#!/usr/bin/env python3
"""Print a deterministic inventory of OCP intros.json against sibling XML files."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def inventory(intros_path: Path) -> dict[str, object]:
    payload = json.loads(intros_path.read_text(encoding="utf-8"))
    documents = payload.get("documents", {})
    if not isinstance(documents, dict):
        raise ValueError("intros.json documents must be an object")

    source_dir = intros_path.parent
    xml_files = {
        path.name
        for path in source_dir.glob("*.xml")
        if not path.name.startswith(".") and path.stat().st_size > 0
    }
    all_xml_files = {
        path.name
        for path in source_dir.glob("*.xml")
        if not path.name.startswith(".")
    }
    document_names = set(documents)
    field_counts: Counter[str] = Counter()
    citation_count = 0
    empty_field_documents: list[str] = []

    for filename, entry in sorted(documents.items()):
        if not isinstance(entry, dict):
            raise ValueError(f"{filename}: document entry must be an object")
        fields = entry.get("fields", {})
        if not isinstance(fields, dict):
            raise ValueError(f"{filename}: fields must be an object")
        field_counts.update(fields.keys())
        if entry.get("citation"):
            citation_count += 1
        if not fields:
            empty_field_documents.append(filename)

    return {
        "meta": payload.get("_meta", {}),
        "intros_documents": len(documents),
        "nonempty_xml_documents": len(xml_files),
        "all_xml_documents": len(all_xml_files),
        "matched_nonempty_xml": len(document_names & xml_files),
        "intros_without_nonempty_xml": sorted(document_names - xml_files),
        "nonempty_xml_without_intros": sorted(xml_files - document_names),
        "intros_without_any_xml": sorted(document_names - all_xml_files),
        "empty_xml_with_intros": sorted((all_xml_files - xml_files) & document_names),
        "citation_documents": citation_count,
        "empty_field_documents": empty_field_documents,
        "field_counts": dict(sorted(field_counts.items())),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: inspect_intros.py PATH/TO/intros.json")
    print(json.dumps(inventory(Path(args[0])), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
