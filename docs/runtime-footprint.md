# Researcher runtime footprint

This note records the normal public-corpus consumption path measured for the published `v0.2.0` corpus. These are reference measurements from one GitHub-hosted Ubuntu runner, not hardware-independent performance guarantees.

## Environment

- Ubuntu 24.04.5 (`ubuntu-24.04` GitHub-hosted runner, image `20260907.300.1`)
- Python 3.12.14
- Text-Fabric 13.1.0
- Pseudepigrapha-TF `v0.2.0`
- public GitHub release transport; no OCP checkout and no conversion

The published stock Text-Fabric `complete.zip` is **9,816,530 bytes (9.36 MiB)**.

## Clean public acquisition

A clean Text-Fabric cache successfully acquired `v0.2.0` from the public GitHub release and loaded the full tracked app with 922,922 word slots. The same populated cache then loaded successfully with networking explicitly blocked and `checkout="local"`.

`v0.2.0` itself has one packaging defect: its package dependency requested plain `text-fabric` even though public GitHub release acquisition requires Text-Fabric's `github` extra. For that historical tag, install the backend explicitly before remote acquisition:

```bash
pip install 'text-fabric[github]>=13.1,<14' \
  'https://github.com/alexsosn/Pseudepigrapha-TF/archive/refs/tags/v0.2.0.zip'
```

Current project metadata fixes this for subsequent installs by depending on `text-fabric[github]>=13.1,<14` directly.

## Measured footprint

| Operation | Wall time | Peak RSS |
| --- | ---: | ---: |
| cold public acquisition + full app load | 59.71 s | 2.24 GiB |
| warm offline full app load | 4.01 s | 1.69 GiB |
| warm full app load + representative 1 Enoch comparison | 3.95 s | 1.69 GiB |
| selective translation-oriented `Fabric.load()` | 3.05 s | 1.33 GiB |

After acquisition, `~/text-fabric-data` occupied **227,070,492 bytes (216.6 MiB)** across 205 files. Text-Fabric retained **no ZIP archives** in that cache, so the footprint is extracted/cached corpus data rather than a duplicate downloaded archive.

The selective load used only the features needed to discover and align generated translations for 1 Enoch. It reduced peak RSS by about **21%** relative to the warm full app, but still required about **1.33 GiB**. That is not a sufficient reduction to describe the corpus as lightweight.

## Current interpretation

Public acquisition and offline reuse work, but ordinary researcher-side memory use is high enough to remain a 1.0 concern. The largest extracted feature files observed in this run included `generation_model.tf` (~28.4 MiB), `version_kind.tf` (~20.1 MiB), `version_title.tf` (~14.9 MiB), and `source_ref_parts.tf` (~14.2 MiB). These repeated-value/version-owned features are candidates for investigation, but data must not be removed or weakened merely to improve the benchmark.

Issue #141 owns follow-up profiling and reduction of avoidable disk/RAM/startup cost. Documentation should recommend selective loading only where the measured workflow actually benefits from it.
