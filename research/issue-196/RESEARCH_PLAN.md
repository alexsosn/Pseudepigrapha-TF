# Issue #196 — Cross-file OCP work identity uniqueness

Status: frozen source-grounded research and plan before tests/implementation.

## Grounded repository evidence

- `source.load_source_directory` validates each XML file and appends a `Book` but never checks cross-file `Book.filename` uniqueness.
- `conversion._validate_and_classify_model` validates that each book ID is nonblank but not unique within the corpus. `build_tf_data` distinguishes objects by integer indices, so two graph books can share the same researcher-facing `ocp_book` identifier, making `/compare?work=` and cross-version lookups ambiguous.
- `audit._raw_inventory` iterates XML separately and records all file hashes and versions but does not reject two book roots with the same work identity. A false-positive raw-vs-graph parity is possible if both sides materialize duplicate IDs.
- Existing `tests/fixtures/sample.xml` is valid modern OCP including text, multiple readings and witnesses, and external DTD reference; `tests/fixtures/legacy.xml` is a valid alternate dialect.

## Chosen fail-closed contract

Unique **exact** nonblank `book/@filename` per **physical XML file** in one input directory / one `build_tf_data` corpus. Do not silently merge/deduplicate, rename, lowercase or trim researcher-visible source work identities. Many `<version>` siblings **within one file** remain supported and can share titles where allowed. Distinct work IDs may coincidentally have versions with identical titles.

## Implementation boundary

1. In `load_source_directory`, maintain `seen_works: dict[str,str]` and raise `InvalidSourceError` on the second parsed physical document that declares an existing `book.filename`, including exact work ID and both source file names. Keep skipped empty XML warnings unchanged.
2. In `_validate_and_classify_model`, track work IDs independently before graph mutation and reject duplicates using `ValueError` including the work ID; distinguish direct API use where source_path may not be set.
3. In `audit._raw_inventory`, independently check root `filename` collisions before inventory insertion, with a separate local `seen_works` dictionary and both filenames, so auditing raw files alone fails closed even without invoking loader.
4. Keep text feature graph, report/provenance, generated translation classification and TF section ID construction unchanged.

## Frozen RED → GREEN → real corpus → independent review

- RED-only tests duplicate a real modern XML source across files and mutate one reading's bytes, asserting loader, model builder, and raw auditor reject same work ID with useful diagnostics. Positive cases confirm distinct work IDs with same version titles and one document containing multiple versions remain supported. Tests committed before implementation and RED confirmed in GitHub Actions.
- Minimal implementation with exact-id checks; run full unit/TF suite and complete pinned 38-nonempty OCP corpus conversion/parity, distribution staging, offline Text-Fabric ZIP load and real 1 Enoch comparison.
- Independent skeptical review on **exact final head** against original parser/loader/model/auditor source and actual pinned CI data, posted to GitHub before merge. No numerical performance claim.

## Explicit limitations

Exact identity uniqueness does not prove that case/Unicode/whitespace-confusable values are distinct to every downstream consumer; that needs separate research. This ticket prevents **exact** OCP work-identity collisions across separate physical source files, without inventing canonical names or merging different scholarly witnesses.
