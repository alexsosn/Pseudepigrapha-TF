# Apparatus helper loading contracts

`pseudepigrapha_tf.Apparatus` is a convenience layer over a loaded Text-Fabric API. Its methods do not implicitly reload omitted features, so selective loads must include the features and edges required by the operation being used.

## Primitive apparatus relations

`unit_readings(unit)` requires the `reading_of` edge. `witness_reading(unit, manuscript)` and `witness_state(unit, manuscript)` additionally require the `witness` edge. Missing required relations are reported as `ValueError` naming the omitted edge instead of leaking Text-Fabric attribute errors.

`apparatus(unit)` reports each reading's text, primary/alternative status, and witness nodes. It therefore requires `reading_of`, `witness`, and `is_primary`. `reading_text` is used as well, but generated Pseudepigrapha-TF corpora declare it in `fmt:reading-default`, so Text-Fabric loads it as a format dependency even when it is not named explicitly in a selective `TF.load()` call.

## Passage-level helpers

`passage()` and the passage-bearing portions of `work_passage()` require the semantic inputs needed to distinguish primary readings, alternatives, witness assignments, omissions, and unattested witnesses: `reading_of`, `witness`, `is_primary`, `manuscript_of`, and `undefined_manuscript` (plus `ocp_book` for `work_passage()`). Omitting `is_primary` is an error; the API never silently turns an unavailable primary/alternative distinction into `primary=False`.

Descriptive fields such as `source_ref`, `unit_id`, `ms_abbrev`, `ms_name`, `ms_language`, and `ms_show` remain optional where the API already provides a neutral fallback. Selective loading therefore needs to preserve semantic distinctions, not every display field.

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
