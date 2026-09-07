from pathlib import Path

path = Path("src/pseudepigrapha_tf/metadata.py")
text = path.read_text(encoding="utf-8")

old = '''def _graph_public_metadata(data: TFData) -> tuple[dict[str, Any], list[str], list[str]]:
    documents: dict[str, Any] = {}
    errors: list[str] = []
    duplicates: list[str] = []
    otype = data.node_features.get("otype", {})
    source_files = data.node_features.get("source_file", {})

    for node, kind in otype.items():
'''
new = '''def _graph_public_metadata(
    data: TFData,
) -> tuple[dict[str, Any], list[str], list[str], list[dict[str, Any]]]:
    documents: dict[str, Any] = {}
    errors: list[str] = []
    duplicates: list[str] = []
    orphan_feature_owners: list[dict[str, Any]] = []
    otype = data.node_features.get("otype", {})
    source_files = data.node_features.get("source_file", {})

    for feature in ALL_INTRO_FEATURES:
        for node in data.node_features.get(feature, {}):
            node_type = otype.get(node)
            if node_type != "document_metadata":
                orphan_feature_owners.append(
                    {"node": node, "node_type": node_type, "feature": feature}
                )

    for node, kind in otype.items():
'''
assert old in text
text = text.replace(old, new, 1)

old = '''        documents[filename] = entry
    return documents, errors, duplicates
'''
new = '''        documents[filename] = entry
    orphan_feature_owners.sort(
        key=lambda record: (record["feature"], repr(record["node"]))
    )
    return documents, errors, duplicates, orphan_feature_owners
'''
assert old in text
text = text.replace(old, new, 1)

old = '''    raw_documents, raw_sha256, source_meta = _raw_public_metadata(source_dir)
    graph_documents, decode_errors, duplicate_files = _graph_public_metadata(data)
    generic = data.metadata.get("", {})
'''
new = '''    raw_documents, raw_sha256, source_meta = _raw_public_metadata(source_dir)
    (
        graph_documents,
        decode_errors,
        duplicate_files,
        orphan_feature_owners,
    ) = _graph_public_metadata(data)
    generic = data.metadata.get("", {})
'''
assert old in text
text = text.replace(old, new, 1)

old = '''    checks["public_metadata_values"] = (
        raw_documents == graph_documents and not decode_errors and not duplicate_files
    )
'''
new = '''    checks["public_metadata_values"] = (
        raw_documents == graph_documents
        and not decode_errors
        and not duplicate_files
        and not orphan_feature_owners
    )
'''
assert old in text
text = text.replace(old, new, 1)

old = '''        "decode_errors": decode_errors,
        "duplicate_graph_files": duplicate_files,
    }
'''
new = '''        "decode_errors": decode_errors,
        "duplicate_graph_files": duplicate_files,
        "orphan_feature_owners": orphan_feature_owners,
    }
'''
assert old in text
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
