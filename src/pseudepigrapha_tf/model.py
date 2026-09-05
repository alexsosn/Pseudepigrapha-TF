from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Token:
    text: str
    prefix: str = ""
    trailer: str = ""
    morph: str | None = None
    lex: str | None = None
    style: str | None = None
    lang: str | None = None
    annotated: bool = False


@dataclass(frozen=True)
class DivisionSpec:
    label: str
    delimiter: str = ""
    text: str = ""


@dataclass(frozen=True)
class Resource:
    name: str
    info: tuple[str, ...]
    url: str = ""


@dataclass(frozen=True)
class Manuscript:
    abbrev: str
    language: str
    show: str
    name: str
    name_xml: str
    bibliography: tuple[str, ...]
    bibliography_xml: tuple[str, ...]


@dataclass
class Reading:
    option: str
    witnesses: tuple[str, ...]
    mss_raw: str
    linebreak: str
    indent: str
    text: str
    content_xml: str
    tokens: tuple[Token, ...]


@dataclass
class Unit:
    unit_id: str
    group: str
    parallel: str
    linebreak: str
    readings: tuple[Reading, ...]


@dataclass(frozen=True)
class Ellipsis:
    """OCP structural omission marker; upstream spells the element ``elipsis``."""

    text: str = ""
    source_tag: str = "elipsis"


@dataclass
class OrphanReading:
    """Reading found directly under a div, outside the source DTD's unit wrapper."""

    reading: Reading
    source_tag: str = "reading"


@dataclass
class Div:
    number: str
    fragment: str
    items: tuple["Div | Unit | Ellipsis | OrphanReading", ...] = ()

    @property
    def children(self) -> tuple["Div", ...]:
        return tuple(item for item in self.items if isinstance(item, Div))

    @property
    def units(self) -> tuple[Unit, ...]:
        return tuple(item for item in self.items if isinstance(item, Unit))

    @property
    def ellipses(self) -> tuple[Ellipsis, ...]:
        return tuple(item for item in self.items if isinstance(item, Ellipsis))

    @property
    def orphan_readings(self) -> tuple[OrphanReading, ...]:
        return tuple(item for item in self.items if isinstance(item, OrphanReading))


@dataclass
class Version:
    title: str
    author: str
    language: str
    fragment: str
    divisions: tuple[DivisionSpec, ...]
    resources: tuple[Resource, ...]
    manuscripts: tuple[Manuscript, ...]
    divs: tuple[Div, ...]


@dataclass
class Book:
    filename: str
    title: str
    text_structure: str
    versions: tuple[Version, ...]
    source_path: str = ""
    source_sha256: str = ""
