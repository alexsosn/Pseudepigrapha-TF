# Issue #194: bounded otype metadata extraction without integrity regression

Status: frozen research before RED-only tests and runtime edits.

## Source evidence

- `_distribution_native._serialized_otype_metadata` currently obtains `payload = ZipFile.read('otype.tf')`, then `payload.decode('utf-8').splitlines()`, but only reads lines before first blank separator to extract identity keys.
- The earlier `_feature_records()` pass in `build_distribution_manifest` has already streamed full ZIP member contents for SHA/CRC parity, but the private metadata reader independently expects whole-payload UTF-8 validation and CRC. Stopping early after `@metadata` would silently weaken both contracts.
- Existing `test_distribution_serialized_identity.py` checks missing/version/provenance, duplicate identity, invalid header and blank separator; pinned upstream conversion/report and fresh offline TF archive are authoritative.

## Frozen architecture

1. Use `ZipFile.open('otype.tf')` with `io.TextIOWrapper(encoding='utf-8', newline=None)`; `read(65536)` in a loop through **entire** member so Python fully validates UTF-8 and ZipExtFile runs CRC validation.
2. Accumulate only *metadata header* lines through the first empty line, respecting Python `str.splitlines()` newline characters (including CRLF/CR/LF and Unicode line separator). Discard subsequent decoded text immediately. Cap an individual metadata line at 64 Ki characters, failing closed with an explicit error rather than allowing attacker-controlled unbounded header allocation.
3. Preserve existing `@node` first-line requirement, duplicate identity key rejection, first-generic-value semantics and all report/manifest formats; do not change compression, TF text, source mapping, ZIP schema or report identity.
4. Catch `KeyError` for absent `otype.tf`; `OSError`, `BadZipFile`, `RuntimeError`, `EOFError` as `DistributionContractError`; `UnicodeDecodeError` remains the separate existing message.

## RED → GREEN → real-data → independent review

- RED-only tests: >1 MiB serialized otype member with valid header and UTF-8 body, patch `ZipFile.read` to raise; assert exact metadata mapping and no eager whole-member API. Add oversized header line fault-injection that must fail closed rather than materialize >64Ki chars.
- Positive/fail-closed controls: CRC corruption *after* header and invalid UTF-8 *after* header must still fail; duplicate identity metadata and missing blank separator remain rejected; CRLF and non-ASCII metadata values parse identically to old `str.splitlines()`.
- Implement then run full `pytest` and pinned upstream OCP conversion/audit, canonical manifest/complete.zip, offline native TF reload and real 1En comparison. Do not assert unmeasured memory or latency speedup.
- Perform genuinely independent adversarial review against old/new source and exact final head CI evidence. Post directly to GitHub before merge.

## Explicit limitations

Bounded **temporary decoding** memory is not an end-to-end process-RSS benchmark. ZipFile decompression uses its own buffers. A pathological archive can still be arbitrarily large; this change does not establish total decompression time/byte quota. A 64Ki-char header-line cap is a fail-closed contract tightening for unsupported giant metadata, not a silently truncated header.
