# Apparatus helper loading contracts

`pseudepigrapha_tf.Apparatus` is a convenience layer over a loaded Text-Fabric API. Its methods do not implicitly reload omitted features, so selective loads must include the features and edges required by the operation being used.

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
