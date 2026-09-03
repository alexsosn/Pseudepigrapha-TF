# Research: Online Critical Pseudepigrapha → Text-Fabric

## Scope

This repository converts the XML editions in the Online Critical Pseudepigrapha (OCP) `static/docs` directory into Text-Fabric. The converter is designed against upstream commit `2d1d14d23434a784d377ff7f4409ccdb2d18aafb` (2026-08-27) and keeps the generated warp layer as close to BHSA conventions as the OCP data permits.

The converter repository contains code and synthetic fixtures only. It does not vendor OCP XML or generated Text-Fabric data; redistribution of the source editions should be handled separately from converter licensing.

## Source format

OCP calls the editions TEI XML in current project documentation, but the corpus itself uses a small project-specific Grammateus vocabulary described by `static/docs/grammateus.dtd`:

- `book` contains one or more `version` elements.
- Each `version` declares division labels, optional resources, manuscript metadata, and a text.
- Text is a recursive hierarchy of `div` elements terminating in `unit` elements.
- A `unit` contains one or more alternative `reading` elements.
- A reading records `option`, a space-separated `mss` witness list, optional `linebreak`/`indent`, and mixed text with optional `<w>` annotations.
- `<w>` can carry `morph`, `lex`, `style`, and `lang`.

This is an apparatus-oriented model: `unit` is the textual locus, while readings are mutually exclusive alternatives at that locus.

## Observed edge cases

The converter must follow the files rather than assumptions in the old application validator.

- `3Macc.xml` is currently zero bytes and must be skipped explicitly rather than treated as valid XML.
- `ArisEx.xml` has three division levels (`Book`, `Chapter`, `Line`), starts with `unit id="0"`, and contains a division numbered `heading`.
- Other fragmentary files use labels such as `Heading` and section values such as `4b`, so source section identifiers cannot safely be coerced to integers.
- Some files contain multiple versions/languages under the same OCP `book` (for example Testament of Adam).
- Mixed `<w>` markup appears inside readings and must survive conversion.
- Empty readings are meaningful omissions, not parser errors.
- The current OCP browser chooses `reading option="0"` as the default reading, falling back to the first reading if option 0 is absent. That is the least arbitrary primary stream for a BHSA-shaped Text-Fabric corpus.

## BHSA compatibility target

BHSA uses `word` as its slot type and exposes `book`, `chapter`, and `verse` as the section hierarchy. Its standard Unicode surface display is built from `g_word_utf8` plus `trailer_utf8`. Pseudepigrapha-TF therefore uses the same warp shape and surface feature names where the semantics genuinely correspond.

Compatibility does not mean pretending that a critical apparatus is a single diplomatic text. OCP-specific structures are added as ordinary Text-Fabric nodes and edges around the BHSA-shaped slot stream.

### Mapping

| OCP source | Text-Fabric representation |
| --- | --- |
| token in primary (`option=0`) reading | `word` slot |
| `book` + one `version` | `book` section node |
| first source division level | `chapter` section node when there are ≥2 source levels |
| second source division level | `verse` section node when there are ≥2 source levels |
| one-level source division | synthetic chapter `1`; source division becomes `verse` |
| source `div` at every level | additional `div` node with literal number/label/path |
| `unit` | `unit` node over the locus slots |
| every `reading` | `reading` node over the same locus slots |
| tokens of non-primary readings | `variant_word` nodes linked to their reading |
| `ms` | `manuscript` node |
| `reading@mss` | `witness` edges from reading to manuscript |
| `resource` | `resource` node linked to its version/book |
| `<w>` attributes | `lex`, `morph`, `style`, `language`, `w_annotated` features |
| primary surface text | `g_word_utf8`, `trailer_utf8`, plus `prefix_utf8` when needed |

## Section policy

`book`, `chapter`, and `verse` exist primarily for the standard Text-Fabric section API and BHSA-like user expectations.

OCP section values are stored as strings because the source includes values such as `4b` and `heading`. Numeric ordinals are supplied separately as `chapter_index` and `verse_index`. Every original `div` remains available with `div_number`, `div_level`, `div_label`, `div_path`, and its `parent` edge, so the source hierarchy is not flattened away.

When an OCP file contains multiple versions, each version receives a unique TF `book` identifier such as `TAdam__Syriac` and `TAdam__Greek`. The original OCP filename remains in `ocp_book`. This keeps `(book, chapter, verse)` addresses unambiguous.

## Apparatus policy

The primary reading supplies the contiguous slot stream. All readings, including the primary one, get `reading` nodes. Alternative tokens are represented as non-slot `variant_word` nodes rather than being inserted into the global slot stream.

This preserves several properties at once:

- normal TF text traversal remains linear;
- variant readings remain token-queryable;
- all alternatives share the same `unit` locus through `oslots`;
- witness membership is explicit in graph edges;
- original reading text and mixed XML are retained on the reading node;
- empty readings remain explicit omissions.

If the primary reading is empty, the converter creates a `word` anchor slot with `is_gap=1`. It carries no invented surface text; it exists so the unit and every alternative at that locus can be represented by valid TF slot mappings.

## Information preservation

The conversion aims to preserve OCP semantics rather than byte-for-byte XML serialization. It stores:

- source path and SHA-256;
- book/version metadata;
- division declarations and literal hierarchy;
- unit IDs, group, and parallel metadata;
- every reading, its option, witness string, indentation/linebreak flags, normalized text, and mixed XML;
- manuscript names, bibliography, language/show flags;
- resources;
- `<w>` lexical/morphological/style/language annotations.

The original XML remains the authority for byte-level round trips.

## Validation strategy

Unit tests use synthetic XML designed to cover the source grammar without copying OCP edition text. They assert parser preservation, Text-Fabric warp invariants, BHSA-style sections and surface features, variants, omissions, one- and three-level division schemes, nonnumeric section labels, multi-version books, source-directory handling, and the writer API.

CI additionally clones the pinned OCP upstream commit and converts the complete direct `static/docs/*.xml` set. It then reloads the emitted dataset with Text-Fabric. This catches source-shape regressions that synthetic fixtures cannot predict.

## Rejected designs

### `unit` as the slot type

This maps the apparatus elegantly but loses BHSA compatibility for ordinary word queries, text formats, and section traversal. `word` slots are preferable for this project.

### Put every variant token in the slot stream

That produces a sequence that no witness actually reads and makes standard TF traversal misleading. Alternative tokens are therefore non-slot `variant_word` nodes.

### Discard deeper divisions to force `book/chapter/verse`

Fragmentary works and source citations use deeper structures. The first two levels feed BHSA-style sections, while all source `div` nodes remain in the graph.

### Coerce chapter and verse values to integers

Real source values are not uniformly numeric. Literal strings plus ordinal index features preserve the data and still support ordering.

## Distribution boundary

The converter is MIT-licensed. OCP's current repository-level statements about the editions and older per-edition/copyright statements are not sufficiently consistent to make redistribution of a generated corpus an implementation assumption. For now, users run the converter against an OCP checkout. Publishing generated TF data can be revisited after the upstream rights position is clarified.
