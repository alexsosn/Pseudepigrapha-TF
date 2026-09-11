# Issue 141 — researcher runtime footprint

## Baseline

Issue #104 measured the published `v0.2.0` consumption path on a clean GitHub-hosted Ubuntu 24.04 / Python 3.12 / Text-Fabric 13.1.0 runner:

- public `complete.zip`: 9,816,530 B (9.36 MiB)
- populated Text-Fabric cache: 227,070,492 B (216.6 MiB), 205 files, no retained ZIPs
- cold acquisition + full app: 59.71 s / 2,347,328 KiB peak RSS
- warm offline full app: 4.01 s / 1,767,192 KiB peak RSS
- full app + representative comparison: 3.95 s / 1,769,268 KiB peak RSS
- selective translation-oriented load: 3.05 s / 1,397,648 KiB peak RSS

Selective loading therefore saves only about 21% of peak RSS and does not remove the 1.0 concern.

The largest extracted feature files include:

- `generation_model.tf`: 29,744,146 B
- `version_kind.tf`: 21,103,140 B
- `version_title.tf`: 15,654,664 B
- `source_ref_parts.tf`: 14,915,744 B
- `generation_marker.tf`: 8,501,587 B
- `ocp_book.tf`: 7,060,040 B

## Source-level findings

`conversion._stamp_version_kind()` currently treats two different concepts as one physical denormalization policy:

1. `version_kind`, which some APIs genuinely need below book level; and
2. generated-translation provenance (`generation_marker`, `generated_language`, `generation_method`, `generation_model`), which is version-owned metadata.

For every generated translation it currently copies all five values onto every generated non-slot object and every generated word slot. The long model identifier is therefore serialized once per generated descendant/slot even though it describes the generated version as a whole.

Existing public behavior gives a narrower semantic contract:

- `Translations.versions()` reads `generation_marker`, `generated_language`, `generation_method`, and `generation_model` from generated **book nodes**.
- generation-provenance scope tests assert those fields on generated **book nodes**, not on words/readings/divs.
- `Translations.source_version()` and generated-version discovery use `version_kind` on **book nodes**.
- generated/source unit alignment and `Apparatus._reject_generated_unit()` require `version_kind` on **unit nodes**.
- `synthetic_witness` independently marks the generated provenance manuscript.
- generated-layer generic metadata lets callers detect that the corpus has a generated layer even when provenance features are not loaded.

There is therefore direct evidence that generated provenance can be stored once per generated book while preserving the existing public translation API and scholarly data. There is not yet equivalent evidence that `version_kind`, `version_title`, `ocp_book`, or `source_ref_parts` can be narrowed without changing researcher-visible node-feature semantics.

## Frozen plan

### Phase 1 — generated provenance deduplication

1. Add a TDD regression that requires generated provenance (`generation_marker`, `generated_language`, `generation_method`, `generation_model`) to live on generated book nodes only, while preserving:
   - their exact values on the generated book;
   - `version_kind` on source/generated book and unit nodes;
   - generated/source alignment edges;
   - synthetic witness marking;
   - public `Translations` behavior after TF write/reload.
2. Observe RED against the current broad stamping implementation.
3. Split `version_kind` stamping from generated provenance stamping. Keep `version_kind` behavior unchanged in this phase; stamp generated provenance only on the generated book node.
4. Update feature descriptions/docs to state the provenance features' book-level scope rather than implying arbitrary descendant coverage.
5. Run ordinary tests and the pinned complete-OCP gate.

### Phase 1 measurement gate

Use a temporary PR-only measurement workflow or equivalent ephemeral runner, removed before merge, to build the pinned full corpus and compare against the #104 baseline on the same runner class. Record at least:

- sizes of the four generated-provenance `.tf` files;
- final generated corpus/cache footprint where practical;
- warm full-app wall time and peak RSS;
- selective translation load wall time and peak RSS;
- representative comparison correctness.

Proceed to Phase 2 only if Phase 1 leaves a major avoidable hotspot and there is a separately demonstrated semantic-safe narrowing. Do **not** broaden the patch merely to chase an arbitrary benchmark.

### Phase 2 candidates — research only unless still necessary

Investigate, in this order, without assuming they should be changed:

1. `version_kind`: likely needs only version-owner and unit semantics, but current audits/helpers must be checked before narrowing.
2. `version_title` / `ocp_book`: heavily duplicated onto slots via `_surface()` and onto many objects via `_common()`, but existing low-level researcher queries may rely on direct word/node feature access.
3. `source_ref_parts`: repeated structural JSON that may be derivable from unit/div ownership, but changing its scope is more invasive and must not weaken source traceability.
4. Text-Fabric compiled `.tfx` footprint and default app feature loading, if raw feature deduplication does not explain enough RAM.

Any Phase 2 change requires its own RED semantic contract and before/after measurement on this branch.

## TDD execution evidence

The test-only head `a329823d24e7a91551cd0a783ac0b6683df189f4` produced the intended RED result: **1 failed, 580 passed**. The sole failure was `test_generation_provenance_is_owned_by_generated_book_not_denormalized_to_descendants`; the fixture showed `generation_marker` on eight extra generated descendants/slots in addition to the generated book.

The Phase 1 implementation then split `version_kind` stamping from generated provenance. The four generated-version provenance fields are now attached once to the generated TF book; `version_kind` stamping remains unchanged for all generated/source descendants and slots, and the synthetic provenance manuscript remains independently marked with `synthetic_witness=1`.

## Acceptance

- No upstream scholarly value is deleted; generated provenance remains losslessly available through the generated book and `Translations` API.
- Existing comparison, apparatus, translation alignment, semantic-audit, source-parity, and release-candidate tests remain green.
- The full pinned corpus gate passes on the exact final head.
- The runtime documentation is updated with measured post-change results, not estimated savings.
- Temporary benchmarking CI is removed before merge.
- A logically independent adversarial review checks both semantic preservation and whether the measured improvement justifies the schema-scope change.

## Non-goals

- converter-build micro-optimization (#133)
- release immutability/attestation (#135)
- deleting generated translations or provenance
- changing `version_kind`, `version_title`, `ocp_book`, or source-reference scope without a separate measured and tested justification
- redesigning Text-Fabric
