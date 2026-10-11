# Issue #211 — consistent XML work identity with and without intros.json

Frozen source-grounded research and TDD plan. This is committed **before** RED tests or production changes.

## Reproduced code-level gap

`source.load_source_directory()` validates input boundary and parses every root-level `*.xml` with `parser.parse_bytes()`. The parser preserves `root.get("filename")` as `Book.filename` while saving `xml_path.name` in `Book.source_path`, and the loader checks only duplicate work IDs *between* different XML files, not a mismatched filename on a single source document. `metadata._validate_xml_identities()` independently re-reads XML to require `<book filename>` to equal the XML basename, but it runs only when optional public `intros.json` is present. A directory with `Wrong.xml` claiming `filename="Sample"` currently passes the common source loader; the researcher-facing `ocp_book` can disagree with the documented XML source path.

The pinned source is not implicated: the public-metadata path already checks all nonempty XML source filenames. This issue targets hand-supplied subsets and materializers lacking intros.json, without altering textual content or the 1.1 prepared release version.

### Legacy test-fixture complication

`tests/test_source.py` uses `sample.xml` with `filename="Sample"`. `tests/test_unique_ocp_book_identities.py` creates `first.xml`/`second.xml` with `filename="Sample"`, and `one-work.xml` with that same root identity. These deliberately unrelated duplicate/multi-version tests must be adjusted to **use identity-coherent synthetic filenames** while still exercising their original behavior. In the duplicate-ID test, the duplicate logic may legitimately precede mismatched-stem rejection, but the fixture should no longer depend on that ordering.

## RED test gate

New `tests/test_source_file_work_identity.py`:
- Nonempty single `Another.xml` claiming `filename="Sample"` must raise `InvalidSourceError` with source filename and claimed `Sample` identity even without intros.json.
- A valid `Sample.xml` containing original exact `filename="Sample"` remains supported (same parser model and source hash). No canonicalization or case-folding.
- A case-sensitive mismatch `sample.xml` vs `Sample` must fail explicitly, because identity keys are exact.
- Empty XML filename is skipped with existing warning rather than rejected as missing root work identity.
- Optional `intros.json` absence must not alter duplicate/no-nonempty-source semantics.

Commit RED tests separately, capture expected failures in GitHub Actions before implementation. The fixture updates happen only in GREEN implementation.

## GREEN implementation and review gates

In `source.load_source_directory()`, just after successful `parse_bytes`, require `book.filename == xml_path.stem`. Raise `InvalidSourceError` naming path and declared filename; never silently rename work identifiers. Preserve existing duplicate check, generated translations, and empty-file behavior. Update only necessary synthetic fixtures for consistency.

Run complete unit suite and exact-head pinned full OCP integration: full source conversion, semantic source-vs-graph audit, canonical/express distribution, stock offline Text-Fabric load, advanced app and comparison acceptance. Separately inspect final diff adversarially for original errors and fixture drift, source-path edge cases, empty-file behavior, ASCII/Unicode case, existing metadata check and pinned-source identity; post this review directly to GitHub and merge only if all gates pass.

## Deliberate exclusions

No changes to `parse_bytes()` behavior for in-memory research-use parser callers without a trusted filesystem name, no XML reparsing, no upstream pin changes, no new scholarly fields, and no changes to converter 1.1.0 / data 1.1 or release publisher. Release issue #206 stays open until actual public release and Agora registry pin verification.
