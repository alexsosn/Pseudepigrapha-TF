# Issue #119 — canonical distribution test-fixture consolidation

## Baseline

Exact merged-green `main`: `4cf954d101c47bcab2c99500dc2af6625aac2bb1`.

This is test-maintainability / drift-prevention work discovered during the logically independent review of #114. It must not change runtime release semantics.

## Research findings

### Duplication inventory

Five distribution-test modules currently implement the same nominally-valid canonical OCP release baseline independently:

- `tests/test_distribution_directory_validation.py`
- `tests/test_distribution_feature_set.py`
- `tests/test_distribution_manifest.py`
- `tests/test_distribution_provenance_closure.py`
- `tests/test_distribution_staging.py`

Each repeats `_canonical_generic()` and/or `_canonical_otype_payload()` around the same researched source tuple and `corpus_license_metadata(..., source_identity_verified=True)`, then projects the profile through `report_provenance()`.

This duplication already caused #114's first GREEN to expose stale partial fixtures when the release contract became stricter. A future canonical verified-profile field would again require coordinated edits across several files.

### Tests that should *not* be normalized behind the same helper

`test_distribution_provenance_profile_authenticity.py` deliberately mutates individual canonical profile fields to challenge the release trust boundary. The hostile mutation functions and expected bad values must remain local and visible.

`test_distribution_serialized_identity.py`, `test_distribution_tf_metadata_binding.py`, and related representation-integrity suites intentionally construct asymmetric or partial identities to test which layer diagnoses a defect. Moving all of those constructions behind a positive-profile helper would obscure the representation under test and risk making negative tests tautological.

The shared helper is therefore for **nominally valid positive baselines only**. Negative tests may start from that baseline where appropriate, but their mutation/omission must stay explicit at the call site.

### Import / packaging boundary

The project uses a `src/` runtime layout and pytest is configured with `testpaths = ["tests"]`. A repository-root `test_support/` namespace is importable during repository tests but is outside `src/pseudepigrapha_tf`, so it is not part of the installed runtime package/wheel. It also avoids introducing `tests/__init__.py` and avoids relying on a potentially shadowed generic top-level `tests` package.

Chosen helper path: `test_support/distribution.py` (PEP 420 namespace; no `__init__.py`).

### Canonical source of truth

The positive baseline should derive from production provenance ownership rather than copy policy constants:

- `OCP_REPOSITORY` / `OCP_PIN` identify the researched source tuple;
- `corpus_license_metadata(..., source_identity_verified=True)` owns the complete canonical verified profile;
- `report_provenance()` owns the generic-TF → report key projection.

The helper may use synthetic converter/data versions (`0.1.0` / `0.1`) where existing tests intentionally exercise schema mechanics independent of the current release version. This refactor must not silently convert historical/synthetic fixture identity to 0.2.

## Plan

### Test-only helper API

Create `test_support/distribution.py` with:

- `canonical_generic(overrides=None)` — complete verified OCP generic metadata plus the existing synthetic converter version;
- `canonical_report_provenance(overrides=None, omit=())` — projection from that generic profile with explicit report-level mutation/removal support;
- `canonical_otype_payload(generic_overrides=None, extra_metadata=None, data_version="0.1")` — deterministic `otype.tf` bytes containing the complete canonical profile plus normal TF generic metadata.

The helper must return fresh mappings and must not mutate shared global state.

### Refactor scope

Replace only duplicated positive baseline construction in the five inventoried modules. Keep each test's own archive/report/feature identity mechanics, release commits, and deliberately malformed values local.

Do not change `src/pseudepigrapha_tf/*`.

### Anti-circularity rule

The shared helper is allowed to derive the positive canonical baseline from `corpus_license_metadata()` because the purpose is fixture drift prevention. Tests whose purpose is to challenge canonical-profile truth must keep hostile field names/values and mutation functions outside the helper. No helper method such as `wrong_license_profile()` will be introduced.

## TDD sequence

### RED

Add a structural regression before the helper/refactor which enumerates the five positive-baseline modules and fails while any still defines `_canonical_generic()` or `_canonical_otype_payload()` locally.

Expected current failure: all five inventoried modules are reported as offenders; unrelated tests remain unchanged.

### GREEN

1. add the test-only helper;
2. refactor the five nominally-valid baseline modules to import it;
3. extend the drift regression to prove:
   - `canonical_generic()` contains every field produced by the canonical verified `corpus_license_metadata()` profile;
   - `canonical_report_provenance()` exactly follows `report_provenance(canonical_generic())` before explicit overrides/omissions;
   - `canonical_otype_payload()` serializes every canonical generic field;
   - explicit omission removes only the requested report key, so asymmetry tests remain possible;
4. no production source edits.

## Verification gates

1. focused distribution suite (`tests/test_distribution_*.py` plus the new fixture-contract test);
2. full pytest / real Text-Fabric suite;
3. wheel/fresh-install contract remains green and test support is not shipped as runtime API;
4. exact pinned OCP integration remains green;
5. `git diff --check` / no accidental production changes.

## Logically independent adversarial review

Review the exact final GREEN head without relying on this plan. Challenge:

- has consolidation made #113 authenticity tests circular?
- are wrong/omitted profile values still explicit where they matter?
- can an added canonical verified-profile field silently be absent from positive fixtures?
- do override/omit helpers accidentally mutate shared state or leak between tests?
- did a synthetic 0.1 fixture get incorrectly upgraded to current release 0.2?
- is `test_support` accidentally included in runtime packaging?
- did representation-asymmetry diagnostic tests lose specificity?
- are there still duplicated complete canonical positive-profile builders elsewhere?

Any blocker restarts RED → GREEN → full gates.

## Gate checkpoint

The historical RED unit job on commit `08258878da17e61cfe401ca849e34d7e5553fcc3` completed before its superseding run was cancelled: exactly the structural regression failed, reporting all five inventoried positive-baseline modules, while 484 unrelated tests passed. The implementation candidate remains test-only. This checkpoint commit exists to obtain fresh full GREEN gates for the completed refactor against the current `main` before independent adversarial review.