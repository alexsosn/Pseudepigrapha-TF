# Issue #97 — implementation plan

Research gate closed on 2026-09-08. The exact supported corpus is 169,467,455 bytes across 96 `.tf` features and compresses to a native Text-Fabric `tf-0.1.zip` of 9,801,766 bytes in the research probe. Native `tf-zip` deliberately excludes `conversion-report.json`, so provenance/report association must be a separate cryptographically verified release contract.

## Chosen publication contract

One GitHub release is the authoritative publication event. For release `vX.Y.Z` and TF data version `D`, it publishes exactly these required corpus assets:

1. `tf-D.zip` — the unmodified native Text-Fabric express archive used by `tf.app.use()` / Text-Fabric cache loading.
2. `conversion-report.json` — the exact semantic/parity report produced by the same materialization that was archived.
3. `dataset-manifest.json` — a deterministic JSON manifest binding the release identity, converter identity, TF data identity, exact OCP snapshot, report, archive and provenance statuses.

The three files are one logical release unit, but the native TF archive is not modified or wrapped, so stock Text-Fabric loading remains compatible.

## Manifest schema v1

The manifest is UTF-8 JSON with stable key ordering when serialized and contains at least:

- `schema_version`: `1`;
- `release.tag`: e.g. `v0.1.0`;
- `release.commit`: immutable repository commit SHA;
- `converter.version`: e.g. `0.1.0`;
- `text_fabric.data_version`: e.g. `0.1`;
- `upstream.repository`;
- `upstream.commit`;
- `assets.tf.name`, `sha256`, `bytes`;
- `assets.report.name`, `sha256`, `bytes`;
- `audit.status` from the conversion report;
- `provenance.source_identity_status`;
- `provenance.content_license_status`;
- `provenance.content_license`;
- `provenance.converter_software_license`;
- `provenance.upstream_software_license`.

The manifest builder must derive report/upstream/provenance fields from `conversion-report.json`, not accept duplicate caller-supplied values that could silently disagree. Release tag/commit, converter version and TF data version are publication inputs and are cross-checked against package/app/report metadata where those identities already exist.

## Validation semantics

A validator is fail-closed and must reject or clearly diagnose:

- missing required asset;
- filename mismatch (`tf-<data-version>.zip` is canonical);
- TF archive byte-size or SHA-256 mismatch;
- report byte-size or SHA-256 mismatch;
- malformed/unsupported manifest schema;
- non-`ok` conversion report;
- report source-identity or content-license status not `verified`;
- upstream repository/commit mismatch between manifest and report;
- converter version mismatch where report/package identity exposes it;
- TF data version mismatch with the publication contract;
- release tag/commit mismatch when an expected immutable release identity is supplied.

Validation must not depend on ZIP byte reproducibility across rebuilds. The checksum identifies the one canonical published archive. Agora rebuilds may prove deterministic semantic/materialization equivalence without claiming the independently rebuilt ZIP container has the same bytes.

## Researcher loading paths

### Normal online path

Stock Text-Fabric remains the data transport:

```python
from tf.app import use
A = use("alexsosn/Pseudepigrapha-TF", checkout="vX.Y.Z")
```

The release asset name and app `provenanceSpec.version` must make this resolve `tf-D.zip` without pretending generated `tf/D` files are committed in Git.

### Offline path

After Text-Fabric has populated its cache, the same app/data must load with `checkout="local"` and no network fallback. A release integration test will populate a fresh temporary cache from the exact candidate asset, then prove the local-only load succeeds after the network-facing acquisition phase is removed from the test environment.

### Reproducibility / Agora path

Agora remains the deterministic materializer from exact converter release + exact OCP commit. It must resolve the same release identity and verify the resulting conversion report/provenance against the canonical manifest contract. It must not invent an independent dataset version. Byte equality of the ZIP container is not required unless archive determinism is separately established; semantic TF feature content and report identity are the required rebuild equivalence.

## Production components

1. Add `pseudepigrapha_tf.distribution` with small pure functions for SHA-256/size calculation, manifest building and fail-closed validation.
2. Keep manifest generation independent of GitHub APIs so it can be unit-tested offline and reused by release automation/Agora.
3. Add a release-artifact build command/helper that accepts an already validated materialized TF directory and creates the native `tf-D.zip`, copies the exact conversion report, builds the manifest, then validates all three before publication.
4. Add release automation only after the pure contract is green. It must materialize from the exact supported OCP commit and publish assets from the same job/output generation that passed semantic parity.
5. Do not publish a partially validated release set. Upload/publish ordering must prevent the manifest from advertising assets that failed validation; release automation should stage all files, validate locally, then attach them to one release identity.
6. Keep the existing direct converter/materializer path fully supported.

## TDD sequence

### RED 1 — pure manifest contract

Add tests before `pseudepigrapha_tf.distribution` exists. They require:

- deterministic schema-v1 manifest generation from a tiny TF archive + representative conversion report;
- exact asset names, SHA-256 and sizes;
- report-derived upstream/provenance fields;
- validation success for the intact set;
- rejection of one-byte TF archive mutation;
- rejection of report mutation;
- rejection of wrong upstream/release/data-version identity;
- rejection of non-verified provenance and non-`ok` report status.

### GREEN 1

Implement the smallest offline distribution module satisfying those tests. No GitHub/network behavior yet.

### RED 2 — build/staging contract

Require a staging helper to produce exactly `tf-D.zip`, `conversion-report.json`, and `dataset-manifest.json` from an already materialized corpus, and reject missing/mismatched reports. Assert the TF archive contains feature files only and the separate report remains manifest-bound.

### GREEN 2

Implement native TF archive staging using the Text-Fabric-supported archive convention while keeping report/manifest separate.

### RED 3 — release workflow contract

Static/integration tests require the release workflow to:

- use the exact supported OCP commit;
- build/install the release wheel rather than editable source for publication materialization;
- run existing semantic/parity/reload gates before asset publication;
- stage and validate all three assets;
- publish the native `tf-D.zip` naming expected by Text-Fabric;
- never claim generated data is stored under Git `tf/D`;
- never publish from mutable upstream HEAD.

### GREEN 3

Add release automation and researcher-facing loading documentation.

### RED/GREEN 4 — actual TF loading

Against a release candidate/fresh cache, prove:

- stock Text-Fabric obtains the canonical express asset under the intended app/release contract;
- loaded TF metadata identifies the expected converter/upstream provenance;
- `checkout="local"` succeeds from the already populated cache with no network acquisition;
- a deliberately mismatched manifest/report candidate is rejected before publication/installation.

This network-facing proof belongs in release/integration validation, not the normal unit suite.

## Compatibility and version policy

- Git release/tag `vX.Y.Z` identifies the publication event and converter/app release.
- package version is `X.Y.Z` and must match the release tag for a published corpus event.
- TF data version is an explicit independent schema/data contract (`0.1` today); it changes only when the TF dataset contract changes, not on every converter patch.
- exact OCP commit is immutable and recorded separately.
- the canonical archive checksum identifies the published artifact, not the abstract corpus semantics.

## Acceptance gates before finalization

- all pure manifest/staging tests green;
- full existing unit/Text-Fabric suite green;
- fresh release-wheel install green;
- exact pinned OCP conversion and semantic parity green;
- real TF reload/public metadata/classification/apparatus/generated-translation gates green;
- release-candidate assets validate as one manifest-bound set;
- actual stock Text-Fabric loading proven from a fresh cache candidate and then local/offline mode;
- no generated corpus committed into Git as a side effect;
- temporary research measurement workflow removed;
- logically independent adversarial review of the exact green head and candidate artifacts before merge/publication.

## Adversarial review checklist

Challenge, rather than merely confirm:

- whether `tf-0.1.zip`, report and manifest can get out of sync;
- whether a release can become partially published;
- whether manifest fields duplicate mutable truths instead of being derived/cross-checked;
- whether a rebuild is incorrectly promised byte-identical despite ZIP metadata;
- whether Text-Fabric actually resolves the asset in a genuinely fresh cache;
- whether `checkout="local"` proves offline operation rather than silently reaching the network;
- whether app/release/package/TF/OCP versions can skew;
- whether Agora becomes a second source of corpus identity;
- whether license/source provenance survives packaging;
- whether any unstable OCP reader URL has been smuggled into the transport contract.
