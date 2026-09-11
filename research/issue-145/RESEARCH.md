# Issue 145 research — duplicate source-unit occurrence ownership

## Question

Can the source→TF semantic audit prove that readings remain owned by the correct source occurrence when two units in one version share the same upstream `(source_ref, unit_id)`?

## Concrete failure

OCP can contain repeated unit identities. Pseudepigrapha-TF deliberately preserves literal `source_ref` and `unit_id`, so two distinct source occurrences may legitimately have the same values.

`Apparatus.unit_readings()` resolves ownership through the `reading_of` edge. Before this ticket, the semantic audit required every reading to have exactly one unit owner in the same version with matching work, version, source ref, and unit id. Two duplicate occurrences therefore remained interchangeable to that check.

A mutation with occurrence 1 reading `alpha` and occurrence 2 reading `beta` could swap only the two `reading_of` targets while keeping every payload and identity feature unchanged. The pre-fix report stayed green even though researcher-facing apparatus results were reversed. RED was observed on commit `588f349559de0c269f7b612c4e396fa4e7023a89`.

## First implementation attempt and rejected trade-off

The first GREEN design independently re-read the XML and rebuilt a source-order unit→reading inventory. It caught the corruption without adding TF features, but it read every XML document twice during semantic audit.

The existing performance contract `test_semantic_audit_reads_special_structure_source_once` rejected that design: CI observed two reads of the same source file. Duplicating the complete XML traversal is disproportionate for an ownership relation that already carries independent structural/order signals in TF.

## Available occurrence signals

Three graph facts are created independently of the final `reading_of` target:

1. `unit_index` is the 1-based source-order unit occurrence inside one version;
2. reading nodes preserve source creation order inside their Text-Fabric node-type block, while `reading_index` resets to 1 for the first reading of every unit and increments within that unit;
3. every reading receives the same non-empty `oslots` support as the unit structurally containing it; distinct unit occurrences have distinct primary/gap support.

The builder's finalization groups objects by node type but explicitly preserves creation order within each type. Therefore, for each exact `(ocp_book, version_id)`, the audit can independently reconstruct reading groups from node order plus `reading_index`, pair those groups with units ordered by `unit_index`, and require `reading_of` to point to that expected occurrence. `oslots` equality is then a second independent structural check.

This uses no synthetic source identifier and adds no serialized feature.

## Adversarial refinement

An intermediate implementation used only the `oslots` equality check. Independent review constructed a coordinated mutation that swapped both duplicate units' `reading_of` targets and the two reading support sets. In that state the ownership-specific predicate incorrectly remained green. RED was observed on commit `0cac85223879eb1300dce0ce06ef15e87f79a61d` with 566 other tests passing.

The final design therefore derives the expected occurrence from `unit_index` plus reading creation order/`reading_index` and separately checks support equality. Rewriting both the owner edge and support no longer changes the independently reconstructed expected owner.

The surrounding semantic report still reads the raw XML once and independently compares source reading payloads, units, versions, source hashes, and reconstruction semantics. The occurrence predicate supplies the missing ownership binding without another source pass.

## User-visible acceptance

A real Text-Fabric serialization/load regression preserves both duplicate upstream ids and exposes the correct readings through `Apparatus.unit_readings()`:

- occurrence 1 → `alpha`;
- occurrence 2 → `beta`.

This exercises the public researcher API rather than relying only on the in-memory builder graph.

## Performance and footprint

The final check is linear apart from sorting each version's units by already-present `unit_index`. It performs no XML I/O and adds no TF feature values or files, so it does not increase researcher download or ordinary load memory.

## Adversarial review coverage

Review covers relation-only duplicate swaps, coordinated owner+support swaps, missing/multiple owners, cross-version targets, malformed/missing support, invalid `unit_index`/`reading_index` sequences, empty/gap readings, generated-translation readings, public identifier stability, and single-pass source I/O. Existing ownership tests already cover missing, multiple, wrong-type, and wrong-version owner classes.

## Scope conclusion

This is a bounded scholarly-data correctness fix under #137. It changes no upstream identifiers and introduces no release/certification machinery.
