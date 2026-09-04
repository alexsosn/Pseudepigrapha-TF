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
| witness | `manuscript` node; `witness` edge from reading; citation-only witnesses have `undefined_manuscript=1` |
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

Pinned OCP also contains a few **exact duplicate source citations**: for example `4Ezra/Syriac 10:4`, `Jub/Greek 10:21`, and `SibOr/Greek 3:261`/`3:262` each occur twice in the source structure. The converter does not guess whether these are editorial typos, fragments, or another upstream convention, and it does not merge the corresponding source divisions. The first occurrence keeps the ordinary TF verse label; later occurrences receive only a deterministic technical suffix (`4~2`, `21~2`, and so on) and a `section_occurrence` feature. Their exact `source_ref` remains unchanged, so `4Ezra__Syriac / 10 / 4` and `4Ezra__Syriac / 10 / 4~2` are separately addressable TF sections whose `source_ref` is `10:4` in both cases. The `~N` suffix is therefore an interface disambiguator, **not an editorial correction to OCP numbering**.

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
A.passage("1En__Ethiopic", "1", "2")
A.work_passage("1En", "1", "2")
```

### Passage-level apparatus

`Apparatus.passage(book, chapter, verse)` is the high-level interface for retrieving a verse together with all of its critical evidence from **one textual OCP version**. When an OCP work contains several top-level `<version>` elements, `book` is that version's stable TF section id, for example:

```python
passage = A.passage("1En__Ethiopic", "1", "2")

passage["units"]
passage["witnesses"]["p"]["text"]
passage["witnesses"]["Bertalotto"]["segments"]
```

The result contains every apparatus `unit` in the verse, every reading at each unit, and every witness linked to the containing OCP version. This includes abbreviations that occur in reading citations even when OCP did not declare a corresponding `<ms>` entry: the converter preserves them as citation-only manuscript nodes instead of dropping the evidence. Every witness record has a boolean `declared` field: `True` for an upstream-declared manuscript and `False` for a citation-only synthesized witness. Per-witness `segments` explicitly distinguish:

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

Textual versions are keyed by their stable TF book/version id rather than by human-readable title, so duplicate titles cannot overwrite one another. Each version record includes its title, language, author, all linked witnesses with their `declared` provenance, status, and passage result.

The status is explicit:

- `available`: that textual version contains the requested TF section;
- `not_present`: the textual version exists, but that requested section does not;
- `metadata_only`: the upstream version is declared by OCP but contains no textual units at all.

Metadata-only versions are returned separately under `metadata_only_versions` with their witness metadata and `passage=None`. Thus a fragmentary or not-yet-transcribed version never disappears from the work-level result and is never converted into a fake empty passage.

`chapter` and `verse` are the normalized TF section address, applied independently to each textual OCP version. This is deliberately **not** an automatic alignment claim: fragmentary works can use different division schemes in different versions. Exact upstream addresses remain available in each returned passage's `source_refs`, while a version without the requested normalized section is reported as `not_present` instead of being forced into a false correspondence.

For example, on the pinned corpus a `TJob` query still exposes the Coptic version metadata even though OCP has `<text></text>` for that version:

```python
result = A.work_passage("TJob", "1", "1")
result["metadata_only_versions"]["TJob__Coptic"]
```

The pinned `1En.xml` is a particularly useful real-world case: it contains four top-level textual OCP versions — Ethiopic, Qumran Aramaic, Latin Fragments, and Greek. One call exposes all four version records and, where the requested section exists, their complete apparatus:

```python
result = A.work_passage("1En", "1", "2")

result["versions"]["1En__Ethiopic"]["passage"]["witnesses"]
result["versions"]["1En__Qumran_Aramaic"]["status"]
result["versions"]["1En__Latin_Fragments"]["status"]
result["versions"]["1En__Greek"]["status"]
```

When loading only selected TF features, `work_passage()` requires at least `ocp_book` plus the features/edges needed by `passage()` (`reading_text`, `ms_abbrev`, `undefined_manuscript`, `unit_id`, `reading_of`, `witness`, `manuscript_of`). `undefined_manuscript` is always serialized, including as an empty feature when every witness is declared, so this requirement is stable across generated corpora. Load `title`, `version_title`, `language`, `author`, `ms_language`, `ms_name`, and `ms_show` as well if those metadata fields are desired in the returned records. If the loaded corpus contains metadata-only versions, load `version_id` as well so those versions can be keyed unambiguously.

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
- complete and unique `book/chapter/verse` coverage for the textual slot stream, including deterministic disambiguation of repeated exact upstream citations without changing their `source_ref`;
- graph size including `oslots` edge count.

The report says `status: "ok"` only when every semantic check passes. Section coverage is computed in linear time so the audit itself does not reintroduce the dense-scaling problem eliminated from the graph.

## Test

```bash
pytest
```

The synthetic suite covers parser, graph, apparatus helpers, passage-level witness coverage and declaration provenance, work-level multi-version retrieval, semantic parity, legacy OCP, deep/non-numeric and duplicate references, omissions, metadata-only versions, and reproducible paths. CI additionally installs real Text-Fabric, verifies node-type `T.text()` behavior and deep/duplicate `T.sectionFromNode()`/`T.nodeFromSection()` addresses, converts and audits the pinned complete OCP checkout, reloads the full dataset, exercises `Apparatus.passage("1En__Ethiopic", "1", "2")`, verifies witness declaration provenance, verifies that `Apparatus.work_passage("1En", "1", "2")` exposes all four real 1 Enoch versions, and verifies that real `TJob/Coptic` remains visible as metadata-only evidence.

## Licensing

The converter code is MIT-licensed. OCP source editions have their own rights/provenance situation; this repository intentionally does not redistribute the XML or generated TF corpus. See `research.md` for the current distribution boundary.
