# Researcher runtime footprint

This note records reference measurements for the normal researcher consumption path. They were measured on GitHub-hosted Ubuntu runners and are **not** hardware-independent system requirements.

## Environment

- Ubuntu 24.04.5 (`ubuntu-24.04`, runner image `20260907.300.1`)
- Python 3.12.14
- Text-Fabric 13.1.0
- pinned OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`

Two states are distinguished below:

1. the published `v0.2.0` corpus, which provides the pre-optimization baseline; and
2. the post-#141 corpus generated from the current converter branch, which is the shape intended for the next corpus publication.

The post-#141 corpus is not yet a published GitHub release, so its remote network-acquisition latency cannot be measured honestly. The optimized measurements therefore separate transport size, first local load immediately after unpacking the stock `complete.zip`, and warm offline reuse.

## Installation footprint

A clean Python 3.12 virtual environment occupied 11,120,805 bytes on the reference runner. After upgrading `pip`, it occupied 10,705,061 bytes. Installing the built `pseudepigrapha-tf` wheel through the supported dependency path (`text-fabric[github]>=13.1,<14`) produced a 110,382,279-byte environment.

Relative to the post-`pip` baseline, Pseudepigrapha-TF plus its runtime dependency closure therefore added **99,677,218 bytes (about 95.1 MiB)**. The project wheel itself was **109,919 bytes**; nearly all installation footprint belongs to Text-Fabric and its runtime dependencies rather than this package's own Python code.

`v0.2.0` had a packaging defect: it requested plain `text-fabric` even though public GitHub release acquisition requires Text-Fabric's `github` extra. Current project metadata fixes this by depending on `text-fabric[github]>=13.1,<14` directly.

## Corpus transport and cache

| Measurement | Published `v0.2.0` | Post-#141 corpus |
| --- | ---: | ---: |
| stock `complete.zip` | 9,816,530 B (9.36 MiB) | 9,643,396 B (9.20 MiB) |
| populated stock Text-Fabric cache | 227,070,492 B (216.6 MiB) | 152,510,275 B (145.4 MiB) |
| files in populated cache | 205 | 205 |
| retained ZIP archives | 0 | 0 |

The optimized stock cache is about **32.8% smaller** than the published baseline. Text-Fabric does not retain the downloaded ZIP in the populated cache, so there is no second full archive copy consuming disk after acquisition.

The small change in compressed transport size relative to the much larger extracted/cache reduction is expected: the removed data consisted mainly of highly repetitive values that ZIP already compressed efficiently.

## Load and memory measurements

| Operation | Published `v0.2.0` | Post-#141 corpus |
| --- | ---: | ---: |
| first load after transport is present locally | n/a as a separate measurement | 46.35 s / 2,179,456 KiB RSS (~2.08 GiB) |
| warm offline full app | 4.01 s / 1,767,192 KiB (~1.69 GiB) | 3.63 s / 1,407,908 KiB (~1.34 GiB) |
| warm full app + representative 1 Enoch comparison | 3.95 s / 1,769,268 KiB (~1.69 GiB) | 3.74 s / 1,410,164 KiB (~1.34 GiB) |
| selective translation-oriented `Fabric.load()` | 3.05 s / 1,397,648 KiB (~1.33 GiB) | 2.86 s / 1,047,596 KiB (~1023 MiB) |

The published baseline's combined **remote acquisition + first full app load** was 59.71 s / 2,347,328 KiB (~2.24 GiB). The optimized corpus is not yet published, so that network-inclusive number must not be compared directly with the 46.35-second local-first-load measurement above.

The first local load is expensive because Text-Fabric compiles/cache-materializes feature data. Subsequent loads reuse that compiled state. Wall-clock timings fluctuate between hosted runners; the byte and peak-RSS reductions are the more stable evidence.

Compared with published `v0.2.0`, post-#141 measurements show approximately:

- **20% lower** peak RSS for a warm full-app load;
- **25% lower** peak RSS for the measured selective translation workflow;
- **33% less** stock cache disk use.

## Lower-memory selective loading

Researchers who only need generated/source translation alignment do not need the full advanced-app feature set. A representative selective load is:

```python
from tf.fabric import Fabric
from pseudepigrapha_tf import Translations

TF = Fabric(locations=["tf/0.2"], modules=[""], silent="deep")
api = TF.load(
    "book ocp_book version_title version_kind language generated_language "
    "generation_marker generation_method generation_model unit_id unit_index source_ref "
    "reading_text is_primary translation_of translation_unit_of reading_of",
    silent="deep",
)

T = Translations(api)
versions = T.versions(work="1En", language="French")
aligned = T.aligned_units(versions[0]["node"])
```

On the reference runner this path peaked at **1,047,596 KiB**, just under 1 GiB. This is useful when the task does not require apparatus, browser, or the complete feature inventory, but it should not be interpreted as a general promise that every selective query will stay below 1 GiB.

## What #141 changed

Profiling found two large cases of accidental denormalization that could be removed without deleting scholarly information:

- generated-translation provenance (`generation_marker`, `generated_language`, `generation_method`, `generation_model`) was repeated across every generated descendant and slot even though it belongs to the generated version and the public API consumes it from the generated `book` node;
- converter-owned `version_kind` was repeated across every descendant and slot even though demonstrated semantics consume it only on `book`, `unit`, and metadata-only `version_metadata` nodes.

The four generated-provenance feature files fell from about 45.8 MiB combined to roughly 23 KiB, and `version_kind.tf` fell from 21,103,140 bytes to 1,389,289 bytes. Full pinned-corpus parity, generated/source alignment, apparatus behavior, metadata-only versions, stock offline loading, browser/app loading, and representative comparison tests remain green.

Further scope narrowing intentionally stops here. The remaining large features such as `version_title`, `ocp_book`, and `source_ref_parts` are upstream/source-identity and traceability data with plausible direct researcher-query value. Any future reduction there requires its own research, semantic contract, TDD gate, and measurement rather than treating smaller RAM as sufficient justification.
