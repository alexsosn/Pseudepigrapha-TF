# Issue #75 — historical OCP genre and biblical-figure classifications

## Research gate

### Historical source

The recoverable published OCP database snapshot is at upstream commit
`d722fb62a48782ced67c678dc111cfb1b391cc89`, dated
`2017-10-30T20:32:12-04:00`.

The consulted SQLite object is `databases/storage.sqlite`:

- Git blob: `17b6931b5c2c37289e23d28c598d4bd0b4950075`
- SHA-256: `85f039815cb0b814dc896654115c0de59cdeb7492d94064051cf7e23e0712283`

The extraction queried the database read-only and only these public columns:

- `docs(id, name, filename, genres, figures)`
- `genres(id, genre)`
- `biblical_figures(id, figure)`

No `auth_*`, user/email, draft, or unrelated application rows were queried or copied. The database itself is not committed or distributed here. `public-source-extract.json` contains only the public classification rows required for reproducibility.

### Public-use evidence

At the same historical commit, `models/grammateus.py` defines `docs.genres` as `list:reference genres` and `docs.figures` as `list:reference biblical_figures`. `controllers/default.py:index()` resolves those references and constructs `genrerows` and `figurerows`. `views/default/index.html` publishes two document catalogues headed **Alphabetical by Genre** and **Alphabetical by Biblical Figure**. The classifications were therefore public OCP catalogue semantics, not unused schema.

### Historical inventory

The public snapshot contains:

- 32 published document rows;
- 32 documents with at least one genre;
- 22 documents with at least one biblical-figure assignment;
- 39 genre assignments;
- 25 biblical-figure assignments;
- 11 distinct genre labels;
- 17 distinct biblical-figure labels.

There are no duplicate vocabulary labels, empty labels, duplicate document filenames, dangling vocabulary references, or unsupported list-reference encodings after accounting for Web2Py/PyDAL's `'||'` representation of an empty `list:reference` value.

The exact genre labels are:

1. `apocalypses and visionary texts`
2. `psalms and hymns`
3. `testaments`
4. `parabiblical works (re-written Bible)`
5. `lives and biographies`
6. `histories and history-like narratives`
7. `drama`
8. `uncertain genre`
9. `philosophical and theological discourses`
10. `epic poetry`
11. `prophecy`

The exact biblical-figure labels are: `Adam`, `Eve`, `Baruch`, `Enoch`, `Solomon`, `Moses`, `Rechabites`, `Jacob`, `Job`, `Joseph`, `Sibyl`, `Prophets`, `Ezra`, `Abraham`, `Jeremiah`, `Ezekiel`, `Amram`.

Representative multi-valued records include:

- `Mois`: three genres (`apocalypses and visionary texts`, `parabiblical works (re-written Bible)`, `testaments`) and figure `Moses`;
- `AdamEve`: two genres (`lives and biographies`, `parabiblical works (re-written Bible)`) and figures `Adam`, `Eve`;
- `Artap`: two genres and figures `Abraham`, `Moses`;
- `4Bar`: two genres and figures `Baruch`, `Jeremiah`.

### Identity mapping

Historical `docs.filename` stores the bare OCP work identifier, e.g. `TJob`, while current source paths use `<work>.xml`. All 32 historical work IDs match current XML stems exactly; no historical row is stale or unmappable.

Seven current XML works have no 2017 historical row and must remain unclassified rather than inferred:

- `2Bar-Syr.xml`
- `Esdl.xml`
- `Esdr.xml`
- `JosAsen.xml`
- `Jubi.xml`
- `TAbA.xml`
- `TAbB.xml`

The 32 historical work IDs also equal exactly the 32 work IDs exported in current `static/docs/intros.json`. Consequently every historical classification can be owned by the existing `document_metadata` node introduced by #73, including metadata-only `3Macc`.

### Current-upstream check

Current upstream commit checked: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.

The legacy model/controller still contains the genre/figure fields and catalogue logic, but the static exporter `scripts/export_intros.py` does not export either `genres` or `figures`, and no newer authoritative static classification export was found. The imported layer must therefore be described explicitly as a historical 2017 OCP catalogue snapshot, not as a newly curated 2026 taxonomy.

## Plan gate

### Source artifact

Create a minimal packaged JSON fixture derived mechanically from the public-only extraction. It will contain only:

- exact historical source repository/commit/date/database blob/SHA provenance;
- vocabulary IDs and exact labels;
- per-document historical OCP document ID, work ID, ordered genre IDs, and ordered biblical-figure IDs.

Do not package `storage.sqlite`, raw HTML/editor fields, auth data, draft data, email/user data, or unrelated database rows. Keep `research/issue-75/public-source-extract.json` as independent extraction evidence used by tests/audit, not as runtime input.

### TF representation

Reuse one existing `document_metadata` node per classified work. Do not create vocabulary nodes: Text-Fabric non-slot vocabulary nodes would require artificial `oslots` and would add containment semantics unrelated to the historical catalogue.

Attach these features only to `document_metadata` nodes:

- `historical_ocp_doc_id` — historical `docs.id`;
- `historical_genres_json` — JSON array of exact historical genre labels in source order;
- `historical_biblical_figures_json` — JSON array of exact historical biblical-figure labels in source order.

The vocabulary IDs remain preserved in the packaged source fixture and parity audit; labels are the researcher-facing TF values because they are the public semantics rendered by the historical catalogue. JSON arrays preserve multiplicity/order and avoid delimiter ambiguity.

Seven newer/current works with no historical row receive no classification value. No taxonomy normalization, synonym merging, title-based guessing, inheritance, or cross-work inference is allowed.

### Validation and mapping

The runtime loader must validate before attachment:

- exact schema and source provenance fields;
- unique vocabulary IDs and labels;
- unique historical document IDs and work IDs;
- every assignment ID resolves to the declared vocabulary;
- no empty labels;
- every classified work maps to exactly one `document_metadata` node by `ocp_book` identity;
- no duplicate attachment;
- source work IDs are not silently dropped.

Unknown/dangling/duplicate/ambiguous mappings raise `ValueError`.

### Researcher API

Add `HistoricalClassifications(api)` with selective-load required features and convenient exact-label queries:

- `for_work('Mois')` → historical document ID, genres, biblical figures;
- `works_by_genre('testaments')` → exact work IDs;
- `works_by_figure('Moses')` → exact work IDs;
- `genres()` and `figures()` → exact controlled labels represented in the attached corpus.

Unknown query labels return an empty tuple; unknown work lookup follows normal mapping-style `get`/`__getitem__` semantics. The API must not imply that unclassified newer works were historically categorized.

### Provenance

Generated TF generic metadata will expose machine-readable historical classification provenance including:

- source repository;
- exact historical commit;
- historical commit date;
- historical SQLite blob and SHA-256;
- packaged fixture SHA-256;
- explicit status such as `historical OCP catalogue snapshot (2017)`.

Conversion-report diagnostics will expose vocabulary/assignment counts and the same provenance.

### Independent parity audit

Conversion-time audit will reread the packaged raw fixture independently of the typed loader and compare all represented labels/assignments/provenance to the graph. Tests and pinned integration will additionally compare generated/reloaded TF against `research/issue-75/public-source-extract.json`, which was produced directly from the historical SQLite in an isolated read-only extraction. This keeps extraction evidence independent from runtime model construction.

Acceptance counts for the exact historical fixture:

- 32 classified works;
- 39 genre assignments;
- 25 biblical-figure assignments;
- 11 genre labels;
- 17 biblical-figure labels.

### TDD / test gate

Before implementation add RED tests proving current code cannot provide the layer. Cover at minimum:

- TJob single genre + single figure;
- Mois multi-genre assignment;
- AdamEve multi-figure assignment;
- exact punctuation for `parabiblical works (re-written Bible)`;
- 3Macc classification on metadata-only work;
- seven newer/current works remain unclassified;
- deterministic mapping by `ocp_book` identity;
- duplicate work/vocabulary IDs and labels rejected;
- dangling IDs rejected;
- full fixture counts 32/39/25/11/17;
- real TF save/reload exact preservation;
- reverse query ergonomics;
- independent audit detects graph tampering/provenance tampering.

After GREEN unit tests, run exact current OCP pinned conversion, semantic parity, TF reload, full historical extraction parity, and existing apparatus regressions. Remove all temporary research/TDD workflows before PR.

### Independent review gate

A logically independent reviewer must inspect the exact green PR head against:

- historical schema/controller/view at `d722fb62...`;
- the public-only extracted source inventory;
- current upstream `c939dcb...`;
- the packaged fixture and generated TF.

It must challenge private-data leakage, historical/current provenance wording, stale mappings, taxonomy mutation, assignment-count parity, handling of the seven unclassified newer works, 3Macc ownership, and query ergonomics. Any blocker becomes a regression test/correction followed by all gates and another exact-head independent review.
