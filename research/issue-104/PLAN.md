# Issue #104 — frozen release plan

Status: **frozen before implementation**.

## Release identity

- release-prep base: `ec0139670ffeeb80dabb3668bbed7af69049e8e8`;
- package/converter/runtime/materializer version: `0.2.0`;
- GitHub release tag: `v0.2.0`;
- TF data/app version: `0.2`;
- canonical TF asset: `tf-0.2.zip`;
- companion assets: `conversion-report.json`, `dataset-manifest.json`;
- exact OCP source commit: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.

The final release commit is **not** this plan commit. It will be the exact green merged commit of the release-prep PR and will be recorded before tagging.

## TDD sequence

### RED 1 — version identity

Add a permanent release-identity test that requires all owned version-bearing surfaces to agree with this frozen plan:

- `pyproject.toml` project version = `0.2.0`;
- `src/pseudepigrapha_tf/__init__.py` runtime version = `0.2.0`;
- `agora.materializer.json` plugin version = `0.2.0`;
- `app/config.yaml` `provenanceSpec.version` = `0.2`;
- canonical archive identity derives as `tf-0.2.zip`;
- release tag implied by package version is `v0.2.0`.

Current main must fail this test before version edits.

### RED 2 — permanent publication workflow

Add contract tests that require a release publisher which:

- is explicit/manual (`workflow_dispatch`) rather than an automatic main-push publisher;
- accepts/fixes the exact release tag and commit identity;
- delegates corpus construction to `build-corpus-release-assets.yml`;
- downloads the named validated candidate artifact;
- refuses an existing release and uses tag verification/no-clobber semantics;
- publishes exactly the three canonical assets;
- runs a fresh-cache explicit-tag Text-Fabric load after publication;
- verifies release/converter/data/upstream/license identity from manifest and loaded TF metadata;
- runs a second `checkout="local"` load with network disabled/unavailable;
- does not contain tag-force/move or asset-clobber operations.

Current main must fail because no publisher exists.

## GREEN implementation

1. bump the three converter/materializer SemVer surfaces to `0.2.0`;
2. bump app/TF data version to `0.2`;
3. remove hard-coded CI `0.1.0` / `0.1` candidate assumptions where they represent current package/data identity, deriving them from owned metadata when practical;
4. add the fail-closed permanent publication workflow;
5. update release-facing docs/examples that would otherwise instruct users to produce/load `tf/0.1` for the current release;
6. do not change the OCP source pin or historical `v0.1.0` documentation.

## Permanent pre-tag test gates

The exact release-prep head must pass:

1. full unit/Text-Fabric suite;
2. wheel build and install in a fresh venv;
3. exact pinned OCP conversion + semantic parity;
4. full app/apparatus/translations/public-metadata/classification checks;
5. canonical `tf-0.2.zip` staging, report/manifest binding, extraction and stock-TF reload;
6. release workflow contract tests;
7. logically independent adversarial review of the exact green head.

After merge, the exact merged release-candidate commit must pass the same permanent main CI before tagging.

## Tag / publication gate

Only after the exact merged release candidate is green and independently reviewed:

- create `v0.2.0` once at that exact SHA;
- never force/move the tag;
- run the publisher from the tagged workflow revision with the frozen tag/SHA;
- candidate builder must verify tag→commit equality before asset generation;
- publisher must fail if a `v0.2.0` GitHub release already exists;
- release contains exactly `tf-0.2.zip`, `conversion-report.json`, `dataset-manifest.json`.

## Post-publication gates

Use a clean HOME/cache and stock Text-Fabric to acquire both app and data explicitly from `v0.2.0`. Verify:

- app loads;
- nonzero corpus slots and expected corpus identity;
- loaded generic metadata says converter `0.2.0`, TF version `0.2`, exact OCP commit, verified source/license status and CC-BY-4.0;
- downloaded `tf-0.2.zip` / report / manifest validate as one release unit;
- the cached corpus reloads with app/data `local` and no network fallback.

A failed post-publication gate blocks #104 completion and requires fix-forward under a new release identity.

## Agora gate

After Pseudepigrapha-TF live verification succeeds:

1. update `alexsosn/Agora` registry entry `pseudepigrapha-tf` to version `0.2.0` and the exact `v0.2.0` release commit;
2. preserve materializer IDs, repository, manifest and stable GitHub-release tracking semantics;
3. run Agora's registry/materializer tests;
4. execute its Pseudepigrapha reference materialization if available and compare output identity to the canonical report/feature-set contract;
5. independently review the Agora PR before merge.
