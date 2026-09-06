# Pseudepigrapha-TF

Convert the Online Critical Pseudepigrapha XML corpus to Text-Fabric while preserving source structure, readings, witnesses, resource metadata, public document metadata, and explicit provenance.

The generated TF corpus is a transformation of the supplied OCP source checkout; this repository does not redistribute the upstream XML corpus.

## Install

```bash
pip install -e .
```

For development/tests:

```bash
pip install -e '.[dev]'
```

## Convert

```bash
pseudepigrapha-tf convert /path/to/Online-Critical-Pseudepigrapha/static/docs \
  --output tf/0.1
```

The converter processes direct `*.xml` files in the supplied OCP `static/docs` directory, skips zero-byte XML with an explicit warning, preserves the exact upstream commit when detectable (or when supplied with `--upstream-commit`), runs an independent semantic audit before publication, writes the TF dataset transactionally, and emits `conversion-report.json` beside the generated corpus by default.

The supported/pinned integration source is currently:

```text
https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha
c939dcbacad78c5d18d2c4282cad23c47e19ac07
```

At that source snapshot generated OCP English/French translation versions are deliberately excluded from ordinary critical/source-version semantics pending an explicit provenance-aware translation layer. The original-language/source editions and their source corrections remain in the corpus.

## Text-Fabric model

Word nodes are TF slots. Non-slot nodes include the source textual hierarchy and metadata structures such as:

- `book`, `chapter`, `verse` section nodes;
- source divisions and units;
- readings and manuscript declarations;
- version/resource/manuscript metadata;
- `document_metadata` work records from public `intros.json`.

The conversion retains source identifiers, source references, relevant XML attributes/fragments, witness declarations, primary/alternative readings, omissions, anomaly markers, and ownership/containment edges. `conversion-report.json` independently compares the source inventory with the generated graph and fails conversion when required parity checks do not hold.

For textual-critical access, use `Apparatus`:

```python
from tf.fabric import Fabric
from pseudepigrapha_tf import Apparatus

TF = Fabric(locations=['tf/0.1'], modules=[''], silent='deep')
api = TF.load('reading_text ms_abbrev ms_language ms_name ms_show undefined_manuscript resource_name source_ref is_primary unit_id is_missing_unit_id is_source_anomaly version_title version_id is_metadata_only ocp_book title language author reading_of witness manuscript_of', silent='deep')
A = Apparatus(api)

A.passage('1En__Ethiopic', '1', '2')
A.work_passage('1En', '1', '2')
```

`Apparatus.work_passage()` distinguishes textual versions from metadata-only evidence and keeps generated OCP translations out of the ordinary witness/version view.

## Semantic parity

Conversion writes `conversion-report.json`. The report records source and graph counts, semantic checks, diagnostics, and exact upstream provenance. A non-`ok` report aborts publication.

The audit covers, among other things:

- source files, versions, units, readings, words, manuscripts, resources, and references;
- node/edge ownership and section reconstruction;
- source anomalies such as a real missing unit id;
- duplicate section addresses without source-reference loss;
- metadata-only versions;
- explicit exclusions of generated translation versions;
- public `intros.json` document/value/provenance parity.

The report says `status: "ok"` only when every semantic check passes. Section coverage, ownership, source-structure validation, and special-anomaly scans are linear in their respective node/element/edge counts so the audit itself does not reintroduce the dense-scaling problem eliminated from the graph.

## Test

```bash
pytest
```

The synthetic suite covers parser, graph, apparatus helpers, reading-token semantics on real Text-Fabric, passage-level witness coverage and declaration provenance, work-level multi-version retrieval, semantic parity, ownership-edge corruption, explicit source-structure and required-attribute drift rejection, ambiguous duplicate non-empty witness declarations at XML/raw-audit/direct-model boundaries plus abbreviation-less controls, preserved ellipsis/direct-reading anomalies and their corruption detection, legacy OCP, deep/non-numeric and duplicate references, omissions, empty source divisions, metadata-only versions, reproducible paths, public-document metadata serialization, and historical catalogue classification parity. CI additionally installs real Text-Fabric, verifies node-type `T.text()` behavior and deep/duplicate `T.sectionFromNode()`/`T.nodeFromSection()` addresses, converts and audits the pinned complete OCP checkout, reloads the full dataset, exercises `Apparatus`, verifies the complete public `intros.json` layer, and checks the historical OCP catalogue classifications against their public-only extraction inventory.

## Licensing

The converter code is MIT-licensed. OCP source editions have their own rights/provenance situation; this repository intentionally does not redistribute the XML or generated TF corpus. See `research.md` for the current distribution boundary.

## Public document metadata (`intros.json`)

When the supplied OCP `static/docs` directory contains the committed public `intros.json` export, conversion includes it automatically. Records are matched to works by the exact root-level XML filename, never by display title; duplicate JSON object keys are rejected rather than accepted with last-write-wins semantics. This matters because OCP metadata titles are not guaranteed to equal XML titles. A public record whose XML file is empty, such as pinned `3Macc.xml`, is still preserved as a `document_metadata` node; its single `oslots` value is only a Text-Fabric technical anchor and does not create a `book`, chapter, verse, or word.

Each public document gets one `document_metadata` node. `title`, edition `version`, per-work `citation`, and the public body fields `introduction`, `provenance`, `themes`, `status`, `manuscripts`, `bibliography`, `corrections`, `sigla`, and `copyright` are stored only on that node. The TF feature names are `intro_title_json`, `intro_version_json`, `intro_citation_json`, and `intro_<field>_json`. Values use reversible JSON-scalar encoding because raw multi-line HTML is not lossless through Text-Fabric's line-oriented feature serialization. The encoding preserves HTML, CRLF/newline characters, entities, Unicode, and the distinction between a missing key, an empty string, and JSON `null`.

Researchers normally should not decode those features manually. Load the metadata feature set and use `WorkMetadata`:

```python
from tf.fabric import Fabric
from pseudepigrapha_tf import WorkMetadata

TF = Fabric(locations=['tf/0.1'], modules=[''], silent='deep')
api = TF.load(' '.join(WorkMetadata.REQUIRED_FEATURES), silent='deep')
M = WorkMetadata(api)

tjob = M['TJob']
tjob['fields']['provenance']
tjob['fields']['manuscripts']
tjob['fields']['bibliography']
tjob['citation']
M['TAdam']['fields']['introduction']
M['3Macc']
```

Dataset-level TF metadata records `introsSource`, `introsSha256`, and the export date when supplied upstream. `conversion-report.json` independently rereads raw `intros.json` and checks document coverage, scalar values, and provenance against the graph, so corrupt or dropped metadata fails the same semantic parity gate as XML conversion.

## Historical OCP genre and biblical-figure catalogue

OCP's recoverable **2017 public catalogue** classified documents by genre and by associated biblical figure. These labels came from the historical Web2Py database and were publicly rendered under “Alphabetical by Genre” and “Alphabetical by Biblical Figure”. Current `intros.json` does not export them, so Pseudepigrapha-TF preserves a minimal public-only extraction with explicit historical provenance. It is **not** presented as a newly curated or current 2026 taxonomy.

The snapshot contains 32 classified works, 39 genre assignments, 25 biblical-figure assignments, 11 exact genre labels, and 17 exact figure labels. Seven current works added outside that historical catalogue (`2Bar-Syr`, `Esdl`, `Esdr`, `JosAsen`, `Jubi`, `TAbA`, `TAbB`) remain unclassified; no categories are inferred for them.

Classifications live only on the existing work-level `document_metadata` nodes as `historical_ocp_doc_id`, `historical_genres_json`, and `historical_biblical_figures_json`. Use the query helper instead of decoding JSON features manually:

```python
from tf.fabric import Fabric
from pseudepigrapha_tf import HistoricalClassifications

TF = Fabric(locations=['tf/0.1'], modules=[''], silent='deep')
api = TF.load(' '.join(HistoricalClassifications.REQUIRED_FEATURES), silent='deep')
C = HistoricalClassifications(api)

C['Mois']
# {'historical_doc_id': 11,
#  'genres': ('apocalypses and visionary texts',
#             'parabiblical works (re-written Bible)',
#             'testaments'),
#  'biblical_figures': ('Moses',)}

C.works_by_genre('testaments')
C.works_by_figure('Moses')
C.genres()
C.figures()
C.get('TAbA')  # None: no historical classification is invented
```

The runtime fixture contains only public vocabulary IDs/labels, public document IDs/work IDs, assignments, and source provenance. It contains no historical auth/user/email/draft/application rows and does not distribute `storage.sqlite`. Generated TF metadata records the historical upstream repository, exact commit/date, SQLite blob/SHA-256, fixture SHA-256, and the status `historical OCP catalogue snapshot (2017)`. The conversion report independently compares the raw fixture with the graph; CI additionally compares the fixture against the separately extracted public rows documented in `research/issue-75/`.
