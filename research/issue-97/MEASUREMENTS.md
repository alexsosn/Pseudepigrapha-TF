# Issue #97 — exact distribution measurements

Measured by GitHub Actions run `34218318894` on 2026-09-08 from the exact supported OCP snapshot `c939dcbacad78c5d18d2c4282cad23c47e19ac07` using Text-Fabric 13.1.0.

## Materialized corpus

- converted OCP XML files: 38
- word slots: 922,922
- total TF nodes: 1,193,651
- serialized `.tf` feature files: **96**
- serialized `.tf` bytes: **169,467,455**
- `conversion-report.json` bytes: **8,630**
- TF + report bytes: **169,476,085**

Largest serialized features in the measured corpus:

| Feature | Bytes |
| --- | ---: |
| `generation_model.tf` | 29,744,082 |
| `version_kind.tf` | 21,103,078 |
| `version_title.tf` | 15,654,596 |
| `source_ref_parts.tf` | 14,915,682 |
| `generation_marker.tf` | 8,501,523 |
| `ocp_book.tf` | 7,059,942 |
| `unit_id.tf` | 6,708,874 |
| `source_ref.tf` | 6,556,132 |
| `reading_xml.tf` | 6,513,562 |
| `reading_text.tf` | 6,484,078 |

## Native Text-Fabric express archive

`tf-zip alexsosn/Pseudepigrapha-TF/tf` produced the conventional asset:

- name: **`tf-0.1.zip`**
- bytes: **9,801,766**
- SHA-256 from this probe: `7fc11642e6aeec7e54e319d5dfd2900a64de6bc01cc3d31200b248c4823e21e9`
- archive entries: **96**
- compression factor relative to raw `.tf` bytes: about **17.3×**
- archive size is about **5.78%** of the raw `.tf` bytes

The measured SHA-256 is evidence for this exact probe output, not a permanent release checksum: ZIP container metadata can make independently generated archives byte-different even when their extracted TF feature bytes are equivalent. Release production must therefore create one canonical archive and record the checksum of that exact published artifact.

## Important `tf-zip` behavior

Text-Fabric emitted:

> `WARNING: non feature file "0.1/conversion-report.json"`

and the resulting archive contained exactly the 96 `.tf` feature files. Therefore `conversion-report.json` is **not** part of the native `tf-0.1.zip` express asset.

The release contract must publish the report separately and bind both assets with an immutable manifest/checksums. A consumer must never infer report/artifact association only from matching filenames or release-page proximity.

## Transport decision

These measurements close the outstanding size gate in `RESEARCH.md`:

- committing ~169.5 MB of generated data per TF version to Git is unnecessary for the first canonical distribution;
- the native ~9.8 MB TF express asset is practical as a GitHub Release asset and is directly compatible with Text-Fabric's release/cache loader;
- the canonical publication unit will be the release event containing `tf-0.1.zip`, `conversion-report.json`, and a manifest that cryptographically binds them to the converter release, TF data version, exact OCP snapshot, and license/provenance identity;
- Agora remains a deterministic materialization/reproducibility path under the same release identity and must not define a competing corpus version.