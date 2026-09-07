# Generated translation load-contract research correction for #76

## Trigger

Adversarial inspection of the clean green #83 head `50915a8e7533e0ed1c486f1ecbccfb05253a8fb0` found that `Apparatus` filtered generated books and synthetic witnesses only when `version_kind` / `synthetic_witness` happened to be loaded. On a generated corpus loaded without those features, the API therefore failed open.

A test-only regression then proved the opposite extreme is also wrong: requiring those provenance features unconditionally broke valid source-only/legacy `Apparatus` APIs. The strict experiment produced 23 failures in the existing suite. The distinction must therefore be made at corpus level, independently of which data features the caller loaded.

## Text-Fabric metadata behavior

Text-Fabric 13.1 provides the required boundary without a language/title/witness-name heuristic:

- `Fabric.save()` merges generic metadata (`metaData[""]`) into every serialized feature's metadata;
- `Fabric` indexes metadata for every feature it finds, whether that feature is loaded or not;
- the runtime `Api` retains the `Fabric` instance as `api.TF`;
- `otype` is a warp feature and is loaded for every normal API, while its metadata is also present in `api.TF.features["otype"].metaData`.

Therefore a generic corpus marker is visible after TF reload even when `version_kind` and `synthetic_witness` are intentionally omitted from the caller's feature load string.

## Correct capability boundary

When and only when the generated graph contains at least one `version_kind=generated_translation` node, the converter should emit a generic metadata marker such as:

`generatedTranslationLayer=1`

`Apparatus` can read that marker from `api.TF.features["otype"].metaData` without loading generated-layer node features.

For a corpus declaring this marker:

- an operation that must distinguish generated/source books must require `version_kind`;
- an operation that returns or interprets manuscript witnesses must require `synthetic_witness` before historical-witness filtering;
- missing provenance features are load-contract errors, not permission to treat unknown data as source/historical.

For a corpus with no marker:

- source-only/legacy compatibility remains unchanged;
- absence of the generated-layer features does not itself become an error;
- generated status is never inferred from title, language, `OCP-Trans` string matching, or absence/presence of unrelated edges.

This boundary is intentionally presence-based. A source-only corpus has no generated evidence to hide, so forcing new provenance features on it would add compatibility cost without increasing safety.

## Test implications

The corrected TDD gate must cover both sides:

1. generated-layer marker present + missing `version_kind` => direct/work passage fails closed;
2. generated-layer marker present + missing `synthetic_witness` => witness/apparatus views fail closed;
3. source-only corpus without marker continues to support its existing partial-load contracts;
4. marker survives real TF serialization and is visible through `api.TF.features["otype"].metaData` even when generated provenance node features are not loaded.
