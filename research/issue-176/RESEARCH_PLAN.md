# #176 Research and frozen plan: app-scoped landing page cache

Status: planned before tests and implementation.

## Primary-source research

- `src/pseudepigrapha_tf/web.py`: a request without all three passage parameters takes `_landing_html(tf_app.api)` on every call. `_landing_html` enumerates `list_comparison_works`, which invokes `F.otype.s('book')`, filters `version_kind == generated_translation`, deduplicates/sorts source work IDs, then concatenates an escaped HTML select/form. Loaded Text-Fabric corpus is immutable for one browser-app instance.
- `register_comparison_route` already retains `Apparatus`, `PassageNavigator`, `Translations` in one app-lifetime closure. It is safe and consistent to retain the identical computed landing string in that closure only. No global state or new dependency.
- Existing `tests/test_comparison_web.py` has Flask/fake-API route tests and real miniature Text-Fabric acceptance; `tests/pinned_comparison_acceptance.py` tests a complete pinned actual corpus. The real pinned corpus contains 349 source-declared versions (231 are generated translations) and is materialized/loaded in CI.

## Options considered

1. Compute at registration: rejected; callers only visiting `/compare?work=...` would pay work inventory cost, and minimal fake API tests would break.
2. Process-global memoization by `id(api)` or weakref: rejected; cross-corpus/Flask isolation and lifecycle/collision risks.
3. **Chosen:** lazily evaluate `_landing_html(tf_app.api)` on the first incomplete/landing request, cache the fully escaped HTML within that particular route closure. Concurrent first requests may each compute harmlessly; correctness must not depend on a lock. Errors during computation leave the cache unset and propagate as today.
4. Cache only the work inventory and rebuild HTML every time: correct but retains unnecessary string reconstruction; not chosen.

## Frozen RED → GREEN → test → review gates

1. RED-only regression tests: route registration triggers no work enumeration; two landings (plain/incomplete) use precisely one HTML computation; a valid passage never populates the cache; distinct Flask apps with different APIs never share cached work options; first computation exceptions do not poison the cache; output remains escaped and contains source works.
2. Implementation: minimal closure-local nullable `landing_html`, using a helper so the `Response(..., mimetype='text/html')` contract stays unchanged and `_landing_html` remains available as a public testable function.
3. Focused and full suite GREEN + pinned full OCP conversion, TF 13.1 reload and real browser comparison workflow. No performance threshold or unsupported numerical speedup claim.
4. Freeze PR head and independently adversarially review source code, tests, cache lifecycle, error behavior, and pinned acceptance. Merge only when both exact-head jobs succeeded.

## Limits

One Flask app's underlying TF API is treated as immutable. A manually mutated fake API after caching is not expected to be reflected until a new Flask app; this mirrors existing persistent source/helper indexes. In a simultaneous first-landing race, duplicate initial computation is allowed but cached HTML will be equivalent. Any future dynamic corpus reload would require a new app registration or explicit invalidation contract.
