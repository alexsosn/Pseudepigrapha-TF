from __future__ import annotations

from xml.etree import ElementTree as ET


class SourceStructureError(ValueError):
    """Raised when a well-formed XML tree contains unsupported source structure."""


MODERN_CHILDREN: dict[str, frozenset[str]] = {
    "book": frozenset({"version"}),
    "version": frozenset({"divisions", "resources", "manuscripts", "text"}),
    "divisions": frozenset({"division"}),
    "division": frozenset(),
    "resources": frozenset({"resource"}),
    "resource": frozenset({"info", "URL"}),
    "info": frozenset(),
    "URL": frozenset(),
    "manuscripts": frozenset({"ms"}),
    "ms": frozenset({"name", "bibliography"}),
    "name": frozenset({"sup"}),
    "sup": frozenset(),
    "bibliography": frozenset({"booktitle"}),
    "booktitle": frozenset(),
    "text": frozenset({"div"}),
    # Pinned OCP has two known deviations from the shared DTD. Aristob.xml
    # declares <elipsis> in an embedded DTD; PssSol.xml contains direct <reading>
    # children of <div> despite its embedded DTD. Both are preserved explicitly.
    "div": frozenset({"div", "unit", "elipsis", "reading"}),
    "elipsis": frozenset(),
    "unit": frozenset({"reading"}),
    "reading": frozenset({"w"}),
    "w": frozenset(),
}

LEGACY_CHILDREN: dict[str, frozenset[str]] = {
    "book": frozenset({"resources", "manuscripts", "text"}),
    "resources": frozenset({"resource"}),
    "resource": frozenset({"info", "URL"}),
    "info": frozenset(),
    "URL": frozenset(),
    "manuscripts": frozenset({"ms"}),
    "ms": frozenset({"name", "bibliography"}),
    "name": frozenset({"sup"}),
    "sup": frozenset(),
    "bibliography": frozenset({"booktitle"}),
    "booktitle": frozenset(),
    "text": frozenset({"chapter"}),
    "chapter": frozenset({"verse"}),
    "verse": frozenset({"unit"}),
    "unit": frozenset({"reading"}),
    "reading": frozenset({"w"}),
    "w": frozenset(),
}

# ``None`` means arbitrary attributes are safe because the complete element is
# already retained inside an independently audited mixed-XML feature. For all
# other elements, accepting an unlisted attribute would silently discard it.
MODERN_ATTRIBUTES: dict[str, frozenset[str] | None] = {
    "book": frozenset({"filename", "title", "textStructure"}),
    "version": frozenset({"title", "author", "fragment", "language"}),
    "divisions": frozenset(),
    # ApocrEzek.xml in the pinned corpus uses capitalized Delimiter in several
    # later versions. Parser and raw audit normalize either spelling to the same
    # semantic delimiter field. Simultaneous use is rejected below as ambiguous.
    "division": frozenset({"label", "delimiter", "Delimiter"}),
    "resources": frozenset(),
    "resource": frozenset({"name"}),
    "info": frozenset(),
    "URL": frozenset(),
    "manuscripts": frozenset(),
    "ms": frozenset({"abbrev", "language", "show"}),
    "name": frozenset(),
    "sup": None,
    "bibliography": frozenset(),
    "booktitle": None,
    "text": frozenset(),
    "div": frozenset({"number", "fragment"}),
    "elipsis": frozenset(),
    # unit/@linebreak is a converter-supported source extension used by legacy
    # material even though it is absent from the shared modern Grammateus DTD.
    "unit": frozenset({"id", "group", "parallel", "linebreak"}),
    "reading": frozenset({"option", "mss", "linebreak", "indent"}),
    "w": None,
}

# Presence requirements copied from the pinned modern Grammateus DTD.
MODERN_REQUIRED_ATTRIBUTES: dict[str, frozenset[str]] = {
    "book": frozenset({"filename", "title"}),
    "version": frozenset({"title", "author"}),
    "division": frozenset({"label"}),
    "resource": frozenset({"name"}),
    "ms": frozenset({"abbrev", "language", "show"}),
    "div": frozenset({"number"}),
    "unit": frozenset({"id"}),
    "reading": frozenset({"option", "mss"}),
}

# These exact pinned manuscript records embed/inhabit DTDs declaring
# ms/@language #REQUIRED while omitting it in the source. Scope the exception
# to source basename + OCP book identity + version title + manuscript abbrev;
# neighboring records in the same file still obey the DTD requirement.
KNOWN_MISSING_MANUSCRIPT_LANGUAGE: frozenset[tuple[str, str, str, str]] = frozenset(
    {
        ("ClMal.xml", "ClMal", "Jewish Antiquities", "Niese"),
        ("ClMal.xml", "ClMal", "Praep. Evang.", "Mras"),
        ("Eup.xml", "Eup", "Praep. Evang. (Frag. 3)", "Mras"),
        ("Ps-Eup.xml", "Ps-Eup", "Praep. Evang. (Frag. 1)", "Mras"),
        ("Ps-Eup.xml", "Ps-Eup", "Praep. Evang. (Frag. 2)", "Mras"),
    }
)

LEGACY_ATTRIBUTES: dict[str, frozenset[str] | None] = {
    "book": frozenset({"filename", "title", "textStructure", "language"}),
    "resources": frozenset(),
    "resource": frozenset({"name"}),
    "info": frozenset(),
    "URL": frozenset(),
    "manuscripts": frozenset(),
    "ms": frozenset({"abbrev", "language", "show"}),
    "name": frozenset(),
    "sup": None,
    "bibliography": frozenset(),
    "booktitle": None,
    "text": frozenset(),
    "chapter": frozenset({"number", "fragment"}),
    "verse": frozenset({"reference", "fragment"}),
    "unit": frozenset({"id", "group", "parallel", "linebreak"}),
    "reading": frozenset({"option", "mss", "linebreak", "indent"}),
    "w": None,
}


def validate_source_structure(
    root: ET.Element,
    *,
    legacy: bool,
    source_path: str = "",
) -> None:
    """Reject source structure that cannot be mapped without ambiguity or loss.

    This is deliberately narrower than full DTD validation. It guards the
    converter's preservation boundary while leaving unrelated cardinality/order
    checks to separate validation work. Elements and attributes are each visited
    a constant number of times, so validation remains linear in source size.
    """

    allowed_children = LEGACY_CHILDREN if legacy else MODERN_CHILDREN
    allowed_attributes = LEGACY_ATTRIBUTES if legacy else MODERN_ATTRIBUTES
    location = source_path or "<memory>"
    source_name = source_path.replace("\\", "/").rsplit("/", 1)[-1] if source_path else ""
    book_filename = root.attrib.get("filename", "")

    # Carry the containing version title through the iterative traversal so
    # record-specific exceptions remain linear and do not require ancestor scans.
    stack: list[tuple[ET.Element, str, str]] = [(root, f"/{root.tag}", "")]
    while stack:
        parent, path, version_title = stack.pop()
        if parent.tag == "version":
            version_title = parent.attrib.get("title", "")

        allowed = allowed_children.get(parent.tag)
        if allowed is None:
            raise SourceStructureError(
                f"{location}: unsupported <{parent.tag}> element at {path}"
            )

        if not legacy:
            required = MODERN_REQUIRED_ATTRIBUTES.get(parent.tag, frozenset())
            if parent.tag == "ms":
                manuscript_identity = (
                    source_name,
                    book_filename,
                    version_title,
                    parent.attrib.get("abbrev", ""),
                )
                if manuscript_identity in KNOWN_MISSING_MANUSCRIPT_LANGUAGE:
                    required = required - {"language"}
            for attribute in sorted(required):
                if attribute not in parent.attrib:
                    raise SourceStructureError(
                        f"{location}: missing required attribute {attribute} on <{parent.tag}> at {path}"
                    )

        if parent.tag == "manuscripts":
            seen_abbrevs: set[str] = set()
            for manuscript in parent.findall("ms"):
                abbrev = manuscript.get("abbrev", "")
                if abbrev in seen_abbrevs:
                    owner = f"version {version_title!r}" if not legacy else "legacy version"
                    raise SourceStructureError(
                        f"{location}: duplicates manuscript abbreviation {abbrev!r} in {owner} at {path}"
                    )
                seen_abbrevs.add(abbrev)

        if (
            not legacy
            and parent.tag == "division"
            and "delimiter" in parent.attrib
            and "Delimiter" in parent.attrib
        ):
            raise SourceStructureError(
                f"{location}: both delimiter and Delimiter on <division> at {path}"
            )

        attribute_policy = allowed_attributes[parent.tag]
        if attribute_policy is not None:
            for attribute in parent.attrib:
                if attribute not in attribute_policy:
                    raise SourceStructureError(
                        f"{location}: unsupported attribute {attribute} on <{parent.tag}> at {path}"
                    )

        children = list(parent)
        for child in children:
            if child.tag not in allowed:
                raise SourceStructureError(
                    f"{location}: unsupported <{child.tag}> child of <{parent.tag}> at {path}"
                )
        for child in reversed(children):
            stack.append((child, f"{path}/{child.tag}", version_title))
