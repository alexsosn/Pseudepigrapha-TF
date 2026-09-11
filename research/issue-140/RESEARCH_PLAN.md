# Issue 140 — web-app acceptance hardening

## Goal

Close the 1.0 web-app gate by validating the existing Text-Fabric/Flask comparison UI against real pinned-corpus researcher workflows. This is an acceptance/hardening ticket, not an architecture redesign.

## Existing implementation and coverage

The application already has a narrow architecture:

- the stock Text-Fabric browser remains at `/`;
- `pseudepigrapha-tf browse` loads the tracked advanced app in browser mode and adds `/compare` to the same Flask application;
- `build_passage_comparison()` delegates historical evidence to `Apparatus` and generated-text ownership/alignment to `Translations`;
- the comparison renderer explicitly presents `reading`, `[omission]`, `[unattested]`, and `not present` as different states;
- metadata-only versions are listed separately from textual source-version choices;
- generated translations are nested under the source version identified by `translation_of`/`source_id`;
- Previous/Next navigation follows actual source-version verse topology and preserves selected source versions/witnesses;
- CSS already uses wrapping/grid fallbacks and a `max-width: 760px` layout rule.

Existing focused tests cover route parsing/error escaping, stock TF browser coexistence, ambiguous witness failure, navigation state, explicit empty witness selection, source-vs-generated selection, omission/unattested/not-present rendering, metadata-only rendering, occurrence-aware translations, app rendering, and technical-anchor suppression.

`tests/pinned_comparison_acceptance.py` already validates the full pinned corpus for 1 Enoch source-version comparison, witness differences, English/French translation placement/alignment, classification parity, and generated/source separation. It currently exercises the view model/render function directly, not the real Flask route for the edge-case workflows below.

## Source-grounded edge cases

Pinned OCP commit: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.

### TJob

`TJob.xml` contains a normal Greek textual version plus a Coptic metadata-only version. The Greek version has a large manuscript inventory, including P, S, V, Brock, Kraft and several hidden witnesses. Passage `1:1` is suitable for checking:

- ordinary direct passage HTTP rendering;
- many-witness selector behavior without fabricating manuscript text;
- metadata-only Coptic shown separately from source text;
- Previous/Next links on the real corpus.

### PssSol

`PssSol.xml` contains many manuscript declarations and an upstream direct `<reading>` under a `<div>` (preserved by the converter as an `orphan_reading` anomaly). The comparison layer must not reinterpret that technical/anomalous node as normal passage text or crash merely because it exists in the source graph.

### Aristob

`Aristob.xml` contains the upstream-spelled `<elipsis/>` structural anomaly between ordinary textual divisions. The converter preserves this separately; the comparison UI should remain passage-centered and must not render a technical `oslots` anchor as content.

### Duplicate source citations

Pinned OCP has exact duplicate source citations such as `4Ezra/Syriac 10:4`; TF exposes later occurrences using the documented `~N` section suffix while preserving exact `source_ref`. Navigation must use the real TF section topology rather than collapse the duplicate address.

## Acceptance matrix

The persistent full-corpus acceptance should cover these user-visible contracts:

1. **Direct passage + navigation:** real HTTP GET for an ordinary passage returns 200 and Previous/Next links resolve to valid comparison URLs while preserving selection state.
2. **Multiple source versions:** existing 1 Enoch full-corpus assertions remain green and the real route can render the same comparison.
3. **Multiple manuscripts:** a real passage with a large witness inventory exposes a usable selector and multiple witness rows without accidental technical-anchor text.
4. **Missing-state semantics:** focused tests continue to distinguish reading / omission / unattested / version-not-present; at least one real-corpus route must render the relevant semantic classes without server error.
5. **Translations:** existing full-corpus source ownership/alignment assertions remain green and route HTML keeps generated translations nested under the correct source version.
6. **Metadata/anomalies:** TJob metadata-only Coptic is displayed separately; known anomaly-bearing works can be requested without turning preserved technical nodes into displayed source content. A genuine source ambiguity may still return the existing readable 400 rather than being guessed away.
7. **Narrow viewport/many witnesses:** retain a deterministic CSS contract for wrapping, one-column fallback, `min-width: 0`, and `overflow-wrap: anywhere`; no JavaScript/layout rewrite is justified unless an actual rendering defect is demonstrated.
8. **Supported startup path:** retain the already-proven `pseudepigrapha-tf browse` path from #141. Do not introduce a second web-server path.

## Research conclusion

No broad UI or server rewrite is justified by the current evidence. The main gap is persistent **real full-corpus HTTP acceptance** for the edge cases above. Existing pure model/render tests already cover the semantic distinctions and should not be duplicated.

## TDD / test gate

1. Add an ephemeral full-corpus HTTP probe first, using the exact pinned OCP materialization and tracked app, to identify concrete failing routes/claims.
2. If the probe reveals a crash, misleading render, broken navigation, wrong source/witness/translation association, or technical-anchor leak, freeze that exact case as a RED regression test before changing production code.
3. If the behavior is already correct, add the missing persistent acceptance assertions without inventing a production defect. In that case the ticket is acceptance hardening rather than a code fix; the ordinary suite must remain green.
4. Any CSS change requires a concrete failing layout contract, not cosmetic preference.
5. Run ordinary unit/TF CI and the pinned full-corpus integration gate on the exact final head.

## Observed probe and TDD evidence

The ephemeral pinned-corpus HTTP probe exercised the actual tracked Flask app rather than only the view-model renderer. Its source-grounded results were:

- `TJob 1:1`: 200; metadata-only Coptic remained separate, the large witness selector rendered, and passage navigation was present.
- `1En 1:2`: 200 with the selected Ethiopic/Greek source versions, distinct omission/unattested witness states, and generated translations nested under the Ethiopic source card.
- ordinary `PssSol` passages rendered normally, while the known orphan-reading locus `1:5` failed closed with the existing readable 400 ambiguity diagnostic instead of guessing at source ownership.
- `Aristob 7:32:13`: 200 despite the preserved upstream structural anomaly.
- the second duplicate `4Ezra/Syriac 10:4~2` occurrence rendered normally, but the first `10:4` returned 400 with `generated translation ... source unit ... is outside requested source passage`.

That last result exposed a real occurrence-selection bug rather than an ambiguous source. A persistent full-corpus RED was added to require both duplicate 4Ezra sections to render through `/compare`. On the RED head, ordinary tests passed and the pinned job passed conversion/parity/release staging before failing specifically at the first duplicate-section HTTP assertion.

The implementation changes only generated-translation lookup for comparison: it adds `Translations.aligned_to_source_units()` and resolves generated units through exact `translation_unit_of` source-node identity. `Translations.passage()` remains available for direct section-address access, and inconsistent missing-source/generated-passage states still fail closed. The first focused implementation attempt was rejected by its own gate because the comparison test double did not implement the new source-unit contract; no implementation was pushed from that run. After updating the test double, focused translation/comparison/web/navigation tests passed and the occurrence-aware implementation was pushed.

The persistent pinned acceptance now also carries the successful real-corpus checks from the probe, so no temporary probe workflow remains in the PR.

## Stop rule

Stop when the required researcher workflows are persistently exercised on the pinned corpus and no material web defect remains. Do not broaden this ticket into frontend replacement, TF-server replacement, release machinery, or cosmetic redesign.

## Independent review checklist

The final review must re-check independently:

- source versions are not confused with generated translations;
- metadata-only versions are never fabricated as text;
- reading / omission / unattested / not-present remain distinct;
- technical `oslots` anchors are not presented as scholarly content;
- generated translations remain under their exact source version;
- Previous/Next uses real TF topology, including duplicate-section suffixes;
- many-witness selectors remain understandable on narrow layouts;
- malformed/ambiguous source evidence fails readably rather than being guessed.
