# Issue 143 research — duplicate translation-unit occurrence alignment

## Question

Can the independent semantic audit prove the converter's documented occurrence-by-occurrence generated-translation alignment when more than one unit has the same structural identity?

## Current source and converter semantics

Generated translations are identified from the source-declared `OCP-Trans` structure. Their source version is matched by the multiset of normalized unit identities `(full division path, unit id)`.

During graph construction, `conversion._unit_key_index()` groups unit object keys by `(source_ref_parts, normalized unit_id)` in source creation order. `_add_generated_translation()` requires equal identity sets and multiplicities, then zips each generated identity group with the corresponding source identity group. Consequently duplicate identities are aligned by occurrence ordinal within that identity group, while unrelated identity groups may be reordered in the generated version.

This is the behavior documented in the README and exercised by `test_unit_alignment_uses_structural_identity_and_occurrence_not_position_or_bare_id`.

## Independent audit path

`audit._raw_translation_unit_identities()` independently rereads XML and returns the ordered identity sequence. The current raw translation matcher immediately converts that sequence to `Counter`, which is sufficient to choose the source version but intentionally discards order.

`semantic_audit._graph_generated_translation_inventory()` then checks each generated unit has one `translation_unit_of` target, that the target is a source unit in the selected source version, that source ref and normalized unit id match, and that no target is reused. It reports only counts.

For an identity group occurring twice, swapping the two source targets preserves all of those predicates. The semantic report therefore has a false negative: `generated_translation_alignment` can remain true while researcher-facing source↔translation occurrence pairs are reversed.

## Threat model / minimal counterexample

Source version:

- `(1:1, 7)` occurrence 1 → `source-first`
- `(1:1, 7)` occurrence 2 → `source-second`

Generated version:

- `(1:1, fr_7)` occurrence 1 → `translated-first`
- `(1:1, fr_7)` occurrence 2 → `translated-second`

Correct edges are generated occurrence 1 → source occurrence 1 and generated occurrence 2 → source occurrence 2. Swapping those two targets is semantically wrong but currently satisfies identity, version, cardinality, multiplicity, and target-uniqueness checks.

## Design constraints

The audit must continue allowing a generated version to reorder different structural identities; global positional zip is invalid. It must compare order only inside equal normalized identity groups.

The check should stay linear apart from deterministic sorting already available from `unit_index`/node order. No all-pairs matching is needed.

The existing generated-translation summary fields should remain stable. A boolean occurrence check can be folded into `generated_translation_alignment`; a compact diagnostic is optional but not required for the fix.

## Preferred implementation

On the graph side, construct ordered source-unit groups keyed by exact source-version id plus `(source_ref, unit_id)`. Construct generated groups keyed by generated version plus `(source_ref, stripped unit_id)`. For each generated book, obtain its exact source book/version through `translation_of`. For each generated identity group, require the tuple of actual `translation_unit_of` targets, in generated unit order, to equal the tuple of source units for that identity, in source unit order.

Use `unit_index` as the explicit source-order feature, with node id as a deterministic tie-breaker. The existing raw XML inventory still independently establishes version identity/multiplicity and the existing raw↔graph `units` parity establishes the represented unit identities; the new graph relation check closes the occurrence-edge hole without duplicating the converter's internal key objects.

## TDD evidence required

1. RED mutation test: build the existing duplicate/reordered fixture, verify the normal report is green, swap the two duplicate `translation_unit_of` targets, and require `generated_translation_alignment == False`.
2. GREEN existing fixture: valid reordered identity groups continue to pass.
3. Adversarial review should try cross-version targets, reused targets, missing targets, duplicate groups with reordered unrelated identities, and absent/odd `unit_index` values.

## Scope conclusion

This is a bounded correctness gap in #138. No data model change or release/certification mechanism is required.