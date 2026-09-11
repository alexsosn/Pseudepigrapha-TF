# Issue 145 plan — preserve source occurrence ownership

## 1. Original RED — completed

Add a fixture with two consecutive source units that deliberately share the same `source_ref` and `unit_id` but have distinguishable readings. Build valid TF, swap only their `reading_of` targets, and require the semantic report to fail `reading_ownership`.

RED was observed on `588f349559de0c269f7b612c4e396fa4e7023a89`: the previous audit remained green after the mutation.

## 2. Rejected implementation — performance gate

A direct second XML traversal rebuilt source occurrence ownership correctly but failed the established single-pass source-audit contract. Do not retain it.

## 3. Lean implementation

Keep literal upstream identity untouched and derive occurrence ownership from existing TF structure:

- retain exact-version/cardinality/source-identity ownership checks;
- order units within each `(ocp_book, version_id)` by validated 1-based `unit_index`;
- use reading node creation order plus the per-unit `reading_index` reset/increment sequence to reconstruct each unit's reading group independently of `reading_of`;
- require every reading's actual `reading_of` target to equal that reconstructed unit occurrence;
- separately require the reading's non-empty `oslots` support to equal the expected unit's support;
- add no source reread and no new serialized feature.

## 4. Adversarial RED — completed

Independent review must not assume `oslots` itself cannot be corrupted. Swap both duplicate occurrences' owner edges and reading support sets while leaving source identities/payloads intact. Require `reading_ownership` itself to become false.

RED was observed on `0cac85223879eb1300dce0ce06ef15e87f79a61d`: 566 other tests passed while the ownership-specific check remained incorrectly true. The order/index discriminator closes this bypass.

## 5. Researcher-facing regression

Serialize the duplicate fixture with the normal writer, load it through stock Text-Fabric, and verify:

- both unit occurrences retain literal `source_ref=1:1` and `unit_id=7`;
- ordering by `unit_index` identifies the two occurrences;
- `Apparatus.unit_readings()` returns `alpha` for occurrence 1 and `beta` for occurrence 2.

## 6. Test gates

Run the complete repository CI. In particular verify the focused mutation/API tests, single-pass audit test, ownership/audit tests, apparatus/TF integration tests, generated-translation tests, and full pinned-OCP conversion/reload/advanced-app/comparison path.

## 7. Logically independent adversarial review

Falsify the final diff against:

- relation-only duplicate ref/id owner swap;
- coordinated owner+support swap;
- missing or multiple owner edge;
- cross-version target with matching local identity;
- invalid/missing/duplicate `unit_index` or malformed `reading_index` sequence;
- missing, empty, or mismatched reading/unit oslots;
- empty-primary/gap-slot occurrences;
- generated-translation readings;
- accidental changes to upstream ids or section addressing;
- extra XML reads, corpus-size growth, or hidden super-linear scans.

Add a regression for any material bypass. Merge only after both CI jobs are green and the review has no blocking finding.
