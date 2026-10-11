# Issue #213 — eliminate redundant full XML parse in public metadata loader

Frozen research and development plan. This file is the sole change in the planning commit, preceding RED tests and implementation.

## Evidence from actual code

In `cli.main()`, `books = load_source_directory(args.source)` uses `parse_bytes(raw, source_path=xml_path.name)`; its `Book.source_sha256` and strict `Book.filename == xml_path.stem` are already validated (#211). If `intros.json` exists, `load_public_metadata(args.source)` calls `_validate_xml_identities(source_dir)`, which traverses **all** `*.xml`, reads raw bodies, and runs `ET.fromstring(raw)` for each nonempty document solely to repeat the identity check. The independent `semantic_audit.build_conversion_report()` separately re-reads/re-audits raw XML and must remain unchanged.

Full pinned OCP includes 32 public metadata records plus source corpus XML; no reason to build a second full in-memory ElementTree when the CLI has already parsed the same source before metadata loading. Standalone `load_public_metadata` must continue to validate XML itself.

## RED tests

New unit tests use exact fixture XML and `intros.json` with two documents, an empty XML placeholder, and the unaltered `load_source_directory`. Tests should require:
1. On CLI/path with already parsed books, `load_public_metadata(source, parsed_books=books)` accepts exact inputs **without calling `ET.fromstring` or rereading nonempty XML** in the metadata module.
2. Standalone `load_public_metadata(source)` still reparses XML and rejects mismatch, malformed XML and unsupported source metadata entries.
3. The optimization must fail closed if caller supplies a missing book, mismatched identity or duplicate source path, or if an unparsed **nonempty XML file** appears in source; empty/whitespace-only unparsed placeholders remain allowed.
4. A CLI wiring test proves it passes the parsed book models instead of using the full standalone reparse path, without mocking away source validation.
5. Source SHA/TF text and JSON scalar values unchanged.

Commit tests only and confirm actual RED failure on GitHub Actions, with untouched production code.

## GREEN implementation

- Add `parsed_books: Sequence[Book] | None = None` keyword-only argument to `load_public_metadata`. For `None`, retain standalone `_validate_xml_identities` behavior unchanged. When provided, validate a **complete** path-qualified parsed source inventory against the directory's visible XML names without reparsing already parsed files. Validate each Book's `source_path` and `filename` exactly, reject duplicates or a claimed work without corresponding XML. Any path not covered by provided models must be checked for blank bytes or rejected as unparsed nonempty XML, allowing OCP empty placeholders. Names of XML source files need to agree with the metadata `documents` keys as they did before.
- The CLI passes its own parser output only on the metadata-enabled path. Preserve the direct `load_public_metadata(path)` and `parse_bytes` contracts. Keep semantic audit's independent raw checks and source hash provenance.
- Avoid building source XML trees again or materializing duplicate XML for already parsed books. Add no editorial normalization, no changes to 1.1 data.

## Final gates

Run full unit and pinned OCP end-to-end CI for the **exact final head**, including corpus source/graph parity, native/express release candidate validation, stock offline TF reload, researcher app and 1 Enoch comparison. Conduct a logically independent skeptical review against actual diff, source fixtures and CI logs; challenge fabricated inventory, duplicate XMLs, late-added XML, empties/hidden entries, and TOCTOU/documented limitations. Post review to GitHub and only merge with exact-head protection after all tests pass.
