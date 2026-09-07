# Generated translation load-contract plan correction for #76

This plan supplements `generated-translations-plan.md` after the fail-open finding and the over-broad strict RED documented in `generated-translations-load-contract-research.md`.

## Metadata contract

During graph finalization, detect whether the built graph actually contains generated translations. If yes, add the generic Text-Fabric metadata flag:

`generatedTranslationLayer=1`

Do not emit it for source-only corpora. The marker describes the corpus payload, not the caller's current load selection.

## Apparatus guard

Add one internal predicate that reads the generic marker through `api.TF.features["otype"].metaData`. It must not inspect version titles, languages, manuscript abbreviations, or loaded generated-layer edges.

Then make provenance requirements conditional:

- `_is_generated_book()` requires `version_kind` only when the corpus marker is present; otherwise it returns false as before.
- historical witness filtering requires `synthetic_witness` only when the corpus marker is present; otherwise existing source-only behavior remains unchanged.
- `work_passage()` filters by `version_kind` only when the corpus marker is present.

The generated-layer case remains fail-closed: marker present plus missing required provenance feature raises a concise `ValueError` naming that feature.

## TDD sequence

Use a test-only RED before implementation:

1. generated fake API carries only the corpus marker through an `api.TF.features["otype"].metaData` stub; removing `version_kind` must fail;
2. same marked API without `synthetic_witness` must fail in witness/apparatus operations;
3. an otherwise equivalent unmarked source-only fake remains usable without either provenance feature;
4. a real TF serialization test proves the generic marker is recoverable from `api.TF.features["otype"].metaData` when the feature load string omits `version_kind` and `synthetic_witness`.

Observe isolated red first. Implement the minimum marker + conditional guard. Run the complete unit/TF suite and exact pinned OCP integration afterward.

## Review targets

The next logically independent exact-head review must specifically try to bypass the guard by:

- omitting `version_kind` on a marked generated corpus;
- omitting `synthetic_witness` on a marked generated corpus;
- loading only ordinary apparatus features;
- entering via `passage`, `work_passage`, `apparatus(unit)`, `_witnesses`, witness state/text helpers, and direct generated section ids;
- checking that an unmarked source-only corpus is not made artificially dependent on generated-layer features.
