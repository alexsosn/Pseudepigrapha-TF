from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Iterable

from .graph import (
    TFData,
    _Builder,
    _add_version,
    _book_ids,
    _common,
    _ref_features,
    _slug,
)
from .model import Book, Div, Ellipsis, OrphanReading, Unit, Version
from .source_structure import KNOWN_BLANK_UNIT_IDS


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


def _source_basename(source_path: str) -> str:
    return source_path.replace("\\", "/").rsplit("/", 1)[-1] if source_path else ""


def _is_known_blank_unit_id(
    book: Book,
    version: Version,
    path: tuple[str, ...],
    unit: Unit,
) -> bool:
    return (
        unit.unit_id == ""
        and (
            _source_basename(book.source_path),
            book.filename,
            version.title,
            path,
        )
        in KNOWN_BLANK_UNIT_IDS
    )


def _validate_model_identities(books: Iterable[Book]) -> None:
    """Reject blank graph identities before any graph mutation occurs."""

    for book in books:
        if not book.filename.strip():
            raise ValueError("blank book filename")
        for version in book.versions:
            stack = [(div, ()) for div in version.divs]
            while stack:
                div, path = stack.pop()
                if not div.number.strip():
                    raise ValueError(f"{book.filename}/{version.title}: blank div number")
                dpath = path + (div.number,)
                for item in div.items:
                    if isinstance(item, Div):
                        stack.append((item, dpath))
                    elif isinstance(item, Unit):
                        if not item.unit_id.strip() and not _is_known_blank_unit_id(
                            book, version, dpath, item
                        ):
                            raise ValueError(f"{book.filename}/{version.title}: blank unit id")
                        for reading in item.readings:
                            if not reading.option.strip():
                                raise ValueError(
                                    f"{book.filename}/{version.title}: blank reading option"
                                )
                    elif isinstance(item, OrphanReading):
                        if not item.reading.option.strip():
                            raise ValueError(
                                f"{book.filename}/{version.title}: blank reading option"
                            )


def _validate_unique_manuscript_abbreviations(books: Iterable[Book]) -> None:
    """Reject ambiguous non-blank witness identity before graph mutation."""

    for book in books:
        for version in book.versions:
            seen: set[str] = set()
            for manuscript in version.manuscripts:
                abbrev = manuscript.abbrev
                if not abbrev.strip():
                    continue
                if abbrev in seen:
                    raise ValueError(
                        f"{book.filename}/{version.title}: duplicate manuscript abbreviation {abbrev!r}"
                    )
                seen.add(abbrev)


def _stamp_version_identity(builder: _Builder, start: int, version_id: str) -> None:
    """Stamp source-derived version identity on nodes created for one version."""

    for obj in builder.objects[start:]:
        obj.features["version_id"] = version_id


def _without_special_div_items(div: Div) -> Div:
    """Return only the Div/Unit structure understood by the core text builder."""

    return Div(
        number=div.number,
        fragment=div.fragment,
        items=tuple(
            _without_special_div_items(item) if isinstance(item, Div) else item
            for item in div.items
            if not isinstance(item, (Ellipsis, OrphanReading))
        ),
    )


def _textual_version_for_core_builder(version: Version) -> Version:
    return Version(
        title=version.title,
        author=version.author,
        language=version.language,
        fragment=version.fragment,
        divisions=version.divisions,
        resources=version.resources,
        manuscripts=tuple(
            replace(ms, abbrev="") if not ms.abbrev.strip() else ms
            for ms in version.manuscripts
        ),
        divs=tuple(_without_special_div_items(div) for div in version.divs),
    )


def _manuscript_keys(builder: _Builder, vkey: str) -> dict[str, str]:
    """Return the unique manuscript key for each declared abbreviation."""

    result: dict[str, str] = {}
    prefix = f"{vkey}:ms:"
    for obj in builder.objects:
        if not obj.key.startswith(prefix):
            continue
        abbrev = str(obj.features.get("ms_abbrev", ""))
        if not abbrev.strip():
            continue
        if abbrev in result and result[abbrev] != obj.key:
            raise ValueError(f"{vkey}: duplicate manuscript abbreviation {abbrev!r}")
        result[abbrev] = obj.key
    return result


def _attach_orphan_witnesses(
    builder: _Builder,
    *,
    source_key: str,
    owner_key: str,
    anchor: set[int],
    book: Book,
    version: Version,
    vkey: str,
    witnesses: tuple[str, ...],
    manuscripts: dict[str, str],
) -> None:
    """Preserve orphan-reading witness citations without inventing a unit."""

    for abbrev in witnesses:
        mkey = manuscripts.get(abbrev)
        if mkey is None:
            mkey = f"{vkey}:ms:undefined:{_slug(abbrev)}"
            if mkey not in builder.by_key:
                builder.node(
                    mkey,
                    "manuscript",
                    anchor,
                    **_common(book, version),
                    ms_abbrev=abbrev,
                    undefined_manuscript=1,
                )
                builder.edge("manuscript_of", mkey, owner_key)
                builder.warnings.append(
                    f"{book.filename}/{version.title}: orphan reading cites undeclared manuscript {abbrev!r}"
                )
            manuscripts[abbrev] = mkey
        builder.edge("witness", source_key, mkey)


def _add_orphan_reading_node(
    builder: _Builder,
    *,
    key: str,
    parent_key: str,
    anchor: set[int],
    book: Book,
    version: Version,
    path: tuple[str, ...],
    source_child_index: int,
    orphan: OrphanReading,
    is_metadata_only: int = 0,
) -> None:
    reading = orphan.reading
    features: dict[str, object] = {
        **_common(book, version),
        **_ref_features(path, version.divisions),
        "source_tag": orphan.source_tag,
        "source_child_index": source_child_index,
        "reading_option_source": reading.option,
        "mss": reading.mss_raw.strip(),
        "linebreak": reading.linebreak,
        "indent": reading.indent,
        "reading_text": reading.text,
        "reading_xml": reading.content_xml,
        "is_source_anomaly": 1,
    }
    if is_metadata_only:
        features["is_metadata_only"] = 1
    builder.node(key, "orphan_reading", anchor, **features)
    builder.edge("parent", key, parent_key)


def _add_textual_source_anomalies(
    builder: _Builder,
    book: Book,
    version: Version,
    book_index: int,
    version_index: int,
) -> None:
    """Attach preserved non-core source items after Div nodes have TF anchors."""

    vkey = f"book:{book_index}:version:{version_index}"
    specs = version.divisions
    manuscripts = _manuscript_keys(builder, vkey)
    owner_key = f"{vkey}:book"
    div_serial = 0
    ellipsis_serial = 0
    orphan_serial = 0

    def visit(div: Div, path: tuple[str, ...]) -> None:
        nonlocal div_serial, ellipsis_serial, orphan_serial
        div_serial += 1
        dkey = f"{vkey}:div:{div_serial}"
        dpath = path + (div.number,)
        parent = builder.by_key[dkey]
        if not parent.slots:
            raise ValueError(
                f"{book.filename}/{version.title}: special source item parent {dpath!r} has no TF anchor"
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
            elif isinstance(item, OrphanReading):
                orphan_serial += 1
                okey = f"{vkey}:orphan_reading:{orphan_serial}"
                _add_orphan_reading_node(
                    builder,
                    key=okey,
                    parent_key=dkey,
                    anchor=technical_anchor,
                    book=book,
                    version=version,
                    path=dpath,
                    source_child_index=child_position,
                    orphan=item,
                )
                _attach_orphan_witnesses(
                    builder,
                    source_key=okey,
                    owner_key=owner_key,
                    anchor=technical_anchor,
                    book=book,
                    version=version,
                    vkey=vkey,
                    witnesses=item.reading.witnesses,
                    manuscripts=manuscripts,
                )

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
    orphan_serial = 0
    pending_orphan_witnesses: list[tuple[str, OrphanReading]] = []

    def add_div(div: Div, level: int, sibling: int, path: tuple[str, ...], parent: str | None) -> None:
        nonlocal div_serial, ellipsis_serial, orphan_serial
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
            elif isinstance(item, OrphanReading):
                orphan_serial += 1
                okey = f"{vkey}:orphan_reading:{orphan_serial}"
                _add_orphan_reading_node(
                    builder,
                    key=okey,
                    parent_key=dkey,
                    anchor=technical_anchor,
                    book=book,
                    version=version,
                    path=dpath,
                    source_child_index=source_child_index,
                    orphan=item,
                    is_metadata_only=1,
                )
                pending_orphan_witnesses.append((okey, item))
            else:
                raise ValueError(
                    f"{book.filename}/{version.title}: metadata-only classification encountered textual unit"
                )

    for top_index, div in enumerate(version.divs, 1):
        add_div(div, 1, top_index, (), None)

    mkeys: list[str] = []
    manuscripts: dict[str, str] = {}
    for midx, ms in enumerate(version.manuscripts, 1):
        if ms.abbrev.strip() and ms.abbrev in manuscripts:
            raise ValueError(
                f"{book.filename}/{version.title}: duplicate manuscript abbreviation {ms.abbrev!r}"
            )
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
        if ms.abbrev.strip():
            manuscripts[ms.abbrev] = mkey

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

    for okey, orphan in pending_orphan_witnesses:
        _attach_orphan_witnesses(
            builder,
            source_key=okey,
            owner_key=target,
            anchor=technical_anchor,
            book=book,
            version=version,
            vkey=vkey,
            witnesses=orphan.reading.witnesses,
            manuscripts=manuscripts,
        )

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


def _mark_known_missing_unit_ids(data: TFData, books: Iterable[Book]) -> None:
    """Expose accepted source-declared blank unit ids without inventing identity."""

    expected: set[tuple[str, str, str]] = set()
    for book in books:
        version_ids = _book_ids(book)
        for version, version_id in zip(book.versions, version_ids):
            stack = [(div, ()) for div in version.divs]
            while stack:
                div, path = stack.pop()
                dpath = path + (div.number,)
                for item in div.items:
                    if isinstance(item, Div):
                        stack.append((item, dpath))
                    elif isinstance(item, Unit) and _is_known_blank_unit_id(
                        book, version, dpath, item
                    ):
                        source_ref = str(_ref_features(dpath, version.divisions)["source_ref"])
                        expected.add((book.filename, version_id, source_ref))

    if not expected:
        return

    otype = data.node_features.get("otype", {})
    ocp_books = data.node_features.get("ocp_book", {})
    version_ids = data.node_features.get("version_id", {})
    source_refs = data.node_features.get("source_ref", {})
    unit_ids = data.node_features.get("unit_id", {})
    for ocp_book, version_id, source_ref in expected:
        matches = [
            node
            for node, kind in otype.items()
            if kind == "unit"
            and ocp_books.get(node) == ocp_book
            and version_ids.get(node) == version_id
            and source_refs.get(node) == source_ref
            and unit_ids.get(node, "") == ""
        ]
        if len(matches) != 1:
            raise ValueError(
                f"known missing unit id {ocp_book}/{version_id} at {source_ref}: "
                f"expected exactly one graph unit, found {len(matches)}"
            )
        node = matches[0]
        data.node_features.setdefault("is_missing_unit_id", {})[node] = 1
        data.node_features.setdefault("is_source_anomaly", {})[node] = 1


def build_tf_data(
    books: Iterable[Book],
    *,
    upstream_repository: str = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha",
    upstream_commit: str = "",
    converter_version: str = "0.1.0",
) -> TFData:
    """Build TF while preserving declared upstream versions that contain no text."""

    books = list(books)
    _validate_model_identities(books)
    _validate_unique_manuscript_abbreviations(books)
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
                    _textual_version_for_core_builder(version),
                    version_id,
                    bidx,
                    vidx,
                )
                _add_textual_source_anomalies(builder, book, version, bidx, vidx)
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
    _mark_known_missing_unit_ids(data, books)
    data.metadata["otext"]["fmt:version_metadata-default"] = "{version_title}"
    data.metadata["otext"]["fmt:ellipsis-default"] = "{ellipsis_text}"
    data.metadata["otext"]["fmt:orphan_reading-default"] = "{reading_text}"
    if "is_metadata_only" in data.metadata:
        data.metadata["is_metadata_only"]["valueType"] = "int"
        data.metadata["is_metadata_only"]["description"] = (
            "1 for metadata attached to an upstream version with no textual units"
        )
    if "is_source_anomaly" in data.node_features:
        data.metadata.setdefault("is_source_anomaly", {})["valueType"] = "int"
        data.metadata["is_source_anomaly"]["description"] = (
            "1 for a preserved upstream structure or identity anomaly"
        )
    if "is_missing_unit_id" in data.node_features:
        data.metadata["is_missing_unit_id"] = {
            "valueType": "int",
            "description": "1 when the upstream unit explicitly has an empty id and no id is inferred",
        }
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
