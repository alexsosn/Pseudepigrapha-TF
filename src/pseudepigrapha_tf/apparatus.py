from __future__ import annotations

from collections import Counter
from typing import Iterable


class Apparatus:
    """Convenience access to OCP apparatus relations on a loaded Text-Fabric API."""

    def __init__(self, api) -> None:
        self.api = api

    def _feature(self, name: str, node: int, default=None):
        feature = getattr(self.api.F, name, None)
        if feature is None:
            return default
        value = feature.v(node)
        return default if value is None else value

    def _require_feature(self, name: str):
        feature = getattr(self.api.F, name, None)
        if feature is None:
            raise ValueError(f"feature {name!r} must be loaded for this Apparatus operation")
        return feature

    def _book_id(self, book_node: int) -> str:
        """Resolve the canonical TF book/section id for a textual version.

        Text-Fabric uses section features internally when compiling ``T`` and
        does not guarantee that a loaded section feature is exposed as a normal
        ``F.<name>`` feature on section nodes. Resolve through the canonical
        section API instead of depending on that implementation detail.
        """

        slots = tuple(self.api.L.d(book_node, otype="word"))
        if not slots:
            raise ValueError(f"textual OCP version node {book_node} contains no word slots")
        section = self.api.T.sectionFromNode(slots[0])
        if not section or not section[0]:
            raise ValueError(f"cannot resolve TF book section id for textual OCP version node {book_node}")
        return str(section[0])

    def _declared_witnesses(self, owner: int) -> dict[str, dict[str, object]]:
        manuscript_of = getattr(self.api.E, "manuscript_of", None)
        if manuscript_of is None:
            raise ValueError("manuscript_of edge feature must be loaded for this Apparatus operation")
        nodes = tuple(
            sorted(
                manuscript_of.t(owner),
                key=lambda node: (str(self._feature("ms_abbrev", node, "")), node),
            )
        )
        witnesses: dict[str, dict[str, object]] = {}
        for manuscript in nodes:
            abbrev = str(self._feature("ms_abbrev", manuscript, manuscript))
            if abbrev in witnesses:
                raise ValueError(f"duplicate manuscript abbreviation for TF version owner {owner}: {abbrev!r}")
            witnesses[abbrev] = {
                "node": manuscript,
                "abbrev": abbrev,
                "language": self._feature("ms_language", manuscript, ""),
                "name": self._feature("ms_name", manuscript, ""),
                "show": self._feature("ms_show", manuscript, ""),
            }
        return witnesses

    def unit_readings(self, unit: int) -> tuple[int, ...]:
        return tuple(sorted(self.api.E.reading_of.t(unit)))

    def reading_text(self, reading: int) -> str:
        return self.api.F.reading_text.v(reading) or ""

    def reading_tokens(self, reading: int) -> tuple[int, ...]:
        variants = tuple(sorted(self.api.E.variant_word_of.t(reading)))
        if variants:
            return variants
        oslots = getattr(self.api.E, "oslots", None)
        return tuple(oslots.f(reading)) if oslots is not None else ()

    def witness_reading(self, unit: int, manuscript: int) -> int | None:
        matches = [
            reading
            for reading in self.unit_readings(unit)
            if manuscript in self.api.E.witness.f(reading)
        ]
        if len(matches) > 1:
            raise ValueError(f"manuscript {manuscript} has multiple readings at unit {unit}: {matches}")
        return matches[0] if matches else None

    def witness_state(self, unit: int, manuscript: int) -> dict[str, object]:
        """Return an explicit witness state at one apparatus unit.

        ``omission`` means the witness is explicitly assigned to an empty OCP
        reading. ``unattested`` means no reading at the unit cites the witness.
        The latter must not be silently interpreted as an omission or lacuna.
        """

        reading = self.witness_reading(unit, manuscript)
        unit_id = str(self._feature("unit_id", unit, unit))
        if reading is None:
            return {
                "unit": unit_id,
                "unit_node": unit,
                "status": "unattested",
                "reading": None,
                "text": None,
            }
        text = self.reading_text(reading)
        return {
            "unit": unit_id,
            "unit_node": unit,
            "status": "omission" if text == "" else "reading",
            "reading": reading,
            "text": text,
        }

    def witness_text(self, manuscript: int, units: Iterable[int] | None = None) -> str:
        if units is None:
            selector = getattr(self.api.F.otype, "s", None)
            if selector is None:
                raise ValueError("units must be supplied when the TF otype feature has no selector")
            units = selector("unit")
        chunks: list[str] = []
        for unit in units:
            reading = self.witness_reading(unit, manuscript)
            if reading is not None:
                text = self.reading_text(reading)
                if text:
                    chunks.append(text)
        return " ".join(chunks)

    def apparatus(self, unit: int) -> tuple[dict[str, object], ...]:
        result = []
        for reading in self.unit_readings(unit):
            result.append(
                {
                    "reading": reading,
                    "text": self.reading_text(reading),
                    "primary": self.api.F.is_primary.v(reading) == 1,
                    "witnesses": tuple(sorted(self.api.E.witness.f(reading))),
                }
            )
        return tuple(result)

    def passage(self, book: str, chapter: str | int, verse: str | int) -> dict[str, object]:
        """Return one TF verse together with its full OCP apparatus by witness.

        This is the high-level entry point for questions such as "give me
        1En 1:2 in every witness". The result preserves the distinction between
        an explicit empty reading (``omission``) and a witness for which the
        source gives no reading at that unit (``unattested``).

        A witness-level ``text`` is returned only when every unit in the verse is
        attested (including explicit omissions). ``attested_text`` is always the
        concatenation of the non-empty readings that are actually present.
        """

        reference = (str(book), str(chapter), str(verse))
        verse_node = self.api.T.nodeFromSection(reference)
        if verse_node is None:
            raise KeyError(f"Text-Fabric section not found: {reference!r}")

        units = tuple(self.api.L.d(verse_node, otype="unit"))
        book_nodes = tuple(self.api.L.u(verse_node, otype="book"))
        if len(book_nodes) != 1:
            raise ValueError(f"expected one containing book for {reference!r}, found {book_nodes}")
        book_node = book_nodes[0]

        source_refs: list[str] = []
        unit_records: list[dict[str, object]] = []
        for unit in units:
            source_ref = str(self._feature("source_ref", unit, ""))
            if source_ref and source_ref not in source_refs:
                source_refs.append(source_ref)
            readings: list[dict[str, object]] = []
            for reading in self.unit_readings(unit):
                witness_nodes = tuple(sorted(self.api.E.witness.f(reading)))
                readings.append(
                    {
                        "node": reading,
                        "text": self.reading_text(reading),
                        "primary": self._feature("is_primary", reading, 0) == 1,
                        "omission": self.reading_text(reading) == "",
                        "witness_nodes": witness_nodes,
                        "witnesses": tuple(
                            str(self._feature("ms_abbrev", manuscript, manuscript))
                            for manuscript in witness_nodes
                        ),
                    }
                )
            unit_records.append(
                {
                    "node": unit,
                    "unit": str(self._feature("unit_id", unit, unit)),
                    "source_ref": source_ref,
                    "readings": tuple(readings),
                }
            )

        manuscripts = self._declared_witnesses(book_node)
        witness_records: dict[str, dict[str, object]] = {}
        for abbrev, manuscript_record in manuscripts.items():
            manuscript = int(manuscript_record["node"])
            segments = tuple(self.witness_state(unit, manuscript) for unit in units)
            coverage = Counter(str(segment["status"]) for segment in segments)
            complete = coverage["unattested"] == 0
            chunks = [
                str(segment["text"])
                for segment in segments
                if segment["status"] == "reading" and segment["text"]
            ]
            attested_text = " ".join(chunks)
            witness_records[abbrev] = {
                **manuscript_record,
                "segments": segments,
                "coverage": dict(coverage),
                "complete": complete,
                "text": attested_text if complete else None,
                "attested_text": attested_text,
            }

        return {
            "reference": reference,
            "verse_node": verse_node,
            "source_refs": tuple(source_refs),
            "units": tuple(unit_records),
            "witnesses": witness_records,
        }

    def work_passage(self, work: str, chapter: str | int, verse: str | int) -> dict[str, object]:
        """Return the requested passage across every OCP version of one work.

        Textual versions are returned under ``versions`` and keyed by their
        stable TF book id (for example ``Multi__Greek``). A textual version whose
        requested section is absent remains in the result with
        ``status='not_present'`` and ``passage=None`` rather than disappearing.

        Upstream versions that contain metadata but no textual units are returned
        separately under ``metadata_only_versions``. This preserves the semantic
        distinction between "this version exists but OCP has no text for it" and
        "this textual version simply does not attest the requested section".
        """

        ocp_book = self._require_feature("ocp_book")
        work = str(work)
        chapter = str(chapter)
        verse = str(verse)

        textual_books = tuple(
            sorted(
                (
                    node
                    for node in self.api.F.otype.s("book")
                    if str(ocp_book.v(node) or "") == work
                ),
                key=self._book_id,
            )
        )
        metadata_nodes = tuple(
            sorted(
                (
                    node
                    for node in self.api.F.otype.s("version_metadata")
                    if str(ocp_book.v(node) or "") == work
                ),
                key=lambda node: str(self._feature("version_id", node, "")),
            )
        )

        if not textual_books and not metadata_nodes:
            raise KeyError(f"OCP work not found in loaded Text-Fabric data: {work!r}")

        owner_for_title = textual_books[0] if textual_books else metadata_nodes[0]
        title = str(self._feature("title", owner_for_title, ""))

        versions: dict[str, dict[str, object]] = {}
        for book_node in textual_books:
            version_id = self._book_id(book_node)
            try:
                passage = self.passage(version_id, chapter, verse)
            except KeyError:
                passage = None
            versions[version_id] = {
                "node": book_node,
                "id": version_id,
                "title": str(self._feature("version_title", book_node, "")),
                "language": self._feature("language", book_node, ""),
                "author": self._feature("author", book_node, ""),
                "status": "available" if passage is not None else "not_present",
                "witnesses": self._declared_witnesses(book_node),
                "passage": passage,
            }

        metadata_only_versions: dict[str, dict[str, object]] = {}
        for metadata_node in metadata_nodes:
            version_id = str(self._feature("version_id", metadata_node, ""))
            if not version_id:
                raise ValueError(
                    f"metadata-only OCP version node {metadata_node} has no loaded version_id feature"
                )
            metadata_only_versions[version_id] = {
                "node": metadata_node,
                "id": version_id,
                "title": str(self._feature("version_title", metadata_node, "")),
                "language": self._feature("language", metadata_node, ""),
                "author": self._feature("author", metadata_node, ""),
                "status": "metadata_only",
                "witnesses": self._declared_witnesses(metadata_node),
                "passage": None,
            }

        return {
            "work": work,
            "title": title,
            "reference": (chapter, verse),
            "versions": versions,
            "metadata_only_versions": metadata_only_versions,
        }
