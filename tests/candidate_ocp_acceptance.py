"""Unmodified OCP 2026 checkout -> local native Text-Fabric researcher acceptance."""
from __future__ import annotations

import json
from hashlib import sha256
from html import escape
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from pseudepigrapha_tf.cli import main as cli_main
from pseudepigrapha_tf.rights_review import build_2026_rights_evidence
from tf.fabric import Fabric


UPSTREAM_SHA = "853a64b623de296d2b8532a43593607772e7c45a"
# Six compact-dialect originals and translations are now supported; the
# separately named TEI root is an explicitly reported optional morphology layer.
UNSUPPORTED_ROOT_FILES = frozenset({"ApDan_TEI.xml"})
COMPACT_ROOT_FILES = frozenset({
    "CithDavid.xml", "Demetr.xml", "Justus.xml",
    "OrMois.xml", "ThrenSeila.xml", "VisKenaz.xml",
})
CHANGED_STANDARD_FILES = frozenset({
    "3Macc.xml", "5Ezra.xml", "6Ezra.xml", "AndronAsaph.xml",
    "ApDan.xml", "ApEzra.xml", "ConfEsdr.xml", "DeAdam.xml",
    "Jub.xml", "NarrMois.xml", "OrJos.xml", "OrMan.xml",
    "Ps151.xml", "PsHecat.xml", "PsOrph.xml", "PsPhoc.xml",
    "RevEsdr.xml", "Sedrach.xml", "T12P.xml", "Thallus.xml",
    "Theoph.xml", "TracSem.xml", "VisEl.xml",
})


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, timeout=15,
    ).strip()


def verify(upstream_repo: Path) -> None:
    upstream_repo = upstream_repo.resolve()
    docs = upstream_repo / "static" / "docs"
    assert docs.is_dir(), docs
    actual_commit = _git(upstream_repo, "rev-parse", "HEAD")
    assert actual_commit == UPSTREAM_SHA, (
        f"candidate requires exact immutable OCP SHA {UPSTREAM_SHA}; got {actual_commit}"
    )
    assert not _git(upstream_repo, "status", "--porcelain=v1",
                    "--untracked-files=all", "--", "static/docs"), (
        "OCP candidate source directory has local modifications"
    )

    root_xml = sorted(docs.glob("*.xml"))
    nonempty = {path.name for path in root_xml if path.read_bytes().strip()}
    assert len(root_xml) == len(nonempty) == 67, (
        f"unexpected upstream root XML inventory: {len(root_xml)} total, "
        f"{len(nonempty)} nonempty"
    )
    assert UNSUPPORTED_ROOT_FILES <= nonempty
    assert CHANGED_STANDARD_FILES <= nonempty
    standard = sorted(nonempty - UNSUPPORTED_ROOT_FILES)
    assert len(standard) == 66, (len(standard), standard)
    assert COMPACT_ROOT_FILES <= set(standard)

    # Independent, byte-hashed 2026 rights evidence on the *entire*
    # original upstream tree; optional data-redistribution evidence is not a software release authorization.
    # This is NOT legal clearance and must not change publication status.
    rights = build_2026_rights_evidence(upstream_repo)
    assert rights["source_commit"] == UPSTREAM_SHA
    assert rights["publication_allowed"] is False
    assert rights["rights_attestation"] == "not_attested"
    counts = rights["counts"]
    assert counts["root_xml"] == 67
    assert counts["core_candidate_xml"] == 66
    assert counts["compact_editorial_english_review_required"] == 6
    assert counts["restricted_morphology_xml"] == 1
    assert counts["public_metadata_documents"] == 61
    assert counts["tei_mirror_nonempty"] > 0
    assert {name for name in standard} == {
        entry["path"].rsplit("/", 1)[-1]
        for entry in rights["root_documents"] if entry["core_candidate"]
    }

    with TemporaryDirectory(prefix="ocp-2026-standard-") as workdir:
        workdir = Path(workdir)
        # Ephemeral CI-only rights evidence. Do not include it in unrestricted
        # TF features, release manifest or any distributable archive.
        (workdir / "rights-evidence.json").write_text(
            json.dumps(rights, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        assert not (workdir / "rights-evidence.json").is_relative_to(workdir / "tf")
        tf_dir = workdir / "tf"
        # Exercise the same unmodified directory and revision passed by Agora.
        assert cli_main(["convert", str(docs), "--output", str(tf_dir),
                         "--upstream-commit", UPSTREAM_SHA]) == 0
        report = json.loads((tf_dir / "conversion-report.json").read_text())
        assert report["status"] == "ok", report["failed_checks"]
        assert report["source"]["versions"] == report["graph"]["versions"]
        assert report["source"]["readings"] == report["graph"]["readings"]
        assert report["source"]["public_metadata_documents"] == 61
        assert report["semantic_checks"]["parallel_translation_alignment"]
        assert report["source"]["public_metadata_scalars"] == report["graph"]["public_metadata_scalars"]
        assert report["source"]["files"] == 66
        assert report["provenance"]["upstream_commit"] == UPSTREAM_SHA
        assert report["provenance"]["source_identity_status"] == "verified"
        assert report["provenance"]["intros_sha256"] == sha256((docs / "intros.json").read_bytes()).hexdigest()
        excluded = report["diagnostics"]["excluded_source_layers"]
        assert {row["path"] for row in excluded} == {"ApDan_TEI.xml"} | {"tei/" + name for name in standard}
        assert all(row["sha256"] == sha256((docs / row["path"]).read_bytes()).hexdigest() for row in excluded)
        assert report["provenance"]["content_license_status"] != "verified"

        from pseudepigrapha_tf import Apparatus, Translations, WorkMetadata
        features = set(Apparatus.PASSAGE_FEATURES)
        features.update(Translations.REQUIRED_FEATURES)
        features.update({"source_format", "version_source_id", "division_source_ids", "division_source_types"})
        features.update(WorkMetadata.REQUIRED_FEATURES)
        features.update(WorkMetadata.OPTIONAL_FEATURES)
        features.update({"ocp_book", "version_id", "version_kind", "source_ref",
                         "source_file", "source_sha256", "g_word_utf8"})
        TF = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep")
        api = TF.load(" ".join(sorted(features)), silent="deep")
        assert api is not None
        assert tuple(api.T.sectionTypes) == ("book", "chapter", "verse")

        source_books: dict[str, list[str]] = {}
        for node in api.F.otype.s("book"):
            if api.F.version_kind.v(node) == "source":
                source_books.setdefault(api.F.ocp_book.v(node), []).append(
                    api.F.version_id.v(node)
                )
        assert all(name.removesuffix(".xml") in source_books for name in standard)

        # Compare the original, separately sourced clavis crosswalk to the
        # already-built TF corpus without importing catalogue prose or data.
        import csv
        from pseudepigrapha_tf.catalog import catalog_lookup
        crosswalk_path = upstream_repo / "data" / "master_crosswalk.csv"
        assert _git(upstream_repo, "hash-object", str(crosswalk_path)) == (
            "e1e4a6d651e6acf3132d2ec202004c94141516c4"
        )
        raw_crosswalk = crosswalk_path.read_bytes()
        with crosswalk_path.open(encoding="utf-8", newline="") as stream:
            raw_catalogue = list(csv.DictReader(stream))
        # Independent ground truth is literal filesystem coverage, not the
        # catalogue's declared status or the lookup implementation's index.
        expected_matched = {
            row["ocp_canon_id"] for row in raw_catalogue
            if row["ocp_xml"] in standard
        }
        expected_missing = {
            row["ocp_canon_id"] for row in raw_catalogue
            if row["ocp_xml"] and not (docs / row["ocp_xml"]).is_file()
        }
        assert len(expected_matched) == 50
        assert len(expected_missing) == 37
        catalog = catalog_lookup(api, raw_crosswalk)
        assert catalog["counts"] == {
            "catalog_records": 299, "exact_tf_match": 50,
            "declared_filename_not_in_tf": 37, "no_declared_filename": 212,
            "matched_tf_files": 49, "unmatched_tf_files": 17,
        }, catalog["counts"]
        assert catalog["redistribution_permission"] == "not_attested"
        by_id = {row["ocp_canon_id"]: row for row in catalog["records"]}
        assert {key for key, row in by_id.items()
                if row["match_status"] == "exact_tf_match"} == expected_matched
        assert {key for key, row in by_id.items()
                if row["match_status"] == "declared_filename_not_in_tf"} == expected_missing
        assert set(catalog["unmatched_tf_files"]) == set(standard) - {
            row["ocp_xml"] for row in raw_catalogue
        }
        assert by_id["CAVT-084"]["same_filename_catalog_ids"] == [
            "CAVT-084", "CAVT-JH-08",
        ]
        assert by_id["CAVT-177"]["same_filename_catalog_ids"] == [
            "CAVT-177", "CAVT-218",
        ]
        for canon_id, existing_name in (
            ("CAVT-118", "T12P.xml"), ("CAVT-148", "ThrenSeila.xml"),
            ("CAVT-152", "CithDavid.xml"), ("CAVT-181", "ConfEsdr.xml"),
            ("CAVT-185", "RevEsdr.xml"), ("CAVT-213", "LivPro.xml"),
        ):
            assert by_id[canon_id]["tf_source_versions"] == []
            assert existing_name in catalog["unmatched_tf_files"]
        for row in catalog["records"]:
            for version in row["tf_source_versions"]:
                assert version["version_id"] in source_books[version["ocp_book"]]
                assert version["source_sha256"] == sha256(
                    (docs / row["ocp_xml"]).read_bytes()
                ).hexdigest()

        metadata_api = WorkMetadata(api)
        assert metadata_api["5Ezra"]["author"] == "Pseudo-Ezra"
        assert metadata_api["5Ezra"]["editor"] == "Robert L. Bensly (1895)"
        assert metadata_api["6Ezra"]["author"] == "Pseudo-Ezra"
        A = Apparatus(api)
        passage_checks = {}
        for work in ("3Macc", "5Ezra", "6Ezra", "ApDan", "Jub", "T12P",
                     "CithDavid", "Demetr", "Justus", "OrMois", "ThrenSeila", "VisKenaz"):
            # Choose a textual source version rather than assuming the final
            # version in upstream order is textual (some are metadata-only).
            candidates = [
                (version_id, [
                    node for node in api.F.otype.s("verse")
                    if api.F.ocp_book.v(node) == work
                    and api.F.version_id.v(node) == version_id
                ])
                for version_id in source_books[work]
            ]
            assert any(verses for _, verses in candidates), (work, candidates)
            version_id, verses = next(
                (version_id, verses) for version_id, verses in candidates if verses
            )
            first_verse = verses[0]
            section = api.T.sectionFromNode(first_verse)
            assert section[0] == version_id, (work, section)
            resolved = api.T.nodeFromSection(section)
            assert resolved == first_verse, (work, section, resolved)
            assert api.T.text(first_verse).strip(), (work, section)
            assert api.F.source_ref.v(first_verse), (work, section)
            result = A.passage(version_id, section[1], section[2])
            assert result["units"], (work, section)
            passage_checks[work] = section

        # Real T12P has title units at testament/Title (two levels),
        # alongside ordinary testament/chapter/verse (three levels).
        # Test exact primary source refs and reachability for both forms.
        t12p = source_books["T12P"][0]
        for chapter, verse, source_ref in (
            ("Reuben", "Title", "Reuben Title"),
            ("Reuben 1", "1", "Reuben 1:1"),
        ):
            node = api.T.nodeFromSection((t12p, chapter, verse))
            assert node is not None, (t12p, chapter, verse)
            assert api.F.source_ref.v(node) == source_ref
            assert api.T.text(node).strip()
            assert A.passage(t12p, chapter, verse)["units"]
        passage_checks["T12P_shallow_title"] = (t12p, "Reuben", "Title")
        passage_checks["T12P_deep_verse"] = (t12p, "Reuben 1", "1")

        # Use the public Text-Fabric API to walk every non-generated parallel
        # English unit back to the exact original in each of the six works.
        translations = Translations(api)
        for work in ("CithDavid", "Demetr", "Justus", "OrMois", "ThrenSeila", "VisKenaz"):
            version_id, chapter, verse_id = passage_checks[work]
            source_passage = A.passage(version_id, chapter, verse_id)
            # The original XML unit/@id is the exact cited textual locus:
            # `div/@number` alone would collapse 1.1, 1.2, 1.3, etc.
            assert source_passage["source_refs"] == (verse_id,), (work, source_passage["source_refs"])
            assert all(unit["source_ref"] == verse_id for unit in source_passage["units"])
        expected_alignment_counts = {
            "CithDavid": 6, "Demetr": 27, "Justus": 7,
            "OrMois": 5, "ThrenSeila": 6, "VisKenaz": 8,
        }
        aligned_counts = {}
        for work, expected in expected_alignment_counts.items():
            versions = tuple(v for v in translations.versions(work=work)
                             if api.F.version_kind.v(v["node"]) == "parallel_translation")
            assert len(versions) == 1, (work, versions)
            record = versions[0]
            source_book = record["source_node"]
            translation_book = record["node"]
            assert api.F.version_kind.v(source_book) == "source"
            assert api.F.version_kind.v(translation_book) == "parallel_translation"
            assert api.F.version_source_id.v(translation_book) == "English"
            assert api.F.source_format.v(translation_book) == "compact"
            pairs = translations.aligned_units(translation_book)
            assert len(pairs) == expected, (work, len(pairs), expected)
            assert all(p["translation_unit_id"] == p["source_unit_id"] for p in pairs)
            assert all(p["translation_text"] and p["source_text"] for p in pairs)
            aligned_counts[work] = len(pairs)

        # Rights-isolated morphology acceptance. Read the restricted TEI
        # from exact upstream test inputs, prove each of its 2,150 words maps
        # to an existing Greek source slot, and serialize only an ephemeral
        # opt-in CC BY-NC module. Never publish as a release artifact.
        from pseudepigrapha_tf.apdan_morphology import (
            align_apdan_morphology,
            write_apdan_morphology_module,
        )
        aligned_morph = align_apdan_morphology(
            api,
            (docs / "ApDan.xml").read_bytes(),
            (docs / "ApDan_TEI.xml").read_bytes(),
        )
        assert aligned_morph.summary["verses"] == 170, aligned_morph.summary
        assert aligned_morph.summary["words"] == 2150, aligned_morph.summary
        assert aligned_morph.summary["punctuation_elements"] == 220, aligned_morph.summary
        assert aligned_morph.summary["source_declared_license"] == "CC-BY-NC-4.0"
        assert aligned_morph.summary["redistribution_permission"] == "not_attested"
        # Both files come from the pinned Git snapshot even though the
        # temporary standalone TF staging directory has no Git HEAD.
        assert aligned_morph.summary["ocp_commit"] == UPSTREAM_SHA
        assert not any((tf_dir / f"{name}.tf").exists()
                       for name in aligned_morph.features)
        overlay_dir = workdir / "restricted-cc-by-nc-apdan"
        assert write_apdan_morphology_module(
            aligned_morph, base_tf_directory=tf_dir,
            output=overlay_dir, accept_noncommercial=True,
        )
        assert all((overlay_dir / f"{name}.tf").is_file()
                   for name in aligned_morph.features)
        assert not any((tf_dir / f"{name}.tf").exists()
                       for name in aligned_morph.features)
        morph_api = Fabric(
            locations=[str(tf_dir), str(overlay_dir)], modules=[""], silent="deep",
        ).load("apdan_tei_lemma apdan_tei_pos apdan_tei_msd", silent="deep")
        assert morph_api is not None
        first_slot = min(aligned_morph.features["apdan_tei_lemma"])
        assert morph_api.F.apdan_tei_lemma.v(first_slot) == aligned_morph.features["apdan_tei_lemma"][first_slot]
        assert morph_api.F.apdan_tei_pos.v(first_slot) == aligned_morph.features["apdan_tei_pos"][first_slot]
        assert morph_api.F.apdan_tei_msd.v(first_slot) == aligned_morph.features["apdan_tei_msd"][first_slot]

        # Genuine researcher-facing browser E2E on the full *new* 66-work
        # dataset and wheel, rather than relying on the legacy 1.1 smoke.
        from pseudepigrapha_tf.web import load_local_comparison_web_app
        from pseudepigrapha_tf.release_identity import TF_DATA_VERSION
        app_dir = Path(__file__).resolve().parents[1] / "app"
        browser = load_local_comparison_web_app(
            tf_dir, app_dir, version=TF_DATA_VERSION, silent="deep",
        )
        client = browser.test_client()
        root = client.get("/")
        assert root.status_code == 200, root.get_data(as_text=True)[:700]
        landing = client.get("/compare")
        assert landing.status_code == 200
        landing_html = landing.get_data(as_text=True)
        assert '<option value="3Macc">' in landing_html
        assert all(f'<option value="{work}">' in landing_html
                   for work in expected_alignment_counts)
        stylesheet = client.get("/data/static/comparison.css")
        assert stylesheet.status_code == 200
        assert ".translation-block" in stylesheet.get_data(as_text=True)

        http_checks = {}
        for work in expected_alignment_counts:
            version_id, chapter, verse_id = passage_checks[work]
            response = client.get("/compare", query_string={
                "work": work, "chapter": chapter, "verse": verse_id,
            })
            markup = response.get_data(as_text=True)
            assert response.status_code == 200, (work, markup[:1800])
            assert f'data-version-id="{escape(version_id, quote=True)}"' in markup
            parallel = tuple(
                item for item in translations.versions(work=work)
                if api.F.version_kind.v(item["node"]) == "parallel_translation"
            )
            assert len(parallel) == 1
            translation_id = parallel[0]["id"]
            assert f'data-translation-id="{escape(translation_id, quote=True)}"' in markup
            assert f'data-version-id="{escape(translation_id, quote=True)}"' not in markup
            assert 'data-witness="Eng"' not in markup
            # No claimed generator or historical manuscript in the HTML.
            assert 'data-translation-kind="parallel_translation"' in markup
            assert "Source-declared parallel translation" in markup
            translated = translations.passage(translation_id, chapter, verse_id)
            assert translated["units"]
            translation_text = translated["units"][0]["translation_text"]
            assert escape(str(translation_text), quote=True) in markup
            selected = client.get("/compare", query_string=[
                ("work", work), ("chapter", chapter), ("verse", verse_id),
                ("version", translation_id),
            ])
            assert selected.status_code == 400
            assert "unknown source version" in selected.get_data(as_text=True)
            http_checks[work] = {
                "status": response.status_code,
                "source_id": version_id, "parallel_id": translation_id,
                "reference": f"{chapter}.{verse_id}",
            }
        for work, chapter, verse_id in (
            ("3Macc", "1", "1"), ("1En", "1", "2")
        ):
            res = client.get("/compare", query_string={
                "work": work, "chapter": chapter, "verse": verse_id,
            })
            assert res.status_code == 200, (work, res.get_data(as_text=True)[:1800])
        # Exercise a real invalid work and reject it as a safe HTTP request.
        invalid = client.get("/compare?work=not_a_real_work&chapter=1&verse=1")
        assert invalid.status_code == 400
        assert "Invalid comparison request" in invalid.get_data(as_text=True)

        print(json.dumps({
            "new_candidate_browser_e2e": http_checks,
            "apdan_morphology": aligned_morph.summary,
            "candidate_sha": UPSTREAM_SHA,
            "root_xml_nonempty": len(nonempty),
            "root_xml_converted": len(standard),
            "root_xml_excluded_for_review": sorted(UNSUPPORTED_ROOT_FILES),
            "real_tf_passages": passage_checks,
            "compact_parallel_aligned_units": aligned_counts,
            "source_counts": report["source"],
            "clavis_catalogue_counts": catalog["counts"],
            "rights_evidence_counts": rights["counts"],
            "rights_review_blockers": rights["review_blockers"],
            "rights_attestation": rights["rights_attestation"],
            "publication_allowed": rights["publication_allowed"],
        }, ensure_ascii=False, default=str))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: candidate_ocp_acceptance.py /path/to/ocp")
    verify(Path(sys.argv[1]))
