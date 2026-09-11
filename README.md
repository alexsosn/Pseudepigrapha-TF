# Pseudepigrapha-TF

Pseudepigrapha-TF is a published [Text-Fabric](https://annotation.github.io/text-fabric/tf/) corpus derived from the [Online Critical Pseudepigrapha (OCP)](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha), plus a small Python package for apparatus, translation, metadata, and local comparison workflows.

The normal researcher path is to **load the published corpus directly**. You do not need to clone OCP or run the converter. Rebuilding from OCP is a maintainer/custom-snapshot workflow documented later in this README.

Python 3.10+ and Text-Fabric 13.1.x are supported.

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

The public `v0.2.0` release contains the derived Text-Fabric corpus (`complete.zip` for stock Text-Fabric acquisition and `tf-0.2.zip` as a native feature archive), its conversion report, and its dataset manifest. The upstream OCP XML remains in the OCP repository. See [data licensing and attribution](DATA_LICENSE.md) for the exact source/license boundary.

## Get and load the published corpus

The shortest supported path uses Text-Fabric's normal GitHub-release acquisition. For corpus access alone:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install "text-fabric[github]>=13.1,<14"
```

Then load the published release:

```python
from tf.app import use

app = use(
    "alexsosn/Pseudepigrapha-TF:v0.2.0",
    checkout="v0.2.0",
    silent="deep",
)
api = app.api
```

The first call obtains the release's stock Text-Fabric `complete.zip` and populates the Text-Fabric cache. After that acquisition, an offline/local reload is:

```python
from tf.app import use

app = use(
    "alexsosn/Pseudepigrapha-TF:local",
    checkout="local",
    silent="deep",
)
api = app.api
```

Both the fresh tagged acquisition and a network-blocked `checkout="local"` reload are exercised by the repository's published-release verification workflow.

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
app.load(
    "ocp_book version_id version_title version_kind language author "
    "reading_text is_primary ms_abbrev ms_language ms_name ms_show "
    "unit_id source_ref undefined_manuscript synthetic_witness "
    "reading_of witness manuscript_of"
)

from pseudepigrapha_tf import Apparatus

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

Load the additional generated-translation features and query them separately from historical apparatus:

```python
app.load(
    "generated_language generation_marker generation_method generation_model "
    "unit_index translation_of translation_unit_of"
)

from pseudepigrapha_tf import Translations

T = Translations(app.api)
french = T.versions(work="1En", language="French")
generated_book = french[0]["node"]

aligned = T.aligned_units(generated_book)
aligned[0]["source_text"]
aligned[0]["translation_text"]
```

`Translations.aligned_units()` uses the explicit graph alignment rather than positional zipping or bare verse labels. This matters for repeated source citations such as the two Syriac `4Ezra 10:4` occurrences.

The synthetic `OCP-Trans` witness remains provenance for the generated layer but is excluded from historical manuscript/apparatus semantics. A genuine scholarly English source version, such as pinned `4Q548`, is therefore not reclassified merely because it is English.

## Browse and compare

The published corpus works with the standard Text-Fabric advanced app loaded by `tf.app.use()` above. Pseudepigrapha-TF also provides a local `/compare` view for passage-centered comparison across source versions, manuscripts, and generated translations.

The comparison server takes a **local materialized TF feature directory**; it does not run the OCP converter. One reproducible layout is to extract the published native archive and use the tracked app from this repository:

```bash
curl -L \
  -o /tmp/tf-0.2.zip \
  https://github.com/alexsosn/Pseudepigrapha-TF/releases/download/v0.2.0/tf-0.2.zip

mkdir -p /tmp/pseudepigrapha-tf/0.2
python -m zipfile -e /tmp/tf-0.2.zip /tmp/pseudepigrapha-tf/0.2

git clone --depth 1 https://github.com/alexsosn/Pseudepigrapha-TF.git
cd Pseudepigrapha-TF
python -m pip install .
pseudepigrapha-tf browse /tmp/pseudepigrapha-tf/0.2 --app app
```

Open `http://127.0.0.1:8000/compare`. The stock Text-Fabric browser remains available at `/`; the comparison route is an addition, not a replacement server.

The real pinned-corpus acceptance gate exercises, among other cases:

- 1 Enoch with multiple source versions and distinguishable witness omission/unattested states;
- TJob with a metadata-only Coptic version and a large witness inventory;
- generated English/French translations nested under their exact source version;
- duplicate Syriac `4Ezra 10:4` occurrences as separate TF sections;
- readable fail-closed behavior where OCP source evidence is genuinely ambiguous.

## Resource expectations

Resource measurements are reference measurements from GitHub-hosted Ubuntu runners, **not hardware requirements**.

For the currently published `v0.2.0` corpus, the stock `complete.zip` is about **9.36 MiB**, the populated stock Text-Fabric cache measured about **216.6 MiB**, and a warm full-app load measured about **1.69 GiB peak RSS**.

Current post-#141 corpus output intended for the next publication is smaller: about **9.20 MiB** compressed, **145.4 MiB** in the populated stock cache, about **1.34 GiB peak RSS** for a warm full-app load, and about **1023 MiB peak RSS** for the measured translation-oriented selective load. Text-Fabric retained no ZIP archive in the populated cache in either measurement.

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
tjob["citation"]
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

Rebuilding is for maintainers, reproducibility work, or researchers intentionally converting another OCP snapshot. It is **not required to use the published corpus**.

For the release-pinned source used by the full integration gate:

```bash
git clone https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha.git
git -C Online-Critical-Pseudepigrapha checkout c939dcbacad78c5d18d2c4282cad23c47e19ac07

pseudepigrapha-tf convert \
  Online-Critical-Pseudepigrapha/static/docs \
  --output tf/0.2
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

The full CI additionally converts/audits the pinned OCP corpus and reloads it through real Text-Fabric, including stock `complete.zip`, advanced-app, apparatus, translation, metadata, classification, and comparison acceptance.

### Contributor and implementation reference

The README intentionally stops short of reproducing the complete feature catalogue and every converter invariant. Start with:

- [Text-Fabric feature reference](docs/features/0_home.md) for serialized node/edge contracts;
- [source identity and anomaly policy](docs/source-identity-and-anomalies.md) for fail-closed source handling;
- [apparatus helper contracts](docs/apparatus.md) for semantic/selective-load requirements;
- [data licensing and attribution](DATA_LICENSE.md) for corpus/software license boundaries;
- tests under `tests/` for executable graph, audit, release-loading, and public-API contracts.

The repository-authored converter/package code is MIT-licensed. The supported OCP text/edition source boundary is CC BY 4.0 under OCP's license clarification; OCP asks researchers to attribute the project and the individual editor of the edition being used. Per-work citation/copyright metadata is preserved in the corpus where supplied upstream.
