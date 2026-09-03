# Research: Online Critical Pseudepigrapha → Text-Fabric

## Scope

This repository converts the XML editions in the Online Critical Pseudepigrapha (OCP) `static/docs` directory into Text-Fabric. The converter is designed and integration-tested against upstream commit `2d1d14d23434a784d377ff7f4409ccdb2d18aafb` (2026-08-27) and keeps the generated warp layer as close to BHSA conventions as OCP semantics permit.

The converter repository contains code and synthetic fixtures only. It does not vendor OCP XML or generated Text-Fabric data; redistribution of source editions is intentionally separated from converter licensing.

## Source format

OCP documentation sometimes calls the editions TEI XML, but the pinned corpus primarily uses the project-specific Grammateus vocabulary described by `static/docs/grammateus.dtd`:

- `book` contains one or more `version` elements;
- each `version` declares division labels, optional resources, manuscript metadata, and text;
- text is a recursive hierarchy of `div` elements terminating in `unit` elements;
- a `unit` contains one or more alternative `reading` elements;
- a reading records `option`, a space-separated `mss` witness list, optional `linebreak`/`indent`, and mixed text with optional `<w>` annotations;
- `<w>` can carry `morph`, `lex`, `style`, and `lang`.

`unit` is therefore the textual locus and readings are mutually exclusive alternatives at that locus.

### Legacy dialect

Full-corpus CI exposed one important exception: `Esdr.xml` uses a legacy direct `book/manuscripts/text/chapter/verse/unit/reading` dialect rather than `version/div`. It also puts `linebreak` on `unit`. The parser normalizes that source shape into the same intermediate model with synthetic `Chapter`/`Verse` division declarations while preserving the legacy unit-level linebreak.

## Observed edge cases

- `3Macc.xml` is zero bytes and must be skipped explicitly rather than treated as valid XML.
- `ArisEx.xml` has three division levels (`Book`, `Chapter`, `Line`), starts with `unit id="0"`, and includes nonnumeric labels.
- `Eup.xml` includes four-level references such as `1:23:153:4` (`Book → Section → Chapter → Verse`).
- Other fragmentary files use values such as `4b`, `heading`, `{heading}`, and `Heading`; source identifiers cannot safely be coerced to integers.
- Some books contain multiple versions/languages under one OCP `book` (for example Testament of Adam and Eupolemus).
- `TJob.xml` declares a Coptic version with division/manuscript metadata but an intentionally empty `<text></text>`. OCP's introduction states that the fragmentary Coptic evidence has not yet been included in the edition. This is valid upstream metadata, not malformed input.
- Mixed `<w>` markup appears inside readings and must survive conversion.
- Empty readings are meaningful omissions, not parser errors.
- OCP uses `linebreak="following"` and `linebreak="doubleFollowing"`; the historical renderer emitted one or two breaks respectively.
- OCP's default reader selects `reading option="0"`, falling back to the first reading if option 0 is absent.
- The DTD permits PCDATA inside `<division>` declarations. The pinned corpus appears to use self-closing declarations, but the parser preserves declaration text rather than silently discarding a grammar-permitted field.

## BHSA compatibility target

BHSA uses `word` as slot type and `book`, `chapter`, `verse` as the standard section hierarchy. Pseudepigrapha-TF uses that warp shape and the familiar `g_word_utf8`/`trailer_utf8` feature names where the semantics correspond.

Compatibility must not make the apparatus look like a single diplomatic text. OCP-specific structures therefore remain ordinary Text-Fabric nodes/edges around a BHSA-shaped primary slot stream.

### Mapping

| OCP source | Text-Fabric representation |
| --- | --- |
| token in primary reading | `word` slot |
| textual `book` + one `version` | `book` section node |
| declared version with no textual units | `version_metadata` node, never a fabricated `book` section |
| one source level | synthetic chapter `1`; source level becomes `verse` |
| two source levels | parent becomes `chapter`; terminal becomes `verse` |
| three or more source levels | complete parent path becomes compound `chapter`; terminal level becomes `verse` |
| source `div` at every textual level | `div` node with literal number/label/full reference |
| `unit` | `unit` node over locus slots, explicitly parented to enclosing `div` |
| every `reading` | `reading` node over the locus slots |
| non-primary reading token | `variant_word` node linked to its reading and one technical locus anchor |
| `ms` | `manuscript` node with one technical TF anchor and semantic witness/version edges |
| `reading@mss` | `witness` edges from reading to manuscript |
| `resource` | `resource` node linked to version/book with one technical TF anchor |
| `<w>` attributes | `lex`, `morph`, `style`, effective `language`, literal `w_lang`, `w_annotated` |
| source citation | `source_ref` plus JSON `source_ref_parts` |
| source display boundary | `boundary_utf8` on the final primary slot of a unit |

## Section policy

Text-Fabric's standard section machinery supports at most `book/chapter/verse`; adding a fourth section type is not a valid solution for OCP's deeper citations.

The initial design projected source levels 1 and 2 into chapter/verse. Review showed that this made references such as `Eup 1:23:153:4` look like `1 / 23` in normal TF navigation, leaving `153:4` only in generic `div` nodes. That technically retained data but produced a misleading research interface.

The corrected policy is:

- one source level: chapter `1`, terminal source division as verse;
- two levels: direct parent/terminal mapping;
- three or more levels: `chapter = full source path except terminal`, `verse = terminal`.

Thus `1:23:153:4` becomes chapter `1:23:153`, verse `4`. Every source `div`, `unit`, `reading`, primary word, and variant word also exposes the exact full `source_ref`, so OCP citations require no graph archaeology.

Section values remain strings. Numeric document-order ordinals are supplied separately as `chapter_index` and `verse_index`. Multi-version files receive unique TF `book` identifiers while `ocp_book` retains the original filename.

A metadata-only upstream version is deliberately excluded from the section hierarchy. For example, `TJob/Coptic` is retained as `version_metadata` plus its manuscript metadata, but it contributes no fake Coptic word slot or `book/chapter/verse` address.

## Apparatus and technical-anchor policy

The primary reading supplies the contiguous slot stream. All readings get `reading` nodes. Alternative tokens remain non-slot `variant_word` nodes rather than entering the global slot stream, which would create a fictitious text containing mutually exclusive readings.

Alternative `reading` nodes still occupy the primary locus through `oslots` for locality and graph queries. That creates an important Text-Fabric interface hazard: without a node-specific default, `T.text(alternative_reading)` descends to its contained primary slots and can display the **wrong textual content**. The corpus therefore defines:

- `reading-default={reading_text}`;
- `variant_word-default={prefix_utf8}{g_word_utf8}{trailer_utf8}`;
- `manuscript-default={ms_abbrev}`;
- `resource-default={resource_name}`;
- `version_metadata-default={version_title}`.

Text-Fabric 13.1 does not serialize non-slot nodes with empty `oslots` in this generated dataset. Metadata-like nodes therefore use **one technical anchor slot only**, never their full witnessed/resource/version extent. Type-specific formats prevent standard `T.text()` from rendering that technical anchor as if it were the node's own text. Each `variant_word` likewise uses one locus anchor rather than copying the whole primary locus. This reduces the earlier multiplicative `oslots` expansion to O(1) anchoring per metadata/variant node.

The package adds an `Apparatus` helper API for routine reading/witness operations so researchers need not manually join every edge.

If the primary reading is empty, the converter creates a surface-less `word` anchor with `is_gap=1`. This preserves an otherwise anchorless apparatus locus without inventing text.

## Surface reconstruction

XML indentation is not textual content. Ordinary whitespace inside token separators is canonicalized while the original mixed XML remains on `reading_xml`. Meaningful OCP unit/reading boundaries are made explicit in `boundary_utf8`:

- `following` → one newline;
- `doubleFollowing` → two newlines;
- otherwise a space is inserted between adjacent units when no explicit break exists.

This prevents `T.text(book)` from silently producing `lastwordNextword` across XML element boundaries.

## Information preservation

The conversion is semantic rather than byte-for-byte. It preserves:

- stable source-relative file path, SHA-256, upstream repository/commit, converter version;
- every declared book/version, including metadata-only versions;
- division declarations including label, delimiter, and permitted PCDATA;
- every structural textual division and full source reference;
- unit IDs, group, parallel, and linebreak metadata;
- every reading, literal/numeric option, witnesses, indentation/linebreak flags, normalized text, and mixed XML;
- manuscript names, bibliography, language/show flags;
- resources;
- `<w>` lexical/morphological/style/language annotations.

The original XML remains the authority for byte-level round trips.

## Semantic parity validation

A successful parse/write/reload is not evidence of losslessness. The converter therefore creates `conversion-report.json` from an **independent reread of the raw XML**, not merely from the converter's intermediate model.

Corpus-wide checks compare raw XML with generated TF for:

- source SHA-256s and every declared version, including metadata-only versions;
- division declarations and all structural division records;
- unit attributes and unit→div parent linkage;
- reading option/witness/flag/text/mixed-XML payloads;
- manuscript metadata/bibliography;
- resources;
- annotated `<w>` records;
- primary reconstruction from slots;
- alternative reconstruction from `variant_word` nodes;
- complete/unique BHSA section coverage over the textual slot stream.

The report also records slot/node/`oslots`/variant/witness counts. Conversion exits non-zero if any semantic check fails. Section coverage and address uniqueness are calculated with slot maps in linear time rather than scanning every section for every slot.

CI additionally installs real Text-Fabric and verifies that `T.text()` uses the node-specific defaults, metadata-only versions do not masquerade as text, and deep `source_ref` values map to the intended three-level TF address. It then converts the pinned complete OCP source and reloads the result.

## Rejected designs

### `unit` as slot type

This maps the apparatus elegantly but loses BHSA compatibility for ordinary word queries, text formats, and section traversal.

### Put every variant token in the slot stream

That produces a sequence no witness actually reads and makes standard TF traversal misleading.

### Project only the first two source levels

This was implemented initially and rejected after review because it crippled normal citation/navigation for three- and four-level fragmentary sources.

### Give manuscripts/resources/full variant tokens broad `oslots`

This made `T.text()` semantics misleading and created dense graph expansion. Semantic edges plus one technical anchor per metadata/variant node are more faithful and scale linearly.

### Turn an empty upstream version into a fake textual book

`TJob/Coptic` declares valid metadata while explicitly containing no text. Synthesizing slots or sections would imply that OCP provides Coptic text when it does not. A `version_metadata` node preserves the declaration without making that claim.

### Coerce chapter and verse values to integers

Real source values are not uniformly numeric. Literal strings plus ordinal index features preserve the data and ordering.

## Distribution boundary

The converter is MIT-licensed. OCP's current repository-level licensing statements and older edition-specific/copyright statements are not sufficiently consistent to make redistribution of a generated corpus an implementation assumption. For now, users run the converter against an OCP checkout. Publishing generated TF data can be revisited after the upstream rights position is clarified.
