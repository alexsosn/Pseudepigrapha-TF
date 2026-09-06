# Generated translations implementation plan for #76

This plan follows the exact-source inventory in `docs/generated-translations-research.md`. Production changes start only after test-only regressions demonstrate the missing semantics.

## Compatibility boundary

Existing non-generated source/critical versions keep their current parser semantics, TF `book` ids, witness/apparatus behavior, and reconstruction. Generated versions are added as a separate layer so adding 231 translation versions cannot rename the existing source books.

`Book.versions` therefore remains the collection of non-generated source/critical versions used by the existing `_book_ids()` policy. A new `Book.generated_translations` collection stores generated versions plus explicit provenance to one source version.

## Intermediate model

Add a generated-translation record containing:

- parsed `Version` payload for the generated XML version;
- target language;
- strict provenance marker (`OCP-Trans`);
- source-version ordinal/index within `Book.versions`;
- source-version title/language for diagnostics only;
- exact generation method/model facts evidenced by the selected OCP snapshot (`llm`, `openrouter/google/gemini-3.7-flash`);
- alignment diagnostics needed to fail closed on a future source snapshot.

Generated status is established only by `is_generated_translation_version()`; language and title remain descriptive fields.

## Source-version mapping

During parsing, build an occurrence-aware unit signature for every version from:

`(full division path, source unit id, occurrence ordinal within that exact (path,id) identity)`.

For a generated version the language prefix is removed from the unit id before indexing. Source/generated versions are matched by the multiset of `(path, stripped-id)` identities. The selected snapshot has exactly one candidate for every generated version.

A future snapshot with zero or multiple source candidates must raise a concise `InvalidSourceError` rather than guess. Sequence order is not a matching requirement because four selected-snapshot generated versions reorder a structurally identical multiset.

## Unit alignment

Each generated unit is linked to exactly one source unit by the occurrence-aware identity above. Both source and generated sides are indexed independently, so order drift does not break alignment. Multiplicity mismatch for any identity is an error.

Bare ids are never used as unique alignment keys. This avoids reproducing the upstream generator's duplicate-id dictionary collision bug in converter semantics.

## Text-Fabric graph

Generated translations are textual TF books so they remain directly navigable/searchable with ordinary TF text APIs, but they are machine-readably marked:

- node feature `version_kind=generated_translation` on generated book/div/unit/reading/word/manuscript nodes where the owning version is relevant;
- `generated_language` / ordinary `language` as appropriate;
- `generation_method=llm`;
- `generation_model=openrouter/google/gemini-3.7-flash`;
- `generation_marker=OCP-Trans`;
- `synthetic_witness=1` on the generated `OCP-Trans` manuscript node.

Source/critical textual books receive `version_kind=source` (or equivalent canonical value) so APIs can fail closed instead of inferring from absence.

Add semantic edges:

- `translation_of`: generated TF `book` → source TF `book`, exactly one target for every generated book;
- `translation_unit_of`: generated `unit` → source `unit`, exactly one target for every generated unit.

Edge type/cardinality validation is extended so malformed alignment cannot serialize silently.

Generated book ids are deterministic and namespaced, for example `<existing-source-book-id>__translation__English` with collision suffixes when necessary. Existing source book ids are computed before generated versions and do not change.

## Synthetic witness policy

`OCP-Trans` is retained in the graph because it is upstream provenance, but is explicitly synthetic. Default textual-criticism helpers must not report it as a historical manuscript witness.

`Apparatus.work_passage()` considers only `version_kind=source` textual versions by default. `_witnesses()` omits `synthetic_witness=1` nodes from default witness results. Direct TF access still permits provenance inspection.

## Researcher translation API

Add a small `Translations` helper alongside `Apparatus` with operations sufficient for the documented workflows:

- list generated translation versions, optionally filtered by work/language;
- resolve the unique source version for a generated translation through `translation_of`;
- return generated-unit/source-unit pairs through `translation_unit_of`;
- retrieve an aligned passage with generated text and source text/reference without routing the synthetic witness through apparatus semantics.

The helper treats missing required features/edges as explicit load-contract errors, following `Apparatus` precedent.

## Preservation and quality diagnostics

Generated text is preserved exactly as upstream parsed reading text; the converter does not regenerate, repair, normalize away, or reinterpret upstream collision/omission behavior.

The conversion report records at least:

- generated version/unit counts by language;
- aligned generated version/unit counts;
- synthetic witness count;
- generator collision diagnostics from the independent raw-source audit;
- generated empty/placeholder counts;
- unmatched/ambiguous/multiplicity failures (which must make parity fail).

The independent semantic audit reconstructs generated classification and mapping from raw XML structural evidence, rather than trusting graph provenance fields.

## TDD sequence

Before production changes, add tests proving current behavior fails to provide:

1. a representative generated version in the parsed model/graph;
2. strict generated-vs-genuine-English classification (`4Q548`-style fixture case);
3. generated book → exact source book relation in a multi-version work;
4. generated unit → source unit alignment across reordered units;
5. duplicate `(path,id)` occurrence alignment without collapsing duplicates;
6. source book ids remaining unchanged when generated versions are present;
7. `OCP-Trans` excluded from default apparatus witness results;
8. `Translations` listing/source-resolution/aligned-unit behavior;
9. generated provenance features surviving TF write/reload;
10. fail-closed behavior for unmatched/ambiguous/multiplicity-mismatched generated mappings.

Observe isolated red on the test-only head, then implement the minimum changes required.

## Full gates

After implementation:

- complete unit suite;
- real Text-Fabric write/load/reload integration;
- exact OCP pin conversion;
- independent raw-source semantic parity including generated counts/alignment;
- existing apparatus reconstruction gates;
- exact pinned generated-translation inventory gate;
- performance sanity: mapping/index construction remains linear in source/generated units rather than version-pair quadratic scans.

## Adversarial exact-head review

A fresh review pass on the exact green head must independently challenge:

- false generated classification, especially genuine English/French source material;
- source book-id regressions caused by added translations;
- multi-version source mapping ambiguity;
- positional alignment assumptions in `4Ezra`/`SibOr`;
- duplicate identity occurrence collapse;
- accidental exposure of `OCP-Trans` as historical evidence;
- ungrounded model/method claims;
- generated text mutation or omission reinterpretation;
- audit logic that merely echoes graph provenance;
- edge/cardinality/load-contract failures after TF serialization.

Any blocker becomes a red regression or research correction, followed by the implementation/full-gate cycle and another fresh exact-head review.
