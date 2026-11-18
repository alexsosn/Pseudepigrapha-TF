"""Real OCP 2026 candidate -> native Text-Fabric researcher acceptance.

This is an intentionally partial *staging* corpus: the full upstream snapshot
contains one namespaced TEI root file needing separate source-equivalence review.
No published data version or general converter exclusion is implied.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from pseudepigrapha_tf.cli import main as cli_main
from tf.fabric import Fabric


UPSTREAM_SHA = "853a64b623de296d2b8532a43593607772e7c45a"
# Six compact-dialect originals and translations are now supported; the
# separately named TEI root remains outside this format-bound staging test.
# No source is silently excluded from *production* conversion by this test.
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

    with TemporaryDirectory(prefix="ocp-2026-standard-") as workdir:
        workdir = Path(workdir)
        staged_docs = workdir / "docs"
        tf_dir = workdir / "tf"
        staged_docs.mkdir()
        for filename in standard:
            shutil.copyfile(docs / filename, staged_docs / filename)
        # The source includes 61 metadata records, now including all six
        # compact works. Staging excludes only separate ApDan_TEI.xml.
        original_intros = json.loads((docs / "intros.json").read_text(encoding="utf-8"))
        metadata = original_intros["documents"]
        assert len(metadata) == 61, len(metadata)
        assert set(metadata) <= nonempty
        staged_metadata = {name: value for name, value in metadata.items() if name in standard}
        excluded_metadata = set(metadata) - set(staged_metadata)
        assert not excluded_metadata, excluded_metadata
        assert len(staged_metadata) == 61, len(staged_metadata)
        staged_intros = dict(original_intros)
        staged_intros["documents"] = staged_metadata
        (staged_docs / "intros.json").write_text(
            json.dumps(staged_intros, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        assert cli_main(["convert", str(staged_docs), "--output", str(tf_dir)]) == 0
        report = json.loads((tf_dir / "conversion-report.json").read_text())
        assert report["status"] == "ok", report["failed_checks"]
        assert report["source"]["versions"] == report["graph"]["versions"]
        assert report["source"]["readings"] == report["graph"]["readings"]
        assert report["source"]["public_metadata_documents"] == 61
        assert report["semantic_checks"]["parallel_translation_alignment"]
        assert report["source"]["public_metadata_scalars"] == report["graph"]["public_metadata_scalars"]
        # Assembled in a temporary directory, not an attested full OCP checkout.
        assert report["provenance"]["source_identity_status"] != "verified"
        assert report["provenance"]["content_license_status"] != "verified"

        from pseudepigrapha_tf import Apparatus, Translations, WorkMetadata
        features = set(Apparatus.PASSAGE_FEATURES)
        features.update(Translations.REQUIRED_FEATURES)
        features.update({"source_format", "version_source_id", "division_source_ids", "division_source_types"})
        features.update(WorkMetadata.REQUIRED_FEATURES)
        features.update(WorkMetadata.OPTIONAL_FEATURES)
        features.update({"ocp_book", "version_id", "version_kind", "source_ref"})
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

        print(json.dumps({
            "candidate_sha": UPSTREAM_SHA,
            "root_xml_nonempty": len(nonempty),
            "root_xml_converted": len(standard),
            "root_xml_excluded_for_review": sorted(UNSUPPORTED_ROOT_FILES),
            "real_tf_passages": passage_checks,
            "compact_parallel_aligned_units": aligned_counts,
            "source_counts": report["source"],
        }, ensure_ascii=False, default=str))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: candidate_ocp_acceptance.py /path/to/ocp")
    verify(Path(sys.argv[1]))
