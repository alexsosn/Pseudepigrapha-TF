# Apparatus helper loading contracts

`pseudepigrapha_tf.Apparatus` is a convenience layer over a loaded Text-Fabric API. Its methods do not implicitly reload omitted features, so selective loads must include the features and edges required by the operation being used. The main README includes an end-to-end `work_metadata()` researcher example; this page specifies the selective-load contract behind it.

## Primitive apparatus relations

`unit_readings(unit)` requires the `reading_of` edge. `witness_reading(unit, manuscript)` and `witness_state(unit, manuscript)` additionally require the `witness` edge. Missing required relations are reported as `ValueError` naming the omitted edge instead of leaking Text-Fabric attribute errors.

`apparatus(unit)` reports each reading's text, primary/alternative status, and witness nodes. It therefore requires `reading_of`, `witness`, and `is_primary`. `reading_text` is used as well, but generated Pseudepigrapha-TF corpora declare it in `fmt:reading-default`, so Text-Fabric loads it as a format dependency even when it is not named explicitly in a selective `TF.load()` call.

## Passage-level helpers

`passage()` and the passage-bearing portions of `work_passage()` require the semantic inputs needed to distinguish primary readings, alternatives, witness assignments, omissions, and unattested witnesses: `reading_of`, `witness`, `is_primary`, `manuscript_of`, and `undefined_manuscript` (plus `ocp_book` for `work_passage()`). Omitting `is_primary` is an error; the API never silently turns an unavailable primary/alternative distinction into `primary=False`.

Descriptive fields such as `source_ref`, `unit_id`, `ms_abbrev`, `ms_name`, `ms_language`, and `ms_show` remain optional where the API already provides a neutral fallback. Selective loading therefore needs to preserve semantic distinctions, not every display field.

## Document-level scholarly metadata

When an OCP source directory contains the committed `intros.json` export, the converter creates exactly one `work` node for every OCP XML document identity. Textual `book` nodes and `version_metadata` nodes point to that document node through `version_of`. A work whose sibling XML is empty (currently `3Macc.xml` in the pinned source) is preserved as a metadata-only `work` node with one technical slot anchor but no fabricated textual version or section.

The long introduction, bibliography, sigla, manuscript notes, and related source values live **only on the `work` node**, not on every textual version. This avoids duplicating large scholarly HTML for multi-version works.

Text-Fabric 13.1 does not safely round-trip raw carriage returns in ordinary string features. Pseudepigrapha-TF therefore stores the exact upstream scalars/strings as JSON string values in `intro_*_json` features. This is a transport encoding, not normalization: after `json.loads`, CRLF, Unicode, tabs, literal backslashes, HTML, and explicitly empty source strings are recovered exactly. Missing upstream fields remain absent, which is distinct from a committed empty string (`""`).

`Apparatus.work_metadata(work)` reverses that transport representation. It returns the OCP work id, source filename, metadata title/version, ordered public body fields as decoded strings, citation, and booleans indicating whether textual content exists and whether the work is metadata-only. A textual work with no `intros.json` record is still represented as a `work` node and returns `metadata_title=None`, `metadata_version=None`, an empty field mapping, and `citation=None`.

For selective loading, `work_metadata()` requires `ocp_book`, `source_file`, `intro_field_order`, `intro_title_json`, `intro_version_json`, `intro_citation_json`, `is_metadata_only_work`, and the `version_of` edge. It also requires every `intro_<field>_json` feature named by the loaded work's `intro_field_order`. The full public body vocabulary is:

- `intro_introduction_json`
- `intro_provenance_json`
- `intro_themes_json`
- `intro_status_json`
- `intro_manuscripts_json`
- `intro_bibliography_json`
- `intro_corrections_json`
- `intro_sigla_json`
- `intro_copyright_json`

The converter always serializes this feature vocabulary when the document-work layer is enabled, even when a particular feature has no values in the current corpus. That keeps selective-load failures explicit instead of making feature-file presence depend on the current metadata distribution.

## `witness_text()`

`Apparatus.witness_text(manuscript)` reconstructs all non-empty **standard unit readings** attributed to one manuscript in Text-Fabric corpus-unit order. In this global mode it requires:

- node feature `reading_text`;
- edge feature `witness` with Text-Fabric reverse lookup (`witness.t(manuscript)`);
- edge feature `reading_of` with forward lookup (`reading_of.f(reading)`);
- the normal Text-Fabric `otype` selector and type lookup used to identify ordinary `reading` nodes and iterate `unit` nodes in corpus order.

The method validates that every cited ordinary `reading` belongs to exactly one apparatus unit and rejects multiple ordinary readings assigned to the same manuscript at one unit. Explicit empty readings are omissions and contribute no text.

Preserved direct-div `orphan_reading` anomalies also carry ordinary `witness` edges, but intentionally have no `reading_of` unit because the converter refuses to invent a locus. Global `witness_text()` therefore excludes `orphan_reading` nodes from reconstructed unit text rather than treating their missing ownership as corruption. Their citation and text remain available in the anomaly graph.

`Apparatus.witness_text(manuscript, units=...)` deliberately retains the older per-unit lookup path because the caller-supplied iterable may encode an arbitrary subset, order, or duplicate units. The returned text therefore follows that iterable exactly rather than corpus order.

Missing requirements for the global path are reported as `ValueError` with the relevant edge or selector named, instead of leaking an implementation-level `AttributeError`.

## Related helpers

`reading_tokens(reading)` has a different selective-load contract: it requires `reading_text` and `is_primary`; non-empty alternative readings additionally require `variant_word_of`, while primary readings use Text-Fabric's warp `oslots` relation. See the main README for token and passage semantics.
