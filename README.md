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
| OCP `<w>` annotation | `lex`, `morph`, `style`, effective `language`, literal `w_lang` |

The primary slot stream is OCP `reading option="0"`, matching OCP's default-selection rule. If option 0 is absent, the converter uses the first reading and emits a warning. Empty primary readings receive a surface-less `is_gap=1` anchor slot so apparatus nodes still have a valid locus.

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
reading-default      -> reading_text
variant_word-default -> the variant token itself
manuscript-default   -> manuscript abbreviation
resource-default     -> resource name
```

This makes standard `T.text()` calls unsurprising. Manuscript and resource nodes intentionally have no fictitious textual extent, and each `variant_word` uses only one technical locus anchor rather than copying the entire primary locus.

For routine apparatus work, the package also provides helpers:

```python
from pseudepigrapha_tf.apparatus import Apparatus

A = Apparatus(api)
A.unit_readings(unit)
A.reading_text(reading)
A.reading_tokens(reading)
A.witness_reading(unit, manuscript)
A.witness_text(manuscript)
A.apparatus(unit)
```

## Preservation audit

`conversion-report.json` is built by rereading the raw XML independently of the converter's parsed model and comparing it with the generated TF graph. It checks:

- source file SHA-256s and version metadata;
- division declarations and every structural division/reference;
- unit attributes and explicit unit→div parent linkage;
- every reading's option, witnesses, flags, normalized text, and mixed XML;
- manuscript metadata and bibliography;
- resources;
- every annotated `<w>` and its attributes;
- primary and alternative token reconstruction;
- complete and unique `book/chapter/verse` coverage;
- graph size including `oslots` edge count.

The report says `status: "ok"` only when every semantic check passes.

## Test

```bash
pytest
```

The synthetic suite covers parser, graph, apparatus helpers, semantic parity, legacy OCP, deep/non-numeric references, omissions, and reproducible paths. CI additionally installs real Text-Fabric, verifies node-type `T.text()` behavior and deep `T.sectionFromNode()` addresses, converts the pinned complete OCP checkout, validates the parity report, and reloads the full dataset.

## Licensing

The converter code is MIT-licensed. OCP source editions have their own rights/provenance situation; this repository intentionally does not redistribute the XML or generated TF corpus. See `research.md` for the current distribution boundary.
