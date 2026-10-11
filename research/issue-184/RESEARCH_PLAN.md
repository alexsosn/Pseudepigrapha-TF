# Issue #184 — Stream SHA-256 identities for native TF releases

Status: frozen research/implementation plan before RED tests and production edits.

## Source-grounded diagnosis

- `_distribution_native._file_record(path)` currently uses `path.read_bytes()` then hashes a full file-sized allocation. It is used for native TF archive/report assets and extracted feature identities.
- `_distribution_native._feature_records(archive)` enumerates ZIP metadata and uses `zf.read(info)` for each complete feature. This stores large decompressed TF files in RAM only to obtain length and SHA-256. It is invoked repeatedly by manifest construction and verification.
- `stage_distribution_assets()` uses `feature.read_bytes()` when building its ZIP; `_serialized_otype_metadata()` reads the whole `otype.tf`; express packaging and parity in `distribution.py` also hold payload bytes. All are **out of scope** to avoid conflating multiple memory and CRC contracts; this change reduces only two clearly identified hash-read buffers.
- Pinned release input is 38 OCP XML documents yielding 922,922 word slots, 1,193,651 graph nodes and ~6.48M slot edges. No matched per-process RSS baseline for native validation has been measured. Do not invent performance ratios.

## Chosen design and counterexamples

1. Introduce a single private bounded read+hash function that consumes binary streams with maximum 1 MiB per `read`, updates `hashlib.sha256` incrementally and counts **actual bytes returned**. Return canonical `{name,bytes,sha256}` and never rely on ZIP header's untrusted `file_size` for identity.
2. In `_file_record`, open file in `rb` mode and stream chunks. Keep path-derived name and original error propagation semantics (`OSError` from path opening/reading).
3. In `_feature_records`, after unchanged checks for nonempty member set, duplicate names and top-level `*.tf`, use `with zf.open(info)` and consume to EOF. This preserves Python ZipExtFile's CRC verification; early closing without EOF is forbidden. Catch the prior `BadZipFile`, `OSError`, `RuntimeError` and additionally `EOFError` as `DistributionContractError`. Keep canonical sorted output and no change to release schema.
4. Avoid trusting `ZipInfo.file_size`/`compress_size` as a replacement for digesting actual data; avoid silently accepting a partial read. No ZIP bomb / DOS envelope added here, since arbitrarily sized legitimate corpora must remain supported; a separately researched bounded-validation policy could address untrusted inputs.

## Frozen RED → GREEN → pinned acceptance → independent review

1. RED-only tests: create a >1 MiB local binary file, patch `Path.read_bytes` to error if invoked, and demand exact SHA/byte size from `_file_record`; build ZIP with >1 MiB `.tf` members, patch `ZipFile.read` to error, and demand canonical sorted records and matching digests.
2. Positive tests verify CRC corruption is rejected rather than hidden by reading only a prefix; invalid nested/non-feature/duplicate entries retain fail-closed behavior already covered by existing distribution tests. Check stored and deflated entries.
3. Implement and run existing distribution/manifest hash fixtures and full unit/TF suite. Test one helper stream whose `read(n)` refuses unbounded reads to guarantee incremental consumption.
4. Complete pinned source conversion, independent semantic parity audit, canonical release staging, complete.zip extraction, fresh offline TF load and real comparison acceptance. No speedup claim without a matched actual benchmark.
5. Genuinely independent skeptical final-head PR review inspecting code paths, tests, ZIP CRC errors, data identity and exact CI results, posted directly to GitHub before merge.

## Risk limits

- ZIP archives under adversarial control can report large actual decompressed contents; streaming hashing keeps per-read memory bounded but does not establish a maximum total decompressed size/time. Treat this as a separate security-hardening research issue if the package begins accepting arbitrary remote ZIPs.
- The native/express packaging path still reads whole individual members for final ZIP construction. This PR improves native validation memory *only*, not overall pipeline peak memory.
