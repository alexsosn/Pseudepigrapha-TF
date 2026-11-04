# Issue #226 — make the comparison work chooser understandable and reachable

## Research (2026-11-04)

Latest main at branch creation: `01d54af3dbe2455b105e8b51ab1028343f363628`.
- `src/pseudepigrapha_tf/web.py::list_comparison_works()` walks non-generated TF book nodes and returns sorted stable `ocp_book` identifiers. `_landing_html()` exposes these as raw option text (e.g. `1En`), giving users no work-title context.
- OCP fixture `tests/fixtures/sample.xml` declares `<book filename="Sample" title="Sample Work">`. `docs/features/title.md` defines `title` as the original work title on book nodes. `Apparatus.work_passage()` already uses `F.title` as the result-page heading.
- `tests/pinned_comparison_acceptance.py` loads real `title`, `ocp_book`, `version_kind` features for the full pinned corpus and verifies the real Flask route.
- A successful result page renders `<nav class="comparison-nav"><a href="/">Text-Fabric browser</a></nav>` but has no link to the existing work selector at bare `/compare`. Invalid-request pages *do* link there. A deep-linked or bookmarked comparison should be able to switch works without URL editing.
- Source book titles can be absent or potentially differ among source versions. Never infer or choose an editorial title arbitrarily; use a full label only when one distinct nonblank upstream title is present across **all** non-generated source versions, otherwise fall back to the canonical id.

## Frozen plan

1. This source-backed plan precedes all tests and production changes.
2. Add tests-only **RED** cases: source work options (original title with stable id, generated exclusion, missing `title` fallback, conflicting titles, deterministic id order), HTML-escaped malicious work id/title, work-picker link on opened comparison, and real pinned source/landing+bookmark route. Preserve existing `list_comparison_works()` id-only contract. Tests-only commit; observe actual failures on original code.
3. Minimal implementation: construct work options in one pass over source `book` nodes from loaded TF features; return `(canonical_id, display_label)` pairs; preserve `list_comparison_works()` as an id-tuple projection; show display labels on the cached landing form and keep option values the exact original ids. Add a normal unfiltered `/compare` link to the result navigation, no JavaScript/new endpoint. Update `docs/tf-app.md`.
4. Run exact-final-head full pytest plus pinned OCP conversion, semantic checks, archive/offline stock TF, advanced app and 1 Enoch browser acceptance in GitHub Actions.
5. Perform logically independent adversarial diff/code/real-data review on the final head. Post review to GitHub. Merge only after exact-head GREEN with SHA lease and confirm post-merge main CI.

## Risk boundaries

No inferred cross-version passage alignment, no changes to apparatus/witness/translation semantics, no new corpus features or source revision, no modification to published v1.1.0 assets. HTML escaping and no hidden re-submission of obsolete version selections when switching works are mandatory. The landing cache stays per Flask app and lazy.
