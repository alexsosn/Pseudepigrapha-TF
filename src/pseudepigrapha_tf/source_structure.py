from __future__ import annotations

from xml.etree import ElementTree as ET

from .source_versions import is_wrapped_legacy_version


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
    # Current OCP's wrapped legacy Esdr source retains the old root language
    # attribute. It is accepted only under the equivalence check below.
    "book": frozenset({"filename", "title", "textStructure", "language"}),
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

# These required modern attributes define researcher-visible work, witness,
# locus, or apparatus identity. DTD #REQUIRED only guarantees presence, so
# whitespace-only CDATA has to be rejected separately. Other required metadata
# is deliberately allowed to be empty because pinned OCP uses that convention.
MODERN_NONBLANK_IDENTITY_ATTRIBUTES: dict[str, frozenset[str]] = {
    "book": frozenset({"filename"}),
    "ms": frozenset({"abbrev"}),
    "div": frozenset({"number"}),
    "unit": frozenset({"id"}),
    "reading": frozenset({"option"}),
}

# AdamEve.xml contains exactly one source-declared blank unit id: Latin
# (Mozley), source div path 26:0. Bind the exception to exact source bytes for
# each supported immutable OCP snapshot. The second digest is the refreshed
# c939dcb... source after generated translations/pretty-printing were added.
KNOWN_BLANK_UNIT_ID_SOURCES: dict[
    tuple[str, str, str, tuple[str, ...]], frozenset[str]
] = {
    (
        "AdamEve.xml",
        "AdamEve",
        "Latin (Mozley)",
        ("26", "0"),
    ): frozenset(
        {
            "a63275351e2349ce8a31b7427a28b80db034be670ba545e2398832a3d9ac6358",
            "b5e20471d7e1b531df49d81acd19462ee92192c3e20019cb110215611d7b9817",
        }
    ),
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
    source_sha256: str = "",
) -> None:
    """Reject source structure that cannot be mapped without ambiguity or loss.

    This is deliberately narrower than full DTD validation. It guards the
    converter's preservation boundary while leaving unrelated cardinality/order
    checks to separate validation work. Elements and attributes are each visited
    a constant number of times, so validation remains linear in source size.

    Current OCP has one hybrid shape produced by its translation generator: an
    old chapter/verse document is wrapped in a modern <version> while its body is
    left in the legacy dialect. Only that version subtree switches dialect; the
    surrounding book and all sibling versions remain subject to modern rules.
    """

    location = source_path or "<memory>"
    source_name = source_path.replace("\\", "/").rsplit("/", 1)[-1] if source_path else ""
    book_filename = root.attrib.get("filename", "")

    if not legacy and "language" in root.attrib:
        wrapped_versions = [version for version in root.findall("version") if is_wrapped_legacy_version(version)]
        if (
            len(wrapped_versions) != 1
            or wrapped_versions[0].attrib.get("language", "") != root.attrib.get("language", "")
        ):
            raise SourceStructureError(
                f"{location}: root book language is only supported when it exactly duplicates one wrapped legacy version"
            )

    # Carry the containing version title, source div path, and hybrid-body flag
    # through the iterative traversal so validation stays linear.
    stack: list[tuple[ET.Element, str, str, tuple[str, ...], bool]] = [
        (root, f"/{root.tag}", "", (), False)
    ]
    while stack:
        parent, path, version_title, div_path, wrapped_legacy = stack.pop()
        if parent.tag == "version":
            version_title = parent.attrib.get("title", "")
            wrapped_legacy = is_wrapped_legacy_version(parent)
        if parent.tag == "div":
            div_path = div_path + (parent.attrib.get("number", ""),)

        # The <version> wrapper itself is modern. Only its descendants use the
        # legacy chapter/verse policy.
        node_legacy = legacy or (wrapped_legacy and parent.tag != "version")
        allowed_children = LEGACY_CHILDREN if node_legacy else MODERN_CHILDREN
        allowed_attributes = LEGACY_ATTRIBUTES if node_legacy else MODERN_ATTRIBUTES

        allowed = allowed_children.get(parent.tag)
        if allowed is None:
            raise SourceStructureError(
                f"{location}: unsupported <{parent.tag}> element at {path}"
            )

        if not node_legacy:
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

            for attribute in sorted(
                MODERN_NONBLANK_IDENTITY_ATTRIBUTES.get(parent.tag, frozenset())
            ):
                value = parent.attrib.get(attribute)
                if value is not None and not value.strip():
                    anomaly_key = (source_name, book_filename, version_title, div_path)
                    expected_digests = KNOWN_BLANK_UNIT_ID_SOURCES.get(anomaly_key, frozenset())
                    known_blank_unit = (
                        parent.tag == "unit"
                        and attribute == "id"
                        and value == ""
                        and source_sha256 in expected_digests
                    )
                    if not known_blank_unit:
                        raise SourceStructureError(
                            f"{location}: blank required identity attribute {attribute} on <{parent.tag}> at {path}"
                        )

        if parent.tag == "manuscripts":
            seen_abbrevs: set[str] = set()
            for manuscript in parent.findall("ms"):
                abbrev = manuscript.get("abbrev", "")
                if not abbrev.strip():
                    continue
                if abbrev in seen_abbrevs:
                    owner = f"version {version_title!r}" if not legacy else "legacy version"
                    raise SourceStructureError(
                        f"{location}: duplicates manuscript abbreviation {abbrev!r} in {owner} at {path}"
                    )
                seen_abbrevs.add(abbrev)

        if (
            not node_legacy
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
            stack.append((child, f"{path}/{child.tag}", version_title, div_path, wrapped_legacy))
