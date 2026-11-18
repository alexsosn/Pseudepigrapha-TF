"""Verified ApDan TEI morphology as a separately licensed local TF feature module.

The ordinary converter never reads ApDan_TEI.xml. Nothing here modifies
the default CC BY corpus or asserts that its third-party linguistic data
may be redistributed. Users must explicitly opt in to write a local
CC BY-NC-restricted module after source/TF alignment has been proved.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unicodedata
from xml.etree import ElementTree as ET


TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
TEI = "{" + TEI_NS + "}"
XML_ID = "{" + XML_NS + "}id"
XML_LANG = "{" + XML_NS + "}lang"
SOURCE_LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
CANDIDATE_SHA = "853a64b623de296d2b8532a43593607772e7c45a"
CANDIDATE_SOURCE_BLOB = "5b5a82b74a767b729d0642adbb162839cec17f95"
CANDIDATE_MORPH_BLOB = "91fc0e55bfca832e5cf80b84846dc9f3dbea6634"

FEATURES = ("apdan_tei_lemma", "apdan_tei_pos", "apdan_tei_msd")


@dataclass(frozen=True)
class MorphologyAlignment:
    features: dict[str, dict[int, str]]
    summary: dict[str, str | int]


def _git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + bytes((0,))
    return hashlib.sha1(header + data).hexdigest()


def _lexical_surface(surface: str) -> str:
    """Ignore punctuation only at lexical edges, never inside Greek words."""
    text = unicodedata.normalize("NFC", surface)
    while text and not text[0].isalnum() and not unicodedata.category(text[0]).startswith("M"):
        text = text[1:]
    while text and not text[-1].isalnum() and not unicodedata.category(text[-1]).startswith("M"):
        text = text[:-1]
    return text


def _parse_source(source_xml: bytes) -> dict[str, tuple[str, ...]]:
    try:
        root = ET.fromstring(source_xml)
    except ET.ParseError as exc:
        raise ValueError(f"invalid ApDan source XML: {exc}") from exc
    if root.tag != "book" or root.get("filename") != "ApDan":
        raise ValueError("source XML identity must be book filename=ApDan")
    versions = root.findall("version")
    if len(versions) != 1 or versions[0].get("title") != "Greek":
        raise ValueError("source XML must declare one Greek ApDan version")
    text = versions[0].find("text")
    if text is None:
        raise ValueError("source XML missing text")
    inventory: dict[str, tuple[str, ...]] = {}
    for chapter in text.findall("div"):
        chapter_id = chapter.get("number", "")
        for verse in chapter.findall("div"):
            verse_id = verse.get("number", "")
            ref = f"{chapter_id}.{verse_id}"
            units = verse.findall("unit")
            if not chapter_id or not verse_id or len(units) != 1:
                raise ValueError(f"source verse {ref}: expected exactly one source unit")
            readings = units[0].findall("reading")
            if len(readings) != 1 or readings[0].get("option") != "0":
                raise ValueError(f"source verse {ref}: expected exactly one primary reading")
            words = tuple("".join(readings[0].itertext()).split())
            if not words or ref in inventory:
                raise ValueError(f"duplicate or empty source verse {ref}")
            inventory[ref] = words
    if not inventory:
        raise ValueError("ApDan source has no verses")
    return inventory


def _parse_tei(morph_tei: bytes) -> tuple[dict[str, tuple[tuple[str, str, str, str], ...]], int]:
    try:
        root = ET.fromstring(morph_tei)
    except ET.ParseError as exc:
        raise ValueError(f"invalid ApDan morphology TEI XML: {exc}") from exc
    if root.tag != TEI + "TEI" or root.get(XML_ID) != "ApDan":
        raise ValueError("TEI identity must be TEI/xml:id=ApDan")
    availability = root.find(
        f"{TEI}teiHeader/{TEI}fileDesc/{TEI}publicationStmt/{TEI}availability"
    )
    if availability is None or availability.get("status") != "restricted":
        raise ValueError("TEI requires source-declared restricted availability / CC BY-NC license")
    licenses = availability.findall(TEI + "licence")
    if (
        len(licenses) != 1
        or licenses[0].get("target") != SOURCE_LICENSE_URL
        or "BY-NC 4.0" not in "".join(licenses[0].itertext())
    ):
        raise ValueError("TEI must declare consistent CC BY-NC 4.0 license and URL")
    text = root.find(TEI + "text")
    body = text.find(TEI + "body") if text is not None else None
    if text is None or text.get(XML_LANG) != "grc" or body is None:
        raise ValueError("TEI requires a Greek text/body")
    work_divisions = body.findall(TEI + "div")
    if (
        len(work_divisions) != 1
        or work_divisions[0].get("type") != "pseudepigraphon"
        or work_divisions[0].get("n") != "ApDan"
    ):
        # A short, single-chapter fixture may omit the outer work wrapper,
        # but real source is validated against the same chapter/ab rules.
        work_divisions = [body]
    inventory: dict[str, tuple[tuple[str, str, str, str], ...]] = {}
    punctuation = 0
    chapters: set[str] = set()
    for work in work_divisions:
        for chapter in work.findall(TEI + "div"):
            number = chapter.get("n", "")
            if chapter.get("type") != "chapter" or not number or number in chapters:
                raise ValueError(f"TEI has duplicate or unexpected chapter {number!r}")
            chapters.add(number)
            for ab in chapter.findall(TEI + "ab"):
                ref = ab.get("n", "")
                if (
                    ab.get("type") != "verse"
                    or not ref.startswith(number + ".")
                    or ab.get(XML_ID) != f"ApDan.{ref}"
                    or ref in inventory
                ):
                    raise ValueError(f"TEI has duplicate or invalid verse identity {ref!r}")
                words: list[tuple[str, str, str, str]] = []
                for child in ab:
                    if child.tag == TEI + "pc":
                        if list(child) or not (child.text or "").strip():
                            raise ValueError(f"TEI punctuation malformed at verse {ref}")
                        punctuation += 1
                    elif child.tag == TEI + "w":
                        if set(child.attrib) != {"lemma", "pos", "msd"} or list(child):
                            raise ValueError(f"TEI word missing/extra lemma,pos,msd at verse {ref}")
                        form = child.text or ""
                        lemma = child.get("lemma", "")
                        pos = child.get("pos", "")
                        msd = child.get("msd", "")
                        if not all(value.strip() for value in (form, lemma, pos, msd)):
                            raise ValueError(f"TEI word has empty surface/lemma/pos/msd at {ref}")
                        if any("\t" in value or "\n" in value or "\r" in value
                               for value in (form, lemma, pos, msd)):
                            raise ValueError(f"TEI word has unsupported whitespace in feature at {ref}")
                        words.append((form, lemma, pos, msd))
                    else:
                        raise ValueError(f"unexpected TEI element {child.tag} in verse {ref}")
                if not words:
                    raise ValueError(f"TEI verse {ref} has no words")
                inventory[ref] = tuple(words)
    if not inventory or not chapters:
        raise ValueError("TEI contains no annotated verses")
    if len(inventory) != len(list(body.iter(TEI + "ab"))):
        raise ValueError("TEI contains verse elements outside reviewed chapter structure")
    if (
        sum(len(words) for words in inventory.values()) != sum(1 for _ in root.iter(TEI + "w"))
        or punctuation != sum(1 for _ in root.iter(TEI + "pc"))
    ):
        raise ValueError("unmapped TEI word or punctuation outside reviewed verses")
    return inventory, punctuation


def _feature(api, feature: str, node: int) -> str:
    obj = getattr(api.F, feature, None)
    if obj is None:
        raise ValueError(f"native TF feature {feature!r} must be loaded")
    value = obj.v(node)
    return "" if value is None else str(value)


def align_apdan_morphology(api, source_xml: bytes, morph_tei: bytes) -> MorphologyAlignment:
    """Match raw source, TEI word inventory and loaded native TF slots exactly.

    Returns only *local* feature maps. No output is written. The raw TEI
    punctuation is counted but never substituted into the existing edition.
    """
    source_verses = _parse_source(source_xml)
    morphology, pc_count = _parse_tei(morph_tei)
    if set(source_verses) != set(morphology):
        missing = sorted(set(source_verses) - set(morphology))[:3]
        extra = sorted(set(morphology) - set(source_verses))[:3]
        raise ValueError(f"source/TEI verse mismatch: missing={missing}, extra={extra}")

    generic = api.TF.features["otype"].metaData
    commit = str(generic.get("upstreamCommit", ""))
    if commit == CANDIDATE_SHA:
        if _git_blob_sha(source_xml) != CANDIDATE_SOURCE_BLOB:
            raise ValueError("ApDan source Git blob SHA mismatches the reviewed OCP candidate")
        if _git_blob_sha(morph_tei) != CANDIDATE_MORPH_BLOB:
            raise ValueError("ApDan TEI Git blob SHA mismatches the reviewed restricted OCP candidate")

    source_sha = hashlib.sha256(source_xml).hexdigest()
    owners = [
        node for node in api.F.otype.s("book")
        if _feature(api, "ocp_book", node) == "ApDan"
        and _feature(api, "version_title", node) == "Greek"
    ]
    if len(owners) != 1:
        raise ValueError(f"expected exactly one Greek ApDan native TF book, found {len(owners)}")
    owner = owners[0]
    if (
        _feature(api, "source_file", owner) != "ApDan.xml"
        or _feature(api, "source_sha256", owner) != source_sha
        or _feature(api, "version_kind", owner) != "source"
    ):
        raise ValueError("TF ApDan source identity or sha256 does not match supplied XML")

    slots_by_ref: dict[str, list[int]] = {}
    for slot in api.F.otype.s("word"):
        if _feature(api, "ocp_book", slot) != "ApDan":
            continue
        if _feature(api, "version_title", slot) != "Greek":
            raise ValueError("other ApDan word version conflicts with morphology owner")
        ref = _feature(api, "source_ref", slot)
        slots_by_ref.setdefault(ref, []).append(slot)
    if set(slots_by_ref) != set(source_verses):
        raise ValueError("TF ApDan word verses do not match source/TEI verses")

    values = {name: {} for name in FEATURES}
    for ref, original in source_verses.items():
        candidates = slots_by_ref[ref]
        tei_words = morphology[ref]
        if len(candidates) != len(original) or len(tei_words) != len(original):
            raise ValueError(f"source/TEI/TF word count mismatch at {ref}")
        for slot, source_form, (tei_form, lemma, pos, msd) in zip(
            candidates, original, tei_words, strict=True
        ):
            tf_form = _feature(api, "g_word_utf8", slot)
            if tf_form != source_form:
                raise ValueError(f"TF word surface mismatch against source at {ref}, slot {slot}")
            if not _lexical_surface(source_form) or (
                _lexical_surface(source_form) != _lexical_surface(tei_form)
            ):
                raise ValueError(f"TEI word surface mismatch against source at {ref}, slot {slot}")
            values["apdan_tei_lemma"][slot] = lemma
            values["apdan_tei_pos"][slot] = pos
            values["apdan_tei_msd"][slot] = msd
    count = len(values["apdan_tei_lemma"])
    if any(len(v) != count for v in values.values()):
        raise ValueError("incomplete morphological feature mapping")
    return MorphologyAlignment(
        features=values,
        summary={
            "work": "ApDan",
            "verses": len(source_verses),
            "words": count,
            "punctuation_elements": pc_count,
            "source_declared_license": "CC-BY-NC-4.0",
            "source_declared_availability": "restricted",
            "redistribution_permission": "not_attested",
            "ocp_commit": commit,
            "source_xml_sha256": source_sha,
            "morph_tei_sha256": hashlib.sha256(morph_tei).hexdigest(),
        },
    )


def write_apdan_morphology_module(
    alignment: MorphologyAlignment,
    *,
    base_tf_directory: str | Path,
    output: str | Path,
    accept_noncommercial: bool,
) -> bool:
    """Locally write isolated, source-attributed TF slot features after opt-in.

    Never write into the base corpus or overwrite an existing module. The
    generated module is not licensed for unrestricted corpus redistribution.
    """
    if not accept_noncommercial:
        raise ValueError("writing a restricted CC BY-NC module requires explicit noncommercial opt-in")
    base = Path(base_tf_directory).resolve()
    destination = Path(output)
    target = destination.resolve()
    if target == base or base in target.parents:
        raise ValueError("noncommercial overlay must be separate and outside the base TF corpus")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing TEI module: {destination}")
    target.parent.mkdir(parents=True, exist_ok=True)
    from tf.fabric import Fabric

    metadata = {}
    for name, description in {
        "apdan_tei_lemma": "Source-declared Greek lemma on aligned ApDan word",
        "apdan_tei_pos": "Source-declared part of speech on aligned ApDan word",
        "apdan_tei_msd": "Source-declared morphosyntactic description on aligned ApDan word",
    }.items():
        metadata[name] = {
            "valueType": "str",
            "description": description,
            "sourceDeclaredLicense": "CC-BY-NC-4.0",
            "sourceDeclaredLicenseUrl": SOURCE_LICENSE_URL,
            "sourceDeclaredAvailability": "restricted",
            "redistributionPermission": "not_attested",
            "sourceXmlSha256": str(alignment.summary["source_xml_sha256"]),
            "morphTeiSha256": str(alignment.summary["morph_tei_sha256"]),
            "upstreamCommit": str(alignment.summary["ocp_commit"]),
            "provenanceNote": "Heiser-Penner/Lexham Press Logos LLS:8.20.7, TEI source-declared annotation",
        }
    with TemporaryDirectory(prefix=".apdan-cc-by-nc-", dir=target.parent) as scratch:
        stage = Path(scratch) / "module"
        stage.mkdir()
        fabric = Fabric(locations=[], modules=[], silent="deep")
        if not fabric.save(
            nodeFeatures=alignment.features,
            edgeFeatures={},
            metaData=metadata,
            location=str(stage),
            module="",
            silent="deep",
        ):
            raise ValueError("Text-Fabric refused noncommercial ApDan morphology module")
        if not all((stage / (name + ".tf")).is_file() for name in FEATURES):
            raise ValueError("incomplete noncommercial TF feature serialization")
        os.replace(stage, target)
    return True
