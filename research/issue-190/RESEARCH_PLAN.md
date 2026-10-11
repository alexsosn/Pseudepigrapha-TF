# Issue #190 — Bounded express app validation against exact checkout

Status: frozen plan committed before RED-only tests and implementation.

## Source-level diagnosis

- `_validate_express_archive` in `distribution.py` already streams native TF features to compare with complete.zip but uses `app_payloads[relative] = zf.read(info)` for every application member. This retains whole decompressed bodies; a malicious huge `app/` entry can exhaust memory before it is rejected by the exact-checkout comparison.
- `_validate_express_app_identity` calls `_collect_app_payloads(app_directory)` which reads every tracked regular app file with `Path.read_bytes()` into a dictionary. This introduces a second full collection of app bytes and is unnecessary for exact byte identity.
- `_collect_app_payloads` simultaneously implements important path/symlink/special entry checks and is consumed by express construction. Preserve its external/private caller behavior as a byte dictionary for construction, but factor out common enumeration for streaming validation.
- Existing `test_express_streaming` expects validator return bytes. This is a private/internal API; tests must move to explicit `{name,bytes,sha256}` records without changing the public manifest JSON or `validate_distribution` return value. Actual Python zip entries need EOF reads for CRC.

## Chosen architecture

1. Factor `_enumerate_app_files(app_directory) -> dict[str, Path]`: reject root symlink, missing directory, symlinked child even in excluded dirs, unsafe path components, non-file special members; preserve filtering of `.DS_Store`, `.tf`, `__pycache__`, `_local`, `_temp`, `.ipynb_checkpoints`, and reserved `__checkout__.txt`. Require config.yaml. Sorted relative path order.
2. `_collect_app_payloads` uses enumeration and still reads bytes only for *builder* compatibility; `_validate_express_app_identity` separately streams each actual file with `_native._hash_stream_record(relative, source)` and checks exactly `name,bytes,sha256` against express records and membership.
3. `_validate_express_archive` streams every `app/` member using `zf.open(info)` and `_native._hash_stream_record(relative, stream)` (bounded 1MiB chunk helper), not `ZipFile.read`. Check canonical order, member kind, paths, known exclusions as before. Parse the app and data checkout markers through a bounded streaming `_streams_equal` check against the exact expected marker rather than treating them as potentially giant byte strings; stream to EOF on correct entries to enforce CRC.
4. Maintain exact app filename/content equality through both SHA-256 and actual decompressed count. No change to native TF member behavior, duplicated names, marker semantics or manifest schema. Handle `BadZipFile`/I/O failures as existing `DistributionContractError`.

## RED → GREEN → pinned-data → skeptical review

1. RED-only regressions: build `complete.zip` with >1MiB app payload, patch `ZipFile.read` to reject all `app/` reads, require stream-hash records. Patch `Path.read_bytes` during `_validate_express_app_identity` and require correct identity; mutate same-length app file to reject; corrupt a stored app member to assert `DistributionContractError` via CRC.
2. Add tests for canonical checkout markers (wrong marker, huge marker), missing config and symlink under excluded dir, verify positive official app fixture still works. Update prior internal validator-byte-return test when implementing revised internal contract.
3. Implement minimal source/enumeration refactor, unit/TF tests, complete pinned OCP conversion, semantic audit, release ZIP packaging/extract, stock offline Text-Fabric load, tracked app identity and 1 Enoch comparison.
4. Perform a genuinely independent skeptical review on exact GREEN HEAD with actual patch, independent data checks and CI logs; post to PR, merge only if no blockers.

## Explicit limits

- Streaming ensures bounded **per-read app member** buffering, not an expanded-archive size/time quota. A malicious ZIP bomb may still require long stream time. A resource budget policy is separate research.
- Express *construction* continues to collect tracked app files into a byte dictionary; this issue targets untrusted complete.zip **validation** only. No claim of measured whole-process RSS reduction.
- SHA-256 equivalence is a cryptographic byte-identity check, not a proof that any app source file is safe to execute. Existing exact-release provenance is still required.
