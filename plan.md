# Plan: OCP → Text-Fabric converter

## Goal

Produce a reproducible converter for the Online Critical Pseudepigrapha XML files that uses BHSA-compatible Text-Fabric warp conventions while retaining the critical apparatus, witnesses, source hierarchy, and OCP-specific metadata.

## Acceptance criteria

- [x] `word` is the Text-Fabric slot type.
- [x] Standard sections are `book`, `chapter`, `verse`.
- [x] Primary Unicode text uses `g_word_utf8` and `trailer_utf8`.
- [x] All source `div`, `unit`, `reading`, manuscript, resource, and `<w>` information required for scholarly reconstruction is retained.
- [x] Alternative readings remain token-queryable without contaminating the primary slot stream.
- [x] Empty readings/omissions and empty primary loci remain representable.
- [x] Nonnumeric division values and more than two source division levels survive conversion.
- [x] Multi-version OCP files have unambiguous TF section addresses.
- [x] Empty source files are reported and skipped; malformed non-empty XML fails loudly.
- [x] Unit tests use synthetic fixtures rather than copied OCP edition text.
- [x] Generated graph invariants are validated before writing.
- [x] CI converts a pinned complete OCP checkout and reloads the resulting `.tf` dataset.
- [x] The converter is independently licensed and does not vendor OCP source data.

## TDD sequence

### 1. Parser contract

Write failing tests for:

- book/version/division/manuscript metadata;
- reading alternatives and witness lists;
- mixed `<w>` content and annotations;
- literal unit/division identifiers;
- empty source detection.

Implement a small OCP-specific parser using the standard XML library and immutable model objects.

### 2. BHSA-compatible graph contract

Write failing tests asserting:

- contiguous `word` slots first in `otype`;
- `book/chapter/verse` in `otext` section metadata;
- `g_word_utf8` + `trailer_utf8` primary surface format;
- option-0 primary stream;
- `unit`/`reading` nodes sharing the locus slots;
- `variant_word` nodes for non-primary tokenization;
- witness edges and manuscript nodes;
- preservation of lexical/morphological `<w>` fields.

Implement graph construction and internal warp validation.

### 3. Source-shape exceptions

Add failing tests for:

- a one-level division scheme;
- a three-level scheme with nonnumeric labels;
- a source unit numbered `0`;
- multiple versions in one OCP book;
- an empty reading/omission.

Implement synthetic chapter handling, preserved generic `div` nodes, version-qualified book IDs, and gap anchors.

### 4. Text-Fabric writer

Write a writer contract test around `Fabric.save`, then implement lazy Text-Fabric integration so parser/graph tests do not require TF import side effects.

### 5. End-to-end source loader and CLI

Add tests for deterministic direct-XML discovery and zero-byte source handling. Implement:

```bash
pseudepigrapha-tf convert PATH/TO/OCP/static/docs --output tf/0.1
```

### 6. Upstream integration CI

Pin OCP commit `2d1d14d23434a784d377ff7f4409ccdb2d18aafb`, clone it in CI, convert the entire `static/docs` directory, and reload the output through Text-Fabric. Keep this integration test separate from synthetic unit tests so failures clearly distinguish converter regressions from upstream changes.

## Follow-up work

The converter core deliberately stops before adding interpretive normalization. Useful subsequent work includes witness reconstruction helpers, apparatus comparison utilities, language-specific token normalization, and a generated-data release once redistribution terms are sufficiently clear.
