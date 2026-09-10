# Pseudepigrapha-TF v0.2.0

This release introduces the first canonical redistributable Text-Fabric corpus generation for the supported Online Critical Pseudepigrapha snapshot.

## Canonical corpus assets

The release publishes one validated four-file generation:

- `tf-0.2.zip` — canonical native Text-Fabric feature archive;
- `complete.zip` — stock Text-Fabric 13.1 express-download transport containing the exact release app plus byte-identical `tf/0.2` feature data;
- `conversion-report.json` — semantic parity, provenance, source/license, and exact serialized feature-set audit;
- `dataset-manifest.json` — release, converter, TF data, upstream, asset, and per-feature integrity binding, including the exact `complete.zip` bytes.

The four files form one release unit. `complete.zip` is the transport stock Text-Fabric can acquire directly from the GitHub release; `tf-0.2.zip` remains the canonical native feature archive used for byte-level feature identity and audit. Canonical validation also binds the app payload embedded in `complete.zip` to the exact release checkout rather than trusting only the ZIP's own hash.

## Release identity

- converter/package/materializer: `0.2.0`;
- Text-Fabric data version: `0.2`;
- supported OCP snapshot: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`;
- textual dataset license for the verified source scope: CC BY 4.0;
- converter software: MIT;
- upstream application/software: GPL-3.0.

## Researcher-facing additions since v0.1.0

- canonical redistributable Text-Fabric corpus assets with integrity manifest and conversion audit;
- stock Text-Fabric `complete.zip` acquisition path, plus fresh-cache and offline/local reload verification;
- exact report-to-serialized-feature and native-to-express byte binding;
- exact release-app binding for the advanced Text-Fabric app/browser layer;
- advanced Text-Fabric app/browser configuration, including researcher-facing manuscript/version/translation comparison support;
- generated feature reference and node-applicability documentation;
- full pinned-corpus release-candidate conversion, semantic parity, staging, extraction, stock-TF reload, app validation, and 1 Enoch comparison in CI.

The historical `v0.1.0` release remains unchanged and has no canonical corpus asset set.
