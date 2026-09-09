# Issue #124 — Text-Fabric `complete.zip` release transport

## Exact upstream contract

Research is grounded in Text-Fabric **v13.1.0**, annotated tag object `53cfa84651556cd3cf35ad0cc325c8fe46ca1485`, commit `dd227ce62b5536de53a0e20eac98c0459da8fd3d` (the version constrained by this project).

At that revision:

- `tf.core.files.APP_EXPRESS_ZIP` is `complete.zip`.
- `tf.advanced.repo` derives the express release asset URL by appending `/complete.zip` to the GitHub release download URL.
- `tf.advanced.zipdata.zipAll()` states that `complete.zip` is unpackable directly into the Text-Fabric cache and gathers both the app and main data.
- `zipAll()` strips the backend clone root before writing members. For this repository the cache-relative roots are therefore:
  - `alexsosn/Pseudepigrapha-TF/app/**`
  - `alexsosn/Pseudepigrapha-TF/tf/<data-version>/**`
- `zipAll()` adds `__checkout__.txt` to each gathered root before collecting files so Text-Fabric can recognize release/commit provenance after extraction.

The project-native `tf-<data-version>.zip` has a deliberately different contract: it contains sorted top-level `.tf` features only. It is the integrity/audit archive and must not be renamed or replaced by `complete.zip`.

## Current release gap

Candidate `b7875fd2bbaf4ddc996ea5f7e0ee4f5b3b3a1059` stages only:

1. `tf-0.2.zip`
2. `conversion-report.json`
3. `dataset-manifest.json`

`publish-corpus-release.yml` explicitly rejects any fourth file, while its post-publication gate subsequently calls stock `tf.app.use()` from an empty cache. Thus the workflow can make a release public before discovering the missing stock-TF express transport.

No `v0.2.0` tag/release exists; #104 remains blocked before any immutable publication.

## Frozen design

### Native archive remains authoritative for feature bytes

`tf-<data-version>.zip` remains exactly the current deterministic top-level feature archive. Its per-feature and feature-set identities remain unchanged.

### Express transport is a separate deterministic asset

Add `complete.zip` with only:

- regular files recursively under the tracked `app/` directory, rooted at `alexsosn/Pseudepigrapha-TF/app/`;
- the exact `.tf` feature bytes already used to construct `tf-<data-version>.zip`, rooted at `alexsosn/Pseudepigrapha-TF/tf/<data-version>/`;
- `__checkout__.txt` at the app root and data-version root.

No symlinks, directories-as-members, path traversal, absolute paths, generated Python caches, or unrelated repository files are allowed.

For our deterministic builder the checkout marker is normalized to two newline-terminated lines:

```
<release-tag>
<40-char release commit>
```

The exact marker bytes are project-owned rather than copied from `git describe`; validation binds them to the explicit release inputs. Text-Fabric consumes the marker as cache provenance and the release tag is sufficient to select the release; retaining the exact raw commit gives an additional immutable identity check.

### Manifest closure

Schema stays version 1 because this is an additive asset record within the existing generic `assets` mapping, not a reinterpretation of existing fields.

When express transport is staged, add:

```json
"assets": {
  "tf": {...},
  "report": {...},
  "express": {"name": "complete.zip", "bytes": ..., "sha256": ...}
}
```

`validate_distribution(..., express_archive=...)` re-derives all three asset records, verifies express layout/markers, and proves every embedded `.tf` payload equals the corresponding native feature record. Thus `complete.zip` cannot drift from the native archive while retaining a matching manifest hash.

Generic unit tests may still construct native-only manifests when no express archive is supplied; **canonical release staging always supplies an app directory and emits express transport**. The release workflows must require exactly four files.

### Staging API

Extend `stage_distribution_assets()` with explicit `app_directory=None` and repository identity defaults. If `app_directory` is supplied, generate and validate `complete.zip`; return it as `assets["express"]`. Release workflows must pass the exact checked-out `app` directory. Existing generic callers that do not model release transport remain source-compatible.

## RED gate

Before production code changes:

- add a focused staging test that supplies a synthetic app and requires `complete.zip`, manifest `assets.express`, exact cache-relative member roots and markers;
- require embedded TF bytes to equal the native archive/source bytes;
- add deterministic repeated-build assertion;
- add validation tests for tampered express bytes/marker/path/member set;
- add a workflow-contract test requiring release workflows to mention and publish `complete.zip`.

Current code must fail these assertions because it has neither the API nor the asset.

## GREEN/full gate

After the minimal implementation:

1. focused express/distribution tests;
2. full pytest/real TF suite;
3. exact pinned OCP full conversion and semantic parity;
4. canonical release staging with `app/`, four-asset validation, native extract/reload;
5. advanced app and 1 Enoch comparison gates;
6. exact-head adversarial review against Text-Fabric v13.1.0 source.

No tag/release action is permitted in #124. After merge, #104 must re-freeze a new exact `main` candidate and repeat pre-tag review.
