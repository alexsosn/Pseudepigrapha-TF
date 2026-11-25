"""Local clavis lookup must distinguish upstream assertions from actual TF coverage."""
from __future__ import annotations

import csv
from io import StringIO
import json
from hashlib import sha256

import pytest
from tf.fabric import Fabric

from pseudepigrapha_tf import build_tf_data
from pseudepigrapha_tf.catalog import catalog_lookup
from pseudepigrapha_tf.cli import main
from pseudepigrapha_tf.parser import parse_bytes
from pseudepigrapha_tf.writer import write_tf
from test_compact_xml import COMPACT_XML


COLUMNS = (
    "ocp_canon_id", "cavt_no", "cant_no", "standard_title", "section",
    "primary_language", "denis_ref", "ditommaso_ref", "otp_ref", "apot_ref",
    "sparks_ref", "ocp_xml", "dossier", "status", "category",
)


def row(id, filename, status="Live Edition"):
    return [
        id, "1", "CANT 1", 'Title, "quoted"', "ADAM", "Latin",
        "Denis 1", "Ch. 2", "OTP 1:1", "", "AOT 3", filename,
        "dossier.md", status, "Backbone",
    ]


def csv_bytes(rows, header=COLUMNS):
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode()


@pytest.fixture
def corpus(tmp_path):
    model = parse_bytes(COMPACT_XML.encode(), source_path="Compact.xml")
    tf_dir = tmp_path / "tf"
    assert write_tf(build_tf_data([model]), tf_dir)
    api = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep").load(
        "source_file source_sha256 ocp_book version_id version_kind", silent="deep",
    )
    assert api is not None
    return tf_dir, api


@pytest.fixture
def crosswalk():
    return csv_bytes([
        row("CAVT-001", "Compact.xml"),
        row("CAVT-JH-01", "Compact.xml", "In Progress / Staged"),
        row("CAVT-002", "compact.xml"),
        row("CAVT-003", "Comp.xml", "In Progress / Staged"),
        row("CAVT-004", "", "Gap"),
    ])


def test_catalog_exact_native_tf_join_keeps_claims_and_coverage_separate(corpus, crosswalk):
    _, api = corpus
    report = catalog_lookup(api, crosswalk)
    assert report["crosswalk_sha256"] == sha256(crosswalk).hexdigest()
    assert report["match_basis"] == "exact_source_filename_only"
    assert report["redistribution_permission"] == "not_attested"
    assert report["counts"] == {
        "catalog_records": 5, "exact_tf_match": 2,
        "declared_filename_not_in_tf": 2, "no_declared_filename": 1,
        "matched_tf_files": 1, "unmatched_tf_files": 0,
    }
    by_id = {r["ocp_canon_id"]: r for r in report["records"]}
    first = by_id["CAVT-001"]
    assert first["standard_title"] == 'Title, "quoted"'
    assert first["otp_ref"] == "OTP 1:1"
    assert first["status"] == "Live Edition"
    assert first["match_status"] == "exact_tf_match"
    assert first["same_filename_catalog_ids"] == ["CAVT-001", "CAVT-JH-01"]
    actual = [
        api.F.version_id.v(n) for n in api.F.otype.s("book")
        if api.F.version_kind.v(n) == "source"
    ]
    assert len(actual) == 1
    assert [r["version_id"] for r in first["tf_source_versions"]] == actual
    assert first["tf_source_versions"][0]["source_sha256"] == sha256(COMPACT_XML.encode()).hexdigest()
    assert by_id["CAVT-JH-01"]["status"] == "In Progress / Staged"
    for id in ("CAVT-002", "CAVT-003", "CAVT-004"):
        assert by_id[id]["tf_source_versions"] == []
    assert by_id["CAVT-002"]["match_status"] == "declared_filename_not_in_tf"
    assert by_id["CAVT-004"]["match_status"] == "no_declared_filename"
    assert report["unmatched_tf_files"] == []


def test_single_id_preserves_duplicate_claims_and_full_inventory_counts(corpus, crosswalk):
    _, api = corpus
    full = catalog_lookup(api, crosswalk)
    filtered = catalog_lookup(api, crosswalk, canon_id="CAVT-JH-01")
    assert filtered["counts"] == full["counts"]
    assert len(filtered["records"]) == 1
    assert filtered["records"][0]["same_filename_catalog_ids"] == ["CAVT-001", "CAVT-JH-01"]
    with pytest.raises(ValueError, match="unknown canonical ID"):
        catalog_lookup(api, crosswalk, canon_id="CAVT-999")


@pytest.mark.parametrize("rows, header", [
    ([row("CAVT-001", "Compact.xml"), row("CAVT-001", "Compact.xml")], COLUMNS),
    ([row("", "Compact.xml")], COLUMNS),
    ([row("CAVT-001", "../Compact.xml")], COLUMNS),
    ([row("CAVT-001", "tei/Compact.xml")], COLUMNS),
    ([row("CAVT-001", "tei\\Compact.xml")], COLUMNS),
    ([row("CAVT-001", "Compact.xml ")], COLUMNS),
    ([row("CAVT-001", "Compact.xml")[:-1]], COLUMNS),
    ([row("CAVT-001", "Compact.xml") + ["extra"]], COLUMNS),
    ([row("CAVT-001", "Compact.xml")], COLUMNS[:-1] + ("ocp_canon_id",)),
    ([], COLUMNS),
])
def test_malformed_catalog_refused(corpus, rows, header):
    _, api = corpus
    with pytest.raises(ValueError):
        catalog_lookup(api, csv_bytes(rows, header))


def test_local_cli_and_unmapped_tf(corpus, tmp_path, capsys):
    base, _ = corpus
    raw = csv_bytes([row("CAVT-001", "", "Gap")])
    path = tmp_path / "master_crosswalk.csv"
    path.write_bytes(raw)
    before = {p.name: p.read_bytes() for p in base.glob("*.tf")}
    assert main(["catalog-lookup", str(base), str(path), "--id", "CAVT-001"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["records"][0]["match_status"] == "no_declared_filename"
    assert report["unmatched_tf_files"] == ["Compact.xml"]
    assert report["counts"]["unmatched_tf_files"] == 1
    assert {p.name: p.read_bytes() for p in base.glob("*.tf")} == before
    assert path.read_bytes() == raw
