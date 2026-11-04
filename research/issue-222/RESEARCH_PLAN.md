# Issue #222 — explicitly empty source-version selection

## Research (2026-11-04)

Current `main` at `6dd2f0339d0592f21a394017fb081bbc44ebc4d4`:
- `comparison.py::build_passage_comparison()` distinguishes `selected_versions=None` (default two) from `selected_versions=()` (show no source cards).
- `comparison.py::render_passage_comparison()` renders only checked/unchecked source-version checkboxes. HTML submits no `version` key when all are unchecked.
- `web.py::register_comparison_route()` filters version keys then passes `selected_versions or None`, conflating this explicit choice with an untouched default request.
- `comparison.py::comparison_href()` serializes only nonempty versions, so navigation from an empty state would reenable defaults.
- Witness controls already use a hidden empty `witness.{id}` input to express an explicit empty selection.
- Pinned 1 Enoch acceptance (`tests/pinned_comparison_acceptance.py`) exercises real source versions, witness evidence and `/compare`. This is a browser state boundary, not an upstream data or TF serialization change.

## Frozen plan

1. First commit this research plan, then write tests only on a separate commit.
2. Expect **RED** on old production: tests for hidden empty version marker, HTTP argument distinction, empty-state text and explicit empty navigation permalink; keep passing controls for no version key and normal selected versions.
3. Minimal production after observed RED:
   - Add an always-present hidden `version=""` in the existing GET form.
   - Distinguish query-key presence: missing `version` means defaults; present `version` with no nonblank values means explicit zero.
   - Make `comparison_href(selected_versions=None)` omit keys as before, while `selected_versions=()` serializes one empty marker. Preserve nonempty chosen version/witness values.
   - Render an explanatory empty state with the normal selector still available; update `docs/tf-app.md`.
4. Require exact final-head full `pytest` + pinned OCP convert/semantic/stock TF/browser tests in CI.
5. Perform a separate adversarial diff/code/tests/real-data review, document results in GitHub review, merge only when final-head gates are green; verify post-merge main CI.

## Scope / risk

The user's clear action of unchecking every source must not silently restore data. This remains fully reversible by checking a source version. Invalid versions still fail closed; metadata-only distinctions, witness semantics, generated translations, OCP source and immutable release v1.1.0 are untouched. No JavaScript or new infrastructure.
