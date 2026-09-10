# Issue #104 — release research

## Post-#125 re-freeze — 2026-09-10

The release research is re-frozen after merge commit `8a0a2496108f11b2cd85b14706272f1eb30163b3` (`#125`). This supersedes the earlier three-asset assumptions below for the actual `v0.2.0` publication.

Current owned identity at this re-freeze point:

- package version in `pyproject.toml`: `0.2.0`;
- runtime release identity: `0.2.0`;
- `agora.materializer.json` plugin version: `0.2.0`;
- tracked Text-Fabric app/data version: `0.2`;
- supported OCP source remains pinned to `c939dcbacad78c5d18d2c4282cad23c47e19ac07`;
- the public release namespace still contains only historical `v0.1.0`; `v0.2.0` has not been published.

Text-Fabric 13.1.0's express-download contract requires a GitHub release asset named `complete.zip` containing the app plus main data under cache-relative `org/repo/...` roots. #125 implements and validates that contract while retaining `tf-0.2.zip` as the canonical native feature archive.

The canonical `v0.2.0` release generation is therefore **four files**:

1. `tf-0.2.zip` — native top-level Text-Fabric feature archive;
2. `complete.zip` — stock Text-Fabric express transport containing the exact tracked `app/**` and byte-identical native `.tf` payloads under `tf/0.2/`;
3. `conversion-report.json` — semantic/provenance/source-license audit;
4. `dataset-manifest.json` — release identity and exact asset/feature integrity binding, including `complete.zip`.

`complete.zip` is additionally bound to the exact checked-out `app/` directory in the canonical manifest builder and validator. A coordinated app substitution plus recomputed outer ZIP hash is therefore rejected unless the substituted app also equals the trusted release checkout.

The permanent publisher now exists at `.github/workflows/publish-corpus-release.yml`. It is manual-only, delegates candidate construction to `.github/workflows/build-corpus-release-assets.yml`, verifies tag→commit equality, refuses a pre-existing release, validates all four candidate/draft/public assets, performs a fresh tagged stock-Text-Fabric load, and then proves a network-blocked `local` reload from cache.

The exact final release commit is **not** `8a0a2496…`: it will be the merge commit of the release re-freeze PR containing the updated plan/release notes. That merged commit must pass the permanent main CI and an independent pre-tag review before `v0.2.0` is created.

Agora still pins Pseudepigrapha-TF `0.1.0` at commit `315439284e765c1d7ea89ffdefdd10f403aa1293`. Its registry update belongs only after the public `v0.2.0` release and live Text-Fabric verification succeed; version and immutable ref must move together to the exact release commit.

## Original research starting point

The original #104 research was frozen against merged `main` commit `ec0139670ffeeb80dabb3668bbed7af69049e8e8`. At that point the authoritative CI run was `34272672126`, the canonical distribution had only the native `tf-0.2.zip`/report/manifest generation, and the permanent publisher/express transport work had not yet been completed.

The version decision made there remains valid:

- converter/package/materializer version: **`0.2.0`**;
- GitHub tag/release: **`v0.2.0`**;
- Text-Fabric data version: **`0.2`**;
- native TF asset: **`tf-0.2.zip`**.

The OCP source pin does not advance because #104 changes distribution/release identity, not upstream source selection.

## Text-Fabric live verification target

The public transport must be exercised with stock Text-Fabric from a genuinely fresh cache:

```python
from tf.app import use
A = use("alexsosn/Pseudepigrapha-TF:v0.2.0", checkout="v0.2.0")
```

Then, after the release has populated the cache, network acquisition must be disabled and the same corpus must load locally:

```python
A = use("alexsosn/Pseudepigrapha-TF:local", checkout="local")
```

The first operation exercises GitHub's real release/`complete.zip` acquisition path. The second proves the downloaded app/data can be reused without network fallback.

## Fail-closed publication ordering

1. merge this release re-freeze PR;
2. verify permanent CI on that exact merged `main` commit;
3. independently adversarial-review the exact merged release candidate and current release namespace;
4. create immutable tag `v0.2.0` once at that exact commit;
5. dispatch the permanent publisher from the tagged/exact revision with the same tag/SHA;
6. candidate builder verifies tag→commit equality and constructs all four assets from the exact OCP snapshot and checked-out app;
7. publisher creates a draft release, verifies/downloads/revalidates the complete four-file generation, then promotes it once;
8. verify the public four-file generation and fresh-cache explicit-tag stock-TF load;
9. disable network and prove `checkout="local"` reload;
10. update/verify Agora to the same `0.2.0`/release-commit identity and independently review that change;
11. if any post-tag/post-release gate fails, never move the tag or silently replace the published generation; fix forward under a new release identity.
