# Issue #110 — serialized provenance closure

## Research result

Baseline: merged `main` commit `ec0139670ffeeb80dabb3668bbed7af69049e8e8`.

The release validator has one asymmetric trust boundary. `_validate_serialized_identity()` computes the canonical provenance projection from the exact archived `otype.tf` using `report_provenance(metadata)`, then iterates only the report-derived `expected_provenance`. Missing or mismatched report-declared fields fail, but an additional canonical provenance key serialized in `otype.tf` is ignored when the report omits it.

This is not just a hypothetical future-schema issue. `REPORT_PROVENANCE_FIELDS` already includes optional identity/provenance fields such as `sourceIdentityDiagnostic`, `contentLicenseUrl`, `upstreamLicenseCommit`, and `contentLicenseDiagnostic`. A modified serialized feature set can therefore assert one of those fields, update the report's feature-byte identity to match the modified `.tf` bytes, omit that field from report provenance, and still reach manifest construction. Stock Text-Fabric would then expose provenance that the successful report/manifest path never bound.

The canonical mapping already exists in `pseudepigrapha_tf.provenance.REPORT_PROVENANCE_FIELDS`; its source comment explicitly says distribution validation should consume the same mapping so provenance cannot silently be checked in only one representation. No new registry is needed.

Legitimate Text-Fabric duplicate non-identity generic metadata remains a separate concern. `_serialized_otype_metadata()` correctly permits repeated non-identity metadata such as `writtenBy` while rejecting duplicate keys in `_SERIALIZED_IDENTITY_KEYS`. Issue #110 must not tighten that parser behavior.

## Chosen rule

For canonical provenance only, the projection from serialized `otype.tf` must equal the report-derived canonical projection exactly.

- report key present, serialized missing → reject;
- both present, values differ → reject;
- serialized canonical key present, report missing → reject;
- neither present → fine;
- non-canonical TF generic metadata → ignored by provenance equality and remains TF-compatible;
- TF `version` remains checked separately against the publication data version.

The existing report and writer paths use the same canonical generic↔report key mapping, so a valid generated corpus is expected to satisfy this equality. The pinned full-corpus gate will prove that expectation before merge.

A successful publication already requires both `source_identity_status` and `content_license_status` to be `verified`. Therefore either corresponding diagnostic key (`source_identity_diagnostic` or `content_license_diagnostic`) is internally contradictory and must fail before archive/report equality can bless the contradiction.

## TDD sequence

### RED

Add a focused serialized-provenance regression file before production code:

1. serialized `sourceIdentityDiagnostic` absent from report provenance must fail;
2. serialized optional positive field (`contentLicenseUrl`) absent from report provenance must fail;
3. an extra non-canonical `writtenBy` metadata field remains accepted;
4. keep all existing missing/mismatch/duplicate/header/data-version regressions green except the new RED cases.

The RED must fail because manifest construction currently accepts the two asymmetric canonical-provenance cases.

### GREEN

In `_validate_serialized_identity()`:

1. compute both canonical projections with the existing `report_provenance()` contract;
2. preserve the current specific missing/mismatch diagnostics;
3. after those checks, detect `serialized_provenance.keys() - expected_provenance.keys()` and reject with a specific unexpected-serialized-provenance diagnostic;
4. do not compare arbitrary non-canonical TF metadata and do not change header parsing.

At the report publication boundary, reject source/license diagnostic keys once the corresponding required status has been proven `verified`.

## Test gates

1. focused serialized identity/distribution tests;
2. full `pytest` unit/Text-Fabric job;
3. wheel/fresh install;
4. exact pinned OCP conversion and semantic parity;
5. canonical stage/manifest/extract/reload;
6. public metadata and advanced app reload.

## Independent adversarial review gate

After the exact candidate is green, review from the reverse trust direction without relying on this implementation plan. Challenge:

- extra canonical fields in archive only;
- extra report fields only;
- mismatched optional fields;
- verified statuses paired with diagnostics;
- duplicate canonical vs duplicate non-canonical TF metadata;
- future additions to `REPORT_PROVENANCE_FIELDS`;
- whether the fix accidentally rejects ordinary Text-Fabric metadata.

Any blocking finding restarts RED → GREEN → full gates before merge.

## Dependency on #104

#104 may continue research/version preparation in parallel, but no tag/release/publication action should finalize until #110 is merged and the #104 branch incorporates the resulting `main`.

## TDD evidence

- RED head `7d5cde85f6a3091a37644584a13095b90aaab73e`, Actions run `34282750663`: exactly the two new asymmetric canonical-provenance regressions failed while 452 existing tests passed; the non-canonical `writtenBy` control passed.
- GREEN implementation commit `cc78bd1206521b1c22441cf9564ba3bbf73165bd`: the branch-local focused gate passed `tests/test_distribution_provenance_closure.py`, `tests/test_distribution_serialized_identity.py`, and `tests/test_distribution_tf_metadata_binding.py`, then removed all temporary helper files before committing.
- First human-authored candidate `5a7cefd4d9f5420a44d3bf61e407ae2b534aee52`, Actions run `34283501641`: unit/Text-Fabric and exact pinned OCP integration both passed, including canonical staging/manifest validation, stock TF reload, public metadata, and advanced app startup.
- The logically separate adversarial pass then found that matching report/archive diagnostics could still accompany required `verified` statuses. RED head `e074097bcded9363e74ea919726a50a9ce3f2411`, Actions run `34284028287`: exactly the two new contradiction cases failed while 454 tests passed.
- Review GREEN implementation commit `df59cc2ee96ce8a6f64ed318e43d7e7d087dc11b`: focused provenance/serialized-identity gates passed in run `34284190790`, and the temporary patch workflow/script removed themselves before commit.
- The final behavioral changes remain limited to two fail-closed publication invariants: canonical serialized provenance cannot exceed report-bound canonical provenance, and a required verified source/license state cannot carry its corresponding failure diagnostic. Text-Fabric header parsing and non-canonical generic metadata behavior are unchanged.