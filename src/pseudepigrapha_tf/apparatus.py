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

        manuscript_of = getattr(self.api.E, "manuscript_of", None)
        if manuscript_of is None:
            raise ValueError("passage() requires the manuscript_of edge feature to be loaded")
        manuscripts = tuple(
            sorted(
                manuscript_of.t(book_node),
                key=lambda node: (str(self._feature("ms_abbrev", node, "")), node),
            )
        )

        witness_records: dict[str, dict[str, object]] = {}
        for manuscript in manuscripts:
            abbrev = str(self._feature("ms_abbrev", manuscript, manuscript))
            if abbrev in witness_records:
                raise ValueError(f"duplicate manuscript abbreviation in TF book {book!r}: {abbrev!r}")
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
                "node": manuscript,
                "abbrev": abbrev,
                "language": self._feature("ms_language", manuscript, ""),
                "name": self._feature("ms_name", manuscript, ""),
                "show": self._feature("ms_show", manuscript, ""),
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
