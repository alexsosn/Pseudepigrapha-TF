from pathlib import Path

import pytest

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory

FIXTURES = Path(__file__).parent / "fixtures"


def _case(tmp_path):
    source = FIXTURES / "ownership_edges.xml"
    (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    data = build_tf_data(books)
    baseline = build_conversion_report(tmp_path, books, data)
    assert baseline["status"] == "ok", baseline["failed_checks"]
    return books, data


def _node(data, kind, feature, value):
    return next(
        node
        for node, node_kind in data.node_features["otype"].items()
        if node_kind == kind and data.node_features.get(feature, {}).get(node) == value
    )


def _node_in_version(data, kind, feature, value, version_id):
    return next(
        node
        for node, node_kind in data.node_features["otype"].items()
        if node_kind == kind
        and data.node_features.get(feature, {}).get(node) == value
        and data.node_features.get("version_id", {}).get(node) == version_id
    )


def _owner(data, version_id):
    textual = data.node_features.get("book", {})
    for node, value in textual.items():
        if value == version_id:
            return node
    return _node(data, "version_metadata", "version_id", version_id)


def _assert_only_ownership_failed(report, check):
    assert report["status"] == "failed"
    assert report["semantic_checks"][check] is False
    assert report["semantic_checks"]["reading_payloads"] is True
    assert report["semantic_checks"]["manuscripts"] is True
    assert report["semantic_checks"]["resources"] is True


@pytest.mark.parametrize("mutation", ["delete", "retarget"])
def test_audit_rejects_reading_ownership_corruption(tmp_path, mutation):
    books, data = _case(tmp_path)
    alpha = _node(data, "reading", "reading_text", "alpha")
    beta = _node(data, "reading", "reading_text", "beta")
    beta_unit = next(iter(data.edge_features["reading_of"][beta]))

    if mutation == "delete":
        data.edge_features["reading_of"].pop(alpha)
    else:
        data.edge_features["reading_of"][alpha] = {beta_unit}

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "reading_ownership")


def test_audit_rejects_reading_with_second_owner(tmp_path):
    books, data = _case(tmp_path)
    alpha = _node(data, "reading", "reading_text", "alpha")
    beta = _node(data, "reading", "reading_text", "beta")
    beta_unit = next(iter(data.edge_features["reading_of"][beta]))
    data.edge_features["reading_of"][alpha].add(beta_unit)

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "reading_ownership")


def test_audit_rejects_reading_owner_of_wrong_type(tmp_path):
    books, data = _case(tmp_path)
    alpha = _node(data, "reading", "reading_text", "alpha")
    same_locus_div = _node_in_version(data, "div", "source_ref", "1:1", "Ownership__Greek")
    data.edge_features["reading_of"][alpha] = {same_locus_div}

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "reading_ownership")


@pytest.mark.parametrize(
    ("abbrev", "mutation", "wrong_owner"),
    [
        ("A", "delete", None),
        ("A", "retarget", "Ownership__Greek_2"),
        ("X", "retarget", "Ownership__Greek_2"),
        ("C", "delete", None),
        ("C", "retarget", "Ownership__Greek"),
    ],
)
def test_audit_rejects_manuscript_ownership_corruption(tmp_path, abbrev, mutation, wrong_owner):
    books, data = _case(tmp_path)
    manuscript = _node(data, "manuscript", "ms_abbrev", abbrev)

    if mutation == "delete":
        data.edge_features["manuscript_of"].pop(manuscript)
    else:
        data.edge_features["manuscript_of"][manuscript] = {_owner(data, wrong_owner)}

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "manuscript_ownership")


def test_audit_rejects_manuscript_with_second_owner(tmp_path):
    books, data = _case(tmp_path)
    manuscript = _node(data, "manuscript", "ms_abbrev", "A")
    data.edge_features["manuscript_of"][manuscript].add(_owner(data, "Ownership__Greek_2"))

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "manuscript_ownership")


def test_audit_rejects_manuscript_owner_of_wrong_type(tmp_path):
    books, data = _case(tmp_path)
    manuscript = _node(data, "manuscript", "ms_abbrev", "A")
    same_version_resource = _node_in_version(
        data, "resource", "resource_name", "Edition A", "Ownership__Greek"
    )
    data.edge_features["manuscript_of"][manuscript] = {same_version_resource}

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "manuscript_ownership")


@pytest.mark.parametrize(
    ("resource_name", "mutation", "wrong_owner"),
    [
        ("Edition A", "delete", None),
        ("Edition A", "retarget", "Ownership__Greek_2"),
        ("Edition C", "delete", None),
        ("Edition C", "retarget", "Ownership__Greek"),
    ],
)
def test_audit_rejects_resource_ownership_corruption(tmp_path, resource_name, mutation, wrong_owner):
    books, data = _case(tmp_path)
    resource = _node(data, "resource", "resource_name", resource_name)

    if mutation == "delete":
        data.edge_features["resource_of"].pop(resource)
    else:
        data.edge_features["resource_of"][resource] = {_owner(data, wrong_owner)}

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "resource_ownership")


def test_audit_rejects_resource_with_second_owner(tmp_path):
    books, data = _case(tmp_path)
    resource = _node(data, "resource", "resource_name", "Edition A")
    data.edge_features["resource_of"][resource].add(_owner(data, "Ownership__Greek_2"))

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "resource_ownership")


def test_audit_rejects_resource_owner_of_wrong_type(tmp_path):
    books, data = _case(tmp_path)
    resource = _node(data, "resource", "resource_name", "Edition A")
    same_version_manuscript = _node_in_version(
        data, "manuscript", "ms_abbrev", "A", "Ownership__Greek"
    )
    data.edge_features["resource_of"][resource] = {same_version_manuscript}

    report = build_conversion_report(tmp_path, books, data)
    _assert_only_ownership_failed(report, "resource_ownership")
