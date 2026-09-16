# Issue #158: anonymous manuscript records and keyed apparatus inventory

## Observed contract and RED result

`tests/test_blank_source_identifiers.py::test_graph_builder_allows_whitespace_only_unaddressable_manuscript_metadata` confirms that direct-model conversion intentionally preserves distinct manuscript metadata nodes with whitespace-only abbreviations and no `witness` edges. The modern XML parser rejects blank required identity attributes; this concerns preserved direct-model/legacy-like input, not permission to relax modern XML validation.

In a real TF serialization/reload, `F.ms_abbrev.v(node)` is **None** for those blank source values; the original nodes and their distinct names survive. `Apparatus._witnesses()` currently iterates every reverse `manuscript_of` node, requires `ms_abbrev` for each in its sorting key, and raises before it reaches the duplicate-abbreviation guard. Both `passage()` and `work_passage()` consequently fail even with three valid addressable witnesses. The corrected test-only RED commit `b50cfa0e4654ab2824ee1ff685dc2ae60bf11777` records 2 failures (`ValueError: feature 'ms_abbrev' has no value for node 7`) and 602 passes in GitHub Actions run 35119859983. The earlier test-only commit `980f7e1` failed prematurely because the fixture called `.strip()` on the TF `None` value; it was corrected before implementing production behavior.

## Semantics

The helper's `witnesses` mapping is keyed by addressable source sigla and drives attestation/coverage. Anonymous manuscript metadata cannot be addressed by that key; do not assign synthetic scholarly sigla or conflate anonymous records into one empty-string witness. Exclude `None`/blank/whitespace-only abbreviation values from **this derived keyed inventory only**, before sorting and required-value access. Keep the TF `manuscript` nodes, preserved metadata, and `manuscript_of` edges untouched, accessible through direct TF. For the blank source `ms_abbrev` field, TF legitimately exposes `None`; do not manufacture a value.

Keep duplicate nonblank sigla as errors, and keep synthetic witness exclusion and missing-feature `ValueError` checks. This is a derived inventory policy, not a change to the graph or parser. Record the distinction in `docs/apparatus.md`.

## Verification target

Use `sample.xml` with its three addressable manuscripts plus two accepted unaddressable records. Serialize with `write_tf`, load through raw `Fabric` with `Apparatus.WORK_PASSAGE_FEATURES`, verify five distinct manuscript TF nodes, two distinct anonymous names, and no witness edges to them. Then verify `passage()` and `work_passage()` expose only `A`/`B`/`C` as keyed witnesses. Full unit and pinned-upstream CI plus independent exact-final-head adversarial review are merge gates.
