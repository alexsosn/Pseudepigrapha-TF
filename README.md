# Pseudepigrapha-TF

Pseudepigrapha-TF is an MIT-licensed converter from the [Online Critical Pseudepigrapha (OCP)](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha) to [Text-Fabric](https://annotation.github.io/text-fabric/tf/), with Python research helpers for apparatus, translation, metadata and local comparison.

The primary distribution target is **local materialization through [Agora](docs/agora-materialization.md)**: Agora obtains OCP source files directly and runs the installed converter. The v1.2.0 materializer manifest selects OCP commit `853a64b623de296d2b8532a43593607772e7c45a`. It converts the upstream checkout directly; the Agora registry updates independently. Existing published v1.1 corpus archives remain usable as a legacy option. Software releases do not depend on publishing or clearing redistribution of new data archives.

The current development package requires **Python 3.12+** and Text-Fabric **13.1.x**. CI runs its full corpus/source-fidelity suite on 3.12 and independently builds and installs a wheel in a clean **Python 3.14** environment for a real Text-Fabric passage, apparatus, stock-browser and HTTP comparison smoke. Python 3.10 has reached end of life and is no longer supported. This support statement applies to code on `main`; published v1.1 dataset assets are unchanged.

## Local materialization

Install via Agora's [materializer catalog](https://github.com/alexsosn/Agora/blob/main/registry/materializers.yaml), or use the standalone command below. No prebuilt corpus is required.

```bash
python -m pip install "git+https://github.com/alexsosn/Pseudepigrapha-TF.git@v1.2.0"
git clone https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha.git
git -C Online-Critical-Pseudepigrapha checkout 853a64b623de296d2b8532a43593607772e7c45a
pseudepigrapha-tf convert Online-Critical-Pseudepigrapha/static/docs --output tf/1.1
```

Load that local output with native Text-Fabric:

```python
from tf.fabric import Fabric

TF = Fabric(locations=["tf/1.1"], modules=[""], silent="deep")
api = TF.load("ocp_book source_ref version_kind", silent="deep")
assert api.T.nodeFromSection(("3Macc", "1", "1")) is not None
```

See the [local app guide](docs/tf-app.md) to browse and compare passages.
The examples in the legacy acquisition section use the existing v1.1 data release instead.

## What the corpus contains

The corpus preserves the parts of OCP needed for research rather than flattening it to plain text:

- textual source versions as Text-Fabric `book / chapter / verse` sections with exact upstream citations retained in `source_ref`;
- apparatus units, primary and alternative readings, manuscript metadata, witness assignments, explicit omissions, and citation-only witnesses;
- metadata-only source versions without fabricating text for them;
- OCP's source-declared generated English/French translations as a separate layer linked to their exact source version and source units;
- public work metadata from OCP's `intros.json`, including introductions, manuscript discussions, bibliography, provenance, and per-work citations;
- historical OCP genre and biblical-figure catalogue classifications, explicitly marked as historical rather than inferred for later works;
- source anomalies and unusual structures without silently repairing or reassigning them.

Generated translations are **not** treated as historical witnesses. Source/critical evidence belongs to `Apparatus`; generated parallel text belongs to `Translations`.

Public corpus releases contain the derived Text-Fabric corpus (`complete.zip` for stock Text-Fabric acquisition and a versioned native `tf-<data-version>.zip` feature archive), its conversion report, and its dataset manifest. The upstream OCP XML remains in the OCP repository. See [data licensing and attribution](DATA_LICENSE.md) for the exact source/license boundary.

## Get and load the published corpus

For the existing legacy dataset, use Text-Fabric's GitHub-release acquisition. For corpus access alone:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install "text-fabric[github]>=13.1,<14"
```

For the legacy published dataset, load its explicit data release (software tags do not contain a corpus):

```python
from tf.app import use

app = use(
    "alexsosn/Pseudepigrapha-TF:v1.1.0",
    checkout="v1.1.0",
    silent="deep",
)
api = app.api
```

The first call selects the historical v1.1.0 corpus and populates the Text-Fabric cache. After that acquisition, an offline/local reload is:

```python
from tf.app import use

app = use(
    "alexsosn/Pseudepigrapha-TF:local",
    checkout="local",
    silent="deep",
)
api = app.api
```

The historical data-release acquisition and a network-blocked `checkout="local"` reload are exercised by the repository's published-release verification workflow.

For the Pseudepigrapha-TF helper APIs used below, install the current package as well:

```bash
python -m pip install "git+https://github.com/alexsosn/Pseudepigrapha-TF.git"
```

The project package already depends on `text-fabric[github]>=13.1,<14`. Installing Text-Fabric separately first is useful when you only need standard Text-Fabric access to the published corpus.

## Query a passage

A normal Text-Fabric section lookup needs no Pseudepigrapha-TF helper:

```python
verse = api.T.nodeFromSection(("1En__Ethiopic", "1", "2"))
assert verse is not None

api.T.text(verse)
api.T.sectionFromNode(verse)
```

`1En__Ethiopic` is the stable TF source-version id. Multi-version OCP works therefore remain distinguishable even when human-readable titles are not unique.

For deeper OCP references, Text-Fabric's three-level section API folds all parent components into the chapter field. The exact OCP address is still available as `source_ref`; see [Known limitations](#known-limitations).

## Apparatus and witnesses

`Apparatus.passage()` returns one source version's passage together with all apparatus units and its witness evidence. The stock advanced app does not need every apparatus relation for display, so load the extra semantic features before using the helper on `app.api`:

```python
from pseudepigrapha_tf import Apparatus

app.load(" ".join(Apparatus.PASSAGE_FEATURES))
A = Apparatus(app.api)
passage = A.passage("1En__Ethiopic", "1", "2")

passage["units"]
passage["witnesses"]["p"]["segments"]
passage["witnesses"]["Bertalotto"]["segments"]
```

Witness segments deliberately distinguish three states:

- `reading` — the witness is assigned to a non-empty reading;
- `omission` — the witness is explicitly assigned to an empty OCP reading;
- `unattested` — no reading at that unit cites the witness.

Those are not interchangeable. If a witness is unattested at one or more units, its reconstructed `text` is `None`; `attested_text` still contains the readings that are actually present. The API does not infer a lacuna or omission from silence.

To ask for one normalized passage across every textual source version of a work:

```python
app.load(" ".join(Apparatus.WORK_PASSAGE_FEATURES))
result = A.work_passage("1En", "1", "2")

result["versions"]["1En__Ethiopic"]["status"]
result["versions"]["1En__Qumran_Aramaic"]["status"]
result["versions"]["1En__Latin_Fragments"]["status"]
result["versions"]["1En__Greek"]["status"]
```

Possible source-version states are `available`, `not_present`, and (separately) `metadata_only`. A normalized address is applied independently to each version; this is not a claim that differently divided source versions are automatically aligned.

See [apparatus helper loading contracts](docs/apparatus.md) for selective-load details and lower-level methods.

## Generated translations

OCP marks its generated translations structurally. Pseudepigrapha-TF preserves them as `version_kind=generated_translation`, links each generated book to one source version with `translation_of`, and links generated units occurrence-by-occurrence with `translation_unit_of`.

This workflow is standalone: it loads the exact translation-oriented feature set without assuming that the apparatus example above has already run.

```python
from pseudepigrapha_tf import Translations

app.load(" ".join(Translations.REQUIRED_FEATURES))
T = Translations(app.api)
french = T.versions(work="1En", language="French")
generated_book = french[0]["node"]

aligned = T.aligned_units(generated_book)
aligned[0]["source_text"]
aligned[0]["translation_text"]
```

`Translations.aligned_units()` uses the explicit graph alignment rather than positional zipping or bare verse labels. This matters for repeated source citations such as the two Syriac `4Ezra 10:4` occurrences.

The synthetic `OCP-Trans` witness remains provenance for the generated layer but is excluded from historical manuscript/apparatus semantics. A genuine scholarly English source version, such as pinned `4Q548`, is therefore not reclassified merely because it is English.

## OCP 2026 compact editions

The newer OCP snapshot has six additional compact-dialect works: CithDavid,
Demetr, Justus, OrMois, ThrenSeila and VisKenaz. The converter preserves the
source-declared Greek/Latin original and its parallel English version without
reclassifying the English as a historical witness or a machine-generated
translation. Compact `unit/@id` values are individual addressable TF verses,
and the original XML identifiers remain in native TF features.

For a locally materialized 2026 dataset, load the `Translations`
helper with `Translations.PARALLEL_FEATURES` (or the full
`Translations.REQUIRED_FEATURES` if the generated layer is also present).
`version_kind` distinguishes `source`, `parallel_translation` and
`generated_translation`. Explicit `translation_of` and
`translation_unit_of` edges retain source-unit identity.

The v1.2 converter accepts the unmodified snapshot, including the reviewed
separate ApDan morphology source and derived TEI mirrors as explicit exclusions
from the independent textual editions. The older v1.1 published dataset does not
contain these additions.
See [the source and fidelity notes](docs/source-identity-and-anomalies.md).

## Optional ApDan TEI morphology (local CC BY-NC module)

The newer OCP snapshot contains `static/docs/ApDan_TEI.xml` with
**2,150 Greek word annotations** (`lemma`, `pos`, `msd`) across 170
verses. Its own TEI header declares `availability=restricted`,
**CC BY-NC 4.0**, and a Logos/Heiser–Penner/Lexham provenance claim.
That source declaration does **not independently establish the right to
redistribute the annotations**. This restricted source is **excluded**
from the normal `convert` pipeline and every default published corpus.

After materializing a compatible Text-Fabric edition locally, inspect
alignment without writing any annotated features:

```bash
pseudepigrapha-tf apdan-morph /path/to/tf /path/to/OCP/static/docs/ApDan.xml /path/to/OCP/static/docs/ApDan_TEI.xml
```

To generate an optional, **separate, noncommercial local module** from
copies you are entitled to use, deliberately opt in and choose an output
directory outside the base Text-Fabric dataset:

```bash
pseudepigrapha-tf apdan-morph /path/to/tf /path/to/OCP/static/docs/ApDan.xml /path/to/OCP/static/docs/ApDan_TEI.xml \
  --accept-noncommercial --output /path/to/restricted-apdan-module
```

The module uses native word features `apdan_tei_lemma`,
`apdan_tei_pos`, `apdan_tei_msd`, with source SHA-256 digests,
source-declared license and restricted status in each feature header.
The audit checks exact source-text/TF word surfaces, 170 verse identities
and the TEI word forms before emitting any annotation. TEI punctuation is
counted but **not** inserted into source text. The module is never
bundled with the default CC BY corpus. Do not distribute this restricted
output without independently checking the applicable rights.

See [source and provenance notes](docs/source-identity-and-anomalies.md)
and [full migration issue #228](https://github.com/alexsosn/Pseudepigrapha-TF/issues/228).
The v1.2 converter directly supports the 2026 source through its local materializer; no new data publication is required.

## Local clavis and bibliography lookup (OCP 2026)

The newer OCP repository has a 299-entry crosswalk in
`data/master_crosswalk.csv`, separate from the XML text corpus. Use a
local copy you are entitled to access to resolve an exact canonical ID
against source-version nodes in a materialized Text-Fabric dataset:

```bash
pseudepigrapha-tf catalog-lookup /path/to/tf /path/to/OCP/data/master_crosswalk.csv --id CAVT-JH-01
```

Omit `--id` for a full coverage audit. Output is JSON, including literal
upstream canonical IDs, bibliography references, declared statuses,
crosswalk SHA-256, matching **source** TF version IDs and their source XML
SHA-256. Generated and parallel translations are not source matches.
Multiple catalogue IDs naming the same XML remain separate assertions.
`match_status` distinguishes `exact_tf_match`,
`declared_filename_not_in_tf`, and `no_declared_filename`; it does not
infer availability from the upstream status or validate scholarly identity.
The exact, case-sensitive filename join does not guess aliases, text
equivalence, or crosswalk/TF revision compatibility.

Python callers can use `from pseudepigrapha_tf.catalog import catalog_lookup,
REQUIRED_FEATURES` and pass a native TF API with those features loaded,
the CSV bytes, and optionally `canon_id="CAVT-JH-01"`.
The upstream CSV is not bundled, nor is any generated dossier HTML,
modern clavis prose, or new TF metadata feature. The command is read-only
with respect to source and TF files; Text-Fabric may maintain its usual
local load caches. Redistribution rights for the catalogue are not
attested; the lookup operates on a local copy.

At the reviewed 2026 snapshot, 50 catalogue rows claim 49 distinct
existing source filenames; 37 rows declare missing filenames and 212
have no filename. Six plausible stale names (including `CithDav.xml`
versus `CithDavid.xml`) require editorial confirmation rather than
automatic aliases. See [research #246](https://github.com/alexsosn/Pseudepigrapha-TF/issues/246).

## Browse and compare

The published corpus works with the standard Text-Fabric advanced app loaded by `tf.app.use()` above. Pseudepigrapha-TF also provides a local `/compare` view for passage-centered comparison across source versions, manuscripts, and generated translations.

The comparison server takes a **local materialized TF feature directory**; it does not run the OCP converter. One reproducible layout is to extract the published native archive and use the tracked app from this repository:

```bash
curl -L \
  -o /tmp/tf-1.1.zip \
  https://github.com/alexsosn/Pseudepigrapha-TF/releases/download/v1.1.0/tf-1.1.zip

mkdir -p /tmp/pseudepigrapha-tf/1.1
python -m zipfile -e /tmp/tf-1.1.zip /tmp/pseudepigrapha-tf/1.1

git clone --depth 1 --branch v1.1.0 https://github.com/alexsosn/Pseudepigrapha-TF.git
cd Pseudepigrapha-TF
python -m pip install .
pseudepigrapha-tf browse /tmp/pseudepigrapha-tf/1.1 --app app
```

Open `http://127.0.0.1:8000/compare`. The stock Text-Fabric browser remains available at `/`; the comparison route is an addition, not a replacement server.

The comparison landing page lets you select a work, then choose an actual
source version, chapter, and verse from the loaded corpus. Non-numeric section
labels and duplicate-citation suffixes are shown as stored, so no reference
guesswork is needed; if you know the chapter and verse, enter them directly
on the landing page. The chosen source version provides the **navigation
context**; comparison still displays its normal source-version selection and
does not claim that differently structured versions are automatically aligned.
Existing direct URLs such as `/compare?work=1En&chapter=1&verse=2` remain valid.

The real pinned-corpus acceptance gate exercises, among other cases:

- 1 Enoch with multiple source versions and distinguishable witness omission/unattested states;
- TJob with a metadata-only Coptic version and a large witness inventory;
- generated English/French translations nested under their exact source version;
- duplicate Syriac `4Ezra 10:4` occurrences as separate TF sections;
- readable fail-closed behavior where OCP source evidence is genuinely ambiguous.

## Resource expectations

Resource measurements are reference measurements from GitHub-hosted Ubuntu runners, **not hardware requirements**.

For the published `v0.2.0` baseline, the stock `complete.zip` is about **9.36 MiB**, the populated stock Text-Fabric cache measured about **216.6 MiB**, and a warm full-app load measured about **1.69 GiB peak RSS**.

The 1.0 corpus output is smaller: about **9.20 MiB** compressed, **145.4 MiB** in the populated stock cache, about **1.34 GiB peak RSS** for a warm full-app load, and about **1023 MiB peak RSS** for the measured translation-oriented selective load. Text-Fabric retained no ZIP archive in the populated cache in either measurement.

These remain the most recent measured figures. The 1.1 corpus changes manuscript metadata only and was not re-measured, so no figure above is restated as a 1.1 measurement.

The first local load is more expensive because Text-Fabric compiles/cache-materializes features. On the reference runner the post-#141 first local load took about 46 seconds and peaked around 2.08 GiB; a warm full-app load took about 3.6 seconds. Hosted-runner wall-clock values fluctuate, so the disk/RSS deltas are more meaningful than the exact seconds.

If you only need a narrow workflow, load only its required features rather than the whole advanced app. The exact measurement method and a tested translation-oriented selective feature list are in [researcher runtime footprint](docs/runtime-footprint.md).

## Metadata and feature reference

Public work metadata is exposed through `WorkMetadata`; researchers normally do not need to decode the serialized JSON-scalar features manually:

```python
from pseudepigrapha_tf import WorkMetadata

app.load(" ".join(WorkMetadata.REQUIRED_FEATURES))
M = WorkMetadata(app.api)

tjob = M["TJob"]
tjob["fields"]["manuscripts"]
tjob["fields"]["bibliography"]
tjob.get("citation")  # optional; absent when upstream did not supply one
```

Historical OCP catalogue categories have their own explicitly historical API:

```python
from pseudepigrapha_tf import HistoricalClassifications

app.load(" ".join(HistoricalClassifications.REQUIRED_FEATURES))
C = HistoricalClassifications(app.api)

C.works_by_genre("testaments")
C.works_by_figure("Moses")
```

For the schema itself, use the generated [Text-Fabric feature reference](docs/features/0_home.md). It is generated from the serialization contracts and is the canonical index for node/edge feature meanings. Additional focused documentation:

- [apparatus helper contracts](docs/apparatus.md)
- [researcher runtime footprint](docs/runtime-footprint.md)
- [source identity and anomaly policy](docs/source-identity-and-anomalies.md)
- [historical classifications](docs/historical-classifications.md)
- [data licensing and attribution](DATA_LICENSE.md)

## Known limitations

Pseudepigrapha-TF preserves source uncertainty and irregularity instead of silently normalizing it. Important consequences:

- **Three-level TF sections:** OCP may use deeper reference trees. Parent components are folded into the TF chapter field; the exact upstream citation remains in `source_ref`.
- **Duplicate source citations:** exact repeated OCP citations remain separate sections. The first keeps the normal verse label and later occurrences receive a technical `~N` suffix such as `4~2`. The suffix is an interface disambiguator, not an editorial correction; both occurrences retain the same exact `source_ref`.
- **No automatic cross-version alignment:** `Apparatus.work_passage()` asks each source version independently for the same normalized TF address. A missing section is `not_present`; it is not forced into a correspondence with another version.
- **Metadata-only versions:** OCP can declare a version with metadata but no text. Pinned `TJob__Coptic` remains visible as metadata-only evidence and does not become a fake empty `book` section.
- **Malformed/exceptional source structures:** pinned Aristob `<elipsis>` markers and PssSol direct-div readings are preserved as dedicated anomaly nodes. They are not reassigned to guessed textual loci. A comparison whose source ownership is genuinely ambiguous may return a readable 400 instead of inventing an answer.
- **Generated translations:** source-declared generated translations are useful parallel text, but they are not historical witnesses and are intentionally excluded from source apparatus semantics.
- **Resource figures:** the numbers above describe one CI environment and corpus state, not a guaranteed minimum-RAM specification for every query or machine.

For exact anomaly provenance and record-specific exceptions, see [source identity and anomaly policy](docs/source-identity-and-anomalies.md).

## Rebuild from OCP

Local conversion is the primary software workflow; Agora automates source acquisition and invokes this CLI. The legacy published corpus can also be loaded without conversion.

The legacy v1.1 pinned upstream `static/docs` files use the **custom Grammateus/OCP XML** vocabulary (`book/version/div/unit/reading`), not TEI XML despite the upstream README's broader label. That pinned directory has 39 `.xml` names, including one empty `3Macc.xml`; the complete release converter processes 38 nonempty files. See [ADR-0002: Text-Fabric-Factory/source format](docs/architecture/ADR-0002-tff-source-format-boundary.md) for the primary-source evidence and migration decision.

For the current Agora source (also tested directly in CI):

```bash
git clone https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha.git
git -C Online-Critical-Pseudepigrapha checkout 853a64b623de296d2b8532a43593607772e7c45a
pseudepigrapha-tf convert Online-Critical-Pseudepigrapha/static/docs --output tf/1.1
```

For historical v1.1 source reproducibility, use the older pin instead:

```bash
git clone https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha.git
git -C Online-Critical-Pseudepigrapha checkout c939dcbacad78c5d18d2c4282cad23c47e19ac07

pseudepigrapha-tf convert \
  Online-Critical-Pseudepigrapha/static/docs \
  --output tf/1.1
```

Conversion auto-detects and records source Git identity where possible. The supported pinned source receives the researched verified content-license profile; arbitrary source tuples are convertible but remain explicitly unverified rather than inheriting that claim.

Every successful conversion writes `conversion-report.json`. The report is built by independently rereading raw source data and checking the generated graph for source files/versions, divisions, apparatus readings and witnesses, ownership edges, annotations, generated translations/alignment, metadata, classifications, preserved anomalies, section coverage, and provenance. Unsupported or ambiguous source structures fail rather than being silently discarded.

### Developer setup

```bash
git clone https://github.com/alexsosn/Pseudepigrapha-TF.git
cd Pseudepigrapha-TF
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

The full CI additionally converts/audits the pinned OCP corpus and reloads it through real Text-Fabric, including stock `complete.zip`, advanced-app, apparatus, translation, metadata, classification, and comparison acceptance. The separate Python 3.14 job tests a clean installed wheel (not an editable checkout). The grouped new-OCP candidate stage exercises all 66 supported source files and a real stock Text-Fabric Flask browser with `/compare` requests for the newly added compact Greek/Latin originals and their source-declared parallel English translations. This acceptance tests local materialization; it is not a publication of corpus data.

### Contributor and implementation reference

The README intentionally stops short of reproducing the complete feature catalogue and every converter invariant. Start with:

- [Text-Fabric feature reference](docs/features/0_home.md) for serialized node/edge contracts;
- [source identity and anomaly policy](docs/source-identity-and-anomalies.md) for fail-closed source handling;
- [conversion report publication and rollback](docs/conversion-report-transaction.md) for recoverable TF/report consistency after disk/report failures;
- [apparatus helper contracts](docs/apparatus.md) for semantic/selective-load requirements;
- [pinned comparison HTTP benchmark](docs/comparison-performance-benchmark.md) for reproducible latency/RSS observations without a claimed speedup;
- [data licensing and attribution](DATA_LICENSE.md) for corpus/software license boundaries;
- tests under `tests/` for executable graph, audit, release-loading, and public-API contracts.

The repository-authored converter/package code is MIT-licensed. The supported OCP text/edition source boundary is CC BY 4.0 under OCP's license clarification; OCP asks researchers to attribute the project and the individual editor of the edition being used. Per-work citation/copyright metadata is preserved in the corpus where supplied upstream.
