# Issue 145 research — duplicate source-unit occurrence ownership

## Question

Can the source→TF semantic audit prove that readings remain owned by the correct source occurrence when two units in one version share the same upstream `(source_ref, unit_id)`?

## Concrete failure

OCP can contain repeated unit identities. Pseudepigrapha-TF deliberately preserves literal `source_ref` and `unit_id`, so two distinct source occurrences may legitimately have the same values.

`Apparatus.unit_readings()` resolves ownership through the `reading_of` edge. Before this ticket, the semantic audit required every reading to have exactly one unit owner in the same version with matching work, version, source ref, and unit id. Two duplicate occurrences therefore remained interchangeable to that check.

A mutation with occurrence 1 reading `alpha` and occurrence 2 reading `beta` could swap only the two `reading_of` targets while keeping every payload and identity feature unchanged. The pre-fix report stayed green even though researcher-facing apparatus results were reversed. RED was observed on commit `588f349559de0c269f7b612c4e396fa4e7023a89`.

## First implementation attempt and rejected trade-off

The first GREEN design independently re-read the XML and rebuilt a source-order unit→reading inventory. It caught the corruption without adding TF features, but it read every XML document twice during semantic audit.

The existing performance contract `test_semantic_audit_reads_special_structure_source_once` rejected that design: CI observed two reads of the same source file. Duplicating the complete XML traversal is disproportionate for a relation invariant that is already encoded structurally in TF.

## Structural occurrence invariant

The graph builder gives every `reading` node exactly the same `oslots` support as the `unit` that structurally contains it. Different unit occurrences have different support sets because each primary occurrence owns its own word slots; an empty primary receives its own gap slot. This remains true when two units have identical upstream reference/id values.

Consequently an occurrence-aware ownership check can require all of the following:

1. `reading_of` has exactly one target;
2. source and target belong to the same exact version and retain the same source identity fields (the pre-existing ownership checks);
3. the reading and its claimed unit owner have the same non-empty `oslots` support.

A relation-only swap between duplicate occurrences now fails condition 3. This check is independent of `reading_of`: the support was created from structural containment before the ownership edge is consulted.

The surrounding semantic report still reads the raw XML once and independently compares source reading payloads, units, versions, source hashes, and reconstruction semantics. The new invariant supplies the missing occurrence binding without another source pass.

## User-visible acceptance

A real Text-Fabric serialization/load regression must preserve both duplicate upstream ids and expose the correct readings through `Apparatus.unit_readings()`:

- occurrence 1 → `alpha`;
- occurrence 2 → `beta`.

This verifies the API researchers actually use rather than only inspecting the in-memory builder representation.

## Performance and footprint

The final occurrence check is O(readings), performs no XML I/O, no sorting, and adds no TF feature values or files. It therefore does not increase corpus download size or ordinary Text-Fabric load memory.

## Adversarial review scope

The final review should attempt to falsify the implementation with duplicate ref/id swaps, missing or multiple owners, cross-version targets with matching local identity, empty/gap readings, generated-translation readings, malformed/missing oslots, and accidental changes to public source identifiers. It should also verify the audit still reads each XML file once and that the new API regression uses stock Text-Fabric.

A coordinated corruption that rewrites both an ownership edge and the reading's structural support is outside the single-edge regression that motivated this ticket; existing raw payload/reconstruction and graph validation checks still provide additional defenses. If review finds a practical converter path that can create such coordinated corruption while all existing gates remain green, it should become a separate focused correctness ticket rather than expanding this fix into a second source parser.

## Scope conclusion

This is a bounded scholarly-data correctness fix under #137. It changes no upstream identifiers and introduces no release/certification machinery.
