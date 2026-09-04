# Research: complete version metadata parity

## Scope

Issue #3 targets the semantic parity gate in `conversion-report.json`.

## Current behavior

The raw XML inventory records only `ocp_book` and `version_title` for each version. The TF graph stores materially more upstream metadata on textual `book` nodes and metadata-only `version_metadata` nodes:

- source book title;
- source `textStructure`;
- version title;
- version author;
- version language;
- version fragment marker;
- source XML filename;
- source XML SHA-256.

Because the audit compares only work/version identity, corruption of any of the other fields is currently invisible. The red regression on PR #4 demonstrates this for seven independent corruptions while unrelated tests remain green.

## Source/model correspondence

For normal `<version>` records, the raw XML values map directly to the graph features above. For legacy chapter/verse books, parser semantics are the contract: version title is `root/@language` or `Default`, author and version fragment are empty, and language is `root/@language`.

`load_source_directory()` supplies stable basename-only `source_path`; the raw audit already computes each source SHA-256 while reading files. Reusing those exact values in each version record avoids a second file read and keeps the comparison deterministic.

Metadata-only versions use the same metadata fields as textual versions, so they must participate in the identical comparison rather than a reduced special-case inventory.

## Design choice

Expand the existing `versions` semantic record instead of adding several independent checks. This keeps one canonical comparison for one conceptual upstream object, catches cross-field mismatches together, and preserves the existing report schema and CI assertions.
