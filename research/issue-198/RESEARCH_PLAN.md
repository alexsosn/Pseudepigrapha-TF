# Issue #198 — Fail-closed maximum OCP `<div>` nesting before recursive consumers

Frozen research/implementation plan; authored before tests and production changes.

## Real code evidence

- `source_structure.validate_source_structure()` already uses an explicit iterative `stack` and tracks `div_path` as a tuple. It currently imposes no nesting limit.
- `parser._parse_div()` recursively constructs nested `Div.items`; `parser._raw_unit_identities()` has a recursive nested `walk` for generated translations; `audit._raw_inventory()` has recursive `walk_div`; `graph._add_version()` defines recursive `visit` for TF graph emission. Python's call stack can be exhausted on deeply nested, well-formed OCP XML before a source-specific diagnostic is raised.
- A hard limit is an intentional safety boundary because stack-safety needs to hold in **all** recursive consumers. A tiny parser-only conversion to iteration would not fix audit and graph consumption. No legitimate pinned text is known to contain near-hundred-level div nesting.

## Chosen boundary

Introduce named public-to-maintainers `MAX_SOURCE_DIV_NESTING = 128` in `source_structure.py`. While traversing a `<div>`, the validator already appends the division's `number` to `div_path`; reject any depth greater than 128 with `SourceStructureError` including the source filename, actual nesting depth, configured maximum, owning `<div>`, and path. `parse_bytes` already converts this to `InvalidSourceError`; raw inventory also calls `parse_bytes` early and should fail with the same source-grounded error. This is fail-closed rather than silently dropping nested content.

## Explicit RED → GREEN tests

1. RED-only synthetic well-formed modern source containing 1100 `<div number='1'>` levels and one meaningful `<unit><reading>` at bottom. Build XML bytes by concatenating strings, *not* `ET.tostring` on a recursive tree. Expect `InvalidSourceError` (never raw `RecursionError`) with `deep.xml` and `nesting depth` and numeric maximum.
2. RED also for direct `validate_source_structure` on ET root, and for source-independent `_raw_inventory` over a temp directory. The root is otherwise structurally valid and has a declared manuscript.
3. Positive tests: a 32-level nested source preserves all 32 model `Div` objects, the final unit ID and raw reading text; standard modern/legacy fixtures remain valid; legacy `chapter/verse` shape is unaffected.
4. Implement the one common preflight depth check. Avoid changes to recursive model builder, scientific graph features, edition text or source attribution.
5. Full unit/TF and pinned OCP source conversion/semantic audit, canonical release ZIP, stock offline TF load, and browser comparison. If pinned OCP hits the bound, examine its actual source depth rather than bypassing the error.
6. Perform a logically independent adversarial review against exact final patch, RED-only CI, complete pinned corpus evidence, error handling and threshold rationale. Post review on GitHub; merge only exact final CI-green SHA.

## Scope limits

This does not claim support for arbitrary-depth documents. A future effort can remove the limit only by making parser, source audit, graph serialization and generated-translation traversal all nonrecursive. Python recursion depth can be configured differently by callers; depth=128 leaves substantial margin under the commonly configured ~1000 stack limit for normal library frames. Other possible adversarial resource exhaustion (huge width, massive text, unbounded total input bytes) needs independent policy and research.
