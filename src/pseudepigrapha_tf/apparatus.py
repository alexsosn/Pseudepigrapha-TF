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

    def _require_edge(self, name: str):
        edge = getattr(self.api.E, name, None)
        if edge is None:
            raise ValueError(f"edge feature {name!r} must be loaded for this Apparatus operation")
        return edge

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

    def _witnesses(self, owner: int) -> dict[str, dict[str, object]]:
        """Return all linked witnesses with explicit upstream declaration provenance."""

        manuscript_of = getattr(self.api.E, "manuscript_of", None)
        if manuscript_of is None:
            raise ValueError("manuscript_of edge feature must be loaded for this Apparatus operation")
        undefined_manuscript = self._require_feature("undefined_manuscript")
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
                "declared": undefined_manuscript.v(manuscript) != 1,
                "language": self._feature("ms_language", manuscript, ""),
                "name": self._feature("ms_name", manuscript, ""),
                "show": self._feature("ms_show", manuscript, ""),
            }
        return witnesses

    def unit_readings(self, unit: int) -> tuple[int, ...]:
        reading_of = self._require_edge("reading_of")
        return tuple(sorted(reading_of.t(unit)))

    def reading_text(self, reading: int) -> str:
        return self.api.F.reading_text.v(reading) or ""

    def reading_tokens(self, reading: int) -> tuple[int, ...]:
        """Return the actual token nodes of one reading, never its technical locus.

        Primary textual readings return their Text-Fabric ``word`` slots.
        Non-primary textual readings return their ``variant_word`` nodes.
        Explicit omissions return no token nodes, including when Text-Fabric
        gives the reading a technical/shared ``oslots`` locus.
        """

        reading_text = self._require_feature("reading_text")
        is_primary = self._require_feature("is_primary")
        text = reading_text.v(reading) or ""
        if not text:
            return ()

        if is_primary.v(reading) == 1:
            oslots = getattr(self.api.E, "oslots", None)
            slots = getattr(oslots, "s", None) if oslots is not None else None
            if slots is None:
                raise ValueError(
                    "Text-Fabric oslots slot lookup must be available for primary reading_tokens()"
                )
            return tuple(slots(reading))

        variant_word_of = getattr(self.api.E, "variant_word_of", None)
        if variant_word_of is None:
            raise ValueError(
                "edge feature 'variant_word_of' must be loaded for non-primary reading_tokens()"
            )
        variants = tuple(sorted(variant_word_of.t(reading)))
        if not variants:
            raise ValueError(
                f"non-primary reading {reading} has text but no variant_word tokens"
            )
        return variants

    def witness_reading(self, unit: int, manuscript: int) -> int | None:
        witness = self._require_edge("witness")
        matches = [
            reading
            for reading in self.unit_readings(unit)
            if manuscript in witness.f(reading)
        ]
        if len(matches) > 1:
            raise ValueError(f"manuscript {manuscript} has multiple readings at unit {unit}: {matches}")
        return matches[0] if matches else None

    def _state_for_reading(self, unit: int, reading: int | None) -> dict[str, object]:
        """Build one witness-state record from an already resolved reading."""

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

    def witness_state(self, unit: int, manuscript: int) -> dict[str, object]:
        """Return an explicit witness state at one apparatus unit.

        ``omission`` means the witness is explicitly assigned to an empty OCP
        reading. ``unattested`` means no reading at the unit cites the witness.
        The latter must not be silently interpreted as an omission or lacuna.
        """

        return self._state_for_reading(unit, self.witness_reading(unit, manuscript))

    def witness_text(self, manuscript: int, units: Iterable[int] | None = None) -> str:
        if units is None:
            otype = getattr(self.api.F, "otype", None)
            selector = getattr(otype, "s", None) if otype is not None else None
            node_type = getattr(otype, "v", None) if otype is not None else None
            if selector is None or node_type is None:
                raise ValueError(
                    "units must be supplied when the TF otype feature has no selector/type lookup"
                )

            witness = getattr(self.api.E, "witness", None)
            witness_sources = getattr(witness, "t", None) if witness is not None else None
            if witness_sources is None:
                raise ValueError(
                    "witness edge feature with reverse lookup must be loaded for global witness_text()"
                )
            reading_of = getattr(self.api.E, "reading_of", None)
            reading_owner = getattr(reading_of, "f", None) if reading_of is not None else None
            if reading_owner is None:
                raise ValueError(
                    "reading_of edge feature with forward lookup must be loaded for global witness_text()"
                )

            reading_by_unit: dict[int, int] = {}
            for reading in witness_sources(manuscript):
                source_type = node_type(reading)
                if source_type == "orphan_reading":
                    continue
                if source_type != "reading":
                    raise ValueError(
                        f"witness edge source {reading} has unexpected node type {source_type!r}"
                    )
                owners = tuple(reading_owner(reading))
                if not owners:
                    raise ValueError(f"reading {reading} has no reading_of unit")
                if len(owners) != 1:
                    raise ValueError(f"reading {reading} has multiple reading_of units: {owners}")
                unit = owners[0]
                previous = reading_by_unit.get(unit)
                if previous is not None:
                    matches = sorted((previous, reading))
                    raise ValueError(
                        f"manuscript {manuscript} has multiple readings at unit {unit}: {matches}"
                    )
                reading_by_unit[unit] = reading

            chunks: list[str] = []
            for unit in selector("unit"):
                reading = reading_by_unit.get(unit)
                if reading is not None:
                    text = self.reading_text(reading)
                    if text:
                        chunks.append(text)
            return " ".join(chunks)

        chunks: list[str] = []
        for unit in units:
            reading = self.witness_reading(unit, manuscript)
            if reading is not None:
                text = self.reading_text(reading)
                if text:
                    chunks.append(text)
        return " ".join(chunks)

    def apparatus(self, unit: int) -> tuple[dict[str, object], ...]:
        is_primary = self._require_feature("is_primary")
        witness = self._require_edge("witness")
        result = []
        for reading in self.unit_readings(unit):
            result.append(
                {
                    "reading": reading,
                    "text": self.reading_text(reading),
                    "primary": is_primary.v(reading) == 1,
                    "witnesses": tuple(sorted(witness.f(reading))),
                }
            )
        return tuple(result)

    def _passage_from_context(
        self,
        reference: tuple[str, str, str],
        verse_node: int,
        manuscripts: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        """Build a passage from already validated, request-local context."""

        is_primary = self._require_feature("is_primary")
        witness = self._require_edge("witness")
        units = tuple(self.api.L.d(verse_node, otype="unit"))
        source_refs: list[str] = []
        unit_records: list[dict[str, object]] = []
        reading_by_witness: dict[int, dict[int, int]] = {}
        for unit in units:
            source_ref = str(self._feature("source_ref", unit, ""))
            if source_ref and source_ref not in source_refs:
                source_refs.append(source_ref)
            readings: list[dict[str, object]] = []
            unit_witnesses: dict[int, int] = {}
            for reading in self.unit_readings(unit):
                witness_nodes = tuple(sorted(witness.f(reading)))
                for manuscript in witness_nodes:
                    previous = unit_witnesses.get(manuscript)
                    if previous is not None:
                        matches = sorted((previous, reading))
                        raise ValueError(
                            f"manuscript {manuscript} has multiple readings at unit {unit}: {matches}"
                        )
                    unit_witnesses[manuscript] = reading
                text = self.reading_text(reading)
                readings.append(
                    {
                        "node": reading,
                        "text": text,
                        "primary": is_primary.v(reading) == 1,
                        "omission": text == "",
                        "witness_nodes": witness_nodes,
                        "witnesses": tuple(
                            str(self._feature("ms_abbrev", manuscript, manuscript))
                            for manuscript in witness_nodes
                        ),
                    }
                )
            reading_by_witness[unit] = unit_witnesses
            unit_records.append(
                {
                    "node": unit,
                    "unit": str(self._feature("unit_id", unit, unit)),
                    "source_ref": source_ref,
                    "readings": tuple(readings),
                }
            )

        witness_records: dict[str, dict[str, object]] = {}
        for abbrev, manuscript_record in manuscripts.items():
            manuscript = int(manuscript_record["node"])
            segments = tuple(
                self._state_for_reading(unit, reading_by_witness[unit].get(manuscript))
                for unit in units
            )
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

        book_nodes = tuple(self.api.L.u(verse_node, otype="book"))
        if len(book_nodes) != 1:
            raise ValueError(f"expected one containing book for {reference!r}, found {book_nodes}")
        book_node = book_nodes[0]
        return self._passage_from_context(reference, verse_node, self._witnesses(book_node))

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

        textual_versions = tuple(
            sorted(
                (
                    (self._book_id(node), node)
                    for node in self.api.F.otype.s("book")
                    if str(ocp_book.v(node) or "") == work
                ),
                key=lambda item: item[0],
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

        if not textual_versions and not metadata_nodes:
            raise KeyError(f"OCP work not found in loaded Text-Fabric data: {work!r}")

        owner_for_title = textual_versions[0][1] if textual_versions else metadata_nodes[0]
        title = str(self._feature("title", owner_for_title, ""))

        versions: dict[str, dict[str, object]] = {}
        for version_id, book_node in textual_versions:
            manuscripts = self._witnesses(book_node)
            reference = (version_id, chapter, verse)
            verse_node = self.api.T.nodeFromSection(reference)
            if verse_node is None:
                passage = None
            else:
                book_nodes = tuple(self.api.L.u(verse_node, otype="book"))
                if len(book_nodes) != 1:
                    raise ValueError(f"expected one containing book for {reference!r}, found {book_nodes}")
                containing_book = book_nodes[0]
                passage_manuscripts = (
                    manuscripts if containing_book == book_node else self._witnesses(containing_book)
                )
                passage = self._passage_from_context(reference, verse_node, passage_manuscripts)
            versions[version_id] = {
                "node": book_node,
                "id": version_id,
                "title": str(self._feature("version_title", book_node, "")),
                "language": self._feature("language", book_node, ""),
                "author": self._feature("author", book_node, ""),
                "status": "available" if passage is not None else "not_present",
                "witnesses": manuscripts,
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
                "witnesses": self._witnesses(metadata_node),
                "passage": None,
            }

        return {
            "work": work,
            "title": title,
            "reference": (chapter, verse),
            "versions": versions,
            "metadata_only_versions": metadata_only_versions,
        }
