# Issue 138 — generated translations completeness, alignment, and researcher usability

## Research findings

Issue #138 is a P0 / 1.0 translation gate. The repository already has strong source-to-graph coverage, including a logically independent raw-XML classifier and mapper for the `OCP-Trans` layer. The correct remaining work is to close the full-corpus **serialized graph → public `Translations` API** boundary, not to add another provenance or release framework.

### Existing source/graph guarantees

The raw audit independently classifies generated translations directly from XML rather than using the parser's generated-version classifier. For each generated version it records the work, version title, target language, `OCP-Trans` marker, uniquely matched source version title/language, unit count, and alignment count.

The semantic audit already compares that independent raw inventory with the generated TF graph and fails closed on:

- missing/extra generated translation versions;
- ambiguous/unmatched source-version mapping;
- missing/extra `translation_of` and `translation_unit_of` relations;
- incomplete unit alignment;
- wrong generated-layer provenance;
- occurrence errors for repeated structural unit identities.

The duplicate-occurrence class is specifically covered by #143/#144: repeated source units such as real `4Ezra__Syriac` `10:4` retain distinct occurrence ownership rather than collapsing to the first matching source reference.

Current pinned integration is green at:

- 231 generated translation versions;
- 54,143 generated translation units;
- 54,143 `translation_unit_of` relations;
- 100% reported alignment coverage;
- English: 115 versions / 27,040 units;
- French: 116 versions / 27,103 units;
- zero raw mapping failures.

### Existing public/API/UI guarantees

`Translations.versions()` exposes generated versions with explicit source node/id, target language, and generation marker/method/model. `aligned_units()` returns occurrence-aligned source/translation units and text. `passage()` returns one generated passage with its aligned source units.

Unit/integration tests already prove:

- generated translations are not ordinary source versions;
- synthetic `OCP-Trans` witnesses are excluded from normal `Apparatus` witness views;
- direct apparatus access to generated translation nodes fails closed;
- `Translations` exposes aligned source and translation text;
- occurrence alignment survives duplicate source refs;
- the comparison model rejects translation units from another source occurrence or a translation when the source passage is not present;
- the web comparison groups translations under their actual source version rather than listing them as source-version columns.

The pinned full-corpus job additionally checks `Translations.versions()` returns all 231 versions with expected languages/provenance and checks one `aligned_units()` result plus the real 1 Enoch comparison workflow.

### Concrete remaining gap

The public API boundary is only sampled for unit alignment. Full source→graph parity can be green while a regression in `Translations.aligned_units()` / `passage()` silently omits or misreports serialized data outside the one sampled version.

There is also no single pinned assertion that the **exact set of target languages available for every source version** matches the independent raw XML inventory. Such a check is the cleanest way to prove that a missing translation stays genuinely absent rather than being substituted/fallen back from another source/version.

## Frozen plan

1. Add a pinned full-corpus translation acceptance helper that receives the already-loaded full-corpus Text-Fabric API plus the pinned OCP source directory. Do **not** create another TF load or another OCP conversion.
2. Use `audit._raw_inventory(source_dir)` as the independent source-side oracle for the intended generated-version inventory. Compare every raw generated translation against `Translations.versions()` by:
   - work;
   - generated version title;
   - target language;
   - `OCP-Trans` marker;
   - source version title/language resolved from the public record's `source_node`;
   - exact per-version aligned-unit count.
3. Require the API inventory to account for all 231 versions and all 54,143 generated units. Compare the set of API-returned generated unit nodes with the complete serialized set of `unit` nodes whose `version_kind` is `generated_translation`, so an API omission cannot hide behind aggregate counts.
4. For every public aligned-unit row, require its `source_unit` to equal the graph's single serialized `translation_unit_of` target. The independent raw semantic audit already proves those graph edges are source-correct; this new gate proves the public API exposes them completely and without substitution.
5. For each generated book, require aligned source-unit nodes to be distinct. This protects the real repeated-occurrence class against a public API collapse even when source refs/unit ids repeat.
6. Build source-version → available target-language maps independently from raw XML and from `Translations.versions()`, and require exact equality. This proves missing English/French translations remain absent rather than silently falling back to another version.
7. Exercise `Translations.passage()` on at least one real passage from **every** generated version: choose the first aligned generated unit, recover its generated section, call `passage()`, and require that exact translation/source unit pair to appear. Keep the existing detailed 1 Enoch web-comparison acceptance as the UI gate rather than adding a second UI framework.
8. Reuse the existing `tests/pinned_comparison_acceptance.py` invocation in pinned CI by calling the new helper from it. No workflow change and no extra full conversion.
9. Keep production translation/converter code unchanged unless this full-corpus acceptance exposes a real discrepancy. Any discrepancy becomes a focused RED regression before a production fix.
10. Leave researcher-first explanatory documentation to #139, which will document the now-proven API/browser path rather than duplicating prose here.

## TDD gates

### RED

Before the acceptance helper is wired in, add a deterministic contract assertion requiring the existing pinned comparison acceptance script to import and invoke the new translation audit helper with the pinned OCP source directory. Current `main` must fail because full-corpus public translation parity is not yet exercised.

### GREEN

Add the helper and invoke it from the existing pinned comparison acceptance path. It must fail closed on:

- generated-version inventory drift;
- target-language/source-version drift;
- omitted generated units;
- public unit mapping differing from serialized `translation_unit_of`;
- duplicate source-unit collapse;
- per-source translation availability/fallback drift;
- failure of `Translations.passage()` on a real passage from any generated version.

### Full tests

Require the ordinary unit/Text-Fabric suite and the exact pinned full-corpus integration to remain green, including raw semantic audit, distribution/reload, offline stock-TF cache load, public metadata/classifications, advanced app startup, and web comparison.

## Independent adversarial review gate

After the exact PR head is green, perform a fresh skeptical review from the opposite trust direction. Challenge at least:

- whether the source oracle is actually independent from serialized TF;
- whether aggregate counts could hide a missing/duplicated version or unit;
- whether source/version identity is checked, not only target language;
- whether a missing language can be silently substituted by another generated version;
- whether duplicate source occurrences can collapse behind identical `source_ref`/`unit_id` strings;
- whether `passage()` is exercised across all generated versions rather than one convenient sample;
- whether the change adds unnecessary conversion/load/workflow/release machinery.

Any blocker becomes a new RED regression followed by fix, full gates, and a fresh exact-head review.

## Definition of done

#138 is complete when the exact pinned raw source inventory, serialized TF translation layer, public `Translations` API, and representative web comparison form one closed researcher-facing chain across all intended generated translations, with no known material discrepancy.