# Pseudepigrapha-TF

A tested converter from the [Online Critical Pseudepigrapha](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha) Grammateus XML files to [Text-Fabric](https://annotation.github.io/text-fabric/), with a BHSA-compatible word/section interface and an apparatus-preserving graph model.

The repository ships the converter, tests, and documentation. It does **not** include OCP XML or generated corpus data.

## Install

Python 3.10+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Convert OCP

For a reproducible conversion, clone OCP and check out the revision used by CI:

```bash
git clone https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha.git
git -C Online-Critical-Pseudepigrapha checkout 2d1d14d23434a784d377ff7f4409ccdb2d18aafb
pseudepigrapha-tf convert \
  Online-Critical-Pseudepigrapha/static/docs \
  --output tf/0.1
```

The converter auto-detects the source Git commit and records it in TF metadata. `--upstream-commit` can override this for a nonstandard checkout. Zero-byte XML files are reported and skipped; malformed non-empty XML fails loudly.

Every successful conversion also writes `conversion-report.json` beside the `.tf` features. The conversion fails if the independent raw-XML parity audit detects a semantic mismatch.

## Data model

The main Text-Fabric shape follows BHSA where OCP semantics permit it:

| Role | Representation |
| --- | --- |
| slots | `word` |
| standard sections | `book`, `chapter`, `verse` |
| primary Unicode display | `prefix_utf8` + `g_word_utf8` + `trailer_utf8` + `boundary_utf8` |
| exact source citation | `source_ref` plus JSON `source_ref_parts` |
| source hierarchy | `div` nodes, literal labels/numbers, `parent` edges |
| textual locus | `unit` node, explicitly parented to its source `div` |
| apparatus alternative | `reading` node |
| alternative-reading token | `variant_word` node |
| witness | `manuscript` node; `witness` edge from reading |
| upstream version with no textual units | `version_metadata` node; never a fabricated TF `book` section |
| OCP `<w>` annotation | `lex`, `morph`, `style`, effective `language`, literal `w_lang` |

The primary slot stream is OCP `reading option="0"`, matching OCP's default-selection rule. If option 0 is absent, the converter uses the first reading and emits a warning. Empty primary readings receive a surface-less `is_gap=1` anchor slot so apparatus nodes still have a valid locus.

OCP can also declare a version whose metadata exists but whose text has not yet been included. The pinned corpus does this for `TJob/Coptic`. Such a version is preserved as `version_metadata` with its version/manuscript/resource metadata, but contributes no `book/chapter/verse` section and no invented text.

### Sections and deep references

Text-Fabric supports the standard three-level section API, while OCP may have deeper references. For one source level, the converter synthesizes chapter `1`. For two levels, source parent/terminal values map directly to chapter/verse. For three or more levels, **all parent components are folded into the TF chapter and the terminal component becomes the verse**.

For example:

```text
OCP source ref: 1:23:153:4
TF address:     <book> / 1:23:153 / 4
```

The full citation remains directly available as `source_ref="1:23:153:4"` on the source `div`, `unit`, `reading`, primary words, and variant words. Researchers do not have to reconstruct the citation by walking generic nodes.

### Apparatus text semantics

Alternative readings occupy the primary locus for graph/search purposes, but `T.text(reading)` must not therefore print the primary reading. The corpus defines node-type default formats:

```text
reading-default          -> reading_text
variant_word-default     -> the variant token itself
manuscript-default       -> manuscript abbreviation
resource-default         -> resource name
version_metadata-default -> version title
```

This makes standard `T.text()` calls unsurprising. Text-Fabric 13.1 requires every non-slot node to serialize with an `oslots` anchor, so manuscripts, resources, metadata-only versions, and variant tokens use a **single O(1) technical anchor** rather than a fabricated textual span. Their node-type formats prevent that anchor from being rendered as their text.

For routine apparatus work, the package also provides helpers:

```python
from pseudepigrapha_tf import Apparatus

A = Apparatus(api)
A.unit_readings(unit)
A.reading_text(reading)
A.reading_tokens(reading)
A.witness_reading(unit, manuscript)
A.witness_state(unit, manuscript)
A.witness_text(manuscript)
A.apparatus(unit)
A.passage("1En", "1", "2")
A.work_passage("1En", "1", "2")
```

### Passage-level apparatus

`Apparatus.passage(book, chapter, verse)` is the high-level interface for retrieving a verse together with all of its critical evidence from one textual OCP version. For example:

```python
passage = A.passage("1En", "1", "2")

passage["units"]
passage["witnesses"]["p"]["text"]
passage["witnesses"]["Bertalotto"]["segments"]
```

The result contains every apparatus `unit` in the verse, every reading at each unit, and every manuscript declared for the containing OCP version. Per-witness `segments` explicitly distinguish:

- `reading`: the witness is assigned to a non-empty reading;
- `omission`: the witness is explicitly assigned to an empty OCP reading;
- `unattested`: no reading at that unit cites the witness.

A witness-level `text` is returned only when the witness is represented at every unit in the verse (explicit omissions count as represented). If one or more units are `unattested`, `text` is `None`; `attested_text` still gives the concatenation of the readings that are actually present. This prevents missing evidence from being silently turned into either an omission or a continuous reconstructed text.

The API does not infer `lacuna` or `fragment` merely from absence. If OCP encodes such information only in the reading content rather than as a structural flag, that source wording remains available in the reading instead of being reclassified by the converter.

### Work-level retrieval across all versions

`Apparatus.work_passage(work, chapter, verse)` is the work-level interface for the common research query “give me this passage in every OCP version and witness”. It discovers all textual versions through the preserved `ocp_book` identity and then applies the same passage/apparatus logic to each one.

For a multi-version work:

```python
result = A.work_passage("Multi", "1", "1")

result["versions"]["Multi__Syriac"]["passage"]
result["versions"]["Multi__Greek"]["passage"]
```

Textual versions are keyed by their stable TF book/version id rather than by human-readable title, so duplicate titles cannot overwrite one another. Each version record includes its title, language, author, declared witnesses, status, and passage result.

The status is explicit:

- `available`: that textual version contains the requested TF section;
- `not_present`: the textual version exists, but that requested section does not;
- `metadata_only`: the upstream version is declared by OCP but contains no textual units at all.

Metadata-only versions are returned separately under `metadata_only_versions` with their declared witness metadata and `passage=None`. Thus a fragmentary or not-yet-transcribed version never disappears from the work-level result and is never converted into a fake empty passage.

For example, on the pinned corpus a `TJob` query still exposes the Coptic version metadata even though OCP has `<text></text>` for that version:

```python
result = A.work_passage("TJob", "1", "1")
result["metadata_only_versions"]["TJob__Coptic"]
```

For `1En`, which has one top-level OCP textual version whose Greek, Latin, Aramaic, and Ethiopic evidence is represented primarily through the witness apparatus, the same work-level call remains useful:

```python
result = A.work_passage("1En", "1", "2")
result["versions"]["1En"]["passage"]["witnesses"]
```

When loading only selected TF features, `work_passage()` requires at least `ocp_book` plus the features/edges needed by `passage()` (`reading_text`, `ms_abbrev`, `unit_id`, `reading_of`, `variant_word_of`, `witness`, `manuscript_of`). Load `title`, `version_title`, `language`, `author`, `ms_language`, `ms_name`, and `ms_show` as well if those metadata fields are desired in the returned records.

## Preservation audit

`conversion-report.json` is built by rereading the raw XML independently of the converter's parsed model and comparing it with the generated TF graph. It checks:

- source file SHA-256s and every declared version, including metadata-only versions;
- division declarations and every structural division/reference;
- unit attributes and explicit unit→div parent linkage;
- every reading's option, witnesses, flags, normalized text, and mixed XML;
- manuscript metadata and bibliography;
- resources;
- every annotated `<w>` and its attributes;
- primary and alternative token reconstruction;
- complete and unique `book/chapter/verse` coverage for the textual slot stream;
- graph size including `oslots` edge count.

The report says `status: "ok"` only when every semantic check passes. Section coverage is computed in linear time so the audit itself does not reintroduce the dense-scaling problem eliminated from the graph.

## Test

```bash
pytest
```

The synthetic suite covers parser, graph, apparatus helpers, passage-level witness coverage, work-level multi-version retrieval, semantic parity, legacy OCP, deep/non-numeric references, omissions, metadata-only versions, and reproducible paths. CI additionally installs real Text-Fabric, verifies node-type `T.text()` behavior and deep `T.sectionFromNode()` addresses, converts the pinned complete OCP checkout, validates the parity report, reloads the full dataset, exercises `Apparatus.passage("1En", "1", "2")`, exercises `Apparatus.work_passage("1En", "1", "2")`, and verifies that real `TJob/Coptic` remains visible as metadata-only evidence.

## Licensing

The converter code is MIT-licensed. OCP source editions have their own rights/provenance situation; this repository intentionally does not redistribute the XML or generated TF corpus. See `research.md` for the current distribution boundary.
