from __future__ import annotations

import json
from pathlib import Path

import pytest
from tf.fabric import Fabric

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.metadata import attach_public_metadata, load_public_metadata
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.writer import write_tf


FIXTURES = Path(__file__).parent / "fixtures"
OCP_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"
OCP_PIN = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
LICENSE_COMMIT = "8c8c2c55a2c55ba4b23ac506956f98dcc25045b2"
GENERAL_CITATION = (
    "Ian W. Scott and Ken M. Penner, eds. The Online Critical Pseudepigrapha. "
    "Atlanta: Society of Biblical Literature / Online: pseudepigrapha.org."
)


def _pinned_data():
    return build_tf_data(
        [parse_file(FIXTURES / "sample.xml")],
        upstream_repository=OCP_REPOSITORY,
        upstream_commit=OCP_PIN,
    )


def _single_source(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "Sample.xml").write_bytes((FIXTURES / "sample.xml").read_bytes())
    return docs


def test_exact_supported_ocp_pin_exposes_verified_content_license_and_separate_software_licenses():
    generic = _pinned_data().metadata[""]

    assert generic["contentLicense"] == "CC-BY-4.0"
    assert generic["contentLicenseStatus"] == "verified"
    assert generic["contentLicenseScope"] == "OCP text editions and TEI XML files under static/docs/"
    assert generic["converterSoftwareLicense"] == "MIT"
    assert generic["upstreamSoftwareLicense"] == "GPL-3.0"
    assert generic["upstreamRepository"] == OCP_REPOSITORY
    assert generic["upstreamCommit"] == OCP_PIN
    assert generic["upstreamLicenseCommit"] == LICENSE_COMMIT
    assert generic["contentCitation"] == GENERAL_CITATION
    assert "OCP" in generic["contentAttribution"]
    assert "LICENSE.CC-BY-4.0" in generic["contentLicenseSource"]
    assert OCP_PIN in generic["contentLicenseSource"]


def test_non_pinned_source_remains_convertible_but_cannot_inherit_verified_cc_by_claim():
    data = build_tf_data(
        [parse_file(FIXTURES / "sample.xml")],
        upstream_repository=OCP_REPOSITORY,
        upstream_commit="deadbeef",
    )
    generic = data.metadata[""]

    assert generic["upstreamCommit"] == "deadbeef"
    assert generic["contentLicenseStatus"] == "unverified"
    assert "contentLicense" not in generic
    assert "contentLicenseScope" not in generic
    assert "upstreamLicenseCommit" not in generic
    assert "deadbeef" in generic["contentLicenseDiagnostic"]


def test_conversion_report_mirrors_verified_graph_provenance(tmp_path: Path):
    docs = _single_source(tmp_path)
    books, _ = load_source_directory(docs)
    data = build_tf_data(
        books,
        upstream_repository=OCP_REPOSITORY,
        upstream_commit=OCP_PIN,
    )

    report = build_conversion_report(docs, books, data)
    provenance = report["provenance"]

    assert report["semantic_checks"]["corpus_license_provenance"] is True
    assert provenance["upstream_repository"] == OCP_REPOSITORY
    assert provenance["upstream_commit"] == OCP_PIN
    assert provenance["content_license"] == data.metadata[""]["contentLicense"]
    assert provenance["content_license_status"] == "verified"
    assert provenance["content_license_scope"] == data.metadata[""]["contentLicenseScope"]
    assert provenance["converter_software_license"] == "MIT"
    assert provenance["upstream_software_license"] == "GPL-3.0"
    assert provenance["upstream_license_commit"] == LICENSE_COMMIT
    assert provenance["content_citation"] == GENERAL_CITATION


def test_semantic_audit_rejects_contradictory_verified_license_source_tuple(tmp_path: Path):
    docs = _single_source(tmp_path)
    books, _ = load_source_directory(docs)
    data = build_tf_data(
        books,
        upstream_repository=OCP_REPOSITORY,
        upstream_commit=OCP_PIN,
    )

    data.metadata[""]["upstreamCommit"] = "different-source"
    report = build_conversion_report(docs, books, data)

    assert report["status"] == "failed"
    assert report["semantic_checks"]["corpus_license_provenance"] is False
    assert "corpus_license_provenance" in report["failed_checks"]


def test_generic_license_provenance_survives_real_text_fabric_reload(tmp_path: Path):
    data = _pinned_data()
    output = tmp_path / "tf"
    assert write_tf(data, output)

    fabric = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = fabric.load("otype", silent="deep")
    assert api is not False and not isinstance(api, bool)

    # Text-Fabric applies generic metadata to serialized features. Read it back
    # from a mandatory loaded feature instead of inspecting the pre-save object.
    generic = api.TF.features["otype"].metaData
    assert generic["contentLicense"] == "CC-BY-4.0"
    assert generic["contentLicenseStatus"] == "verified"
    assert generic["converterSoftwareLicense"] == "MIT"
    assert generic["upstreamCommit"] == OCP_PIN
    assert generic["upstreamLicenseCommit"] == LICENSE_COMMIT
    assert generic["contentCitation"] == GENERAL_CITATION


def test_corpus_license_metadata_coexists_with_lossless_per_work_attribution(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    xml = (FIXTURES / "sample.xml").read_text(encoding="utf-8")
    (docs / "Sample.xml").write_text(xml, encoding="utf-8")
    citation = '<p>Cite <em>Sample</em> exactly.</p>'
    copyright_value = "<p>Individual edition copyright statement.</p>"
    (docs / "intros.json").write_text(
        json.dumps(
            {
                "_meta": {"exported": "2026-09-05"},
                "documents": {
                    "Sample.xml": {
                        "title": "Sample",
                        "version": 1.0,
                        "citation": citation,
                        "fields": {"copyright": copyright_value},
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    books, _ = load_source_directory(docs)
    data = build_tf_data(
        books,
        upstream_repository=OCP_REPOSITORY,
        upstream_commit=OCP_PIN,
    )
    attach_public_metadata(data, load_public_metadata(docs))

    node = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "document_metadata"
    )
    assert data.metadata[""]["contentLicense"] == "CC-BY-4.0"
    assert json.loads(data.node_features["intro_citation_json"][node]) == citation
    assert json.loads(data.node_features["intro_copyright_json"][node]) == copyright_value
