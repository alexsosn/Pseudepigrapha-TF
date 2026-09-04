# Plan: complete version metadata parity

## Acceptance criteria

- Raw XML version inventory includes book title, `textStructure`, version author/language/fragment, source filename, and source SHA-256 together with OCP work/version identity.
- Textual TF `book` inventory compares exactly the same fields.
- Metadata-only `version_metadata` inventory compares exactly the same fields.
- Deliberate corruption of each textual-version field fails the `versions` semantic check.
- Deliberate corruption of metadata-only version metadata also fails the `versions` semantic check.
- Existing semantic checks, Text-Fabric integration tests, and pinned complete-OCP conversion remain green.

## TDD sequence

1. Add the textual-version corruption regression and observe red CI.
2. Add equivalent metadata-only coverage before production changes.
3. Expand raw and graph version inventories without changing the external report shape.
4. Run fast unit/Text-Fabric tests and the complete pinned-upstream integration.
5. Review the final PR independently for false positives/negatives, legacy-source compatibility, redundant I/O, and provenance semantics.
6. Revise and rerun CI if review finds any issue; merge only after the independent review is clean.
