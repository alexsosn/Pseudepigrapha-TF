# Pseudepigrapha-TF

A tested converter from the [Online Critical Pseudepigrapha](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha) Grammateus XML files to [Text-Fabric](https://annotation.github.io/text-fabric/), with a BHSA-compatible warp layer and an apparatus-preserving graph model.

The repository currently ships the converter, tests, and documentation. It does **not** include OCP XML or generated corpus data.

## Install

Python 3.10+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Convert OCP

Clone OCP separately and point the converter at its `static/docs` directory:

```bash
git clone https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha.git
pseudepigrapha-tf convert \
  Online-Critical-Pseudepigrapha/static/docs \
  --output tf/0.1
```

Zero-byte XML files are reported and skipped. A malformed non-empty source is treated as an error.

## Data model

The main Text-Fabric shape follows BHSA where OCP semantics permit it:

| Role | Representation |
| --- | --- |
| slots | `word` |
| standard sections | `book`, `chapter`, `verse` |
| Unicode surface | `g_word_utf8` + `trailer_utf8` |
| source hierarchy | `div` nodes, with literal labels/numbers and `parent` edges |
| textual locus | `unit` node |
| apparatus alternative | `reading` node |
| alternative-reading token | `variant_word` node |
| witness | `manuscript` node; `witness` edge from reading |
| OCP `<w>` annotation | `lex`, `morph`, `style`, `language` features |

The primary slot stream is OCP `reading option="0"`, matching the current OCP reader's default-selection rule. If option 0 is missing, the converter uses the first reading and emits a warning. Empty primary readings receive a surface-less `is_gap=1` anchor slot so apparatus nodes still have a valid locus.

OCP section identifiers remain strings because real files contain values such as `4b`, `heading`, and `Heading`. `chapter_index` and `verse_index` provide numeric document-order ordinals. All original source divisions are preserved even when there are more than two levels.

For files containing multiple OCP versions, each version becomes a distinct TF `book` address (for example `TAdam__Syriac` and `TAdam__Greek`) while `ocp_book` retains the original OCP filename.

See [research.md](research.md) for the source audit and design rationale, and [plan.md](plan.md) for the TDD/acceptance plan.

## Test

```bash
pytest
```

The unit suite uses synthetic fixtures. GitHub Actions additionally converts a pinned complete OCP checkout and reloads the generated dataset with Text-Fabric.

## Licensing

The converter code is MIT-licensed. OCP source editions have their own rights/provenance situation; this repository intentionally does not redistribute the XML or generated TF corpus. See `research.md` for the current distribution boundary.
