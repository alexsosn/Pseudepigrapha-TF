# Issue #220 — Direct passage jump from comparison result

## Source-backed research
- The tracked comparison result renderer currently submits `work`, `chapter`, and `verse` as hidden fields in the same GET form as the source-version choices.
- `/compare` already parses and validates free-form chapter/verse query parameters; no new route, backend state, or data layer is needed.
- The existing witness checkboxes live in version cards outside the form but explicitly refer to `form="comparison-controls"`. Preserve this wiring.
- Previous/Next derives actual source-version topology, and must remain unchanged. A researcher needs a direct arbitrary-reference jump as well.

## Frozen plan
1. RED test in `tests/test_comparison_navigation.py`: result page has a single comparison form with visible labeled required chapter/verse text inputs retaining their current values; existing work, source-version and witness selection contract remains intact; malicious section labels must be HTML-escaped in attributes.
2. Commit test first and observe failing CI against unmodified production. Failure should be attributable to hidden rather than editable input, not arbitrary runner/setup errors.
3. In `render_passage_comparison()`, keep work hidden; replace chapter/verse hidden controls with two labeled editable required controls inside the same existing GET form. Use current escaping helper and avoid JS/new state.
4. Note behavior in `docs/tf-app.md`.
5. Run exact final PR-head unit and complete pinned OCP/Text-Fabric integration CI. Conduct logically-independent skeptical review of source, diff, and real test data. Merge only if green, then verify postmerge main CI.

## Risk/acceptance
- Selection of historical source versions and manuscript witnesses remains submitted to the same route.
- No new serialization, translation/witness semantics, link format, or release publication changes.
- `v1.1.0` immutable tag/assets remain unchanged; these edits are post-release source improvements.
