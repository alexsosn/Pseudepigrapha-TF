from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from .graph import (
    TFData,
    _Builder,
    _add_version,
    _book_ids,
    _common,
    _ref_features,
)
from .model import Book, Div, Ellipsis, Unit, Version


@dataclass(frozen=True)
class _PendingMetadataVersion:
    book: Book
    version: Version
    version_id: str
    book_index: int
    version_index: int


def _div_has_units(div: Div) -> bool:
    return any(
        isinstance(item, Unit) or (isinstance(item, Div) and _div_has_units(item))
        for item in div.items
    )


def _version_has_units(version: Version) -> bool:
    return any(_div_has_units(div) for div in version.divs)


def _stamp_version_identity(builder: _Builder, start: int, version_id: str) -> None:
    """Stamp source-derived version identity on nodes created for one version."""

    for obj in builder.objects[start:]:
        obj.features["version_id"] = version_id


def _without_ellipses(div: Div) -> Div:
    """Return the textual structure understood by the core slot/section builder."""

    return Div(
        number=div.number,
        fragment=div.fragment,
        items=tuple(
            _without_ellipses(item) if isinstance(item, Div) else item
            for item in div.items
            if not isinstance(item, Ellipsis)
        ),
    )


def _textual_version_without_ellipses(version: Version) -> Version:
    return Version(
        title=version.title,
        author=version.author,
        language=version.language,
        fragment=version.fragment,
        divisions=version.divisions,
        resources=version.resources,
        manuscripts=version.manuscripts,
        divs=tuple(_without_ellipses(div) for div in version.divs),
    )


def _add_textual_ellipses(
    builder: _Builder,
    book: Book,
    version: Version,
    book_index: int,
    version_index: int,
) -> None:
    """Attach source omission markers after the core builder has anchored divs."""

    vkey = f"book:{book_index}:version:{version_index}"
    specs = version.divisions
    div_serial = 0
    ellipsis_serial = 0

    def visit(div: Div, path: tuple[str, ...]) -> None:
        nonlocal div_serial, ellipsis_serial
        div_serial += 1
        dkey = f"{vkey}:div:{div_serial}"
        dpath = path + (div.number,)
        parent = builder.by_key[dkey]
        if not parent.slots:
            raise ValueError(
                f"{book.filename}/{version.title}: ellipsis parent {dpath!r} has no TF anchor"
            )
        technical_anchor = {min(parent.slots)}
        for child_position, item in enumerate(div.items, 1):
            if isinstance(item, Div):
                visit(item, dpath)
            elif isinstance(item, Ellipsis):
                ellipsis_serial += 1
                ekey = f"{vkey}:ellipsis:{ellipsis_serial}"
                builder.node(
                    ekey,
                    "ellipsis",
                    technical_anchor,
                    **_common(book, version),
                    **_ref_features(dpath, specs),
                    source_tag=item.source_tag,
                    ellipsis_text=item.text,
                    source_child_index=child_position,
                )
                builder.edge("parent", ekey, dkey)

    for div in version.divs:
        visit(div, ())


def _add_metadata_version(
    builder: _Builder,
    book: Book,
    version: Version,
    version_id: str,
    book_index: int,
    version_index: int,
    anchor: int,
) -> None:
    """Preserve an upstream version that declares metadata but no textual units.

    Text-Fabric requires non-slot nodes to have an ``oslots`` anchor. The one
    supplied slot is purely technical: this node is deliberately *not* a TF
    ``book`` section, and its type-specific text format renders ``version_title``
    instead of descending to the anchor text.
    """

    start = len(builder.objects)
    vkey = f"book:{book_index}:version:{version_index}"
    technical_anchor = {anchor}
    specs = version.divisions

    div_serial = 0
    ellipsis_serial = 0

    def add_div(div: Div, level: int, sibling: int, path: tuple[str, ...], parent: str | None) -> None:
        nonlocal div_serial, ellipsis_serial
        div_serial += 1
        dpath = path + (div.number,)
        dkey = f"{vkey}:div:{div_serial}"
        builder.node(
            dkey,
            "div",
            technical_anchor,
            **_common(book, version),
            **_ref_features(dpath, specs),
            div_number=div.number,
            div_level=level,
            div_label=specs[level - 1].label if level <= len(specs) else "",
            div_fragment=div.fragment,
            div_path="/".join(dpath),
            div_index=sibling,
            is_metadata_only=1,
        )
        if parent:
            builder.edge("parent", dkey, parent)
        child_index = 0
        for source_child_index, item in enumerate(div.items, 1):
            if isinstance(item, Div):
                child_index += 1
                add_div(item, level + 1, child_index, dpath, dkey)
            elif isinstance(item, Ellipsis):
                ellipsis_serial += 1
                ekey = f"{vkey}:ellipsis:{ellipsis_serial}"
                builder.node(
                    ekey,
                    "ellipsis",
                    technical_anchor,
                    **_common(book, version),
                    **_ref_features(dpath, specs),
                    source_tag=item.source_tag,
                    ellipsis_text=item.text,
                    source_child_index=source_child_index,
                    is_metadata_only=1,
                )
                builder.edge("parent", ekey, dkey)
            else:
                raise ValueError(
                    f"{book.filename}/{version.title}: metadata-only classification encountered textual unit"
                )

    for top_index, div in enumerate(version.divs, 1):
        add_div(div, 1, top_index, (), None)

    mkeys: list[str] = []
    for midx, ms in enumerate(version.manuscripts, 1):
        mkey = f"{vkey}:ms:{midx}"
        builder.node(
            mkey,
            "manuscript",
            technical_anchor,
            **_common(book, version),
            ms_abbrev=ms.abbrev,
            ms_name=ms.name,
            ms_name_xml=ms.name_xml,
            ms_language=ms.language,
            ms_show=ms.show,
            bibliography=json.dumps(ms.bibliography, ensure_ascii=False),
            bibliography_xml=json.dumps(ms.bibliography_xml, ensure_ascii=False),
            manuscript_index=midx,
            is_metadata_only=1,
        )
        mkeys.append(mkey)

    target = f"{vkey}:metadata"
    builder.node(
        target,
        "version_metadata",
        technical_anchor,
        version_id=version_id,
        is_metadata_only=1,
        ocp_book=book.filename,
        title=book.title,
        text_structure=book.text_structure,
        version_title=version.title,
        author=version.author,
        language=version.language,
        version_fragment=version.fragment,
        source_file=book.source_path,
        source_sha256=book.source_sha256,
        division_labels=json.dumps([d.label for d in specs], ensure_ascii=False),
        division_delimiters=json.dumps([d.delimiter for d in specs], ensure_ascii=False),
        division_texts=json.dumps([d.text for d in specs], ensure_ascii=False),
    )
    for mkey in mkeys:
        builder.edge("manuscript_of", mkey, target)

    for ridx, resource in enumerate(version.resources, 1):
        rkey = f"{vkey}:resource:{ridx}"
        builder.node(
            rkey,
            "resource",
            technical_anchor,
            **_common(book, version),
            resource_name=resource.name,
            resource_info=json.dumps(resource.info, ensure_ascii=False),
            resource_url=resource.url,
            resource_index=ridx,
            is_metadata_only=1,
        )
        builder.edge("resource_of", rkey, target)

    _stamp_version_identity(builder, start, version_id)


def build_tf_data(
    books: Iterable[Book],
    *,
    upstream_repository: str = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha",
    upstream_commit: str = "",
    converter_version: str = "0.1.0",
) -> TFData:
    """Build TF while preserving declared upstream versions that contain no text."""

    books = list(books)
    builder = _Builder()
    pending: list[_PendingMetadataVersion] = []

    for bidx, book in enumerate(books, 1):
        version_ids = _book_ids(book)
        book_anchor: int | None = None
        metadata: list[_PendingMetadataVersion] = []

        # Textual versions go first so metadata-only siblings can use a technical
        # anchor from the same OCP work even when upstream lists the empty version first.
        for vidx, (version, version_id) in enumerate(zip(book.versions, version_ids), 1):
            if _version_has_units(version):
                first_slot = builder.next_slot
                start = len(builder.objects)
                _add_version(
                    builder,
                    book,
                    _textual_version_without_ellipses(version),
                    version_id,
                    bidx,
                    vidx,
                )
                _add_textual_ellipses(builder, book, version, bidx, vidx)
                _stamp_version_identity(builder, start, version_id)
                if book_anchor is None and builder.next_slot > first_slot:
                    book_anchor = first_slot
            else:
                metadata.append(_PendingMetadataVersion(book, version, version_id, bidx, vidx))

        if book_anchor is None:
            pending.extend(metadata)
        else:
            for item in metadata:
                _add_metadata_version(
                    builder,
                    item.book,
                    item.version,
                    item.version_id,
                    item.book_index,
                    item.version_index,
                    book_anchor,
                )

    # A work with only metadata can reuse a corpus-level technical anchor. This
    # does not create a section or claim textual containment. A corpus with no
    # textual slots at all cannot form a Text-Fabric warp and fails explicitly.
    if pending:
        if builder.next_slot == 1:
            names = ", ".join(f"{item.book.filename}/{item.version.title}" for item in pending)
            raise ValueError(f"metadata-only corpus has no word slot for TF anchoring: {names}")
        for item in pending:
            _add_metadata_version(
                builder,
                item.book,
                item.version,
                item.version_id,
                item.book_index,
                item.version_index,
                1,
            )

    data = builder.finalize(
        upstream_repository=upstream_repository,
        upstream_commit=upstream_commit,
        converter_version=converter_version,
    )
    data.metadata["otext"]["fmt:version_metadata-default"] = "{version_title}"
    data.metadata["otext"]["fmt:ellipsis-default"] = "{ellipsis_text}"
    if "is_metadata_only" in data.metadata:
        data.metadata["is_metadata_only"]["valueType"] = "int"
        data.metadata["is_metadata_only"]["description"] = (
            "1 for metadata attached to an upstream version with no textual units"
        )
    if "version_id" in data.metadata:
        data.metadata["version_id"]["description"] = (
            "stable converter identifier for the exact upstream version owning this node"
        )
    if "source_child_index" in data.metadata:
        data.metadata["source_child_index"]["valueType"] = "int"
        data.metadata["source_child_index"]["description"] = (
            "1-based position of a preserved source child element within its parent"
        )
    if "source_tag" in data.metadata:
        data.metadata["source_tag"]["description"] = "literal upstream XML element name"
    if "ellipsis_text" in data.metadata:
        data.metadata["ellipsis_text"]["description"] = (
            "text content of an upstream <elipsis> structural omission marker"
        )
    return data
