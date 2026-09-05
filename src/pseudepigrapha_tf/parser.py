from __future__ import annotations

import hashlib
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from .model import Book, Div, DivisionSpec, Ellipsis, Manuscript, OrphanReading, Reading, Resource, Token, Unit, Version
from .source_structure import SourceStructureError, validate_source_structure

ETHIOPIC_SEPARATORS = frozenset("፡።፣፤፥፦፧፨")


class SourceError(ValueError):
    """Base class for source XML failures."""


class EmptySourceError(SourceError):
    """Raised when an XML source file is empty."""


class InvalidSourceError(SourceError):
    """Raised when an XML source is not parseable as an OCP book."""


def _plain_text(element: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(element.itertext()).replace("\u200b", "")).strip()


def _inner_xml(element: ET.Element) -> str:
    chunks = [escape(element.text or "")]
    chunks.extend(ET.tostring(child, encoding="unicode") for child in list(element))
    return "".join(chunks).strip()


def _is_separator(char: str) -> bool:
    return char.isspace() or char == "\u200b" or char in ETHIOPIC_SEPARATORS


def _append_raw_segment(tokens: list[Token], segment: str | None, pending_prefix: list[str]) -> None:
    if not segment:
        return
    start = 0
    state_sep = _is_separator(segment[0])
    for i in range(1, len(segment) + 1):
        boundary = i == len(segment) or _is_separator(segment[i]) != state_sep
        if not boundary:
            continue
        part = segment[start:i]
        if state_sep:
            part = re.sub(r"\s+", " ", part.replace("\u200b", ""))
            if tokens:
                tokens[-1].trailer += part
            else:
                pending_prefix.append(part)
        else:
            tokens.append(Token(text=part, prefix="".join(pending_prefix)))
            pending_prefix.clear()
        if i < len(segment):
            start = i
            state_sep = not state_sep


def _tokens(reading: ET.Element) -> tuple[Token, ...]:
    tokens: list[Token] = []
    pending_prefix: list[str] = []
    _append_raw_segment(tokens, reading.text, pending_prefix)
    for child in list(reading):
        if child.tag != "w":
            _append_raw_segment(tokens, "".join(child.itertext()), pending_prefix)
        else:
            tokens.append(
                Token(
                    text=child.text or "",
                    prefix="".join(pending_prefix),
                    morph=child.get("morph"),
                    lex=child.get("lex"),
                    style=child.get("style"),
                    lang=child.get("lang"),
                    annotated=True,
                )
            )
            pending_prefix.clear()
        _append_raw_segment(tokens, child.tail, pending_prefix)
    tokens = [token for token in tokens if token.text != ""]
    if tokens:
        tokens[0].prefix = tokens[0].prefix.lstrip()
        tokens[-1].trailer = tokens[-1].trailer.rstrip()
    return tuple(tokens)


def _parse_reading(element: ET.Element) -> Reading:
    mss_raw = element.get("mss", "")
    return Reading(
        option=element.get("option", ""),
        witnesses=tuple(part for part in mss_raw.split() if part),
        mss_raw=mss_raw,
        linebreak=element.get("linebreak", ""),
        indent=element.get("indent", ""),
        text=_plain_text(element),
        content_xml=_inner_xml(element),
        tokens=_tokens(element),
    )


def _parse_unit(element: ET.Element) -> Unit:
    return Unit(
        unit_id=element.get("id", ""),
        group=element.get("group", "0"),
        parallel=element.get("parallel", ""),
        linebreak=element.get("linebreak", ""),
        readings=tuple(_parse_reading(r) for r in element.findall("reading")),
    )


def _parse_div(element: ET.Element) -> Div:
    items = []
    for child in list(element):
        if child.tag == "div":
            items.append(_parse_div(child))
        elif child.tag == "unit":
            items.append(_parse_unit(child))
        elif child.tag == "elipsis":
            items.append(Ellipsis(text=_plain_text(child)))
        elif child.tag == "reading":
            items.append(OrphanReading(reading=_parse_reading(child)))
    return Div(
        number=element.get("number", ""),
        fragment=element.get("fragment", ""),
        items=tuple(items),
    )


def _parse_manuscript(element: ET.Element) -> Manuscript:
    name_el = element.find("name")
    bibliography = element.findall("bibliography")
    return Manuscript(
        abbrev=element.get("abbrev", ""),
        language=element.get("language", ""),
        show=element.get("show", ""),
        name=_plain_text(name_el) if name_el is not None else "",
        name_xml=_inner_xml(name_el) if name_el is not None else "",
        bibliography=tuple(_plain_text(b) for b in bibliography),
        bibliography_xml=tuple(_inner_xml(b) for b in bibliography),
    )


def _parse_resource(element: ET.Element) -> Resource:
    return Resource(
        name=element.get("name", ""),
        info=tuple(_plain_text(i) for i in element.findall("info")),
        url=_plain_text(element.find("URL")) if element.find("URL") is not None else "",
    )


def _division_delimiter(element: ET.Element) -> str:
    """Normalize the two delimiter spellings present in pinned OCP XML."""

    return element.get("delimiter", element.get("Delimiter", ""))


def _parse_version(element: ET.Element) -> Version:
    divisions_el = element.find("divisions")
    manuscripts_el = element.find("manuscripts")
    text_el = element.find("text")
    if divisions_el is None or manuscripts_el is None or text_el is None:
        raise InvalidSourceError(f"version {element.get('title', '')!r} is missing divisions, manuscripts, or text")
    resources: list[Resource] = []
    for resources_el in element.findall("resources"):
        resources.extend(_parse_resource(r) for r in resources_el.findall("resource"))
    return Version(
        title=element.get("title", ""),
        author=element.get("author", ""),
        language=element.get("language", ""),
        fragment=element.get("fragment", ""),
        divisions=tuple(
            DivisionSpec(d.get("label", ""), _division_delimiter(d), _plain_text(d))
            for d in divisions_el.findall("division")
        ),
        resources=tuple(resources),
        manuscripts=tuple(_parse_manuscript(ms) for ms in manuscripts_el.findall("ms")),
        divs=tuple(_parse_div(d) for d in text_el.findall("div")),
    )


def _parse_legacy_version(root: ET.Element) -> Version:
    manuscripts_el = root.find("manuscripts")
    text_el = root.find("text")
    if manuscripts_el is None or text_el is None:
        raise InvalidSourceError("legacy book is missing manuscripts or text")
    resources: list[Resource] = []
    for resources_el in root.findall("resources"):
        resources.extend(_parse_resource(r) for r in resources_el.findall("resource"))
    chapter_divs: list[Div] = []
    for chapter in text_el.findall("chapter"):
        verse_divs: list[Div] = []
        for verse in chapter.findall("verse"):
            verse_divs.append(
                Div(
                    number=verse.get("reference", ""),
                    fragment=verse.get("fragment", ""),
                    items=tuple(_parse_unit(u) for u in verse.findall("unit")),
                )
            )
        chapter_divs.append(
            Div(
                number=chapter.get("number", ""),
                fragment=chapter.get("fragment", ""),
                items=tuple(verse_divs),
            )
        )
    language = root.get("language", "")
    return Version(
        title=language or "Default",
        author="",
        language=language,
        fragment="",
        divisions=(DivisionSpec("Chapter", ":"), DivisionSpec("Verse", "")),
        resources=tuple(resources),
        manuscripts=tuple(_parse_manuscript(ms) for ms in manuscripts_el.findall("ms")),
        divs=tuple(chapter_divs),
    )


def parse_bytes(data: bytes, *, source_path: str = "") -> Book:
    if not data.strip():
        raise EmptySourceError(f"empty XML source: {source_path or '<memory>'}")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise InvalidSourceError(f"cannot parse {source_path or '<memory>'}: {exc}") from exc
    if root.tag != "book":
        raise InvalidSourceError(f"expected <book> root in {source_path or '<memory>'}, found <{root.tag}>")

    source_sha256 = hashlib.sha256(data).hexdigest()
    has_versions = bool(root.findall("version"))
    is_legacy = not has_versions and root.find("text/chapter") is not None
    try:
        validate_source_structure(
            root,
            legacy=is_legacy,
            source_path=source_path,
            source_sha256=source_sha256,
        )
    except SourceStructureError as exc:
        raise InvalidSourceError(str(exc)) from exc

    versions = tuple(_parse_version(v) for v in root.findall("version"))
    if not versions and is_legacy:
        versions = (_parse_legacy_version(root),)
    if not versions:
        raise InvalidSourceError(f"book has no supported text structure: {source_path or '<memory>'}")
    return Book(
        filename=root.get("filename", ""),
        title=root.get("title", ""),
        text_structure=root.get("textStructure", ""),
        versions=versions,
        source_path=source_path,
        source_sha256=source_sha256,
    )


def parse_file(path: str | Path) -> Book:
    source = Path(path)
    return parse_bytes(source.read_bytes(), source_path=str(source))
