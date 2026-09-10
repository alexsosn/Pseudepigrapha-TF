# Issue #104 — frozen release plan

Status: **re-frozen after #125; publication not yet authorized until the new merged-main candidate is green and independently reviewed**.

## Release identity

- re-freeze base after #125: `8a0a2496108f11b2cd85b14706272f1eb30163b3`;
- package/converter/runtime/materializer version: `0.2.0`;
- GitHub release tag: `v0.2.0`;
- TF data/app version: `0.2`;
- canonical native TF asset: `tf-0.2.zip`;
- stock Text-Fabric express asset: `complete.zip`;
- audit/integrity assets: `conversion-report.json`, `dataset-manifest.json`;
- exact OCP source commit: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.

The final release commit is **not** the re-freeze base. It will be the exact green merged commit of this release-plan update and must be recorded/reviewed before tagging.

## Final distribution contract

The `v0.2.0` GitHub release must contain exactly four files:

1. `tf-0.2.zip` — deterministic top-level `.tf` feature archive and native integrity source;
2. `complete.zip` — deterministic Text-Fabric 13.1 express transport with exact tracked `app/**`, exact native TF feature bytes under `tf/0.2/`, and release/commit checkout markers;
3. `conversion-report.json`;
4. `dataset-manifest.json`, whose asset records bind the other three release files including `complete.zip`.

Canonical express validation must bind `app/**` to an independently supplied exact release checkout and embedded `.tf` bytes to the native archive. Candidate, downloaded draft, and downloaded public generations must all be revalidated against the exact checked-out app.

## Completed TDD/implementation gates

The earlier #104 release-prep work established version identity and the manual fail-closed publisher. #124/#125 subsequently added the missing stock Text-Fabric express transport through research → RED → GREEN → full pinned-corpus test → independent adversarial review. Review-discovered app-substitution/fail-open validation holes received explicit regressions before the final green implementation.

Permanent tests now require:

- owned package/runtime/materializer version `0.2.0` and TF data version `0.2`;
- canonical four-asset staging;
- manifest-bound `complete.zip`;
- exact app-directory evidence for express manifest construction and validation;
- exact native/express feature byte equivalence;
- stock Text-Fabric loading from an extracted `complete.zip` with network blocked;
- a manual publisher that verifies and publishes exactly the four canonical assets.

No further production feature change is part of #104 unless the release gates expose a concrete defect. Any such defect requires a new RED regression and fix-forward release planning if a tag/release has already been created.

## Permanent pre-tag gates

The exact merged release-candidate commit must pass:

1. full unit/Text-Fabric suite;
2. wheel build and install in a fresh venv;
3. exact pinned OCP conversion + semantic parity;
4. full app/apparatus/translations/public-metadata/classification checks;
5. canonical `tf-0.2.zip` + `complete.zip` + report + manifest staging and validation;
6. stock Text-Fabric cache loading from `complete.zip` without network;
7. release workflow contract tests;
8. logically independent adversarial review of the exact merged candidate, including current tag/release absence and publication ordering.

## Tag / publication gate

Only after those gates:

- create `v0.2.0` once at the exact reviewed merged-main SHA;
- never force or move that tag;
- dispatch `.github/workflows/publish-corpus-release.yml` from that exact revision with `release_tag=v0.2.0` and `release_commit=<exact SHA>`;
- candidate builder must verify tag→commit equality before asset generation;
- publisher must fail if a `v0.2.0` GitHub release already exists;
- publisher creates one draft generation containing exactly `tf-0.2.zip`, `complete.zip`, `conversion-report.json`, and `dataset-manifest.json`;
- downloaded draft bytes must revalidate before promotion;
- public bytes must revalidate after promotion.

## Post-publication gates

Use a clean HOME/cache and stock Text-Fabric to acquire both app and data explicitly from `v0.2.0`. Verify:

- the real GitHub express-download path succeeds;
- app loads and corpus has the expected nonzero slot count;
- loaded generic metadata reports converter `0.2.0`, TF version `0.2`, exact OCP commit, verified source/license status and CC BY 4.0;
- the public four-file asset set is exact and validates as one release unit against the checked-out app;
- the same cache reloads with app/data `local` after network access is disabled.

A failed post-publication gate blocks #104 completion. Do not move the tag or mutate the public generation to hide the failure; create a corrective issue and fix forward under a new release identity.

## Agora gate

After Pseudepigrapha-TF live verification succeeds:

1. update `alexsosn/Agora` registry entry `pseudepigrapha-tf` from version `0.1.0` / commit `315439284e765c1d7ea89ffdefdd10f403aa1293` to version `0.2.0` / the exact `v0.2.0` release commit;
2. preserve materializer IDs, repository, manifest path, stable GitHub-release tracking, and the exact OCP source pin semantics;
3. run Agora's registry/materializer tests;
4. execute its Pseudepigrapha reference materialization if available and compare output identity to the canonical feature/report contract;
5. perform a logically independent adversarial review of the Agora PR before merge.
