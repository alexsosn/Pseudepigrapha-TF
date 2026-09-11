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

The largest extracted feature files included:

- `generation_model.tf`: 29,744,146 B
- `version_kind.tf`: 21,103,140 B
- `version_title.tf`: 15,654,664 B
- `source_ref_parts.tf`: 14,915,744 B
- `generation_marker.tf`: 8,501,587 B
- `ocp_book.tf`: 7,060,040 B

## Phase 1 research and implementation

`conversion._stamp_version_kind()` originally treated two different concepts as one physical denormalization policy:

1. `version_kind`, which some APIs genuinely need below book level; and
2. generated-translation provenance (`generation_marker`, `generated_language`, `generation_method`, `generation_model`), which is version-owned metadata.

For every generated translation it copied all five values onto every generated non-slot object and every generated word slot. Public behavior showed a narrower provenance contract:

- `Translations.versions()` reads the four generation-provenance fields from generated **book nodes**.
- `Translations.source_version()` and generated-version discovery use `version_kind` on **book nodes**.
- generated/source unit alignment and `Apparatus._reject_generated_unit()` require `version_kind` on **unit nodes**.
- `synthetic_witness` independently marks the generated provenance manuscript.
- generated-layer generic metadata remains discoverable through always-loaded `otype` metadata.

### Phase 1 TDD evidence

The test-only head `a329823d24e7a91551cd0a783ac0b6683df189f4` produced the intended RED result: **1 failed, 580 passed**. The sole failure was `test_generation_provenance_is_owned_by_generated_book_not_denormalized_to_descendants`; the fixture showed `generation_marker` on eight extra generated descendants/slots in addition to the generated book.

The implementation split `version_kind` stamping from generated provenance. The four generated-version provenance fields are now attached once to the generated TF book; `version_kind` was deliberately left unchanged in Phase 1, and the synthetic provenance manuscript remains independently marked with `synthetic_witness=1`.

After feature-help documentation was updated to the explicit book-level scope, the current-head unit gate passed **581 tests**.

### Phase 1 measurements

A temporary GitHub-hosted Ubuntu 24.04 / Python 3.12 / Text-Fabric 13.1.0 measurement run built the exact pinned OCP corpus and passed a representative comparison and public `Translations` provenance check for all 231 generated versions.

Measured Phase 1 result:

- `generation_model.tf`: 29,744,146 B → **10,672 B**
- `generation_method.tf`: 3,403,374 B → **3,480 B**
- `generation_marker.tf`: 8,501,587 B → **4,888 B**
- `generated_language.tf`: 6,372,959 B → **4,289 B**
- combined four provenance features: about 45.8 MiB removed (>99.9%)
- staged `complete.zip`: 9,816,530 B → **9,691,770 B** (~1.3% smaller; repeated values compressed well already)
- compiled local corpus tree after full-app priming: **173,921,175 B (165.9 MiB)**
- warm full app: 4.01 s / 1,767,192 KiB → **2.84 s / 1,496,964 KiB** (~15.3% lower peak RSS)
- selective translation load: 3.05 s / 1,397,648 KiB → **2.14 s / 1,126,028 KiB** (~19.4% lower peak RSS)

Timing is runner-sensitive; the memory and feature-size reductions are the primary decision signal. Phase 1 is clearly beneficial, but a selective research load still exceeds 1 GiB, and `version_kind.tf` remains 21,103,140 B.

## Frozen Phase 2 — narrow `version_kind` only

Source/API inspection now establishes the actual `version_kind` consumers:

- `Translations.source_version()` and `Translations.versions()` require it on textual **book** nodes.
- `Apparatus._is_generated_book()` and work-level source/generated filtering require it on **book** nodes.
- `Apparatus._reject_generated_unit()` requires it on **unit** nodes.
- `_validate_generated_alignment()` requires it on generated/source **book** and **unit** nodes.
- semantic translation inventory/audit requires it on generated/source **book** and source-target **unit** nodes.
- metadata-only version inventory requires it on **version_metadata** nodes.
- pinned translation acceptance explicitly checks generated/source **book/unit** classification after TF reload.
- no inspected public helper or audit consumes `version_kind` from word slots, readings, div/chapter/verse nodes, manuscripts, resources, variant words, ellipses, or orphan readings.

`version_kind` is converter-owned classification rather than an upstream value. Its semantic role is to classify the version owner and the unit nodes needed by generated/source alignment and apparatus rejection. Copying it to every descendant and every slot is therefore accidental denormalization.

### Phase 2 TDD/test plan

1. Add a RED regression requiring `version_kind` coverage to be exactly the node types that consume its semantics:
   - every textual `book` has `source` or `generated_translation`;
   - every `unit` has the owning version kind;
   - every `version_metadata` has `source`;
   - no word slot or unrelated descendant node carries `version_kind`.
2. Include a metadata-only fixture so `version_metadata=source` is protected explicitly, not incidentally by the pinned corpus.
3. Observe RED against the current all-descendants/all-slots implementation.
4. Change `_stamp_version_kind()` to stamp only `book`, `unit`, and `version_metadata` objects. Remove slot stamping entirely.
5. Update `version_kind` feature descriptions/help to state its owner/unit scope.
6. Run the ordinary suite and exact pinned full-corpus integration, including all 231 generated translations and 54,143 generated/source unit alignments.
7. Rerun the same temporary measurement workflow, additionally extracting staged `complete.zip` into a stock-style cache layout so post-Phase-2 disk footprint is directly comparable to #104.
8. Stop after Phase 2 unless the remaining >1 GiB footprint is traced to another clearly accidental denormalization with an independently provable safe scope. Do not automatically proceed to `version_title`, `ocp_book`, or source-reference changes.

## Deferred candidates requiring separate proof

These remain research candidates only; they are not authorized by this plan:

1. `version_title` / `ocp_book`: heavily duplicated onto slots via `_surface()` and many objects via `_common()`, but they are upstream/source identity values and low-level researcher code may reasonably expect direct word/node access.
2. `source_ref_parts`: repeated structural JSON that may be derivable from unit/div ownership, but changing its scope risks source traceability and query ergonomics.
3. Text-Fabric compiled `.tfx` footprint/default app loading, if scope-safe raw-feature work is exhausted.

Each requires its own research finding, RED contract, measurement, and explicit plan amendment before implementation.

## Acceptance

- No upstream scholarly value is deleted.
- Generated provenance remains losslessly available through the generated book and `Translations` API.
- `version_kind` remains exact on every node type with a demonstrated semantic consumer: book, unit, version_metadata.
- Existing comparison, apparatus, translation alignment, semantic-audit, source-parity, and release-candidate tests remain green.
- The full pinned corpus gate passes on the exact final head.
- Runtime documentation contains measured post-change download/disk/startup/RAM results rather than estimates.
- Temporary benchmarking CI is removed before merge.
- A logically independent adversarial review checks semantic preservation, low-level TF compatibility implications, and whether the measured benefit justifies the scope change.

## Non-goals

- converter-build micro-optimization (#133)
- release immutability/attestation (#135)
- deleting generated translations or provenance
- changing `version_title`, `ocp_book`, or source-reference scope without a separate measured and tested justification
- redesigning Text-Fabric
