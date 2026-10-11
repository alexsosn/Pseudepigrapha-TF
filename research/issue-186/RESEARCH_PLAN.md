# Issue #186 — Native release ZIP construction without full-feature `bytes` buffers

Status: researched/frozen plan committed before RED-only tests or production edits.

## Code-path evidence

- `_distribution_native.stage_distribution_assets()` gets canonical source features and prevalidates report's serialized identity, then writes canonical native `tf-<version>.zip` members via `ZipFile.writestr(_canonical_zip_info(feature.name), feature.read_bytes())`. This makes one full uncompressed feature-sized allocation before compression.
- #184 streams *hash validation*, not ZIP construction. The source/data graph and manifest constraints remain unchanged.
- Existing `tests/test_distribution_reproducibility.py` asserts deterministic archive bytes across changed filesystem timestamps and modes, sorted top-level names, 1980-01-01 timestamps, Unix regular mode, deflate compression and no extra/comment. We must preserve those canonical semantics and, preferably, exact pre-change ZIP **bytes**, not only content parity.
- A research probe on Python's `zipfile` using `ZipInfo.file_size=len(payload)` and incremental `with ZipFile.open(info,'w')` in <=1 MiB chunks produced exact byte equality to the `writestr` baseline for a 1.2 MiB payload. This is a candidate, not proof for real feature sets.

## Selected minimal architecture

1. Extract private `_write_native_feature_archive(archive: Path, features: list[Path]) -> None` to replace the current inline writer. Keep existing caller-supplied, prevalidated sorted order; do not silently sort differently.
2. For each source feature make a fresh `_canonical_zip_info(feature.name)` with fixed metadata; assign `info.file_size = feature.stat().st_size` to match the old `writestr` member header semantics. Open with `ZipFile.open(info, mode='w')` under one `ZipFile(archive, 'w', compression=ZIP_DEFLATED)` and use `shutil.copyfileobj(source_stream, member_stream, length=1_048_576)`.
3. Let `ZipFile` count actual source bytes/CRC and finalize canonical ZIP headers; stage's existing try/except BaseException removes partial generation on failure. Do not copy a whole feature into memory, and do not introduce a second corpus pass beyond stream-to-archive.
4. The reader remains `_feature_records` from #184, whose CRC validation streams decompressed data; bytes and manifest binding remain validated by the same release pipeline.

## Frozen RED → GREEN → CI → skeptical review

1. Test-only RED commit calls new helper with >1 MiB and mixed-size files and asserts byte-for-byte parity with the historical `writestr(_canonical_zip_info, path.read_bytes())` archive. Use monkeypatch to forbid full `Path.read_bytes()` within helper; include source mode/mtime independence and ZIP member metadata checks.
2. Fault-inject read failure on second `.tf` feature in full `stage_distribution_assets` and assert destination never exists, temporary release stage is cleaned up, existing source feature/report bytes untouched. Make test failure target the new bounded read boundary, not unrelated fixture errors.
3. Implement a single helper and tiny stage call-site replacement; run unit/TF tests and pinned complete corpus workflow with archive/report/manifest byte identities. If actual archive bytes change, treat it as potential compatibility/reproducibility break requiring investigation, not an acceptable unnoticed change.
4. Independent adversarial review uses actual production patch, before/after tests, exact final CI logs, and the real pinned OCP/TF archives; post directly to PR before marking ready/merge.

## Limitations

- Larger changes such as express ZIP staging, express validation dictionaries, and serialized otype header reads remain eager and must not be credited to this fix.
- A filesystem source mutation between pre-validation/stat/read remains caught by the subsequent manifest validation; this PR does not offer atomic snapshots against concurrent writes or data races.
- No measured whole-process memory reduction can be claimed without matched isolated-process observations.
