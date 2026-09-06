import json
from pathlib import Path

import pytest

from pseudepigrapha_tf import Apparatus, build_tf_data
from pseudepigrapha_tf import source as source_module
from pseudepigrapha_tf.document_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


def _copy_fixture(source_dir: Path, name: str, *, target: str | None = None) -> Path:
    destination = source_dir / (target or name)
    destination.write_bytes((FIXTURES / name).read_bytes())
    return destination


def _write_intros(source_dir: Path, documents: dict[str, object]) -> Path:
    payload = {
        "_meta": {
            "exported": "2026-08-26",
            "source": "web2py databases/storage.sqlite (docs table)",
            "note": "Regenerate with scripts/export_intros.py after database updates.",
        },
        "documents": documents,
    }
    path = source_dir / "intros.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def _entry(*, title="Metadata title", version=2.0, fields=None, citation=None):
    entry = {
        "title": title,
        "version": version,
        "fields": {} if fields is None else fields,
    }
    if citation is not None:
        entry["citation"] = citation
    return entry


def _catalog(source_dir: Path):
    return source_module.load_document_metadata(source_dir)


def _work_nodes(data):
    return [node for node, kind in data.node_features["otype"].items() if kind == "work"]


def test_intro_loader_preserves_public_schema_and_exact_values(tmp_path):
    _copy_fixture(tmp_path, "sample.xml")
    html = '<table>\r\n<tr><td>Ἰώβ\tC:\\OCP\\docs</td></tr>\r\n</table>'
    citation = '<p>Editor, ed. “Sample”.</p>'
    _write_intros(
        tmp_path,
        {
            "sample.xml": _entry(
                fields={"introduction": html, "themes": ""},
                citation=citation,
            )
        },
    )

    catalog = _catalog(tmp_path)
    assert dict(catalog.meta)["exported"] == "2026-08-26"
    assert len(catalog.documents) == 1
    document = catalog.documents[0]
    assert document.source_file == "sample.xml"
    assert document.title == "Metadata title"
    assert document.version == 2.0
    assert document.fields == (("introduction", html), ("themes", ""))
    assert document.citation == citation


def test_intro_loader_rejects_dangling_document_and_unknown_field(tmp_path):
    _copy_fixture(tmp_path, "sample.xml")
    _write_intros(tmp_path, {"missing.xml": _entry(fields={"introduction": "x"})})
    with pytest.raises(ValueError, match="sibling XML"):
        _catalog(tmp_path)

    _write_intros(tmp_path, {"sample.xml": _entry(fields={"future_private_field": "x"})})
    with pytest.raises(ValueError, match="unknown intro field"):
        _catalog(tmp_path)


def test_multiversion_work_owns_intro_once_and_versions_link_to_it(tmp_path):
    _copy_fixture(tmp_path, "multiple_versions.xml")
    html = "<p>One work, two versions.</p>\r\n<ul><li>exact</li></ul>"
    _write_intros(
        tmp_path,
        {"multiple_versions.xml": _entry(title="Multi-version metadata", fields={"introduction": html})},
    )
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []

    data = build_tf_data(books, document_metadata=_catalog(tmp_path))

    works = _work_nodes(data)
    assert len(works) == 1
    work = works[0]
    assert data.node_features["ocp_book"][work] == "Multi"
    assert json.loads(data.node_features["intro_introduction_json"][work]) == html
    assert list(data.node_features["intro_introduction_json"]) == [work]

    books_nodes = [node for node, kind in data.node_features["otype"].items() if kind == "book"]
    assert len(books_nodes) == 2
    assert all(data.edge_features["version_of"].get(node) == {work} for node in books_nodes)
    assert len(data.edge_features["oslots"][work]) == 1


def test_empty_xml_intro_becomes_metadata_only_work_without_fake_version(tmp_path):
    _copy_fixture(tmp_path, "sample.xml")
    (tmp_path / "3Macc.xml").write_bytes(b"")
    _write_intros(
        tmp_path,
        {
            "3Macc.xml": _entry(
                title="3 Maccabees",
                version=1.0,
                fields={"bibliography": "<p>Bibliography only.</p>"},
            )
        },
    )
    books, warnings = load_source_directory(tmp_path)
    assert warnings == ["skipping empty XML source: 3Macc.xml"]

    data = build_tf_data(books, document_metadata=_catalog(tmp_path))
    works = _work_nodes(data)
    by_work = {data.node_features["ocp_book"][node]: node for node in works}
    assert set(by_work) == {"Sample", "3Macc"}

    empty_work = by_work["3Macc"]
    assert data.node_features["is_metadata_only_work"][empty_work] == 1
    assert json.loads(data.node_features["intro_bibliography_json"][empty_work]) == "<p>Bibliography only.</p>"
    assert not any(empty_work in targets for targets in data.edge_features["version_of"].values())
    assert not any(
        data.node_features["ocp_book"].get(node) == "3Macc"
        for node, kind in data.node_features["otype"].items()
        if kind in {"book", "version_metadata"}
    )
    assert len(data.edge_features["oslots"][empty_work]) == 1


def test_work_metadata_decodes_exact_html_after_real_tf_reload(tmp_path):
    from tf.fabric import Fabric

    _copy_fixture(tmp_path, "sample.xml")
    html = '<table>\r\n<tr><td>Ἰώβ &amp; ሀ</td></tr>\r\n<tr><td>C:\\OCP\\docs\tX</td></tr>\r\n</table>'
    citation = '<p>Scott, ed. “Sample”.</p>\r\n'
    _write_intros(
        tmp_path,
        {"sample.xml": _entry(fields={"introduction": html, "themes": ""}, citation=citation)},
    )
    books, _ = load_source_directory(tmp_path)
    data = build_tf_data(books, document_metadata=_catalog(tmp_path))
    output = tmp_path / "tf"
    assert write_tf(data, output)

    tf = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = tf.load(
        "ocp_book source_file intro_title_json intro_version_json intro_field_order "
        "intro_introduction_json intro_themes_json intro_citation_json is_metadata_only_work version_of",
        silent="deep",
    )
    assert api is not None

    metadata = Apparatus(api).work_metadata("Sample")
    assert metadata["work"] == "Sample"
    assert metadata["source_file"] == "sample.xml"
    assert metadata["metadata_title"] == "Metadata title"
    assert metadata["metadata_version"] == 2.0
    assert metadata["fields"] == {"introduction": html, "themes": ""}
    assert metadata["citation"] == citation
    assert metadata["has_text"] is True
    assert metadata["metadata_only"] is False


def test_conversion_report_audits_raw_intro_values_independently(tmp_path):
    _copy_fixture(tmp_path, "sample.xml")
    html = "<p>Exact\r\nmetadata Ἰώβ.</p>"
    _write_intros(
        tmp_path,
        {"sample.xml": _entry(fields={"introduction": html}, citation="<p>Cite.</p>")},
    )
    books, _ = load_source_directory(tmp_path)
    data = build_tf_data(books, document_metadata=_catalog(tmp_path))

    report = build_conversion_report(tmp_path, books, data)

    assert report["status"] == "ok", report["failed_checks"]
    assert report["source"]["document_metadata_documents"] == 1
    assert report["graph"]["document_metadata_documents"] == 1
    assert report["source"]["document_metadata_citations"] == 1
    assert report["graph"]["document_metadata_citations"] == 1
    assert report["semantic_checks"]["document_metadata_exact"] is True
    assert report["semantic_checks"]["work_version_ownership"] is True
    assert report["diagnostics"]["document_metadata_mismatches"] == []


def test_work_without_intro_metadata_remains_explicit_and_valid(tmp_path):
    _copy_fixture(tmp_path, "sample.xml")
    _write_intros(tmp_path, {})
    books, _ = load_source_directory(tmp_path)

    data = build_tf_data(books, document_metadata=_catalog(tmp_path))

    works = _work_nodes(data)
    assert len(works) == 1
    work = works[0]
    assert data.node_features["ocp_book"][work] == "Sample"
    assert work not in data.node_features.get("intro_title_json", {})
    book = next(node for node, kind in data.node_features["otype"].items() if kind == "book")
    assert data.edge_features["version_of"][book] == {work}
