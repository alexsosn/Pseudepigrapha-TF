# Issue #100 — consolidate duplicate pinned full-corpus app CI

## Research gate

Base inspected: `59ca5021e3c174e16ece532b9fabc22e9e06985f`.

Two permanent workflows currently materialize the same full OCP corpus on every pull request:

- `.github/workflows/test.yml` → `pinned-upstream-integration`
- `.github/workflows/full-app-integration.yml` → `pinned-full-corpus-app`

### Exact overlap

Both workflows:

- run on `ubuntu-latest` with Python `3.12`;
- clone `OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha`;
- check out exact OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`;
- run `pseudepigrapha-tf convert` on `/tmp/ocp/static/docs`;
- materialize to `/tmp/pseudepigrapha-tf/0.1`;
- therefore pay the same network clone and full conversion cost twice.

The permanent `test.yml` job is the stronger environment boundary. It builds the project wheel, creates a fresh virtual environment, installs the wheel there, verifies the installed release contract, then performs the exact pinned conversion and all semantic/reload checks. The dedicated full-app workflow instead installs the checkout editable with dev dependencies before repeating the same clone/conversion.

### Unique semantic coverage in the duplicate workflow

`full-app-integration.yml` adds one unique assertion after materialization: it calls Text-Fabric `findApp()` with:

- the tracked local `app/` directory (`app:<absolute path>`);
- the already materialized local corpus location `/tmp/pseudepigrapha-tf/0.1`;
- `version="0.1"`;
- no remote data source;
- the advanced `TfApp` subclass expected by the tracked app.

It then asserts:

- advanced app startup succeeds;
- the API exists;
- the class is `TfApp`;
- `maxSlot == 922922` on the exact pinned corpus;
- `1En__Ethiopic / 1 / 1` resolves.

This assertion does not require a second corpus build. It can run as a named final step in `test.yml` after the existing pinned conversion/reload checks. Running under the fresh wheel environment is at least as strict as the current editable install: the local app files are read from the checkout, while package/runtime imports resolve through the built wheel.

### Failure isolation

The separate workflow gives a distinct workflow-level red status, but GitHub already isolates failures by named workflow step. App startup can remain a dedicated step at the end of `pinned-upstream-integration`, so a failure is still attributable without duplicating materialization.

Passing the corpus between separate jobs via an artifact would add archive/upload/download work and another environment boundary without adding semantic coverage. The simplest and strongest contract is therefore one full materialization job with the advanced-app assertion appended in-process.

## Plan gate

1. Add a deterministic repository-level CI contract test before workflow changes. It must fail on the current duplicate topology and require:
   - exactly one `pseudepigrapha-tf convert /tmp/ocp/static/docs` invocation across permanent PR workflows;
   - the surviving invocation to remain in `test.yml`'s `pinned-upstream-integration` job;
   - the tracked advanced-app assertion (`findApp`, local corpus location, `TfApp`, pinned max-slot and passage check) to remain present in that same job;
   - no second `full-app-integration.yml` materialization workflow.
2. Observe RED with production workflows unchanged.
3. Move the advanced-app startup step verbatim (except comments/name if useful) into `test.yml` after the full pinned corpus has already been generated and reloaded.
4. Remove `.github/workflows/full-app-integration.yml` entirely.
5. Run full CI on the exact head. The surviving pinned job must still cross all existing release-wheel, semantic parity, generated-translation, metadata, classification, license, reload, and app checks.
6. Perform a logically independent adversarial exact-head review focused on:
   - accidental loss or weakening of app startup coverage;
   - app running against a synthetic/small fixture rather than the exact full corpus;
   - contamination of the fresh-wheel boundary by editable installation;
   - hidden second full conversion in another workflow;
   - dependence on remote corpus loading;
   - brittle coupling that prevents future changes from being diagnosed.

## TDD expectations

The RED test should inspect workflow semantics, not timing. No wall-clock assertion is acceptable. The intended optimization is structural: one pinned full conversion per PR instead of two.

## Acceptance

- one full OCP clone/conversion path per PR;
- exact pinned OCP SHA remains unchanged;
- Python 3.12 and release-wheel fresh-environment coverage remain unchanged;
- advanced tracked `TfApp` loads the exact full local corpus in the surviving job;
- no remote-data publication/loading assumption is introduced;
- existing full test/pinned integration gates remain green;
- duplicate workflow removed only after RED is observed;
- exact green head receives independent adversarial review before merge.
