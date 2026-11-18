"""Strict source-boundary validator for OCP's compact 2026 XML dialect."""
from __future__ import annotations

from xml.etree import ElementTree as ET


def is_compact_source(root: ET.Element) -> bool:
    return root.tag == "book" and root.get("filename", "").endswith(".xml")


_CHILDREN = {
    "book": {"version"}, "version": {"divisions", "manuscripts", "text"},
    "divisions": {"division"}, "division": set(),
    "manuscripts": {"manuscript"}, "manuscript": set(),
    "text": {"div"}, "div": {"unit"}, "unit": {"reading"}, "reading": set(),
}
_ATTRIBUTES = {
    "book": {"filename", "title"},
    "version": {"id", "title", "lang"},
    "divisions": set(), "division": {"id", "title", "type"},
    "manuscripts": set(), "manuscript": {"id", "name"},
    "text": set(), "div": {"number"}, "unit": {"id"},
    "reading": {"option", "mss"},
}


def validate_compact_source_structure(root: ET.Element, *, source_path: str = "") -> None:
    """Fail closed on source vocabulary, identity, witnesses and alignment."""
    location = source_path or "<memory>"
    filename = root.get("filename", "")
    basename = location.replace(chr(92), "/").rsplit("/", 1)[-1]
    if source_path and filename != basename:
        raise ValueError(f"{location}: compact book filename identity {filename!r} != {basename!r}")
    if not filename.endswith(".xml") or not filename[:-4].strip():
        raise ValueError(f"{location}: invalid compact book filename")

    stack = [(root, "/book")]
    while stack:
        element, path = stack.pop()
        tag = element.tag
        if tag not in _CHILDREN:
            raise ValueError(f"{location}: unsupported compact element {tag!r} at {path}")
        missing = _ATTRIBUTES[tag] - set(element.attrib)
        extra = set(element.attrib) - _ATTRIBUTES[tag]
        if missing or extra:
            raise ValueError(
                f"{location}: compact {path} attribute mismatch: missing={sorted(missing)}, unsupported={sorted(extra)}"
            )
        if any(not value.strip() for value in element.attrib.values()):
            raise ValueError(f"{location}: blank compact attribute at {path}")
        children = list(element)
        if tag != "reading":
            if element.text and element.text.strip(" \t\r\n"):
                raise ValueError(f"{location}: unsupported compact direct text at {path}")
            if any(child.tail and child.tail.strip(" \t\r\n") for child in children):
                raise ValueError(f"{location}: unsupported compact child tail at {path}")
        elif children:
            raise ValueError(f"{location}: unsupported compact inline markup at {path}")
        for child in children:
            if child.tag not in _CHILDREN[tag]:
                raise ValueError(f"{location}: unsupported compact {child.tag!r} child of {tag} at {path}")
            stack.append((child, f"{path}/{child.tag}"))

    versions = root.findall("version")
    if len(versions) != 2:
        raise ValueError(f"{location}: compact original plus English translation required")
    source, english = versions
    if (source.get("id"), source.get("lang")) not in {("Greek", "grc"), ("Latin", "lat")}:
        raise ValueError(f"{location}: compact source version id/language mismatch")
    if (english.get("id"), english.get("lang"), english.get("title")) != (
        "English", "eng", "English Translation"
    ):
        raise ValueError(f"{location}: compact English translation id/language/title mismatch")

    signatures = []
    for version in versions:
        label = version.get("title", "")
        divisions = version.findall("divisions")
        manuscripts = version.findall("manuscripts")
        texts = version.findall("text")
        if len(divisions) != 1 or len(manuscripts) != 1 or len(texts) != 1:
            raise ValueError(f"{location}/{label}: one divisions, manuscripts and text block required")
        specs = divisions[0].findall("division")
        if len(specs) != 1 or specs[0].get("id") != "1" or specs[0].get("type") not in {"section", "fragment"}:
            raise ValueError(f"{location}/{label}: unsupported compact division id/type")
        declared = [ms.get("id") for ms in manuscripts[0].findall("manuscript")]
        if not declared or len(declared) != len(set(declared)):
            raise ValueError(f"{location}/{label}: missing/duplicate compact manuscript")
        if version is english and declared != ["Eng"]:
            raise ValueError(f"{location}/{label}: English translation requires only Eng witness")
        if version is source and "Eng" in declared:
            raise ValueError(f"{location}/{label}: source cannot claim translation witness Eng")

        seen_divs = set()
        seen_units = set()
        units = []
        for div in texts[0].findall("div"):
            number = div.get("number")
            if number in seen_divs:
                raise ValueError(f"{location}/{label}: duplicate compact div number {number!r}")
            seen_divs.add(number)
            if not div.findall("unit"):
                raise ValueError(f"{location}/{label}: empty compact div {number!r}")
            for unit in div.findall("unit"):
                uid = unit.get("id")
                if uid in seen_units:
                    raise ValueError(f"{location}/{label}: duplicate compact unit id {uid!r}")
                seen_units.add(uid)
                if not uid.startswith(number + ".") or not uid[len(number) + 1:].strip():
                    raise ValueError(f"{location}/{label}: compact unit {uid!r} conflicts with div {number!r}")
                readings = unit.findall("reading")
                if len(readings) != 1 or readings[0].get("option") != "base":
                    raise ValueError(f"{location}/{label}: one base reading required for {uid!r}")
                mss = readings[0].get("mss", "").split()
                if len(mss) != 1 or mss[0] not in declared:
                    raise ValueError(f"{location}/{label}: undeclared/ambiguous manuscript witness for {uid!r}")
                if version is english and mss != ["Eng"]:
                    raise ValueError(f"{location}/{label}: English witness must be Eng")
                units.append((number, uid))
        if not units:
            raise ValueError(f"{location}/{label}: empty compact version")
        signatures.append((
            tuple((d.get("id"), d.get("title"), d.get("type")) for d in specs),
            tuple(units),
        ))
    if signatures[0] != signatures[1]:
        raise ValueError(f"{location}: parallel English translation unit/division alignment mismatch")
