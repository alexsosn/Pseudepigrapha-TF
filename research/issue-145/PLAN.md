# Issue 145 plan — preserve source occurrence ownership

## 1. RED

Add a focused semantic-audit fixture with one source version containing two consecutive units that deliberately share the same `source_ref` and `unit_id` but have distinguishable primary reading text.

Build TF data and first assert the normal report is green. Then swap only the two `reading_of` edge targets while leaving all node features and reading payloads untouched. Re-run the report and assert `reading_ownership` (or another explicitly occurrence-aware semantic check) becomes false.

Before implementation, observe the test failing because the current report remains green.

## 2. GREEN implementation

Keep the literal source identity untouched and use existing `unit_index` as source-order occurrence identity:

- assign a 1-based, per-version source-order unit index in the raw XML inventory;
- include it in raw unit and reading records;
- stamp the owning `unit_index` on each reading when the graph builder creates it;
- include it in graph unit and reading inventory records;
- require reading `unit_index` to equal its `reading_of` target's `unit_index` in the ownership check.

Do not add a new feature name or synthesize uniqueness into `unit_id`/`source_ref`.

## 3. Public API regression

For the same duplicate fixture, serialize/load through stock Text-Fabric and verify the two unit nodes retain identical upstream ids but `Apparatus.unit_readings()` / passage apparatus returns the first unit's reading before the second unit's reading with the correct payloads.

If an existing lightweight fake API gives equivalent coverage without bypassing TF relation semantics, it may supplement but not replace at least one real TF load regression.

## 4. Test gates

Run:

- the new focused semantic-audit RED/GREEN regression;
- existing audit tests;
- apparatus and Text-Fabric integration tests;
- generated-translation tests, because generated readings also pass through `_add_unit()`;
- the full repository CI including pinned OCP conversion/audit and researcher interface checks.

## 5. Logically independent adversarial review

Review the final diff as a hostile data-integrity check. Attempt to falsify it with:

- duplicate ref/id owner swap;
- cross-version owner with same local identity;
- missing/multiple owner edge;
- corrupted reading-side `unit_index` with otherwise correct edge;
- duplicate or reordered source identities that are legitimately preserved;
- nested and wrapped-legacy traversal order;
- accidental changes to public upstream ids or TF section addressing;
- hidden quadratic scans or avoidable corpus-size expansion.

Add a regression for any material bypass. Merge only after both CI jobs are green and the independent review has no blocking finding.