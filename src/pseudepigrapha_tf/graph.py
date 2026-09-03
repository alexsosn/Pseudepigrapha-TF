from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

from .model import Book, Div, Reading, Token, Unit, Version

INT_FEATURES = {
    "chapter_index", "div_index", "div_level", "is_gap", "is_omission",
    "is_primary", "manuscript_index", "reading_index", "reading_option",
    "resource_index", "token_count", "undefined_manuscript", "unit_index",
    "variant_position", "verse_index", "w_annotated",
}

FEATURE_DESCRIPTIONS = {
    "book": "BHSA-compatible book section identifier; one OCP version is one TF book",
    "chapter": "BHSA-compatible chapter section label",
    "verse": "BHSA-compatible verse section label",
    "g_word_utf8": "Unicode surface form, following the BHSA feature name",
    "trailer_utf8": "Unicode material following a word, following the BHSA feature name",
    "prefix_utf8": "Unicode material preceding a word",
    "ocp_book": "OCP book/@filename",
    "source_sha256": "SHA-256 digest of the source XML bytes",
    "reading_xml": "mixed XML content inside the OCP reading",
    "is_gap": "1 for an anchor slot created for an empty primary reading",
    "is_omission": "1 when an OCP reading has no textual content",
}

EDGE_DESCRIPTIONS = {
    "oslots": "Text-Fabric warp edge to occupied word slots",
    "parent": "source OCP div parent relation",
    "reading_of": "reading node to its OCP unit node",
    "variant_word_of": "variant_word node to its reading node",
    "witness": "reading node to manuscript nodes named by reading/@mss",
    "manuscript_of": "manuscript node to the BHSA-compatible book/version node",
    "resource_of": "resource node to the BHSA-compatible book/version node",
}


@dataclass
class TFData:
    node_features: dict[str, dict[int, str | int]]
    edge_features: dict[str, dict[int, set[int]]]
    metadata: dict[str, dict[str, str]]
    warnings: list[str] = field(default_factory=list)

    @property
    def max_slot(self) -> int:
        return max((n for n, kind in self.node_features.get("otype", {}).items() if kind == "word"), default=0)

    @property
    def max_node(self) -> int:
        return max(self.node_features.get("otype", {}), default=0)

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
        if any(not (1 <= slot <= self.max_slot) for slots in oslots.values() for slot in slots):
            errors.append("oslots points outside slot range")
        if any(set(values) - nodes for values in self.node_features.values()):
            errors.append("node feature refers to unknown nodes")
        for feature, values in self.edge_features.items():
            if feature == "oslots":
                continue
            if any(source not in nodes or any(target not in nodes for target in targets) for source, targets in values.items()):
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

    def finalize(self) -> TFData:
        max_slot = self.next_slot - 1
        node_features = {name: dict(values) for name, values in self.slot_features.items()}
        otype = {n: "word" for n in range(1, max_slot + 1)}
        key_to_node: dict[str, int] = {}
        oslots: dict[int, set[int]] = {}
        for node_id, obj in enumerate(self.objects, max_slot + 1):
            key_to_node[obj.key] = node_id
            otype[node_id] = obj.kind
            oslots[node_id] = set(obj.slots)
            for name, value in obj.features.items():
                node_features.setdefault(name, {})[node_id] = value
        node_features["otype"] = otype
        edges: dict[str, dict[int, set[int]]] = {"oslots": oslots}
        for feature, source, target in self.edges:
            edges.setdefault(feature, {}).setdefault(key_to_node[source], set()).add(key_to_node[target])
        data = TFData(node_features, edges, _metadata(node_features, edges), self.warnings)
        if failures := data.validate():
            raise ValueError("invalid generated Text-Fabric graph: " + "; ".join(failures))
        return data


def _metadata(node_features, edge_features):
    meta = {
        "": {
            "dataset": "Pseudepigrapha-TF",
            "datasetName": "Online Critical Pseudepigrapha Text-Fabric conversion",
            "source": "Online Critical Pseudepigrapha",
            "sourceUrl": "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha",
            "version": "0.1",
            "writtenBy": "Pseudepigrapha-TF converter",
        },
        "otext": {
            "sectionTypes": "book,chapter,verse",
            "sectionFeatures": "book,chapter,verse",
            "fmt:text-orig-full": "{g_word_utf8}{trailer_utf8}",
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
            out.append(char); sep = False
        elif not sep:
            out.append("_"); sep = True
    return "".join(out).strip("_") or "version"


def _book_ids(book: Book) -> list[str]:
    if len(book.versions) == 1:
        return [book.filename]
    used: dict[str, int] = {}
    result = []
    for version in book.versions:
        base = f"{book.filename}__{_slug(version.title)}"
        used[base] = used.get(base, 0) + 1
        result.append(base if used[base] == 1 else f"{base}_{used[base]}")
    return result


def _option(reading: Reading, fallback: int) -> int:
    try:
        return int(reading.option)
    except (TypeError, ValueError):
        return fallback


def _common(book: Book, version: Version) -> dict[str, str]:
    return {"ocp_book": book.filename, "version_title": version.title}


def _surface(token: Token, book: Book, version: Version, unit: Unit, option: int):
    return {
        "g_word_utf8": token.text, "trailer_utf8": token.trailer, "prefix_utf8": token.prefix,
        "language": token.lang or version.language, "lex": token.lex, "morph": token.morph,
        "style": token.style, "w_annotated": 1 if token.annotated else None,
        "ocp_book": book.filename, "version_title": version.title,
        "unit_id": unit.unit_id, "reading_option": option,
    }


def _unit(builder: _Builder, book: Book, version: Version, vkey: str, unit: Unit, index: int, manuscripts: dict[str, str]) -> set[int]:
    if not unit.readings:
        raise ValueError(f"{book.filename}/{version.title}: unit {unit.unit_id!r} has no readings")
    pidx = next((i for i, r in enumerate(unit.readings) if r.option == "0"), 0)
    if unit.readings[pidx].option != "0":
        builder.warnings.append(f"{book.filename}/{version.title} unit {unit.unit_id}: no option=0; using first reading as primary")
    primary = unit.readings[pidx]
    poption = _option(primary, pidx)
    slots = {builder.slot(**_surface(t, book, version, unit, poption)) for t in primary.tokens}
    if not slots:
        slots = {builder.slot(is_gap=1, language=version.language, ocp_book=book.filename,
                              version_title=version.title, unit_id=unit.unit_id, reading_option=poption)}
    ukey = f"{vkey}:unit:{index}"
    builder.node(ukey, "unit", slots, **_common(book, version), unit_id=unit.unit_id,
                 unit_index=index, group=unit.group, parallel=unit.parallel)
    for ridx, reading in enumerate(unit.readings, 1):
        option = _option(reading, ridx - 1)
        rkey = f"{ukey}:reading:{ridx}"
        primary_flag = ridx - 1 == pidx
        builder.node(rkey, "reading", slots, **_common(book, version), unit_id=unit.unit_id,
                     reading_option=option, reading_option_source=reading.option, reading_index=ridx,
                     reading_text=reading.text, reading_xml=reading.content_xml,
                     mss=reading.mss_raw.strip(), linebreak=reading.linebreak, indent=reading.indent,
                     token_count=len(reading.tokens), is_omission=1 if not reading.text else None,
                     is_primary=1 if primary_flag else None)
        builder.edge("reading_of", rkey, ukey)
        for abbrev in reading.witnesses:
            mkey = manuscripts.get(abbrev)
            if mkey is None:
                mkey = f"{vkey}:ms:undefined:{_slug(abbrev)}"
                if mkey not in builder.by_key:
                    builder.node(mkey, "manuscript", (), **_common(book, version), ms_abbrev=abbrev, undefined_manuscript=1)
                    builder.warnings.append(f"{book.filename}/{version.title}: reading cites undeclared manuscript {abbrev!r}")
                manuscripts[abbrev] = mkey
            builder.by_key[mkey].slots.update(slots)
            builder.edge("witness", rkey, mkey)
        if not primary_flag:
            for pos, token in enumerate(reading.tokens, 1):
                wkey = f"{rkey}:word:{pos}"
                builder.node(wkey, "variant_word", slots, **_common(book, version),
                             **{k: v for k, v in _surface(token, book, version, unit, option).items()
                                if k not in {"ocp_book", "version_title"}}, variant_position=pos)
                builder.edge("variant_word_of", wkey, rkey)
    return slots


def _version(builder: _Builder, book: Book, version: Version, book_id: str, book_index: int, version_index: int) -> None:
    vkey = f"book:{book_index}:version:{version_index}"
    manuscript_keys: dict[str, str] = {}
    for midx, ms in enumerate(version.manuscripts, 1):
        key = f"{vkey}:ms:{midx}"
        if ms.abbrev in manuscript_keys:
            builder.warnings.append(f"{book.filename}/{version.title}: duplicate manuscript abbreviation {ms.abbrev!r}")
        else:
            manuscript_keys[ms.abbrev] = key
        builder.node(key, "manuscript", (), **_common(book, version), ms_abbrev=ms.abbrev,
                     ms_name=ms.name, ms_name_xml=ms.name_xml, ms_language=ms.language, ms_show=ms.show,
                     bibliography=json.dumps(ms.bibliography, ensure_ascii=False),
                     bibliography_xml=json.dumps(ms.bibliography_xml, ensure_ascii=False), manuscript_index=midx)

    unit_counter = chapter_counter = verse_counter = 0
    version_slots: set[int] = set()
    specs = version.divisions
    div_serial = 0

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
                slots.update(_unit(builder, book, version, vkey, item, unit_counter, manuscript_keys))
        label = specs[level - 1].label if level <= len(specs) else ""
        builder.node(dkey, "div", slots, **_common(book, version), div_number=div.number,
                     div_level=level, div_label=label, div_fragment=div.fragment,
                     div_path="/".join(dpath), div_index=sibling)
        if parent:
            builder.edge("parent", dkey, parent)
        if len(specs) == 1 and level == 1:
            verse_counter += 1
            builder.node(f"{dkey}:verse", "verse", slots, **_common(book, version), verse=div.number, verse_index=verse_counter)
        elif len(specs) >= 2 and level == 1:
            chapter_counter += 1
            builder.node(f"{dkey}:chapter", "chapter", slots, **_common(book, version), chapter=div.number, chapter_index=chapter_counter)
        elif len(specs) >= 2 and level == 2:
            verse_counter += 1
            builder.node(f"{dkey}:verse", "verse", slots, **_common(book, version), verse=div.number, verse_index=verse_counter)
        return slots

    for top_index, div in enumerate(version.divs, 1):
        version_slots.update(visit(div, 1, top_index, (), None))
    if len(specs) == 1:
        builder.node(f"{vkey}:synthetic-chapter", "chapter", version_slots, **_common(book, version), chapter="1", chapter_index=1)

    bkey = f"{vkey}:book"
    builder.node(bkey, "book", version_slots, book=book_id, ocp_book=book.filename, title=book.title,
                 text_structure=book.text_structure, version_title=version.title, author=version.author,
                 language=version.language, version_fragment=version.fragment, source_path=book.source_path,
                 source_sha256=book.source_sha256,
                 division_labels=json.dumps([d.label for d in specs], ensure_ascii=False),
                 division_delimiters=json.dumps([d.delimiter for d in specs], ensure_ascii=False))
    for key in manuscript_keys.values():
        if key in builder.by_key:
            builder.edge("manuscript_of", key, bkey)
    for ridx, resource in enumerate(version.resources, 1):
        rkey = f"{vkey}:resource:{ridx}"
        builder.node(rkey, "resource", version_slots, **_common(book, version), resource_name=resource.name,
                     resource_info=json.dumps(resource.info, ensure_ascii=False), resource_url=resource.url, resource_index=ridx)
        builder.edge("resource_of", rkey, bkey)


def build_tf_data(books: Iterable[Book]) -> TFData:
    builder = _Builder()
    for bidx, book in enumerate(books, 1):
        for vidx, (version, book_id) in enumerate(zip(book.versions, _book_ids(book)), 1):
            _version(builder, book, version, book_id, bidx, vidx)
    return builder.finalize()
