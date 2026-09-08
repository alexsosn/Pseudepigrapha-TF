# Issue #104 — release research

## Exact starting point

Research is frozen against merged `main` commit `ec0139670ffeeb80dabb3668bbed7af69049e8e8`.

The authoritative post-merge CI run is `34272672126`; both `unit-and-tf` and `pinned-upstream-integration` pass, including wheel installation, exact OCP conversion, semantic parity, canonical staging/extraction/reload, public metadata, and tracked app startup.

## Existing release identity

The only public release is `v0.1.0`, targeting `315439284e765c1d7ea89ffdefdd10f403aa1293`. It has no binary release assets. It is historical and must not be modified or reused.

At the #104 starting point:

- package version in `pyproject.toml`: `0.1.0`;
- runtime `pseudepigrapha_tf.__version__`: `0.1.0`;
- `agora.materializer.json` plugin version: `0.1.0`;
- tracked Text-Fabric app data version: `0.1`;
- Agora registry version/ref: `0.1.0` / `315439284e765c1d7ea89ffdefdd10f403aa1293`;
- supported OCP source remains pinned to `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.

## Version decision

The delta since `v0.1.0` is a researcher-facing contract change, not a patch-only correction. It includes the advanced app/browser surface, generated feature-help/applicability metadata, canonical distribution APIs, exact serialized feature/report/manifest identity, and release-loading semantics. The first canonical corpus distribution therefore uses:

- converter/package/materializer version: **`0.2.0`**;
- GitHub tag/release: **`v0.2.0`**;
- Text-Fabric data version: **`0.2`**;
- native TF asset: **`tf-0.2.zip`**.

The OCP source pin does not advance because #104 changes distribution/release identity, not upstream source selection.

## Text-Fabric transport behavior

Text-Fabric supports an explicit release tag as checkout for app/data acquisition and `checkout="local"` for already cached data. Official TF documentation describes release tags such as `v1.3` as valid checkout specifiers and `local` as a no-network local-cache mode:

- https://annotation.github.io/text-fabric/tf/about/datasharing.html
- https://annotation.github.io/text-fabric/tf/advanced/repo.html

The live verification target is therefore equivalent to:

```python
from tf.app import use
A = use("alexsosn/Pseudepigrapha-TF:v0.2.0", checkout="v0.2.0")
```

followed from the same cache by:

```python
A = use("alexsosn/Pseudepigrapha-TF:local", checkout="local")
```

## Publication primitive gap

#97 intentionally created `.github/workflows/build-corpus-release-assets.yml` as a reusable candidate builder with `workflow_call`. It validates an already-existing tag against an exact commit, builds and installs the release wheel, converts the immutable OCP snapshot, stages/validates `tf-D.zip` + report + manifest, reloads with stock TF, and uploads the candidate set as a workflow artifact.

It does **not** publish a GitHub release, and there is no permanent publication entry point in merged `main`. #104 must add one rather than relying on manual file copying.

The publisher must:

1. run only for an explicit release tag/commit pair;
2. call the #97 reusable candidate builder rather than duplicating corpus construction;
3. refuse a missing/moved tag or a pre-existing GitHub release;
4. download the exact validated candidate artifact;
5. create one release generation containing exactly `tf-0.2.zip`, `conversion-report.json`, and `dataset-manifest.json`;
6. perform fresh-cache stock-TF remote loading after publication;
7. verify manifest/loaded metadata identity;
8. prove a second `checkout="local"` load succeeds with network access unavailable;
9. never move/overwrite a tag or clobber an existing release on failure.

## Agora boundary

Agora currently pins the historical `v0.1.0` release commit. Agora's registry update belongs after the new public release and live verification succeed. The registry must move `version` and immutable `ref` together to the exact `v0.2.0` release commit while preserving repository, manifest path, materializer IDs, release-tracking policy, and source pin semantics.

## Fail-closed publication ordering

1. merge the #104 release-prep PR;
2. verify exact merged `main` CI;
3. independently adversarial-review the exact release-candidate commit;
4. create immutable tag `v0.2.0` at that exact commit;
5. build and validate candidate assets from the tagged commit;
6. create the public release once, with all three assets;
7. fresh-cache explicit-tag TF load and identity checks;
8. offline/local-cache reload;
9. update and verify Agora;
10. if any post-tag/post-release gate fails, do not move the tag or mutate the published generation; fix forward with a new version.
