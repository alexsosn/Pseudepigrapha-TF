# Issue #158: anonymous manuscript records and keyed apparatus inventory

## Observed contract

`tests/test_blank_source_identifiers.py::test_graph_builder_allows_whitespace_only_unaddressable_manuscript_metadata` proves that direct-model conversion intentionally preserves two distinct manuscript nodes with whitespace-only abbreviations and no `witness` edges. The modern XML parser rejects blank required identity attributes, so this test concerns preserved direct-model/legacy-like input, not permission to weaken modern parsing.

`Apparatus._witnesses()` currently iterates every reverse `manuscript_of` node, uses `ms_abbrev` as the mapping key, then raises on duplicates. A pair of intentionally unaddressable metadata-only manuscripts therefore prevents `passage()` and `work_passage()` from returning even correctly identified named witnesses. No reading can name a blank witness through the parsed `reading.witnesses` tokens.

## Semantics

The helper's `witnesses` mapping is addressable by actual source sigla and drives attestation/coverage. Anonymous manuscript metadata cannot be addressed by that key and must not be assigned synthetic scholarly sigla or conflated into one empty-string witness. Exclude abbreviation values whose `strip()` is empty from **this derived keyed inventory only**. Leave every manuscript TF node, its raw `ms_abbrev`/`ms_name` features, and `manuscript_of` edges untouched; researchers can access unaddressable metadata directly in Text-Fabric.

Keep duplicate *nonblank* sigla as an error. Existing `undefined_manuscript`/`synthetic_witness` handling and generated-layer checks must be unaffected. Record this distinction in `docs/apparatus.md`.

## Verification target

Use the existing direct-model helpers to build an accepted version with addressable `A` plus two anonymous manuscript metadata nodes. Serialize to disk with `write_tf`, selectively load via `Apparatus.WORK_PASSAGE_FEATURES`, and prove both public passage operations succeed with `A` alone in their keyed inventories while all three manuscript TF nodes remain readable and no spurious `witness` edges target anonymous nodes. Assert the specific RED failure before implementation, then run all unit and pinned-upstream CI and perform an independent final-diff review.
