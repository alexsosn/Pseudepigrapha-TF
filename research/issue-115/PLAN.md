# Issue #115 — frozen implementation plan

Status: **frozen before RED/production implementation**.

Research base: `16a6a11920ff232e8101b9cb6a8382d52868a206`.

## Invariant

For identical canonical Text-Fabric feature bytes and identical release identity, `stage_distribution_assets()` must produce byte-for-byte identical:

1. `tf-<data-version>.zip`;
2. ZIP asset hash/size recorded in the manifest;
3. `dataset-manifest.json` bytes;

regardless of input feature mtimes or filesystem permission bits.

A feature-byte mutation must still change archive bytes and the manifest's archive hash.

## RED first

Add a dedicated reproducibility test module before any production edit.

### RED 1 — mtime/mode independence

Build two complete valid materialized fixture directories with identical `.tf` and report bytes. Set deliberately different mtimes and modes on corresponding `.tf` files. Stage each directory using the exact same release tag, release commit, converter version, and data version.

Require:

- ZIP bytes equal;
- parsed manifests equal;
- canonical manifest bytes equal;
- manifest `assets.tf.sha256` equal;
- ZIP member order remains the canonical sorted feature order.

Current `ZipFile.write()` implementation must fail on ZIP byte equality (and therefore manifest equality/hash equality).

### RED 2 — explicit normalized member metadata

For every member require:

- `date_time == (1980, 1, 1, 0, 0, 0)`;
- `create_system == 3`;
- `(external_attr >> 16) == 0o100644`;
- `compress_type == ZIP_DEFLATED`;
- `extra == b""`;
- `comment == b""`.

### Positive control

Starting from the same fixture, change one feature payload byte and regenerate a matching valid conversion report. Stage with the same publication identity into a different destination and require:

- ZIP bytes differ;
- manifest `assets.tf.sha256` differs;
- feature-set identity differs;
- both generations individually pass `validate_distribution()`.

### Existing behavior

Retain the existing staging tests for:

- exact 3-asset output;
- top-level `.tf` members only;
- sorted names;
- exact feature payload preservation;
- failed-report cleanup;
- no-mix existing destination;
- validation of the staged generation.

## Minimal GREEN implementation

In `distribution.py`:

1. import `ZipInfo`;
2. add one small helper that builds the fixed member metadata from a top-level feature name;
3. keep iterating the already-sorted `features` list;
4. replace `ZipFile.write(feature, arcname=feature.name)` with `ZipFile.writestr(fixed_zip_info(feature.name), feature.read_bytes())`;
5. keep `ZIP_DEFLATED` explicitly assigned to the member metadata;
6. do not change manifest or feature identity algorithms.

Fixed metadata:

```text
date_time    = 1980-01-01 00:00:00
create_system = 3 (Unix)
external_attr = 0o100644 << 16
extra         = b""
comment       = b""
compress_type = ZIP_DEFLATED
```

The helper must not inspect source stat metadata.

## Verification gates

After GREEN:

1. focused reproducibility + distribution tests;
2. full pytest / real Text-Fabric suite;
3. exact PR-head CI `unit-and-tf`;
4. exact PR-head `pinned-upstream-integration`, including wheel/fresh install, exact OCP conversion/parity, canonical staging/extraction/reload, public metadata and app load;
5. inspect the full-corpus candidate ZIP metadata to ensure normalized members appear in the real path;
6. logically independent adversarial review of the exact final green head.

## Adversarial review questions

The final reviewer must assume the implementation is wrong and challenge:

- Does any `stat()`/mtime/permission-derived metadata still enter the archive?
- Are all member names and order deterministic?
- Can host OS alter `create_system` or permission bits?
- Are extras/comments/time fields actually fixed after serialization?
- Did the change accidentally switch away from deflate or alter feature bytes?
- Does a genuine feature-byte mutation still propagate through feature identity, ZIP bytes, and manifest hash?
- Does `validate_distribution()` still bind the exact report/archive generation?
- Does stock Text-Fabric still load the extracted full-corpus ZIP?
- Did staging atomicity or destination refusal regress?

Any blocker requires a new RED regression, another GREEN/full-gate cycle, and a fresh exact-head adversarial review before merge.