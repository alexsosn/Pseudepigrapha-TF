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

# Presence requirements copied from the pinned modern Grammateus DTD. Known
# pinned-source violations are listed separately and scoped by both exact source
# basename and OCP book identity; merely renaming another source to a known file
# must not weaken validation.
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

# Both files embed a DTD declaring ms/@language #REQUIRED but contain at least
# one manuscript declaration without it. Preserve the absence as unknown
# manuscript language; never infer it from version/@language.
MODERN_REQUIRED_ATTRIBUTE_EXCEPTIONS: dict[
    tuple[str, str], dict[str, frozenset[str]]
] = {
    ("ClMal.xml", "ClMal"): {"ms": frozenset({"language"})},
    ("Eup.xml", "Eup"): {"ms": frozenset({"language"})},
}

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
    """Reject source children/attributes that would otherwise be silently lost.

    This is deliberately narrower than full DTD validation. It guards the
    converter's preservation boundary while leaving cardinality/order checks to
    separate validation work. Elements and attributes are each visited once.
    """

    allowed_children = LEGACY_CHILDREN if legacy else MODERN_CHILDREN
    allowed_attributes = LEGACY_ATTRIBUTES if legacy else MODERN_ATTRIBUTES
    location = source_path or "<memory>"
    source_name = source_path.replace("\\", "/").rsplit("/", 1)[-1] if source_path else ""
    source_identity = (source_name, root.attrib.get("filename", ""))
    required_exceptions = MODERN_REQUIRED_ATTRIBUTE_EXCEPTIONS.get(source_identity, {})

    stack: list[tuple[ET.Element, str]] = [(root, f"/{root.tag}")]
    while stack:
        parent, path = stack.pop()
        allowed = allowed_children.get(parent.tag)
        if allowed is None:
            raise SourceStructureError(
                f"{location}: unsupported <{parent.tag}> element at {path}"
            )

        if not legacy:
            required = MODERN_REQUIRED_ATTRIBUTES.get(parent.tag, frozenset())
            exceptions = required_exceptions.get(parent.tag, frozenset())
            for attribute in sorted(required - exceptions):
                if attribute not in parent.attrib:
                    raise SourceStructureError(
                        f"{location}: missing required attribute {attribute} on <{parent.tag}> at {path}"
                    )

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
            stack.append((child, f"{path}/{child.tag}"))
