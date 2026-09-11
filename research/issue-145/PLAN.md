# Issue 145 plan — preserve source occurrence ownership

## 1. RED — completed

Add a fixture with two consecutive source units that deliberately share the same `source_ref` and `unit_id` but have distinguishable readings. Build valid TF, swap only their `reading_of` targets, and require the semantic report to fail `reading_ownership`.

RED was observed on `588f349559de0c269f7b612c4e396fa4e7023a89`: the previous audit remained green after the mutation.

## 2. Initial GREEN attempt — rejected by performance gate

The first implementation rebuilt occurrence ownership from a second direct XML traversal. It caught the mutation but failed the established single-pass source-audit contract because every XML file was read twice. Do not retain this approach.

## 3. Final GREEN implementation

Keep literal upstream identity untouched and use the existing structural TF invariant:

- retain the existing exact-version/cardinality/source-identity `reading_of` checks;
- independently require every reading's non-empty `oslots` support to equal its claimed unit owner's `oslots` support;
- rely on the surrounding one-pass raw XML parity and reconstruction checks for source payload correctness;
- add no new serialized features and no additional source read.

The mutation regression must become green while `test_semantic_audit_reads_special_structure_source_once` remains green.

## 4. Researcher-facing regression

Serialize the duplicate fixture with the normal writer, load it through stock Text-Fabric, and verify:

- both unit occurrences retain literal `source_ref=1:1` and `unit_id=7`;
- ordering by `unit_index` identifies the two occurrences;
- `Apparatus.unit_readings()` returns `alpha` for occurrence 1 and `beta` for occurrence 2.

## 5. Test gates

Run the complete repository CI. In particular verify the focused mutation/API tests, single-pass audit test, ownership/audit tests, apparatus/TF integration tests, generated-translation tests, and the full pinned-OCP conversion/reload/advanced-app/comparison path.

## 6. Logically independent adversarial review

Review the final diff from a falsification perspective. Attempt:

- duplicate ref/id owner swap;
- missing or multiple owner edge;
- cross-version target with matching local identity;
- missing, empty, or mismatched reading/unit oslots;
- empty-primary/gap-slot occurrences;
- generated-translation readings using the same structural invariant;
- accidental changes to upstream ids or section addressing;
- extra XML reads, corpus-size growth, or hidden super-linear scans.

Also assess coordinated edge+support corruption separately. If it exposes a realistic converter failure not covered by the existing raw parity/reconstruction/validation gates, file a focused follow-up rather than growing this ticket into duplicate parser infrastructure.

Merge only after both CI jobs are green and the independent review has no blocking finding.
