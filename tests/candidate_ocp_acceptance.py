"""Real OCP 2026 candidate -> native Text-Fabric researcher acceptance.

This is an intentionally partial *staging* corpus: the full upstream snapshot
contains seven root files needing separately reviewed format/identity handling.
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
# Six root documents use a distinct compact <manuscript> dialect. One file
# is namespaced TEI, an alternate representation of the root ApDan source.
# No source is silently excluded from *production* conversion by this test.
UNSUPPORTED_ROOT_FILES = frozenset({
    "ApDan_TEI.xml",
    "CithDavid.xml",
    "Demetr.xml",
    "Justus.xml",
    "OrMois.xml",
    "ThrenSeila.xml",
    "VisKenaz.xml",
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
    assert len(standard) == 60, (len(standard), standard)

    with TemporaryDirectory(prefix="ocp-2026-standard-") as workdir:
        workdir = Path(workdir)
        staged_docs = workdir / "docs"
        tf_dir = workdir / "tf"
        staged_docs.mkdir()
        for filename in standard:
            shutil.copyfile(docs / filename, staged_docs / filename)
        # Reuse the same public metadata input as a normal converter build.
        shutil.copyfile(docs / "intros.json", staged_docs / "intros.json")

        assert cli_main(["convert", str(staged_docs), "--output", str(tf_dir)]) == 0
        report = json.loads((tf_dir / "conversion-report.json").read_text())
        assert report["status"] == "ok", report["failed_checks"]
        assert report["source"]["versions"] == report["graph"]["versions"]
        assert report["source"]["readings"] == report["graph"]["readings"]
        # Assembled in a temporary directory, not an attested full OCP checkout.
        assert report["provenance"]["source_identity_status"] != "verified"
        assert report["provenance"]["content_license_status"] != "verified"

        from pseudepigrapha_tf import Apparatus
        features = set(Apparatus.PASSAGE_FEATURES)
        features.update({"ocp_book", "version_id", "version_kind", "source_ref"})
        TF = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep")
        api = TF.load(" ".join(sorted(features)), silent="deep")
        assert api is not None
        assert tuple(api.T.sectionTypes) == ("book", "chapter", "verse")

        source_books = {
            api.F.ocp_book.v(node): api.F.version_id.v(node)
            for node in api.F.otype.s("book")
            if api.F.version_kind.v(node) == "source"
        }
        assert all(name.removesuffix(".xml") in source_books for name in standard)
        A = Apparatus(api)
        passage_checks = {}
        for work in ("3Macc", "5Ezra", "6Ezra", "ApDan", "Jub", "T12P"):
            version_id = source_books[work]
            verses = [
                node for node in api.F.otype.s("verse")
                if api.F.ocp_book.v(node) == work
                and api.F.version_id.v(node) == version_id
            ]
            assert verses, work
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

        print(json.dumps({
            "candidate_sha": UPSTREAM_SHA,
            "root_xml_nonempty": len(nonempty),
            "root_xml_converted": len(standard),
            "root_xml_excluded_for_review": sorted(UNSUPPORTED_ROOT_FILES),
            "real_tf_passages": passage_checks,
            "source_counts": report["source"],
        }, ensure_ascii=False, default=str))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: candidate_ocp_acceptance.py /path/to/ocp")
    verify(Path(sys.argv[1]))
