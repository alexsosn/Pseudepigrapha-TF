from pathlib import Path

import pytest

pytest.importorskip("tf")
from tf.advanced.app import findApp

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.metadata import (
    PublicMetadataCorpus,
    PublicMetadataDocument,
    attach_public_metadata,
)
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def _materialize(tmp_path, *fixture_names):
    output = tmp_path / "tf"
    names = fixture_names or ("sample.xml",)
    books = [parse_file(FIXTURES / name) for name in names]
    assert write_tf(build_tf_data(books), output)
    return output


def _materialize_with_document_metadata(tmp_path):
    output = tmp_path / "tf"
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])
    document = PublicMetadataDocument(
        filename="Sample.xml",
        title="Sample public metadata",
        version="test",
        citation=None,
        citation_present=False,
        fields={},
    )
    attach_public_metadata(
        data,
        PublicMetadataCorpus(
            documents={document.filename: document},
            source_sha256="0" * 64,
            source_meta={},
        ),
    )
    assert write_tf(data, output)
    return output


def _find_local_app(output, *, version=None):
    return findApp(
        f"app:{ROOT / 'app'}",
        "",
        None,
        "github",
        False,
        version=version,
        locations=[str(output)],
        modules=[""],
        silent="deep",
    )


def _load_app_for_rendering(tmp_path, *fixture_names):
    app = _find_local_app(_materialize(tmp_path, *fixture_names), version="0.1")
    assert app is not None
    assert app.api is not None
    return app


def _anchor_text(api, node):
    slot = api.E.oslots.s(node)[0]
    return api.T.text(slot)


def test_local_app_loads_materialized_tf_without_remote_distribution_contract(tmp_path):
    app = _find_local_app(_materialize(tmp_path))

    assert app is not None
    assert app.api is not None
    assert app.api.T.nodeFromSection(("Sample", "1", "Heading")) is not None


def test_pretty_alternative_reading_does_not_render_primary_anchor_text(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    alternative = next(
        node
        for node in api.F.otype.s("reading")
        if api.F.source_ref.v(node) == "1:Heading" and api.F.is_primary.v(node) != 1
    )

    html = app.pretty(alternative, _asString=True)

    assert "κυρίου" in html, html
    assert "θεοῦ" not in html, html


def test_pretty_explicit_omission_remains_visibly_distinct_from_reading(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    omission = next(
        node
        for node in api.F.otype.s("reading")
        if api.F.is_primary.v(node) == 1 and api.F.is_omission.v(node) == 1
    )

    html = app.pretty(omission, _asString=True)

    assert "is_omission" in html, html
    assert "πλήρης" not in html, html


def test_pretty_variant_word_uses_variant_surface_not_primary_anchor_text(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    variant_word = next(
        node
        for node in api.F.otype.s("variant_word")
        if api.F.g_word_utf8.v(node) == "κυρίου"
    )

    html = app.pretty(variant_word, _asString=True)

    assert "κυρίου" in html, html
    assert "θεοῦ" not in html, html


def test_pretty_manuscript_uses_manuscript_identity_not_anchor_text(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    manuscript = next(
        node for node in api.F.otype.s("manuscript") if api.F.ms_abbrev.v(node) == "A"
    )

    html = app.pretty(manuscript, _asString=True)

    assert "A" in html, html
    assert "λόγος" not in html, html
    assert "θεοῦ" not in html, html


def test_pretty_resource_uses_resource_identity_not_anchor_text(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    resource = next(
        node
        for node in api.F.otype.s("resource")
        if api.F.resource_name.v(node) == "Edition"
    )

    html = app.pretty(resource, _asString=True)

    assert "Edition" in html, html
    assert "λόγος" not in html, html


def test_pretty_ellipsis_uses_preserved_marker_not_technical_anchor(tmp_path):
    app = _load_app_for_rendering(tmp_path, "ellipsis.xml")
    api = app.api
    node = next(iter(api.F.otype.s("ellipsis")))
    own = api.F.ellipsis_text.v(node)
    anchor = _anchor_text(api, node)

    assert own == "lost passage"
    assert anchor and anchor != own
    html = app.pretty(node, _asString=True)
    assert own in html, html
    assert anchor not in html, html


def test_pretty_orphan_reading_uses_own_reading_not_technical_anchor(tmp_path):
    app = _load_app_for_rendering(tmp_path, "orphan_reading.xml")
    api = app.api
    node = next(iter(api.F.otype.s("orphan_reading")))
    own = api.F.reading_text.v(node)
    anchor = _anchor_text(api, node)

    assert "orphan" in own and "beta" in own
    assert anchor and anchor != own
    html = app.pretty(node, _asString=True)
    assert "orphan" in html and "beta" in html, html
    assert anchor not in html, html


def test_pretty_metadata_only_version_uses_version_title_not_anchor_text(tmp_path):
    app = _load_app_for_rendering(tmp_path, "metadata_only_version.xml")
    api = app.api
    node = next(
        n
        for n in api.F.otype.s("version_metadata")
        if api.F.version_title.v(n) == "Coptic"
    )
    anchor = _anchor_text(api, node)

    assert anchor and anchor != "Coptic"
    html = app.pretty(node, _asString=True)
    assert "Coptic" in html, html
    assert anchor not in html, html


def test_pretty_document_metadata_uses_intro_label_not_anchor_text(tmp_path):
    app = _find_local_app(_materialize_with_document_metadata(tmp_path), version="0.1")
    assert app is not None and app.api is not None
    api = app.api
    node = next(iter(api.F.otype.s("document_metadata")))
    anchor = _anchor_text(api, node)

    assert anchor and anchor != "Sample public metadata"
    html = app.pretty(node, _asString=True)
    assert "Sample public metadata" in html, html
    assert anchor not in html, html


def test_hidden_technical_type_remains_directly_inspectable(tmp_path):
    app = _load_app_for_rendering(tmp_path)
    api = app.api
    manuscript = next(
        node for node in api.F.otype.s("manuscript") if api.F.ms_abbrev.v(node) == "A"
    )

    html = app.pretty(manuscript, hideTypes=False, _asString=True)

    assert "A" in html, html
    assert "λόγος" not in html, html
