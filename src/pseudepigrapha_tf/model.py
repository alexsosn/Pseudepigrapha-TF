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


@dataclass
class Div:
    number: str
    fragment: str
    items: tuple["Div | Unit", ...] = ()

    @property
    def children(self) -> tuple["Div", ...]:
        return tuple(item for item in self.items if isinstance(item, Div))

    @property
    def units(self) -> tuple[Unit, ...]:
        return tuple(item for item in self.items if isinstance(item, Unit))


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
