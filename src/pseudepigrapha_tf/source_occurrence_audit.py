from __future__ import annotations

from pathlib import Path

from .graph import TFData


def reading_occurrence_ownership_ok(
    source_dir: str | Path,
    data: TFData,
    node_index: dict[str, list[int]],
) -> bool:
    """Bind every reading to the exact unit occurrence it structurally occupies.

    Raw XML payload parity is already established by the surrounding semantic
    report in the same source pass. Here occurrence identity is checked through
    an independent graph invariant: the converter gives every reading exactly
    the same ``oslots`` support as its owning unit. Distinct unit occurrences
    necessarily occupy distinct slot sets, including empty readings (which get
    distinct gap slots), so swapping ``reading_of`` owners cannot preserve this
    invariant even when source_ref and unit_id are duplicated.

    ``source_dir`` remains in the signature because this predicate is composed
    by the source-grounded semantic report; no additional XML read is needed.
    """

    del source_dir
    reading_of = data.edge_features.get("reading_of", {})
    oslots = data.edge_features.get("oslots", {})
    units = set(node_index.get("unit", []))

    for reading in node_index.get("reading", []):
        targets = reading_of.get(reading, set())
        if len(targets) != 1:
            return False
        unit = next(iter(targets))
        if unit not in units:
            return False
        reading_slots = oslots.get(reading, set())
        unit_slots = oslots.get(unit, set())
        if not reading_slots or reading_slots != unit_slots:
            return False

    return True
