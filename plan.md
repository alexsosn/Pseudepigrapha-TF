# Plan: OCP → Text-Fabric converter

## Goal

Produce a reproducible converter for Online Critical Pseudepigrapha XML that uses a BHSA-compatible Text-Fabric interface without hiding or distorting the critical apparatus, source citation hierarchy, witnesses, or metadata.

## Acceptance criteria

- [x] `word` is the Text-Fabric slot type.
- [x] Standard textual sections are `book`, `chapter`, `verse`.
- [x] Primary Unicode text uses BHSA-familiar word/trailer features plus explicit boundary reconstruction.
- [x] Full OCP source citations are directly exposed on loci/readings/tokens.
- [x] Three- and four-level OCP references map truthfully into the three-level TF section API.
- [x] All source `div`, `unit`, `reading`, manuscript, resource, division-declaration, and `<w>` information required for scholarly reconstruction is retained.
- [x] Declared upstream versions with no textual units remain representable without inventing TF text/sections.
- [x] Alternative readings remain token-queryable without contaminating the primary slot stream.
- [x] `T.text(reading)` cannot silently display the primary reading for an alternative.
- [x] Manuscript/resource/metadata-version nodes use only O(1) technical anchoring and do not render that anchor as their own text.
- [x] Empty readings/omissions and empty primary loci remain representable.
- [x] Nonnumeric division values survive conversion.
- [x] Multi-version OCP files have unambiguous TF section addresses.
- [x] Legacy `Esdr` chapter/verse XML is normalized explicitly.
- [x] Empty source files are reported and skipped; malformed non-empty XML fails loudly.
- [x] Source file paths and upstream revision metadata are reproducible.
- [x] Unit tests use synthetic fixtures rather than copied OCP edition text.
- [x] Generated graph invariants are validated before writing.
- [x] Independent corpus-wide raw-XML→TF semantic parity is required for a successful conversion.
- [x] Semantic section validation scales linearly with slots/section edges.
- [x] A researcher can retrieve one `book/chapter/verse` together with all units, readings, and declared witnesses through one high-level API call.
- [x] Passage-level witness reconstruction distinguishes explicit omission from lack of attestation and does not silently turn incomplete evidence into continuous text.
- [x] CI converts a pinned complete OCP checkout, validates the report, reloads the resulting TF dataset, and exercises the passage API on real `1En 1:2`.
- [x] The converter is independently licensed and does not vendor OCP source data.

## TDD sequence

### 1. Parser contract

Write failing tests for source metadata, readings/witnesses, mixed `<w>` content, literal identifiers, and empty-source handling. Implement a small OCP-specific parser.

### 2. BHSA-compatible graph contract

Write failing tests for contiguous `word` slots, `book/chapter/verse`, BHSA surface feature names, primary reading selection, apparatus nodes/edges, and `<w>` annotations. Implement graph construction and warp validation.

### 3. Source-shape exceptions

Write failing tests for one-level and deep division schemes, nonnumeric values, unit `0`, multiple versions, omissions, and then—after full-source CI exposed it—the legacy `Esdr` chapter/verse dialect. Implement explicit normalization and gap anchors.

### 4. Text-Fabric writer

Write a writer contract around `Fabric.save`, then implement lazy Text-Fabric integration. Ensure every feature referenced by an `fmt:*` template is serialized even when all values are empty in a particular corpus.

### 5. End-to-end source loader and CLI

Write tests for deterministic direct-XML discovery and zero-byte handling. Implement `pseudepigrapha-tf convert`.

### 6. Review-driven interface corrections

Write failing tests before implementation for:

- deep citation projection (`9.4b.1` → chapter `9.4b`, verse `1`);
- `source_ref` on units/readings/primary words;
- unit→div parent edges;
- node-specific default text formats;
- deterministic unit/line boundaries;
- O(1) technical `oslots` for manuscripts/resources/variant tokens;
- stable source-relative paths and upstream provenance;
- apparatus helper API.

Implement the corrected section/reference model, text formats, helpers, boundary feature, sparse anchoring, and provenance.

### 7. Semantic parity audit

Write failing tests requiring an independent raw-XML inventory to agree with the generated graph and proving that a deliberately corrupted reading is detected. Add the DTD-permitted division-PCDATA test before implementing support.

Implement `conversion-report.json` with corpus-wide checks for source hashes, divisions, units, readings/witnesses, manuscripts, resources, `<w>` annotations, primary/alternative reconstruction, parent linkage, and section coverage. Fail conversion if parity fails.

### 8. Real Text-Fabric and pinned-upstream CI

Install the real Text-Fabric dependency in CI and assert:

- alternative `T.text(reading)` returns the alternative wording;
- manuscript `T.text()` returns the manuscript identifier rather than primary loci;
- deep `source_ref` values produce the intended `book/chapter/verse` address;
- full pinned OCP conversion passes the semantic report;
- generated TF reloads successfully;
- conversion stays within the CI runtime budget.

### 9. Full-corpus edge cases discovered by the parity run

When pinned-upstream CI exposes a valid source shape not covered by synthetic fixtures, add a failing fixture/test first and preserve the upstream semantics rather than weakening validation.

Applied cases:

- `TJob/Coptic`: upstream declares Coptic division/manuscript metadata but `<text></text>` because the fragmentary Coptic evidence has not yet been included. Preserve it as `version_metadata`; do not synthesize a Coptic textual `book`.
- Text-Fabric 13.1 serialization: metadata-like non-slot nodes require a nonempty technical `oslots` anchor. Use one slot only and node-type formats so the anchor is never presented as their text.
- parity audit scaling: replace slot×section scans with linear slot-coverage maps.

### 10. Passage-level apparatus ergonomics

Use `1En 1:2` as the motivating research query. Add a failing real-Text-Fabric test first requiring one call to return the verse's units/readings and all manuscripts declared for its OCP version.

Implement `Apparatus.passage(book, chapter, verse)` and `witness_state(unit, manuscript)` with three explicit coverage states:

- `reading`: witness assigned to a non-empty reading;
- `omission`: witness explicitly assigned to an empty reading;
- `unattested`: witness absent from all readings at that unit.

Only expose a witness-level continuous `text` when every unit is represented; otherwise return `text=None` plus `attested_text` and the per-unit segments. Do not infer lacunae or fragmentary status from absence unless OCP provides a structural signal for it.

Exercise the same call against the pinned upstream `1En 1:2` in CI so the convenience API is tested on the actual research target rather than only synthetic data.

## Out of scope for this PR

Interpretive normalization of OCP content, editorial correction of upstream editions, and redistribution of generated corpus data remain outside the converter's responsibility.