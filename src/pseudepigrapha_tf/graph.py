from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

from .model import Book, Div, DivisionSpec, Reading, Token, Unit, Version

INT_FEATURES = {
    "chapter_index", "div_index", "div_level", "is_gap", "is_omission", "is_primary",
    "manuscript_index", "reading_index", "reading_option", "resource_index", "token_count",
    "undefined_manuscript", "unit_index", "variant_position", "verse_index", "w_annotated",
}

FEATURE_DESCRIPTIONS = {
    "book": "BHSA-compatible book section identifier; one OCP version is one TF book",
    "chapter": "BHSA-compatible chapter label; compound parent path for deep OCP references",
    "verse": "BHSA-compatible verse label; terminal OCP division",
    "g_word_utf8": "Unicode surface form, following the BHSA feature name",
    "trailer_utf8": "Unicode material following a word inside its OCP reading",
    "prefix_utf8": "Unicode material preceding a word inside its OCP reading",
    "boundary_utf8": "deterministic separator inserted between OCP units",
    "source_file": "stable source path relative to the supplied OCP docs directory",
    "source_sha256": "SHA-256 digest of source XML bytes",
    "source_ref": "full OCP reference using every division and declared delimiter",
    "source_ref_parts": "JSON array of source division identifiers",
    "reading_xml": "mixed XML content inside the OCP reading",
    "reading_option_source": "literal OCP reading/@option before numeric normalization",
    "w_lang": "literal OCP <w>/@lang when present",
    "is_gap": "1 for an anchor slot created for an empty primary reading",
    "is_omission": "1 when an OCP reading has no textual content",
}

EDGE_DESCRIPTIONS = {
    "oslots": "Text-Fabric warp edge to occupied/technical anchor word slots",
    "parent": "OCP structural parent relation (div-to-div or unit-to-div)",
    "reading_of": "reading node to its OCP unit",
    "variant_word_of": "variant_word node to its reading",
    "witness": "reading node to cited manuscript nodes",
    "manuscript_of": "manuscript node to its TF book/version",
    "resource_of": "resource node to its TF book/version",
}


@dataclass
class TFData:
    node_features: dict[str, dict[int, str | int]]
    edge_features: dict[str, dict[int, set[int]]]
    metadata: dict[str, dict[str, str]]
    warnings: list[str] = field(default_factory=list)

    @property
    def max_slot(self) -> int:
        return max((n for n, k in self.node_features.get("otype", {}).items() if k == "word"), default=0)

    @property
    def max_node(self) -> int:
        return max(self.node_features.get("otype", {}), default=0)

    @property
    def oslots_edge_count(self) -> int:
        return sum(len(v) for v in self.edge_features.get("oslots", {}).values())

    def validate(self) -> list[str]:
        otype = self.node_features.get("otype", {})
        if not otype:
            return ["missing otype"]
        errors: list[str] = []
        nodes = set(range(1, self.max_node + 1))
        if set(otype) != nodes:
            errors.append("otype node ids are not contiguous from 1")
        if any(otype.get(n) != "word" for n in range(1, self.max_slot + 1)):
            errors.append("word slots are not the first contiguous nodes")
        if any(otype.get(n) == "word" for n in range(self.max_slot + 1, self.max_node + 1)):
            errors.append("word slot found after non-slot nodes")
        oslots = self.edge_features.get("oslots", {})
        if set(oslots) != set(range(self.max_slot + 1, self.max_node + 1)):
            errors.append("oslots does not map every non-slot node exactly once")
        if any(not 1 <= s <= self.max_slot for slots in oslots.values() for s in slots):
            errors.append("oslots points outside slot range")
        for feature, values in self.edge_features.items():
            if feature == "oslots":
                continue
            if any(src not in nodes or any(dst not in nodes for dst in dsts) for src, dsts in values.items()):
                errors.append(f"edge feature {feature} refers to unknown nodes")
        return errors


@dataclass
class _Node:
    key: str
    kind: str
    slots: set[int]
    features: dict[str, str | int]


class _Builder:
    def __init__(self) -> None:
        self.next_slot = 1
        self.slot_features: dict[str, dict[int, str | int]] = {}
        self.objects: list[_Node] = []
        self.by_key: dict[str, _Node] = {}
        self.edges: list[tuple[str, str, str]] = []
        self.warnings: list[str] = []

    def slot(self, **features: str | int | None) -> int:
        node = self.next_slot
        self.next_slot += 1
        for name, value in features.items():
            if value not in (None, ""):
                self.slot_features.setdefault(name, {})[node] = value
        return node

    def set_slot_feature(self, node: int, name: str, value: str | int | None) -> None:
        if value not in (None, ""):
            self.slot_features.setdefault(name, {})[node] = value

    def node(self, key: str, kind: str, slots: Iterable[int], **features: str | int | None) -> str:
        if key in self.by_key:
            raise ValueError(f"duplicate graph object key: {key}")
        clean = {k: v for k, v in features.items() if v not in (None, "")}
        obj = _Node(key, kind, set(slots), clean)
        self.objects.append(obj)
        self.by_key[key] = obj
        return key

    def edge(self, feature: str, source: str, target: str) -> None:
        self.edges.append((feature, source, target))

    def finalize(self, *, upstream_repository: str, upstream_commit: str, converter_version: str) -> TFData:
        max_slot = self.next_slot - 1
        features = {name: dict(values) for name, values in self.slot_features.items()}
        otype = {n: "word" for n in range(1, max_slot + 1)}
        key_to_node: dict[str, int] = {}
        oslots: dict[int, set[int]] = {}
        for node_id, obj in enumerate(self.objects, max_slot + 1):
            key_to_node[obj.key] = node_id
            otype[node_id] = obj.kind
            oslots[node_id] = set(obj.slots)
            for name, value in obj.features.items():
                features.setdefault(name, {})[node_id] = value
        features["otype"] = otype
        edges: dict[str, dict[int, set[int]]] = {"oslots": oslots}
        for feature, source, target in self.edges:
            edges.setdefault(feature, {}).setdefault(key_to_node[source], set()).add(key_to_node[target])
        data = TFData(
            features,
            edges,
            _metadata(features, edges, upstream_repository, upstream_commit, converter_version),
            self.warnings,
        )
        failures = data.validate()
        if failures:
            raise ValueError("invalid generated Text-Fabric graph: " + "; ".join(failures))
        return data


def _metadata(node_features, edge_features, repo: str, commit: str, converter_version: str):
    generic = {
        "dataset": "Pseudepigrapha-TF",
        "datasetName": "Online Critical Pseudepigrapha Text-Fabric conversion",
        "source": "Online Critical Pseudepigrapha",
        "sourceUrl": repo,
        "upstreamRepository": repo,
        "version": "0.1",
        "converterVersion": converter_version,
        "writtenBy": "Pseudepigrapha-TF converter",
    }
    if commit:
        generic["upstreamCommit"] = commit
    meta = {
        "": generic,
        "otext": {
            "sectionTypes": "book,chapter,verse",
            "sectionFeatures": "book,chapter,verse",
            "fmt:text-orig-full": "{prefix_utf8}{g_word_utf8}{trailer_utf8}{boundary_utf8}",
            "fmt:reading-default": "{reading_text}",
            "fmt:variant_word-default": "{prefix_utf8}{g_word_utf8}{trailer_utf8}",
            "fmt:manuscript-default": "{ms_abbrev}",
            "fmt:resource-default": "{resource_name}",
        },
    }
    for feature in node_features:
        meta[feature] = {
            "valueType": "int" if feature in INT_FEATURES else "str",
            "description": FEATURE_DESCRIPTIONS.get(feature, f"OCP/TF feature {feature}"),
        }
    for feature in edge_features:
        meta[feature] = {"valueType": "str", "description": EDGE_DESCRIPTIONS.get(feature, feature)}
    return meta


def _slug(value: str) -> str:
    out, sep = [], False
    for char in value.strip():
        if char.isalnum():
            out.append(char)
            sep = False
        elif not sep:
            out.append("_")
            sep = True
    return "".join(out).strip("_") or "version"


def _book_ids(book: Book) -> list[str]:
    if len(book.versions) == 1:
        return [book.filename]
    seen: dict[str, int] = {}
    result: list[str] = []
    for version in book.versions:
        base = f"{book.filename}__{_slug(version.title)}"
        seen[base] = seen.get(base, 0) + 1
        result.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return result


def _option(reading: Reading, fallback: int) -> int:
    try:
        return int(reading.option)
    except (TypeError, ValueError):
        return fallback


def _common(book: Book, version: Version) -> dict[str, str]:
    return {"ocp_book": book.filename, "version_title": version.title}


def _reference(path: tuple[str, ...], specs: tuple[DivisionSpec, ...]) -> str:
    parts: list[str] = []
    for index, value in enumerate(path):
        parts.append(value)
        if index < len(path) - 1:
            parts.append(specs[index].delimiter if index < len(specs) else "/")
    return "".join(parts)


def _ref_features(path: tuple[str, ...], specs: tuple[DivisionSpec, ...]) -> dict[str, str]:
    return {"source_ref": _reference(path, specs), "source_ref_parts": json.dumps(path, ensure_ascii=False)}


def _surface(token: Token, book: Book, version: Version, unit: Unit, reading: Reading,
             option: int, path: tuple[str, ...], specs: tuple[DivisionSpec, ...]) -> dict:
    return {
        "g_word_utf8": token.text,
        "trailer_utf8": token.trailer,
        "prefix_utf8": token.prefix,
        "language": token.lang or version.language,
        "w_lang": token.lang,
        "lex": token.lex,
        "morph": token.morph,
        "style": token.style,
        "w_annotated": 1 if token.annotated else None,
        "ocp_book": book.filename,
        "version_title": version.title,
        "unit_id": unit.unit_id,
        "reading_option": option,
        "reading_option_source": reading.option,
        **_ref_features(path, specs),
    }


def _boundary(linebreak: str) -> str:
    value = (linebreak or "").strip().lower()
    if value == "doublefollowing":
        return "\n\n"
    if value:
        return "\n"
    return ""


def _add_unit(builder: _Builder, book: Book, version: Version, vkey: str, unit: Unit, index: int,
              manuscripts: dict[str, str], path: tuple[str, ...], specs: tuple[DivisionSpec, ...],
              parent_div: str, endings: list[tuple[int, str]]) -> set[int]:
    if not unit.readings:
        raise ValueError(f"{book.filename}/{version.title}: unit {unit.unit_id!r} has no readings")
    pidx = next((i for i, r in enumerate(unit.readings) if r.option == "0"), 0)
    if unit.readings[pidx].option != "0":
        builder.warnings.append(
            f"{book.filename}/{version.title} unit {unit.unit_id}: no option=0; using first reading as primary"
        )
    primary = unit.readings[pidx]
    poption = _option(primary, pidx)
    ordered = [
        builder.slot(**_surface(t, book, version, unit, primary, poption, path, specs))
        for t in primary.tokens
    ]
    if not ordered:
        ordered = [builder.slot(
            is_gap=1, language=version.language, ocp_book=book.filename, version_title=version.title,
            unit_id=unit.unit_id, reading_option=poption, reading_option_source=primary.option,
            **_ref_features(path, specs),
        )]
    slots = set(ordered)
    ukey = f"{vkey}:unit:{index}"
    builder.node(
        ukey, "unit", slots, **_common(book, version), **_ref_features(path, specs),
        unit_id=unit.unit_id, unit_index=index, group=unit.group, parallel=unit.parallel,
        unit_linebreak=unit.linebreak,
    )
    builder.edge("parent", ukey, parent_div)

    for ridx, reading in enumerate(unit.readings, 1):
        option = _option(reading, ridx - 1)
        primary_flag = ridx - 1 == pidx
        rkey = f"{ukey}:reading:{ridx}"
        builder.node(
            rkey, "reading", slots, **_common(book, version), **_ref_features(path, specs),
            unit_id=unit.unit_id, reading_option=option, reading_option_source=reading.option,
            reading_index=ridx, reading_text=reading.text, reading_xml=reading.content_xml,
            mss=reading.mss_raw.strip(), linebreak=reading.linebreak, indent=reading.indent,
            token_count=len(reading.tokens), is_omission=1 if not reading.text else None,
            is_primary=1 if primary_flag else None,
        )
        builder.edge("reading_of", rkey, ukey)
        for abbrev in reading.witnesses:
            mkey = manuscripts.get(abbrev)
            if mkey is None:
                mkey = f"{vkey}:ms:undefined:{_slug(abbrev)}"
                if mkey not in builder.by_key:
                    builder.node(
                        mkey, "manuscript", (), **_common(book, version),
                        ms_abbrev=abbrev, undefined_manuscript=1,
                    )
                    builder.warnings.append(
                        f"{book.filename}/{version.title}: reading cites undeclared manuscript {abbrev!r}"
                    )
                manuscripts[abbrev] = mkey
            builder.edge("witness", rkey, mkey)
        if not primary_flag:
            anchor = {ordered[0]}
            for pos, token in enumerate(reading.tokens, 1):
                wkey = f"{rkey}:word:{pos}"
                surface = _surface(token, book, version, unit, reading, option, path, specs)
                surface.pop("ocp_book", None)
                surface.pop("version_title", None)
                builder.node(
                    wkey, "variant_word", anchor, **_common(book, version), **surface,
                    variant_position=pos,
                )
                builder.edge("variant_word_of", wkey, rkey)
    endings.append((ordered[-1], primary.linebreak or unit.linebreak))
    return slots


def _add_version(builder: _Builder, book: Book, version: Version, book_id: str,
                 book_index: int, version_index: int) -> None:
    vkey = f"book:{book_index}:version:{version_index}"
    manuscripts: dict[str, str] = {}
    for midx, ms in enumerate(version.manuscripts, 1):
        key = f"{vkey}:ms:{midx}"
        if ms.abbrev in manuscripts:
            builder.warnings.append(f"{book.filename}/{version.title}: duplicate manuscript abbreviation {ms.abbrev!r}")
        else:
            manuscripts[ms.abbrev] = key
        builder.node(
            key, "manuscript", (), **_common(book, version), ms_abbrev=ms.abbrev,
            ms_name=ms.name, ms_name_xml=ms.name_xml, ms_language=ms.language, ms_show=ms.show,
            bibliography=json.dumps(ms.bibliography, ensure_ascii=False),
            bibliography_xml=json.dumps(ms.bibliography_xml, ensure_ascii=False),
            manuscript_index=midx,
        )

    specs = version.divisions
    version_slots: set[int] = set()
    unit_counter = chapter_counter = verse_counter = div_serial = 0
    endings: list[tuple[int, str]] = []
    chapter_level = max(1, len(specs) - 1)
    verse_level = max(1, len(specs))

    def visit(div: Div, level: int, sibling: int, path: tuple[str, ...], parent: str | None) -> set[int]:
        nonlocal unit_counter, chapter_counter, verse_counter, div_serial
        div_serial += 1
        dpath = path + (div.number,)
        dkey = f"{vkey}:div:{div_serial}"
        slots: set[int] = set()
        child_index = 0
        for item in div.items:
            if isinstance(item, Div):
                child_index += 1
                slots.update(visit(item, level + 1, child_index, dpath, dkey))
            else:
                unit_counter += 1
                slots.update(_add_unit(
                    builder, book, version, vkey, item, unit_counter, manuscripts,
                    dpath, specs, dkey, endings,
                ))
        label = specs[level - 1].label if level <= len(specs) else ""
        builder.node(
            dkey, "div", slots, **_common(book, version), **_ref_features(dpath, specs),
            div_number=div.number, div_level=level, div_label=label,
            div_fragment=div.fragment, div_path="/".join(dpath), div_index=sibling,
        )
        if parent:
            builder.edge("parent", dkey, parent)
        if len(specs) == 1 and level == 1:
            verse_counter += 1
            builder.node(
                f"{dkey}:verse", "verse", slots, **_common(book, version), **_ref_features(dpath, specs),
                verse=div.number, verse_index=verse_counter,
            )
        elif len(specs) >= 2 and level == chapter_level:
            chapter_counter += 1
            builder.node(
                f"{dkey}:chapter", "chapter", slots, **_common(book, version), **_ref_features(dpath, specs),
                chapter=_reference(dpath, specs), chapter_index=chapter_counter,
            )
        elif len(specs) >= 2 and level == verse_level:
            verse_counter += 1
            builder.node(
                f"{dkey}:verse", "verse", slots, **_common(book, version), **_ref_features(dpath, specs),
                verse=div.number, verse_index=verse_counter,
            )
        return slots

    for top_index, div in enumerate(version.divs, 1):
        version_slots.update(visit(div, 1, top_index, (), None))
    if len(specs) == 1:
        builder.node(
            f"{vkey}:synthetic-chapter", "chapter", version_slots, **_common(book, version),
            chapter="1", chapter_index=1,
        )

    for i, (last_slot, linebreak) in enumerate(endings):
        boundary = _boundary(linebreak)
        if not boundary and i < len(endings) - 1:
            boundary = " "
        builder.set_slot_feature(last_slot, "boundary_utf8", boundary)

    bkey = f"{vkey}:book"
    builder.node(
        bkey, "book", version_slots, book=book_id, ocp_book=book.filename, title=book.title,
        text_structure=book.text_structure, version_title=version.title, author=version.author,
        language=version.language, version_fragment=version.fragment, source_file=book.source_path,
        source_sha256=book.source_sha256,
        division_labels=json.dumps([d.label for d in specs], ensure_ascii=False),
        division_delimiters=json.dumps([d.delimiter for d in specs], ensure_ascii=False),
        division_texts=json.dumps([d.text for d in specs], ensure_ascii=False),
    )
    for key in manuscripts.values():
        if key in builder.by_key:
            builder.edge("manuscript_of", key, bkey)
    for ridx, resource in enumerate(version.resources, 1):
        rkey = f"{vkey}:resource:{ridx}"
        builder.node(
            rkey, "resource", (), **_common(book, version), resource_name=resource.name,
            resource_info=json.dumps(resource.info, ensure_ascii=False), resource_url=resource.url,
            resource_index=ridx,
        )
        builder.edge("resource_of", rkey, bkey)


def build_tf_data(
    books: Iterable[Book], *,
    upstream_repository: str = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha",
    upstream_commit: str = "", converter_version: str = "0.1.0",
) -> TFData:
    builder = _Builder()
    for bidx, book in enumerate(books, 1):
        for vidx, (version, book_id) in enumerate(zip(book.versions, _book_ids(book)), 1):
            _add_version(builder, book, version, book_id, bidx, vidx)
    return builder.finalize(
        upstream_repository=upstream_repository,
        upstream_commit=upstream_commit,
        converter_version=converter_version,
    )
