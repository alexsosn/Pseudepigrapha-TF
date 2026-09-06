from __future__ import annotations


class Translations:
    """Convenience access to the explicit OCP generated-translation layer."""

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
            raise ValueError(f"feature {name!r} must be loaded for this Translations operation")
        return feature

    def _require_edge(self, name: str):
        edge = getattr(self.api.E, name, None)
        if edge is None:
            raise ValueError(f"edge feature {name!r} must be loaded for this Translations operation")
        return edge

    def _book_id(self, book_node: int) -> str:
        book_feature = getattr(self.api.F, "book", None)
        value = book_feature.v(book_node) if book_feature is not None else None
        if value:
            return str(value)
        section = self.api.T.sectionFromNode(book_node)
        if not section or not section[0]:
            raise ValueError(f"cannot resolve TF book id for node {book_node}")
        return str(section[0])

    def source_version(self, generated_book: int) -> int:
        version_kind = self._require_feature("version_kind")
        if version_kind.v(generated_book) != "generated_translation":
            raise ValueError(f"node {generated_book} is not a generated translation book")
        targets = tuple(self._require_edge("translation_of").f(generated_book))
        if len(targets) != 1:
            raise ValueError(
                f"generated translation book {generated_book} has {len(targets)} source versions; expected exactly 1"
            )
        return targets[0]

    def versions(
        self,
        *,
        work: str | None = None,
        language: str | None = None,
    ) -> tuple[dict[str, object], ...]:
        """List generated translation books with source and provenance metadata."""

        otype = self._require_feature("otype")
        version_kind = self._require_feature("version_kind")
        records: list[dict[str, object]] = []
        for node in tuple(otype.s("book")):
            if version_kind.v(node) != "generated_translation":
                continue
            node_work = str(self._feature("ocp_book", node, ""))
            target_language = str(
                self._feature("generated_language", node, self._feature("language", node, ""))
            )
            if work is not None and node_work != str(work):
                continue
            if language is not None and target_language != str(language):
                continue
            source = self.source_version(node)
            records.append(
                {
                    "node": node,
                    "id": self._book_id(node),
                    "work": node_work,
                    "title": str(self._feature("version_title", node, "")),
                    "language": target_language,
                    "source_node": source,
                    "source_id": self._book_id(source),
                    "generation_marker": str(self._feature("generation_marker", node, "")),
                    "generation_method": str(self._feature("generation_method", node, "")),
                    "generation_model": str(self._feature("generation_model", node, "")),
                }
            )
        return tuple(sorted(records, key=lambda record: (str(record["work"]), str(record["id"]))))

    def _primary_text(self, unit: int) -> str:
        reading_of = self._require_edge("reading_of")
        is_primary = self._require_feature("is_primary")
        reading_text = self._require_feature("reading_text")
        primary = [reading for reading in reading_of.t(unit) if is_primary.v(reading) == 1]
        if len(primary) != 1:
            raise ValueError(f"unit {unit} has {len(primary)} primary readings; expected exactly 1")
        return str(reading_text.v(primary[0]) or "")

    def _aligned_unit(self, generated_unit: int) -> dict[str, object]:
        targets = tuple(self._require_edge("translation_unit_of").f(generated_unit))
        if len(targets) != 1:
            raise ValueError(
                f"generated translation unit {generated_unit} has {len(targets)} source units; expected exactly 1"
            )
        source_unit = targets[0]
        return {
            "translation_unit": generated_unit,
            "source_unit": source_unit,
            "translation_unit_id": str(self._feature("unit_id", generated_unit, "")),
            "source_unit_id": str(self._feature("unit_id", source_unit, "")),
            "source_ref": str(self._feature("source_ref", source_unit, "")),
            "translation_text": self._primary_text(generated_unit),
            "source_text": self._primary_text(source_unit),
        }

    def aligned_units(self, generated_book: int) -> tuple[dict[str, object], ...]:
        """Return generated/source unit pairs in generated document order."""

        self.source_version(generated_book)
        units = tuple(self.api.L.d(generated_book, otype="unit"))
        unit_index = getattr(self.api.F, "unit_index", None)
        if unit_index is not None:
            units = tuple(sorted(units, key=lambda node: (unit_index.v(node) or 0, node)))
        return tuple(self._aligned_unit(unit) for unit in units)

    def passage(
        self,
        generated_book: str,
        chapter: str | int,
        verse: str | int,
    ) -> dict[str, object]:
        """Return one generated passage together with occurrence-aligned source units."""

        reference = (str(generated_book), str(chapter), str(verse))
        verse_node = self.api.T.nodeFromSection(reference)
        if verse_node is None:
            raise KeyError(f"Text-Fabric generated translation section not found: {reference!r}")
        book_nodes = tuple(self.api.L.u(verse_node, otype="book"))
        if len(book_nodes) != 1:
            raise ValueError(f"expected one containing generated book for {reference!r}, found {book_nodes}")
        book_node = book_nodes[0]
        source_book_node = self.source_version(book_node)
        units = tuple(self.api.L.d(verse_node, otype="unit"))
        unit_index = getattr(self.api.F, "unit_index", None)
        if unit_index is not None:
            units = tuple(sorted(units, key=lambda node: (unit_index.v(node) or 0, node)))
        return {
            "reference": reference,
            "book_node": book_node,
            "source_book_node": source_book_node,
            "units": tuple(self._aligned_unit(unit) for unit in units),
        }
