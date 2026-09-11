from __future__ import annotations

from pathlib import Path

from .graph import TFData


def _positive_index(data: TFData, feature: str, node: int) -> int | None:
    value = data.node_features.get(feature, {}).get(node)
    try:
        index = int(value)
    except (TypeError, ValueError):
        return None
    return index if index > 0 else None


def _version_key(data: TFData, node: int) -> tuple[str, str]:
    return (
        str(data.node_features.get("ocp_book", {}).get(node, "")),
        str(data.node_features.get("version_id", {}).get(node, "")),
    )


def reading_occurrence_ownership_ok(
    source_dir: str | Path,
    data: TFData,
    node_index: dict[str, list[int]],
) -> bool:
    """Bind every reading to the exact source-order unit occurrence.

    The ordinary ownership audit already checks exact version and literal source
    identity. This predicate adds two relation-independent occurrence signals:

    * unit nodes carry their monotonically increasing ``unit_index``;
    * reading nodes preserve creation order and reset ``reading_index`` to 1 at
      the start of every unit, because Text-Fabric finalization preserves source
      creation order within each node type.

    Reconstructing the unit→reading grouping from those two facts means a bad
    ``reading_of`` edge cannot be hidden by also moving the reading's ``oslots``.
    The oslots equality remains a second structural check. The surrounding
    semantic report independently rereads raw XML once for payload/source parity;
    this helper deliberately performs no additional source I/O.
    """

    del source_dir
    reading_of = data.edge_features.get("reading_of", {})
    oslots = data.edge_features.get("oslots", {})

    units_by_version: dict[tuple[str, str], list[int]] = {}
    for unit in node_index.get("unit", []):
        key = _version_key(data, unit)
        if not all(key):
            return False
        units_by_version.setdefault(key, []).append(unit)

    readings_by_version: dict[tuple[str, str], list[int]] = {}
    for reading in node_index.get("reading", []):
        key = _version_key(data, reading)
        if not all(key):
            return False
        readings_by_version.setdefault(key, []).append(reading)

    if set(units_by_version) != set(readings_by_version):
        return False

    for key, units in units_by_version.items():
        ordered_units = sorted(
            units,
            key=lambda node: (
                _positive_index(data, "unit_index", node) or 0,
                node,
            ),
        )
        unit_indices = [_positive_index(data, "unit_index", node) for node in ordered_units]
        if unit_indices != list(range(1, len(ordered_units) + 1)):
            return False

        readings = readings_by_version[key]
        unit_position = -1
        expected_reading_index = 0
        for reading in readings:
            reading_index = _positive_index(data, "reading_index", reading)
            if reading_index is None:
                return False
            if reading_index == 1:
                unit_position += 1
                expected_reading_index = 1
            else:
                expected_reading_index += 1
                if reading_index != expected_reading_index:
                    return False

            if unit_position < 0 or unit_position >= len(ordered_units):
                return False
            expected_unit = ordered_units[unit_position]
            targets = reading_of.get(reading, set())
            if targets != {expected_unit}:
                return False

            reading_slots = oslots.get(reading, set())
            unit_slots = oslots.get(expected_unit, set())
            if not reading_slots or reading_slots != unit_slots:
                return False

        if unit_position + 1 != len(ordered_units):
            return False

    return True
