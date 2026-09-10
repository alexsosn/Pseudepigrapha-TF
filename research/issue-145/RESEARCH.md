# Issue 145 research — duplicate source-unit occurrence ownership

## Question

Can the independent source→TF semantic audit prove that readings remain owned by the correct source occurrence when two units in one version share the same upstream `(source_ref, unit_id)`?

## Source and graph representation

OCP permits repeated unit identities. The converter intentionally preserves the literal upstream `source_ref` and `unit_id`; it does not synthesize uniqueness into either field.

The core graph builder nevertheless has an independent source-order identity: `_add_version()` increments one `unit_counter` through the complete version traversal, and `_add_unit()` writes that 1-based value as the unit node's `unit_index`. Each reading is created inside that exact `_add_unit()` call and immediately linked to the unit with `reading_of`, but the reading node does not currently retain the owning unit's `unit_index` as a feature.

Researcher-facing apparatus access relies on `reading_of`: `Apparatus.unit_readings()` reverse-resolves that edge, and passage/apparatus methods assemble the readings of each unit from it. A wrong edge therefore changes which reading researchers see for the first versus second duplicate occurrence.

## Independent audit gap

The raw XML inventory records units and readings using work/version/source ref/unit id plus payload values, but it does not record the source-order unit index. The graph inventory mirrors those records. Both inventories are canonicalized as unordered JSON records before equality comparison.

`semantic_audit._ownership_edge_ok()` verifies every reading has exactly one `reading_of` target in the same exact source version and with equal `ocp_book`, `version_title`, `source_ref`, and `unit_id` features. When two units share those values, swapping their reading owners preserves all current predicates. The reading payload itself remains stamped on the reading node, so unordered raw↔graph payload parity also remains unchanged.

Minimal counterexample:

- unit occurrence 1: `(1:1, 7)`, reading text `alpha`;
- unit occurrence 2: `(1:1, 7)`, reading text `beta`.

After conversion, swap only the two `reading_of` targets. The corpus still contains one `alpha` and one `beta` record with identical work/version/ref/id metadata, but `Apparatus.unit_readings(first_unit)` now exposes `beta`.

## Smallest source-grounded fix

Use the existing `unit_index` as the occurrence discriminator rather than inventing a synthetic source identifier.

1. The raw XML inventory should assign the same 1-based source-order unit index used by the converter: one monotonically increasing counter per version across the full source traversal.
2. Add that index to raw unit and raw reading audit records.
3. Stamp `unit_index` on each graph reading at construction time. This stamp is source-derived and independent of the later `reading_of` edge.
4. Include `unit_index` in graph unit/reading inventory records.
5. Add `unit_index` to the reading ownership identity check, so a reading stamped as occurrence 1 cannot point to occurrence 2.

This closes both sides of the proof: raw parity checks the source-derived occurrence stamp, while ownership checks that the edge target agrees with that stamp.

The public upstream identifiers remain unchanged. No new TF feature is required because `unit_index` already exists and is documented as the 1-based source-order index within a version; the feature simply becomes available on readings as well as unit nodes.

## Traversal equivalence

For modern nested `<div>` sources, both parser/model conversion and the raw audit traverse divisions depth-first in document order and emit a unit when encountered. For wrapped legacy `<chapter>/<verse>` sources, both traverse chapters, then verses, then units in document order. A per-version counter in the raw audit therefore matches `_add_version()`'s `unit_counter` semantics.

Generated translations use the same core builder, so their readings will also receive `unit_index`; this is harmless and makes the feature semantics uniform. The raw inventory already includes generated versions and can verify those values too.

## Performance and compatibility

The change is linear in source and graph reading counts. No relation joins beyond the existing O(1) ownership checks are needed.

Adding `unit_index` values to reading nodes increases the serialized feature by one entry per reading but does not add a new feature file. Given that correctness of occurrence ownership is a 1.0 blocker, this small footprint is justified; #141 remains responsible for measuring overall corpus/runtime size.

## Adversarial cases for review

The final review must attempt:

- swapping owners of duplicate units with distinguishable reading payloads;
- swapping owners while keeping source ref/id/version identical;
- corrupting the reading's `unit_index` stamp without changing the edge;
- pointing a reading at another source version with matching local identity;
- missing or multiple owners;
- valid duplicate units retaining their literal upstream ids and appearing in source order through the public apparatus API;
- legacy and nested source traversal retaining monotonic per-version indexes.

## Scope conclusion

This is a bounded scholarly-data ownership fix under #137. It does not require release attestations, historical corpus snapshots, or generic certification infrastructure.