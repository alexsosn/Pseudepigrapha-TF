from __future__ import annotations

from xml.etree import ElementTree as ET


class SourceStructureError(ValueError):
    """Raised when a well-formed XML tree contains unsupported child elements."""


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


def validate_source_structure(
    root: ET.Element,
    *,
    legacy: bool,
    source_path: str = "",
) -> None:
    """Reject child elements outside the supported modern or legacy vocabulary.

    The check is deliberately narrower than full DTD validation: it guards
    against silent subtree loss while leaving attribute/cardinality/order checks
    to separate validation work. Every element is visited once.
    """

    allowed_children = LEGACY_CHILDREN if legacy else MODERN_CHILDREN
    location = source_path or "<memory>"

    stack: list[tuple[ET.Element, str]] = [(root, f"/{root.tag}")]
    while stack:
        parent, path = stack.pop()
        allowed = allowed_children.get(parent.tag)
        if allowed is None:
            raise SourceStructureError(
                f"{location}: unsupported <{parent.tag}> element at {path}"
            )
        children = list(parent)
        for child in children:
            if child.tag not in allowed:
                raise SourceStructureError(
                    f"{location}: unsupported <{child.tag}> child of <{parent.tag}> at {path}"
                )
        for child in reversed(children):
            stack.append((child, f"{path}/{child.tag}"))
