# Issue 145 research — duplicate source-unit occurrence ownership

## Question

Can the independent source→TF semantic audit prove that readings remain owned by the correct source occurrence when two units in one version share the same upstream `(source_ref, unit_id)`?

## Source and graph representation

OCP permits repeated unit identities. The converter intentionally preserves the literal upstream `source_ref` and `unit_id`; it does not synthesize uniqueness into either field.

The core graph builder has a source-order identity: `_add_version()` increments one `unit_counter` through the complete version traversal, and `_add_unit()` writes that 1-based value as the unit node's `unit_index`. Each reading is created inside that exact `_add_unit()` call and immediately linked to the unit with `reading_of`.

Researcher-facing apparatus access relies on `reading_of`: `Apparatus.unit_readings()` reverse-resolves that edge, and passage/apparatus methods assemble each unit's readings from it. A wrong edge therefore changes which reading researchers see for the first versus second duplicate occurrence.

## Independent audit gap

The existing raw XML inventory records units and readings using work/version/source ref/unit id plus payload values, but not the source-order unit occurrence. The graph inventory mirrors those records. Both inventories are canonicalized as unordered JSON records before equality comparison.

`semantic_audit._ownership_edge_ok()` verifies every reading has exactly one `reading_of` target in the same exact source version and with equal `ocp_book`, `version_title`, `source_ref`, and `unit_id` features. When two units share those values, swapping their reading owners preserves all current predicates. The reading payload itself remains stamped on the reading node, so unordered raw↔graph payload parity also remains unchanged.

Minimal counterexample:

- unit occurrence 1: `(1:1, 7)`, reading text `alpha`;
- unit occurrence 2: `(1:1, 7)`, reading text `beta`.

After conversion, swap only the two `reading_of` targets. The corpus still contains one `alpha` and one `beta` record with identical work/version/ref/id metadata, but `Apparatus.unit_readings(first_unit)` now exposes `beta`.

## Preferred source-grounded fix

Do not enlarge the serialized corpus solely for auditing. Instead add a small independent raw-occurrence audit path:

1. Re-read each XML file directly and walk textual versions in document order.
2. Reconstruct the same literal source references from raw division declarations and assign a 1-based unit index per version while walking units in source order.
3. For every raw unit occurrence, retain an ordered/canonical signature of its direct `<reading>` children (reading index, literal option/witness string, text/XML payload, linebreak/indent, and primary selection semantics).
4. On the TF side, group unit nodes by exact `version_id`, sort by the existing `unit_index`, and obtain their actual readings through `reading_of` rather than from duplicated ownership features.
5. Compare raw occurrence records with graph occurrence records after resolving the version's source-file/work/title/language/kind metadata.
6. Fold this predicate into the existing `reading_ownership` semantic check, preserving the public report shape.

This design independently proves both unit occurrence ordering and reading ownership from XML while adding zero serialized per-reading feature entries. It is preferable to stamping `unit_index` onto every reading because #141 is simultaneously trying to keep local install/runtime footprint lean.

The existing broad raw↔graph reading payload parity remains useful and independent; the occurrence audit adds only the missing binding between those payloads and their source unit occurrence.

## Traversal equivalence

For modern nested `<div>` sources, both parser/model conversion and the raw audit traverse divisions depth-first in document order and emit a unit when encountered. For wrapped legacy `<chapter>/<verse>` sources, both traverse chapters, then verses, then units in document order. A per-version raw counter therefore matches the public `unit_index` semantics without relying on `reading_of`.

Generated translations use the same core builder and are source-declared XML versions, so the occurrence audit can cover them too. Metadata-only versions contain no units and contribute no occurrence records.

## Performance and compatibility

The extra audit is linear in XML elements and graph units/readings, apart from sorting unit nodes by an already-small integer key within each version. It performs no all-pairs scans and changes no TF feature files or researcher identifiers.

## Adversarial cases for review

The final review must attempt:

- swapping owners of duplicate units with distinguishable reading payloads;
- swapping owners while keeping source ref/id/version identical;
- corrupting `unit_index` without changing the edge;
- pointing a reading at another source version with matching local identity;
- missing or multiple owners;
- valid duplicate units retaining their literal upstream ids and appearing in source order through the public apparatus API;
- legacy and nested source traversal retaining monotonic per-version indexes;
- generated translation readings continuing to pass the same source-grounded occurrence accounting.

## Scope conclusion

This is a bounded scholarly-data ownership fix under #137. It does not require release attestations, historical corpus snapshots, or generic certification infrastructure.