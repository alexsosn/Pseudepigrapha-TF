# Pseudepigrapha-TF v1.1.0

Pseudepigrapha-TF 1.1 advances the derived Online Critical Pseudepigrapha Text-Fabric corpus to **data version 1.1**. The pinned OCP source snapshot is unchanged at `c939dcbacad78c5d18d2c4282cad23c47e19ac07`; the corpus changes because the converter now preserves manuscript evidence it previously lost.

## New data version

Converting the pinned source with 1.0.0 and with 1.1.0 yields identical node and slot counts (922,922 word slots, 1,193,651 nodes) but different manuscript metadata. Three TSol manuscripts — `HI`, `L`, `VW` — move from undefined status into fully named manuscripts, so `ms_name` grows from 419 to 422 records and `undefined_manuscript` falls from 30 to 27. Eight features change in total: `bibliography`, `bibliography_xml`, `manuscript_index`, `ms_language`, `ms_name`, `ms_name_xml`, `ms_show`, and `undefined_manuscript`.

Because the derived bytes are no longer equivalent to the published 1.0 data, this release publishes `tf-1.1.zip` under data version `1.1`. The `v1.0.0` assets, including `tf-1.0.zip`, are untouched.

## Researcher-visible changes since v1.0.0

- **Manuscript completeness:** all TSol manuscripts are preserved rather than collapsed by lossy singleton-XML duplicate handling, and missing manuscript-language exceptions are bound to exact pinned source bytes instead of being inferred.
- **Fail-closed source validation:** structural OCP XML text that the model does not represent, cross-file duplicate work identities, excessively nested source divisions, and Git index flags that would conceal a modified OCP checkout are now rejected rather than silently accepted. Researchers converting their own checkout may see conversions that previously succeeded now fail with an explicit reason; that is the intended behaviour.
- **Transactional conversion:** Text-Fabric generation is rolled back when a matching conversion report cannot be published, and generated output survives an interruption after the report commit, so a corpus directory and its `conversion-report.json` can no longer disagree.
- **Streamed release assets:** canonical Text-Fabric release archives, `complete.zip` members, feature hashes, and `otype` metadata are constructed and verified by streaming with complete UTF-8 and CRC validation. Release builds hold far less in memory while producing byte-identical archives.
- **Faster comparison views:** work/version discovery, generated translation discovery, comparison helpers, and navigation topology are cached or persisted, and per-app landing HTML is reused lazily. Pinned comparison HTTP latency and pre-cache speed are now covered by benchmarks.
- **Architecture documentation:** ADR-0002 records the OCP source-format and factory boundary that these validation changes rely on.

Apparatus and generated-translation semantics, the feature schema, the provenance model, the distribution format, and the publisher architecture are unchanged. Generated translations remain parallel research text, not historical witnesses.

Runtime-footprint figures were not re-measured for 1.1; the published measurements remain attributed to the 1.0 corpus.

Release assets use the existing distribution format: stock Text-Fabric `complete.zip`, native `tf-1.1.zip`, `conversion-report.json`, and `dataset-manifest.json`.
