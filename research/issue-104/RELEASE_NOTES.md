# Pseudepigrapha-TF v0.2.0

This release introduces the first canonical redistributable Text-Fabric corpus generation for the supported Online Critical Pseudepigrapha snapshot.

## Canonical corpus assets

The release publishes one validated generation:

- `tf-0.2.zip` — native Text-Fabric feature archive;
- `conversion-report.json` — semantic parity, provenance, source/license, and exact serialized feature-set audit;
- `dataset-manifest.json` — release, converter, TF data, upstream, asset, and per-feature integrity binding.

The three assets form one release unit. Consumers should validate them together rather than treating the ZIP as an unaudited standalone export.

## Release identity

- converter/package/materializer: `0.2.0`;
- Text-Fabric data version: `0.2`;
- supported OCP snapshot: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`;
- textual dataset license for the verified source scope: CC BY 4.0;
- converter software: MIT;
- upstream application/software: GPL-3.0.

## Researcher-facing additions since v0.1.0

- canonical Text-Fabric release transport and integrity manifest;
- exact report-to-serialized-feature binding and loaded-TF provenance cross-checks;
- advanced Text-Fabric app/browser configuration;
- generated feature reference and node-applicability documentation;
- full pinned-corpus release-candidate staging, extraction, reload, and app validation in CI.

The historical `v0.1.0` release remains unchanged and has no canonical corpus asset set.
