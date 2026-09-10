# Issue 143 plan — verify duplicate-unit occurrence alignment

## 1. RED

Extend `tests/test_generated_translation_audit.py` with a mutation regression using its existing source fixture. Build valid TF data, locate the two generated and source units sharing `source_ref=1:1` and normalized id `7`, swap only their `translation_unit_of` targets, then rebuild the semantic report. Assert the report marks `generated_translation_alignment` false.

Run the focused test against pre-fix code and record that it fails because the report remains green.

## 2. Implementation

Strengthen graph-side generated-translation validation in `semantic_audit.py`:

- index source units by exact source version and `(source_ref, unit_id)`;
- index generated units by generated version and `(source_ref, normalized unit_id)`;
- order each group by explicit `unit_index` with node id as deterministic tie-breaker;
- for every generated identity group, require the actual edge-target tuple to equal the corresponding source occurrence tuple;
- retain existing version/type/id/ref/uniqueness checks;
- fold this predicate into the existing `generated_translation_alignment` result without changing public report shape.

Avoid quadratic scans.

## 3. GREEN / regression gates

Run at minimum:

- `tests/test_generated_translation_audit.py`
- `tests/test_generated_translations.py`
- `tests/test_translation_api.py`
- `tests/test_comparison_translation_occurrence.py`
- full test suite / repository CI

The existing reordered-group fixture must remain green.

## 4. Logically independent adversarial review

Review the final diff from a falsification perspective rather than restating the implementation. Attempt these bypasses:

- swap duplicate occurrence targets;
- point at a source unit in another source version with the same ref/id;
- reuse one source target or omit an edge;
- reorder unrelated structural identities (must remain valid);
- make `unit_index` absent/duplicated/zero and ensure ordering is deterministic rather than crashing or silently weakening the check;
- inspect asymptotic behavior for hidden nested corpus scans.

Add a regression for any material bypass found. Merge only after the review is clean and CI is green.