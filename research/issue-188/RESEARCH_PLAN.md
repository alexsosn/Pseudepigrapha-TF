# Issue #188 — Stream express `complete.zip` feature construction and parity

Status: frozen before any tests or implementation, based on source review of `distribution.py` at main `6a8e9f30de37bbccd0859fbea8b69f5620e52604`.

## Actual code and source dataset

- `_build_express_archive` currently calls `_native_feature_payloads`, which reads **every decompressed `*.tf` member** into a dict and merges it with app bytes and markers. It then writes all members using `ZipFile.writestr`.
- `_validate_express_archive` independently calls `_native_feature_payloads` again and `zf.read(info)` on every express member, accumulates a second decompressed feature dict, then compares `data_payloads[name]` against `feature_payloads[name]` bytewise. Both hold source feature buffers beyond each member's lifecycle.
- The native ZIP member hash path (#184) and native archive construction (#186) are already incremental. The pinned OCP dataset has 38 nonempty XML documents, 922,922 word slots, 1,193,651 nodes and 6,479,988 slot edges. Express release validation is a substantial remaining whole-corpus memory hotspot.
- Existing `test_distribution_text_fabric_express.py` validates sorted/normalized member names and metadata, identical marker app and TF payloads, corrupted/missing/extra/symlinked ZIP entries, exact app checkout identity, wrong marker, and bit-identical archives on repeated staging. We must preserve all those semantics.

## Planned architecture (frozen)

1. Reuse `_native._feature_records(native_archive)` for a verified **small dictionary of `{name,bytes,sha256}` records**, not payload contents. Open native `ZipFile` for source member streams, express `ZipFile` for destination. Construct sorted list of member specs for two tiny checkout markers, validated app files and native TF record names. App bytes may remain in memory as before; corpora must not.
2. For `.tf` entries, set `ZipInfo.file_size` from verified actual decompressed byte length and stream from `native_zf.open(name)` to `express_zf.open(info,'w')` using `shutil.copyfileobj(..., length=1_048_576)`. This preserves historical `writestr` seekable header/ZIP64 decisions, canonical CRC, compression and member ordering. For markers/app bytes, keep existing `writestr` path.
3. In `_validate_express_archive`, preserve full archive manifest/metadata checks, sorted unique name enforcement, safe path and mode checks. For app entries and marker, keep small `zf.read` payloads. For each TF data member, verify against the native feature's exact **uncompressed bytes**, by chunk-by-chunk comparison of **both** `ZipExtFile` streams until simultaneous EOF; require CRC checks on fully read members. Retain name sets and no surprise members.
4. Stream comparison must reject any differing chunk or mismatched EOF, even when sizes match. It must not reduce comparison to CRC or SHA only, and it must not suppress errors for malformed native/express archive members. For an extra or missing name, preserve explicit error descriptions.
5. Keep public function signatures, `complete.zip` member layout, canonical flags and marker bytes, manifest structure and unrelated app binding semantics unchanged. `_native_feature_payloads` may remain as an unused private compatibility shim, but *neither* construction nor validation should call it.

## RED → implementation → independent review

1. RED-only tests: fixture containing >1 MiB TF `oslots.tf` with a well-formed minimal report and app. Build frozen golden old-style express `complete.zip` from literal member bytes. Forbid `_native_feature_payloads` and `ZipFile.read` for `.tf` members, then call actual `_build_express_archive` and `_validate_express_archive`. Assert exact ZIP bytes, metadata and lossless identity.
2. Additional fault injection: tamper express `.tf` bytes while preserving size and rehash manifest; validation must reject the exact byte mismatch, not just wrong CRC or manifest. Existing express security tests must remain green.
3. Implement narrowly in `distribution.py`, with one stream comparison helper; avoid refactoring native `_distribution_native.py` or TF converter semantics.
4. Full `pytest`/TF suite and pinned 38-source OCP conversion/parity, native/express canonical asset packaging, stock offline TF complete.zip load and real 1 Enoch comparison.
5. Separate adversarial review at tested immutable PR head, grounded in upstream corpus, actual bytes/CRC, false-negative/false-positive cases and CI logs. Post review before merge.

## Limits

- App payloads may be kept in memory; their size is small relative to corpora, and app identity validation remains unchanged.
- `ZipExtFile`/zlib internal buffers still exist. There is no maximum total decoded size/CPU quota for a hostile ZIP; streaming is not full zip-bomb mitigation.
- No numeric peak RSS improvement is claimed without running a matched end-to-end process comparison.
