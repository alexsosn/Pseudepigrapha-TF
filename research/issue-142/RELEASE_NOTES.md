# Pseudepigrapha-TF v1.0.0

Pseudepigrapha-TF 1.0 is the first researcher-facing stable release of the derived Online Critical Pseudepigrapha Text-Fabric corpus and its companion research APIs.

## Researcher-visible changes since v0.2.0

- **Corpus correctness and completeness:** the full pinned OCP snapshot is independently audited against the serialized Text-Fabric graph, including difficult multi-version texts, apparatus ownership, metadata-only versions, historical classifications, preserved source anomalies, and public metadata.
- **Generated translations:** all 231 generated English/French versions and 54,143 generated units are checked for source ownership, occurrence-level alignment, provenance, API exposure, and separation from historical witness evidence.
- **Clean install and acquisition:** the package provisions Text-Fabric's GitHub backend, the published `complete.zip` path is exercised from a fresh cache, and network-blocked local reload is verified after acquisition.
- **Lower disk and memory use:** repeated generated provenance and `version_kind` data were narrowed to their semantic owners. The measured post-optimization stock cache is roughly 145 MiB, warm full-app peak RSS roughly 1.34 GiB, and the translation-oriented selective load roughly 1023 MiB on the reference CI runner.
- **Web comparison hardening:** real-corpus HTTP acceptance now covers multi-version 1 Enoch, TJob metadata-only evidence, witness reading/omission/unattested states, source anomalies, and duplicate citations such as both Syriac `4Ezra 10:4` occurrences. Generated translations are resolved by exact source-unit alignment rather than section-label coincidence.
- **Researcher-first documentation:** the README now leads with acquiring, loading, querying, comparing, and understanding the published corpus. Rebuilding from OCP and contributor machinery are secondary.

The supported OCP source snapshot remains pinned at `c939dcbacad78c5d18d2c4282cad23c47e19ac07`. Source irregularities are preserved or fail closed rather than silently repaired. Generated translations remain parallel research text, not historical witnesses.

Release assets use the existing distribution format: stock Text-Fabric `complete.zip`, native `tf-1.0.zip`, `conversion-report.json`, and `dataset-manifest.json`.
