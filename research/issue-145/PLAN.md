# Issue 145 plan — preserve source occurrence ownership

## 1. RED

Add a focused semantic-audit fixture with one source version containing two consecutive units that deliberately share the same `source_ref` and `unit_id` but have distinguishable primary reading text.

Build TF data and first assert the normal report is green. Then swap only the two `reading_of` edge targets while leaving all node features and reading payloads untouched. Re-run the report and assert `reading_ownership` becomes false.

RED has been observed on commit `588f349559de0c269f7b612c4e396fa4e7023a89`: the existing report remained green after the mutation, so the new assertion failed.

## 2. GREEN implementation

Keep the literal source identity untouched and avoid adding per-reading serialized features.

Add a compact independent occurrence-audit module that:

- re-reads XML directly;
- reconstructs textual versions, source refs, and per-version 1-based unit order;
- records the direct reading payloads belonging to each raw unit occurrence;
- groups TF units by exact version ownership and sorts them by existing `unit_index`;
- resolves actual graph readings through `reading_of`;
- compares each graph occurrence and its attached reading payloads with the corresponding raw XML occurrence.

Fold this source-grounded predicate into the existing `reading_ownership` semantic check so the report shape stays stable.

Do not add a new feature, enlarge the corpus for audit-only metadata, or synthesize uniqueness into `unit_id`/`source_ref`.

## 3. Public API regression

For the same duplicate fixture, serialize/load through stock Text-Fabric and verify the two unit nodes retain identical upstream ids but `Apparatus.unit_readings()` / passage apparatus returns the first unit's reading before the second unit's reading with the correct payloads.

If an existing lightweight fake API gives equivalent coverage without bypassing TF relation semantics, it may supplement but not replace at least one real TF load regression.

## 4. Test gates

Run:

- the new focused semantic-audit RED/GREEN regression;
- direct tests of modern nested and wrapped-legacy raw occurrence traversal;
- existing audit tests;
- apparatus and Text-Fabric integration tests;
- generated-translation tests;
- the full repository CI including pinned OCP conversion/audit and researcher interface checks.

## 5. Logically independent adversarial review

Review the final diff as a hostile data-integrity check. Attempt to falsify it with:

- duplicate ref/id owner swap;
- cross-version owner with same local identity;
- missing/multiple owner edge;
- corrupted `unit_index` with otherwise correct edge;
- duplicate or reordered source identities that are legitimately preserved;
- nested and wrapped-legacy traversal order;
- generated translation occurrence accounting;
- accidental changes to public upstream ids or TF section addressing;
- hidden quadratic scans or avoidable corpus-size expansion.

Add a regression for any material bypass. Merge only after both CI jobs are green and the independent review has no blocking finding.