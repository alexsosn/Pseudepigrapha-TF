# Issue #156 plan: selective feature presets

## Scope

Expose explicit feature tuples for the documented translation and apparatus passage workflows, prove them against real Text-Fabric fixtures, and replace duplicated documentation strings with those constants.

## TDD gates

1. **RED: public API and exact contracts**
   - add focused tests asserting the three tuple constants and their exact contents;
   - prove they are directly joinable for `Fabric.load()`;
   - on current code these tests must fail because the constants do not exist.

2. **RED/acceptance: real selective loads**
   - build a normal TF fixture and load `Apparatus.PASSAGE_FEATURES`; prove `passage()` works;
   - load `Apparatus.WORK_PASSAGE_FEATURES`; prove `work_passage()` works;
   - build a marked generated-translation fixture, load the passage preset, and prove apparatus safety still excludes/rejects generated material;
   - remove a truly required feature from a preset and prove the existing concise missing-feature error remains.

3. **Implementation**
   - add `Translations.REQUIRED_FEATURES` using the already measured translation-oriented load;
   - add minimal semantic `Apparatus.PASSAGE_FEATURES` and `WORK_PASSAGE_FEATURES` including generated-layer safety;
   - do not add any implicit loading or new runtime requirements to helper methods.

4. **Documentation**
   - README apparatus and generated-translation examples use `" ".join(...)` on the public constants;
   - runtime-footprint measurement example uses `Translations.REQUIRED_FEATURES` while retaining the recorded measurement and explaining that the tuple freezes that measured set;
   - `docs/apparatus.md` distinguishes mandatory passage identity/semantic fields from optional display enrichment and names generated-layer safety requirements.

5. **Verification**
   - focused preset/load-contract tests;
   - full repository test workflow including pinned-corpus gates;
   - exact-head CI must be green.

6. **Logically independent adversarial review**
   Re-read only the issue contract and final diff as a skeptical reviewer. Challenge:
   - accidental maximal/over-loaded apparatus presets;
   - missing `version_kind`/`synthetic_witness` fail-closed safety;
   - raw `Fabric.load()` compatibility versus assumptions from the advanced app;
   - metadata-only `work_passage()` identity;
   - documentation/runtime drift from the measured translation load;
   - accidental regression of intentionally narrower lower-level/absent-passage operations.

Any review finding changes the head and therefore requires re-running verification and repeating the exact-head review.
