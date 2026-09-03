from __future__ import annotations

from typing import Iterable


class Apparatus:
    """Convenience access to OCP apparatus relations on a loaded Text-Fabric API."""

    def __init__(self, api) -> None:
        self.api = api

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
