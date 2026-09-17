# Issue #162: published-release identity in local comparison instructions

## Observed mismatch

The ordinary researcher acquisition example in `README.md` calls `tf.app.use("alexsosn/Pseudepigrapha-TF")`, which intentionally resolves the latest public release and remains valid. The separate local `/compare` example is different: it hardcodes a release tag and native archive name. On `main` it currently names `v1.0.0`, `tf-1.0.zip`, and data directory `1.0`.

GitHub release metadata checked on 2026-09-17 shows that the latest public release is still `v0.2.0`, published 2026-09-10. Its corpus assets are `complete.zip`, `tf-0.2.zip`, `conversion-report.json`, and `dataset-manifest.json`; its release notes identify Text-Fabric data version `0.2`. The only older public release is `v0.1.0`. There is no public `v1.0.0` release or `tf-1.0.zip` asset.

`main` is legitimately ahead of that published release: `pyproject.toml` currently reports package version `1.0.0`, and the current source defaults to TF data version `1.0`. Those development identities do not prove that a matching immutable public release exists. Documentation that reproduces a specific public corpus must therefore keep release tag, native archive name, extracted data directory, checked-out app/package tag, and browse `--version` aligned to one release that actually exists.

## Intended correction

Keep the generic latest-release `tf.app.use()` instructions unchanged. For the explicit local `/compare` reproduction example, use the currently published matching set:

- release/tag: `v0.2.0`;
- native corpus asset: `tf-0.2.zip`;
- local TF directory: `/tmp/pseudepigrapha-tf/0.2`;
- checkout: `--branch v0.2.0`;
- browser data version: `--version 0.2`.

Add a short warning that `main` can contain forward development versions and that release-specific commands must use a matching published tag/asset/data version. Do not create a new release, introduce another release-version constant, or broaden this into release automation.

## Regression target

A small static README test should fail while the local comparison example names nonexistent `v1.0.0` assets, and pass only when the example names the verified public `v0.2.0` set consistently. This intentionally makes a future public release update touch the documentation/test together rather than silently advertising an unpublished development identity.