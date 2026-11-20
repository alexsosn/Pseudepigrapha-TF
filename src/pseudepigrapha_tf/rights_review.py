"""Evidence inventory for the unreleased, rights-unattested OCP 2026 snapshot.

This describes source *claims*, identities and unresolved edition rights. It
does not license the XML, grant redistribution permission, or replace the
existing verified-v1.1 distribution gate.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from .compact_structure import is_compact_source, validate_compact_source_structure
from .provenance import OCP_REPOSITORY
from .source import detect_git_commit, git_source_is_clean


OCP_2026_SHA = "853a64b623de296d2b8532a43593607772e7c45a"
README_BLOB = "de2ff68b3c802ef44d9f071905fcccbf8cd858ed"
LICENSE_BLOB = "da6ab6cc8f333d7e89a99812866df8f24374d47c"
HIGH_RISK_SOURCE_BLOBS = {
    "CithDavid.xml": "ceb98a1737a244b0c97ad662b4682857eb2b31da",
    "Demetr.xml": "299d91d7446febc280fba6f91d64c827662ebf5a",
    "Justus.xml": "92805094e7a6c0d2ade60d732ba9572c954275d9",
    "OrMois.xml": "90a5364962df9adb797aafd1189338fb2a6b585f",
    "ThrenSeila.xml": "2d149cd21f47337d0d177eeaa8eb94af5b1e361e",
    "VisKenaz.xml": "33b459bc757c5a3c2516b403d43b91e96cdae6d8",
    "ApDan_TEI.xml": "91fc0e55bfca832e5cf80b84846dc9f3dbea6634",
}
COMPACT_FILES = frozenset(HIGH_RISK_SOURCE_BLOBS) - {"ApDan_TEI.xml"}
RESTRICTED_TEI = "ApDan_TEI.xml"
TEI_NS = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
BY_URL = "https://creativecommons.org/licenses/by/4.0/"
BY_NC_URL = "https://creativecommons.org/licenses/by-nc/4.0/"


def _blob_sha(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _identity(filename: str, data: bytes) -> dict[str, str]:
    return {
        "path": "static/docs/" + filename,
        "sha256": sha256(data).hexdigest(),
        "git_blob_sha1": _blob_sha(data),
    }


def _xml_root(data: bytes, filename: str) -> ET.Element:
    try:
        return ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f"{filename}: invalid XML: {error}") from error


def _tei_license(root: ET.Element, filename: str) -> tuple[str, str]:
    if root.tag != TEI_NS + "TEI":
        raise ValueError(f"{filename}: TEI root namespace/identity is unsupported")
    availability = root.find(
        f"{TEI_NS}teiHeader/{TEI_NS}fileDesc/"
        f"{TEI_NS}publicationStmt/{TEI_NS}availability"
    )
    if availability is None:
        raise ValueError(f"{filename}: missing explicit TEI availability/license")
    licenses = availability.findall(TEI_NS + "licence")
    if len(licenses) != 1:
        raise ValueError(f"{filename}: requires exactly one TEI license declaration")
    target = licenses[0].get("target")
    status = availability.get("status", "")
    license_label = "".join(licenses[0].itertext())
    if target == BY_NC_URL and "BY-NC 4.0" in license_label and status == "restricted":
        return "CC-BY-NC-4.0", status
    if target == BY_URL and "BY 4.0" in license_label and status == "free":
        return "CC-BY-4.0", status
    raise ValueError(
        f"{filename}: unknown or inconsistent TEI license/availability claim "
        "(expected a matching free CC BY or restricted CC BY-NC declaration)"
    )


def classify_root_document(
    filename: str,
    data: bytes,
    metadata_record: dict[str, object] | None,
) -> dict[str, object]:
    """Classify one OCP root XML with evidence, not invented release clearance."""
    if not data.strip():
        raise ValueError(f"{filename}: empty root source cannot be attested")
    result: dict[str, object] = _identity(filename, data)
    root = _xml_root(data, filename)

    if filename == RESTRICTED_TEI:
        license_code, availability = _tei_license(root, filename)
        if (
            root.get(XML_ID) != "ApDan"
            or license_code != "CC-BY-NC-4.0"
            or availability != "restricted"
        ):
            raise ValueError(f"{filename}: restricted ApDan TEI identity/license mismatch")
        result.update(
            source_kind="restricted_tei_morphology",
            core_candidate=False,
            source_declared_license=license_code,
            source_declared_availability=availability,
            rights_review_required=True,
            word_annotations=len(tuple(root.iter(TEI_NS + "w"))),
            verse_annotations=len(tuple(root.iter(TEI_NS + "ab"))),
        )
        return result

    if root.tag != "book":
        raise ValueError(f"{filename}: unsupported source root/identity, expected Grammateus book")

    if filename in COMPACT_FILES:
        if not is_compact_source(root):
            raise ValueError(f"{filename}: expected compact source identity")
        validate_compact_source_structure(root, source_path=filename)
        if not isinstance(metadata_record, dict):
            raise ValueError(f"{filename}: missing public metadata for compact English source")
        fields = metadata_record.get("fields")
        if not isinstance(fields, dict) or "English translation" not in str(fields.get("status", "")):
            raise ValueError(f"{filename}: missing explicit English translation status in public metadata")
        versions = root.findall("version")
        version_ids = [version.get("id", "") for version in versions]
        if version_ids not in (["Greek", "English"], ["Latin", "English"]):
            raise ValueError(f"{filename}: unsupported source/English version identities")
        result.update(
            source_kind="compact_parallel_english",
            core_candidate=True,
            version_ids=version_ids,
            translation_credit="not_declared",
            per_work_copyright_field=("present" if "copyright" in fields else "absent"),
            rights_review_required=True,
        )
        return result

    if is_compact_source(root):
        raise ValueError(f"{filename}: unreviewed compact original/English edition")
    if root.get("filename") != filename.removesuffix(".xml"):
        raise ValueError(f"{filename}: unsupported Grammateus root filename identity")
    result.update(
        source_kind="grammateus_text",
        core_candidate=True,
        # A repository-level declaration is recorded separately and cannot
        # independently clear edition-specific rights for this new snapshot.
        rights_review_required=True,
    )
    return result


def classify_tei_mirror(filename: str, data: bytes) -> dict[str, object]:
    """A claimed conversion is not an independent source edition."""
    root = _xml_root(data, "tei/" + filename)
    license_code, status = _tei_license(root, "tei/" + filename)
    conversion_resps = tuple(
        "".join(node.itertext()).strip()
        for node in root.findall(
            f"{TEI_NS}teiHeader/{TEI_NS}fileDesc/{TEI_NS}titleStmt/"
            f"{TEI_NS}respStmt/{TEI_NS}resp"
        )
    )
    if (
        "TEI P5 conversion from OCP Grammateus XML" not in conversion_resps
        or license_code != "CC-BY-4.0"
        or status != "free"
    ):
        raise ValueError(f"tei/{filename}: unreviewed TEI mirror conversion/license claim")
    return {
        **_identity("tei/" + filename, data),
        "source_kind": "derived_grammateus_tei_mirror",
        "core_candidate": False,
        "source_declared_license": license_code,
        "source_declared_availability": status,
        "rights_review_required": False,
    }


def _reviewed_file(root: Path, name: str, expected_blob: str) -> bytes:
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{name}: missing or symlinked reviewed source/license file")
    data = path.read_bytes()
    if _blob_sha(data) != expected_blob:
        raise ValueError(f"{name}: reviewed source/license Git blob SHA differs from OCP 2026")
    return data


def build_2026_rights_evidence(upstream_root: str | Path) -> dict[str, object]:
    """Attest the exact clean Git source and audit the input byte inventory.

    The result must *never* be interpreted as redistribution permission.
    Reviewed file hashes and source Git identity are checked independently of
    the source-declared copyright claims.
    """
    root = Path(upstream_root)
    docs = root / "static" / "docs"
    if not docs.is_dir():
        raise ValueError(f"missing OCP source directory: {docs}")
    # Do not assign the pinned Git SHA to arbitrary bytes supplied from a
    # lookalike directory. Check identity and even ignored/index-hidden changes,
    # using the same conservative source attestation already used by convert.
    if detect_git_commit(docs) != OCP_2026_SHA or not git_source_is_clean(docs):
        raise ValueError("OCP 2026 rights evidence requires an exact clean source Git checkout")
    readme = _reviewed_file(root, "README.md", README_BLOB)
    _reviewed_file(root, "LICENSE.CC-BY-4.0", LICENSE_BLOB)
    if "Text editions and TEI XML files" not in readme.decode("utf-8"):
        raise ValueError("OCP README source-wide CC BY license claim missing")

    metadata_path = docs / "intros.json"
    if metadata_path.is_symlink() or not metadata_path.is_file():
        raise ValueError("missing public intros.json metadata")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    public_docs = metadata.get("documents") if isinstance(metadata, dict) else None
    if not isinstance(public_docs, dict) or len(public_docs) != 61:
        raise ValueError("unexpected OCP 2026 public metadata document inventory")

    root_files = sorted(docs.glob("*.xml"))
    if len(root_files) != 67 or any(p.is_symlink() or not p.read_bytes().strip() for p in root_files):
        raise ValueError("expected 67 nonempty, unsymlinked OCP 2026 root source files")
    if not COMPACT_FILES <= {p.name for p in root_files} or RESTRICTED_TEI not in {p.name for p in root_files}:
        raise ValueError("reviewed compact/restricted source inventory is incomplete")

    entries: list[dict[str, object]] = []
    for path in root_files:
        payload = path.read_bytes()
        expected_blob = HIGH_RISK_SOURCE_BLOBS.get(path.name)
        if expected_blob and _blob_sha(payload) != expected_blob:
            raise ValueError(f"{path.name}: source Git blob does not match reviewed OCP 2026")
        entries.append(classify_root_document(path.name, payload, public_docs.get(path.name)))

    mirrors: list[dict[str, object]] = []
    mirror_dir = docs / "tei"
    if not mirror_dir.is_dir() or mirror_dir.is_symlink():
        raise ValueError("missing OCP TEI mirror source directory")
    for path in sorted(mirror_dir.glob("*.xml")):
        if path.is_symlink():
            raise ValueError(f"tei/{path.name}: symlinked unreviewed XML")
        payload = path.read_bytes()
        if not payload.strip():
            mirrors.append({
                **_identity("tei/" + path.name, payload),
                "source_kind": "empty_tei_placeholder",
                "core_candidate": False,
            })
            continue
        if not (docs / path.name).is_file():
            raise ValueError(f"tei/{path.name}: mirror has no root source XML")
        mirrors.append(classify_tei_mirror(path.name, payload))

    compact = [r for r in entries if r["source_kind"] == "compact_parallel_english"]
    restricted = [r for r in entries if r["source_kind"] == "restricted_tei_morphology"]
    converted = [r for r in entries if r["core_candidate"]]
    if len(compact) != 6 or len(restricted) != 1 or len(converted) != 66:
        raise ValueError("2026 candidate source inclusion/translation rights classification changed")
    if any(r["per_work_copyright_field"] != "absent" for r in compact):
        # New rights assertions need a new researcher review instead of
        # silently flipping the publication gate.
        raise ValueError("new individual copyright declaration needs independent translation rights review")
    if restricted[0]["verse_annotations"] != 170 or restricted[0]["word_annotations"] != 2150:
        raise ValueError("reviewed ApDan TEI restriction/annotation inventory changed")
    if len([r for r in mirrors if r["source_kind"] == "derived_grammateus_tei_mirror"]) == 0:
        raise ValueError("no reviewed derived TEI mirrors found")
    return {
        "source_repository": OCP_REPOSITORY,
        "source_commit": OCP_2026_SHA,
        "source_claim": {
            "license": "CC-BY-4.0",
            "scope": "repository-wide text/TEI statement, not independently cleared editions",
            "readme_git_blob_sha1": README_BLOB,
            "license_git_blob_sha1": LICENSE_BLOB,
        },
        "rights_attestation": "not_attested",
        "publication_allowed": False,
        "root_documents": entries,
        "tei_mirrors": mirrors,
        "counts": {
            "root_xml": len(entries),
            "core_candidate_xml": len(converted),
            "compact_editorial_english_review_required": len(compact),
            "restricted_morphology_xml": len(restricted),
            "tei_mirror_xml": len(mirrors),
            "tei_mirror_nonempty": sum(
                r["source_kind"] == "derived_grammateus_tei_mirror" for r in mirrors
            ),
            "public_metadata_documents": len(public_docs),
        },
        "review_blockers": [
            "independent contributor/English translation rights not attested for six editions",
            "separately restricted CC BY-NC ApDan morphology must not enter unrestricted core",
            "full 2026 source and edition licensing requires owner review before publication",
        ],
    }
