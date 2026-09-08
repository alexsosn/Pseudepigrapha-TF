# Issue #96 — Browser-addressable Text-Fabric feature documentation

Status: research gate complete; planning gate frozen. No feature-documentation production implementation has been added yet.

Research baseline:

- Pseudepigrapha-TF base commit: `4a8872d6aa6b4c6f83f9f69d3a632787249acd56` (merged #98).
- Text-Fabric contract inspected: `annotation/text-fabric@v13.1.0`.
- BHSA reference: `ETCBC/bhsa` feature documentation, especially `docs/features/0_home.md` and individual feature pages.
- Exact pinned OCP source: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.
- Corrected empirical inventory run: GitHub Actions `34207088506`.

## Research findings

### 1. Text-Fabric feature-help routing is filename based

Text-Fabric 13.1 derives feature documentation links from `docs.featureBase`, whose default is `{docBase}/features/<feature>{docExt}`. The feature landing page replaces `<feature>` with `docs.featurePage`; individual feature links replace it with the exact TF feature name.

Decisions:

- tracked landing page: `docs/features/0_home.md`;
- #96 will set `app/config.yaml` `docs.featurePage: 0_home`;
- individual pages: `docs/features/<feature>.md` using exact serialized names;
- no remote TF-data publication claims are added here; that boundary remains #97.

### 2. BHSA is a discoverability reference, not a schema to copy

Transferable ideas are a grouped landing page, exact feature-name links, explicit applicability, and useful examples. Hebrew-specific grammatical taxonomies and SHEBANQ/MQL assumptions are not transferable. Pseudepigrapha-TF must not duplicate canonical feature descriptions in hand-maintained Markdown.

### 3. The canonical serialized feature contract is assembled in layers

There is no single complete feature registry today.

- `graph.py`: `INT_FEATURES`, partial `FEATURE_DESCRIPTIONS`, `EDGE_DESCRIPTIONS`, core edge type/cardinality contracts, and fallback `OCP/TF feature <name>` metadata.
- `conversion.py`: metadata-only/anomaly fields, generated-translation provenance, `translation_of`, `translation_unit_of`, source identity, and special text formats. Translation edge endpoint semantics are validated separately in `_validate_generated_alignment()`.
- `metadata.py`: `document_metadata`, `intro_label`, and stable `intro_*_json` features with canonical descriptions.
- `classifications.py`: historical classification features and `controlledVocabularyJson` for controlled labels.
- `writer.py`: adds format-required stable features plus stable API features such as `undefined_manuscript`, `witness`, and `manuscript_of`, then guarantees metadata for every serialized feature.

Therefore documentation must be driven by the **serialization-normalized contract**, not merely non-empty `TFData.node_features` or one source snapshot.

### 4. Exact pinned serialized inventory

The first observability attempt was discarded: reading `TF.features` before loading all discovered features lost edge/value metadata. The corrected probe used `TF.explore()` to discover node/edge identity, loaded every discovered feature, and then read final TF metadata.

The exact pinned corpus serializes **87 node features**:

```text
author
bibliography
bibliography_xml
book
boundary_utf8
chapter
chapter_index
div_fragment
div_index
div_label
div_level
div_number
div_path
division_delimiters
division_labels
division_texts
ellipsis_text
g_word_utf8
generated_language
generation_marker
generation_method
generation_model
group
historical_biblical_figures_json
historical_genres_json
historical_ocp_doc_id
indent
intro_bibliography_json
intro_citation_json
intro_copyright_json
intro_corrections_json
intro_introduction_json
intro_label
intro_manuscripts_json
intro_provenance_json
intro_sigla_json
intro_status_json
intro_themes_json
intro_title_json
intro_version_json
is_gap
is_metadata_only
is_missing_unit_id
is_omission
is_primary
is_source_anomaly
language
linebreak
manuscript_index
ms_abbrev
ms_language
ms_name
ms_name_xml
ms_show
mss
ocp_book
otype
prefix_utf8
reading_index
reading_option
reading_option_source
reading_text
reading_xml
resource_name
section_occurrence
source_child_index
source_file
source_ref
source_ref_parts
source_sha256
source_tag
synthetic_witness
text_structure
title
token_count
trailer_utf8
undefined_manuscript
unit_id
unit_index
unit_linebreak
variant_position
verse
verse_index
version_fragment
version_id
version_kind
version_title
```

The exact pinned corpus serializes **8 edge features**:

```text
manuscript_of
oslots
parent
reading_of
translation_of
translation_unit_of
variant_word_of
witness
```

`resource_of` is deliberately absent from this pinned inventory because that snapshot has no resource nodes. It remains a supported converter/API relation and is exercised by repository fixtures. This distinction between the pinned emitted set and the supported union must remain explicit.

### 5. Stable serialized features may be empty

The exact pinned output has three serialized feature files with no values:

```text
ellipsis_text
prefix_utf8
resource_name
```

They still exist because stable Text-Fabric text formats/API contracts depend on them. Documentation coverage therefore must not equate “no values in this snapshot” with “not a supported feature”.

### 6. Forty-four serialized features have placeholder descriptions

The corrected pinned probe found **44** researcher-visible features whose final description is still the generic `OCP/TF feature <name>` fallback:

```text
author
bibliography
bibliography_xml
chapter_index
div_fragment
div_index
div_label
div_level
div_number
div_path
division_delimiters
division_labels
division_texts
ellipsis_text
group
indent
is_primary
language
linebreak
manuscript_index
ms_abbrev
ms_language
ms_name
ms_name_xml
ms_show
mss
ocp_book
otype
prefix_utf8
reading_index
reading_option
reading_text
resource_name
text_structure
title
token_count
undefined_manuscript
unit_id
unit_index
unit_linebreak
variant_position
verse_index
version_fragment
version_title
```

Publishing generated pages directly from current metadata would therefore produce technically complete but poor researcher documentation. #96 must first make canonical metadata descriptions useful at their emission source; docs-only prose is not an acceptable second source of truth.

### 7. Edge endpoint/cardinality semantics must come from validation contracts

Core edges already have machine-readable type/cardinality contracts in `graph.py`. Translation edges are the gap: their semantics are enforced in `_validate_generated_alignment()` rather than represented in the same reusable contract surface.

Decision: centralize or expose canonical edge contracts so validation and documentation share them. Do not add a docs-specific endpoint map.

`oslots` remains special: for several technical nodes it is a Text-Fabric locality/serialization anchor and must not be documented as scholarly textual containment.

### 8. Applicability and optional features

For non-empty node features, observed applicable `otype` values can be derived from the fully built graph. Stable empty or optional supported features have no observed nodes in a particular snapshot, so the contract must distinguish observed applicability from canonical supported applicability where needed.

Do not guess applicability from feature names.

### 9. Per-feature provenance is not yet uniformly machine-readable

The source-preserved / converter-derived / generated-translation distinction is important, but current feature metadata has no uniform per-feature provenance classifier. Do not reconstruct it with filename/name heuristics in the renderer.

If #96 needs this classification for grouping/pages, add a controlled canonical metadata field at the existing emission sites and have both TF metadata and documentation consume it.

### 10. Generation point and API shape

The production conversion sequence is:

1. load source XML, public metadata, and historical classification fixture;
2. `build_tf_data()`;
3. provenance attestation;
4. `attach_public_metadata()`;
5. `attach_historical_classifications()`;
6. semantic audit;
7. serialization normalization and `Fabric.save()`.

A deterministic docs generator should consume the same fully augmented in-memory graph plus the same serialization-normalization logic. It should not parse emitted `.tf` files and should not require network access.

Preferred minimal abstraction: a public/read-only `serialized_feature_contract(data)` (name may change) that returns the exact serialized node/edge feature names and final metadata without mutating `TFData`.

Avoid a large registry rewrite unless RED tests show it is needed. Prefer improving descriptions at their current canonical emission sites, exposing the serialization-normalized contract, and exposing reusable edge contracts.

## Frozen page contract

Each generated feature page must be derived from canonical contracts and contain, where applicable:

- exact feature name;
- node vs edge;
- value type;
- canonical researcher-facing description;
- provenance/category metadata when canonicalized;
- node applicability: observed node types plus explicit supported applicability for stable-empty/optional features when available;
- edge direction, source types, target types, and cardinality from canonical validation contracts;
- controlled vocabulary from TF metadata;
- explicit technical-anchor caveat for `oslots` and related support semantics;
- deterministic representative values only when genuinely useful.

No page may contain an independently maintained semantic description that can silently diverge from emitted TF metadata.

## Frozen landing-page groups

1. Text-Fabric warp and section/text features.
2. Source/version identity and provenance.
3. Apparatus and witness features/relations.
4. Generated-translation features/relations.
5. Public work metadata.
6. Historical classifications.
7. Preserved anomalies / technical anchors.
8. Remaining source-preserved XML attributes/content.

If grouping requires metadata, make the category canonical at the feature source rather than adding a docs-only map.

## TDD sequence

### Phase 1 — RED: serialization-normalized feature contract

Add tests that current main cannot satisfy:

1. a public deterministic contract represents the serialization-normalized node/edge feature set without writing files;
2. it includes stable empty format/API features;
3. obtaining it does not mutate `TFData`;
4. controlled metadata such as `controlledVocabularyJson` survives;
5. every researcher-visible serialized feature has a non-placeholder canonical description;
6. reusable edge contracts cover core relations plus translation relations, while `oslots` is explicitly treated as TF support semantics.

### Phase 2 — GREEN: canonical contract and metadata quality

- expose serialization-normalized feature metadata through one reusable API;
- expose/centralize endpoint/cardinality contracts, including translation edges;
- improve the 44 placeholder descriptions at their existing canonical metadata sources;
- add provenance/category/applicability metadata only where required and canonical.

### Phase 3 — RED/GREEN: deterministic docs renderer

Require semantically:

- `docs/features/0_home.md`;
- one `<feature>.md` per supported documented feature;
- exact coverage of the canonical supported contract, including stable empty/optional features;
- page value type/description/controlled vocabulary matching canonical metadata;
- edge endpoint/cardinality text matching canonical contracts;
- deterministic output with no network dependency.

Avoid large Markdown snapshots; compare parsed semantic fields or regenerated files.

### Phase 4 — app routing

Set `docs.featurePage: 0_home` and verify TF 13.1 feature-base substitution resolves the landing page and individual tracked feature pages. Do not add remote TF-data provenance fields owned by #97.

### Phase 5 — pinned full-corpus drift gate

The existing pinned integration path must fail closed if:

- any emitted serialized feature lacks documentation coverage;
- tracked generated docs are stale relative to canonical metadata/contracts;
- any emitted edge relation with a canonical type contract lacks matching endpoint documentation.

The permanent check should reuse the existing pinned conversion rather than add another full-corpus workflow.

### Phase 6 — fresh adversarial review

Review the exact green head against source code and generated docs, challenging:

- hidden duplicate registries;
- generic descriptions presented as scholarship;
- incorrect source/derived/generated provenance;
- wrong edge direction/cardinality;
- false textual-containment implications for technical `oslots` anchors;
- missing stable empty or supported optional features;
- docs generated from a snapshot instead of the serialization contract;
- broken TF feature links;
- nondeterministic examples/order;
- unnecessary network/build-tool dependencies.

## Out of scope

- tutorial notebooks;
- remote corpus publication/loading (#97);
- changing scholarly graph semantics merely to improve prose;
- hand-authored per-feature pages that duplicate canonical TF metadata;
- BHSA-specific grammatical taxonomies or SHEBANQ integration.
