# Issue #192 — Canonical express app construction with streamed source files

Status: research/plan frozen before tests and production changes.

## Grounded code finding

- `_build_express_archive` currently calls `_collect_app_payloads(app_directory)`, a byte dictionary for all tracked app files, then copies its values to `members` and uses `zf.writestr` for each. This retains every app payload as bytes through complete.zip construction.
- Issue #190 already factored the exact path/symlink/allowed-file rules into `_enumerate_app_files(app_directory)` and changed *validation* to stream hashes. The builder is now the remaining tracked app full-buffer path; native corpus feature construction and validation are streamed separately.
- `_native._canonical_zip_info`, `_native._feature_records`, `ZipFile.open` and `shutil.copyfileobj(length=1_048_576)` already underlie byte-compatible streaming of native and express TF members. The change can reuse the same known approach without new dependencies.
- Existing express reproducibility tests independently verify deterministic names, timestamps, permissions, content and release manifest SHA. The new test must compare against actual historical `writestr` output, not just decompressed equivalence.

## Chosen implementation

1. Build `app_files = _enumerate_app_files(app_directory)`; use `members` values of one of three types: `bytes` for generated small checkout markers, `Path` for tracked app files, and `(native_tf_name, uncompressed_bytes)` tuples for native TF ZIP members.
2. For a `Path` entry: `info = _native._canonical_zip_info(name)`; `info.file_size = entry.stat().st_size` to preserve old `writestr` ZIP header/Zip64 selection; `with entry.open('rb'), zf.open(info, 'w')` transfer with `shutil.copyfileobj(..., length=1_048_576)`.
3. Keep exact member sorting, marker bytes, TF native member transfer and downstream source/express SHA manifest binding. Do not modify public data schemas or converter.
4. Failure in source `open`/`copyfileobj` must propagate into existing `stage_distribution_assets` outer `except BaseException` cleanup; no new partially published generation.

## RED → GREEN → real data → independent review gates

1. RED-only tests create a >1 MiB tracked asset and a canonical historic express archive using byte `zf.writestr`; patch `Path.read_bytes` and `_collect_app_payloads` to fail during the proposed new builder; assert SHA and exact ZIP **bytes**, member order, marker contents, ZIP metadata and TF CRC. Probe bounded 1 MiB app read calls specifically, not merely existing TF-member reads.
2. Inject copy failure during an app `ZipFile.open` stream within full `stage_distribution_assets` with valid TF feature/report fixture and verify stage cleanup, original files unchanged, no destination.
3. Implement narrow constructor change and pass full unit/TF + pinned OCP conversion and semantic audit, native/express reproducible archive build/manifest identity checks, fresh offline stock Text-Fabric load, advanced app and 1 Enoch comparison.
4. Publish logically independent skeptical review of final code/actual ZIP bytes and exact-head CI; merge only with no blockers.

## Limits

- The constructor still stores one small checkout-marker bytes object per root and metadata for all members. Streamed tracked app files avoid feature-sized buffers but do not establish a global peak RSS measurement.
- Uncoordinated file changes between preflight, stat and read are outside transactional snapshots; downstream manifest parity must fail closed.
- `ZipFile` compression retains internal zlib buffers, and issue #190's validator still has no total decompressed-byte/time budget. This is strictly a per-app-input buffering change.
