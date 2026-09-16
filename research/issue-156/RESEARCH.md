# Issue #156 research: selective feature presets

## Question

Freeze public, joinable Text-Fabric feature presets for `Translations` and passage-oriented `Apparatus` workflows without hiding load cost, weakening fail-closed behavior, or turning every helper call into a maximal load.

## Existing precedent

`WorkMetadata.REQUIRED_FEATURES` and `HistoricalClassifications.REQUIRED_FEATURES` already expose tuples that callers pass explicitly to Text-Fabric with `" ".join(...)`. Constructors do not perform loading.

## Runtime consumers

### `Translations`

The documented lower-memory workflow calls `versions()`, `aligned_units()`, and may call `passage()`/`aligned_to_source_units()`.

Hard semantic dependencies are:

- `version_kind`, `translation_of` for generated/source identity;
- `translation_unit_of` for occurrence alignment;
- `reading_of`, `is_primary`, `reading_text` for source/translation text.

The public `versions()` result also intentionally exposes `ocp_book`, `version_title`, `language`/`generated_language`, `generation_marker`, `generation_method`, and `generation_model`; aligned-unit records expose `unit_id` and `source_ref`; `unit_index` preserves generated document order when available; `book` gives a direct stable book id before the section fallback.

`docs/runtime-footprint.md` already measured the following exact selective load on the pinned corpus:

`book ocp_book version_title version_kind language generated_language generation_marker generation_method generation_model unit_id unit_index source_ref reading_text is_primary translation_of translation_unit_of reading_of`

Conclusion: `Translations.REQUIRED_FEATURES` should freeze that measured feature set exactly. This avoids changing the semantics or memory evidence attached to the documented path.

### `Apparatus.passage()`

The real selective-load tests establish a smaller semantic contract. A successful passage requires:

- `reading_of`, `witness`, `is_primary`, `reading_text` for readings and assignments;
- `manuscript_of`, `ms_abbrev`, `undefined_manuscript` for witness inventory and identity;
- `unit_id` for stable unit identity.

For a corpus whose generic TF metadata declares `generatedTranslationLayer=1`, apparatus semantics additionally fail closed unless `version_kind` and `synthetic_witness` are loaded. These must therefore be in the public passage preset even though a source-only fixture can run without them.

`source_ref`, `ms_language`, `ms_name`, and `ms_show` are optional display enrichment: existing tests deliberately prove that passage semantics remain correct without them. They should not inflate `PASSAGE_FEATURES`.

Text-Fabric warp features such as `otype`/`oslots` are not repeated in the user feature string; raw `Fabric.load()` supplies the warp API. The preset should remain compatible with both `app.load(...)` and raw `Fabric.load(...)`.

Conclusion:

`Apparatus.PASSAGE_FEATURES = (reading_text, is_primary, ms_abbrev, undefined_manuscript, unit_id, version_kind, synthetic_witness, reading_of, witness, manuscript_of)`

Order should group node features before edge features and stay deterministic for documentation/tests.

### `Apparatus.work_passage()`

`work_passage()` needs the passage contract for an available section plus cross-version identity:

- `ocp_book` is mandatory for finding all source/critical versions of a work;
- `version_id` is required to identify metadata-only versions in the public corpus. Without it, metadata-only records fail rather than returning a usable identity.

`title`, `version_title`, `language`, and `author` are display enrichment with neutral fallbacks. `source_ref` is likewise optional enrichment. Keeping these out of the semantic preset preserves the low-load intent and matches existing fail-closed/optional-field boundaries.

Conclusion:

`Apparatus.WORK_PASSAGE_FEATURES = PASSAGE_FEATURES + (ocp_book, version_id)` with deterministic ordering chosen in implementation (prefer identity node features before edge features rather than literal tuple concatenation if readability is better).

## Documentation drift found

`docs/apparatus.md` currently says `unit_id` and `ms_abbrev` are optional where neutral fallbacks exist. That is false for `passage()`: `_passage_from_context()` requires both. The same document understates generated-layer requirements by omitting `version_kind` and `synthetic_witness` from the public generated-capable corpus contract.

README and `docs/runtime-footprint.md` also duplicate long feature strings. Once constants exist, examples should join the constants instead.

## Guardrails

- No constructor or helper method may auto-load features.
- Existing missing-feature `ValueError` behavior remains unchanged.
- The presets are convenience load contracts, not claims that every lower-level method requires the whole tuple.
- `work_passage()` absent-section behavior must remain usable with its intentionally narrower hand-selected feature set; adding an opt-in preset must not add runtime checks.
- Exact generated-layer safety features must be exercised with a marked corpus, because source-only fixtures cannot reveal accidental omission.
