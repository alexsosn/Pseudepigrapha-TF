# Issue #95 — Text-Fabric application/browser layer

Status: research baseline complete; planning gate started. No production app/browser behavior has been changed on this branch yet.

Research baseline:

- Pseudepigrapha-TF base commit: `6381c76e4833797462b9d5768dd3b9c09dfabb57`.
- Reference BHSA commit: `4db00e2157915495e1a4d3d57e41223df24775da`.
- Supported Text-Fabric range: `>=13.1,<14`.
- Exact Text-Fabric contract inspected for planning: tag `v13.1.0`.
- Exact pinned OCP snapshot used by permanent integration CI: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.

## Research gate

### 1. Architectural comparison

BHSA keeps corpus-specific behavior in the Text-Fabric app layer rather than maintaining a separate web server. At the reference commit its `app/` contains:

- `config.yaml` with `dataDisplay`, `docs`, `provenanceSpec`, `typeDisplay`, and `writing`;
- a tiny `app.py` whose corpus-specific behavior is limited to translating a BHSA lexeme into the identifier expected by SHEBANQ;
- one static logo.

The actual query/browser/server implementation is Text-Fabric infrastructure.

Pseudepigrapha-TF currently has only:

```yaml
apiVersion: 3
provenanceSpec:
  corpus: Online Critical Pseudepigrapha (Text-Fabric conversion)
  version: 0.1
```

There is no custom `app.py` and no static app content. The current gap is therefore application configuration and integration coverage, not a missing Pseudepigrapha-specific HTTP service.

Decision: keep the generic Text-Fabric server. Do not add a separate web service in this ticket.

### 2. Text-Fabric 13.1.0 app contract

The exact `v13.1.0` `tf/advanced/settings.py` contract confirms the declarative app layer already supports the controls needed for the first implementation:

- `dataDisplay.textFormat`, `exampleSection`, `exampleSectionHtml`, `excludedFeatures`, `noneValues`, browser navigation settings;
- `docs.docBase`, `docPage`, `featureBase`, `featurePage`;
- `provenanceSpec` including `org`, `repo`, `relative`, `version`, `branch`, and optional web-edition settings;
- `typeDisplay` including `hidden`, `label`, `template`, `features`, `featuresBare`, `boundary`, `children`, `level`, `flow`, `style`, etc.;
- `dataDisplay.textFormats` plus `app.py` `fmt_*` hooks when declarative formats are insufficient.

`tf.app.use()`/`tf.advanced.app.findApp()` also explicitly support a local app path of the form `app:/path/to/app`. This is relevant because Pseudepigrapha-TF intentionally does not commit generated `tf/0.1` corpus data.

Decision: declarative configuration is the default implementation route. Custom `app.py` is conditional on a failing semantic-rendering probe, not on BHSA precedent.

### 3. Distribution boundary affects app provenance

Pseudepigrapha-TF ships the converter and app source, but generated corpus data is materialized separately. Therefore a BHSA-style `use("org/repo")` path must not be advertised until the repository/release actually exposes fetchable versioned TF data in the location claimed by `provenanceSpec`.

Adding `org: alexsosn`, `repo: Pseudepigrapha-TF`, `relative: tf`, `version: 0.1` without testing this boundary could make Text-Fabric attempt to fetch a dataset that is deliberately absent from the repository.

Plan consequence:

- test the local materialized-corpus + local app path first;
- keep documentation URLs independent of remote-data-fetch assumptions where necessary;
- do not claim `tf alexsosn/Pseudepigrapha-TF` zero-preparation loading in this ticket;
- revisit remote fetching only if/when generated TF data is published as a supported artifact/release.

### 4. Pseudepigrapha-specific display hazard

The data layer already protects `T.text()` with type-specific formats:

- `reading-default -> reading_text`;
- `variant_word-default -> variant surface`;
- `manuscript-default -> ms_abbrev`;
- `resource-default -> resource_name`;
- `version_metadata-default -> version_title`;
- `ellipsis-default -> ellipsis_text`;
- `orphan_reading-default -> reading_text`;
- `document_metadata-default -> intro_label`.

This is necessary because several non-textual or alternative nodes have technical `oslots` anchors. In particular:

- an alternative `reading` occupies the primary reading locus for locality/search;
- `variant_word` nodes use one primary-locus technical anchor;
- manuscript/resource/version-metadata/document-metadata nodes use technical anchors;
- preserved empty/anomalous structures may use technical anchors while explicitly not claiming textual containment.

A browser configuration that lets those types inherit generic presentation can visually imply false containment or display the wrong anchor text. App-level display policy must preserve the same distinction already enforced by the data/API layer.

### 5. Node-type inventory and proposed initial policy

Builder/conversion/metadata code plus permanent pinned-CI assertions establish the following application-relevant type set. The first pinned integration gate for this ticket must obtain `tuple(api.F.otype.all)` from the exact generated corpus and prove that the declared policy covers the exact runtime set before production behavior is accepted.

| `otype` | Semantic role | Initial browser policy to test |
| --- | --- | --- |
| `word` | primary slot | visible/base; normal Unicode text |
| `book` | top section / exact textual version | normal section; expose `version_title`, `version_kind`, `language` as useful metadata |
| `chapter` | normalized TF section | normal section |
| `verse` | normalized TF section | normal lowest section/condense behavior |
| `div` | exact OCP source hierarchy | hidden by default; label from `div_label` + `div_number`; expose `source_ref` when shown |
| `unit` | textual apparatus locus | hidden by default for clean reading; label with `unit_id`; expose `source_ref` when shown |
| `reading` | mutually exclusive apparatus reading | hidden by default; label from source option; expose primary/omission state and witnesses when shown |
| `variant_word` | token belonging to non-primary reading | hidden by default; own node format must remain authoritative |
| `manuscript` | historical or citation-only witness / synthetic translation provenance | hidden by default; label with `ms_abbrev`; show provenance flags when explicitly displayed |
| `resource` | version resource metadata | hidden by default; label with `resource_name` |
| `version_metadata` | upstream version with no textual units | hidden by default; label with `version_title`; must never look like anchor text |
| `ellipsis` | preserved upstream `<elipsis>` marker | hidden by default but explicitly labeled; inspectable with hidden types enabled |
| `orphan_reading` | preserved direct-div reading anomaly | hidden by default but explicitly labeled; expose source reference/option when shown |
| `document_metadata` | public work-level `intros.json` metadata | hidden by default; label with `intro_label` |

Rationale for the initial hidden policy: default verse/book reading should remain a readable primary text. Apparatus/source-structure/metadata nodes remain queryable and can be revealed through the standard `hideTypes=False` mechanism. The RED rendering probe must confirm that an outer search result for a hidden type remains inspectable enough for research; if Text-Fabric's hidden behavior makes a directly requested apparatus node unusable, revise the policy rather than accepting invisible evidence.

Generated translations do not add a new `otype`; they use ordinary textual types with `version_kind=generated_translation`, `generated_language`, and explicit translation edges. Book-level display should make that classification visible when the generated version is being inspected.

### 6. Feature presentation policy

Do not use `excludedFeatures` as a generic way to simplify the corpus. It prevents the browser from loading those features, so every exclusion needs a concrete size/noise justification and must not remove semantic identity required by the configured labels/templates.

Initial candidates for browser exclusion are only lossless/raw payload representations that are poorly suited to the generic feature UI and already have structured researcher APIs or readable counterparts, for example:

- `reading_xml` (readable `reading_text` remains available);
- `ms_name_xml` (readable manuscript metadata remains available);
- `bibliography_xml` (structured/readable bibliography remains available);
- `source_ref_parts` (readable exact `source_ref` remains available);
- large `intro_*_json` HTML/scalar payloads if empirical app-load/rendering shows they materially degrade the browser.

The initial RED/GREEN cycle should start with the smallest exclusion set. Large public introduction fields must remain present in the TF dataset and accessible through `WorkMetadata`; excluding them from the browser is a display/load decision only.

Do not exclude text-format dependencies such as `prefix_utf8`, `g_word_utf8`, `trailer_utf8`, `boundary_utf8`, or identity/provenance features used by labels.

### 7. External OCP web links

Do not configure `webBase`, `webUrl`, or `webFeature` in the first implementation.

The Pseudepigrapha data model preserves stronger identifiers than a generic section template (`ocp_book`, exact `version_id`, exact `source_ref`), but the current OCP public reader/DTS transition does not yet provide a stable URL contract proven suitable for every version/deep reference. Legacy/decommissioned reader URLs must not become corpus metadata.

A stable OCP DTS/reader link contract can be a follow-up ticket once it is source-grounded and covers multi-version/deep-reference cases.

## Plan gate

### Phase 0 — close the empirical research inventory

Before any production config change, add a test/probe on the exact pinned conversion path that records/asserts the runtime `otype` set and checks each non-slot type against a declared app-policy inventory.

This closes the remaining gap between source-code inventory and exact generated-corpus inventory. A newly emitted type must fail the gate until its browser semantics are researched.

No production graph change is expected.

### Phase 1 — RED: application contract

Add `tests/test_tf_app_config.py` (or equivalent) with failing assertions against current `app/config.yaml`:

1. default format is explicitly `text-orig-full`;
2. a real existing section is provided as the browser example;
3. documentation routing points to tracked Pseudepigrapha-TF documentation;
4. every special/non-section `otype` in the declared runtime inventory has an intentional `typeDisplay` policy;
5. technical-anchor types have explicit labels/templates and cannot rely on generic slot-derived text;
6. `webBase`/`webUrl` are absent until an external URL contract is separately proven;
7. the config does not claim a remote TF data location that the repository does not publish.

The current four-line config must fail this gate.

The test should parse YAML semantically, not compare the whole file as a string.

### Phase 2 — GREEN: minimal declarative app config

Implement the smallest `app/config.yaml` that satisfies Phase 1 and the exact Text-Fabric 13.1.0 schema.

Candidate shape (not a frozen implementation; RED rendering tests may adjust individual type policies):

```yaml
apiVersion: 3

dataDisplay:
  exampleSection: 1En__Ethiopic 1:1
  exampleSectionHtml: <code>1En__Ethiopic 1:1</code>
  textFormat: text-orig-full

docs:
  docBase: https://github.com/alexsosn/Pseudepigrapha-TF/blob/main/docs
  docExt: .md
  docPage: tf-app
  featureBase: '{docBase}/features/<feature>{docExt}'
  featurePage: 0_home

provenanceSpec:
  corpus: Online Critical Pseudepigrapha (Text-Fabric conversion)
  version: 0.1

typeDisplay:
  book:
    features: version_title version_kind language
  div:
    hidden: true
    label: '{div_label} {div_number}'
    featuresBare: source_ref
  unit:
    hidden: true
    label: 'unit {unit_id}'
    featuresBare: source_ref
  reading:
    hidden: true
    label: 'reading {reading_option_source}'
    features: is_primary is_omission
    featuresBare: mss
  variant_word:
    hidden: true
    level: 0
  manuscript:
    hidden: true
    label: '{ms_abbrev}'
    features: undefined_manuscript synthetic_witness
  resource:
    hidden: true
    label: '{resource_name}'
  version_metadata:
    hidden: true
    label: '{version_title}'
  ellipsis:
    hidden: true
    label: '{ellipsis_text}'
    featuresBare: source_ref
  orphan_reading:
    hidden: true
    label: 'orphan reading {reading_option_source}'
    featuresBare: source_ref
  document_metadata:
    hidden: true
    label: '{intro_label}'
```

Do not add `writing`: the corpus is multilingual and one global BHSA-style writing code would be false. Text style must remain driven by Unicode/text formats rather than declaring the whole corpus Greek, Hebrew, Syriac, etc.

### Phase 3 — RED/GREEN: real Text-Fabric advanced-app rendering

Add `tests/test_tf_app_rendering.py` using real installed Text-Fabric, a deterministic locally generated fixture, and the repository app directory.

The test should exercise the advanced app API rather than only reading YAML. It must verify semantic output, not complete HTML snapshots.

Required cases:

1. normal book/verse rendering uses the primary slot text and `text-orig-full`;
2. non-primary `reading` displays its `reading_text`, never the primary-locus slot text;
3. `variant_word` displays its own variant surface;
4. `manuscript` displays `ms_abbrev`, never its technical anchor word;
5. `resource` displays `resource_name`, never its technical anchor word;
6. `version_metadata` displays `version_title`, never its technical anchor word;
7. `document_metadata` displays `intro_label`, never its technical anchor word;
8. `ellipsis` and `orphan_reading` use their own formats/labels and cannot visually become their parent anchor word;
9. hidden-by-default apparatus types can still be intentionally revealed/inspected;
10. generated-translation books expose source/generated classification without being confused with historical witnesses.

Prefer `A.plain()`/`A.pretty()` returned/observable semantic fragments and the app context over brittle full-page markup assertions.

### Phase 4 — local app + materialized corpus startup contract

Add a deterministic test/documented invocation for the supported current distribution boundary:

- materialize TF to a temporary/local version directory;
- load the app from the repository/local `app/` path;
- point Text-Fabric at the local materialized data through the supported 13.1 API;
- prove no network fetch is required;
- verify that docs/config/app loading succeeds in a fresh environment.

Do not advertise a remote `org/repo` data fetch until this repository actually publishes the versioned TF dataset in the location Text-Fabric expects.

If the 13.1 API makes a combined local app + external local data location awkward, document the exact supported invocation and keep the config honest rather than adding misleading provenance fields merely to simplify a command.

### Phase 5 — feature documentation without duplicated semantics

Create `docs/tf-app.md` and `docs/features/0_home.md`.

Individual feature pages should be generated or mechanically validated from the same canonical descriptions already stored in `FEATURE_DESCRIPTIONS`, `EDGE_DESCRIPTIONS`, and later metadata attachment modules. The implementation should avoid a second independently maintained prose definition for every feature.

Preferred design:

- a small deterministic documentation generator consumes canonical metadata descriptions;
- generated tracked pages include feature type/value type, description, and a link/context note where needed;
- a CI test regenerates into a temporary directory and compares tracked outputs, failing on drift;
- specialized pages may extend generated content for features whose scholarly semantics need more explanation, but generated core definitions remain authoritative.

If generation proves disproportionately invasive, reduce scope to an app landing page plus mechanically checked links and create a follow-up ticket for full per-feature documentation rather than hand-writing a drifting duplicate catalog.

### Phase 6 — decision gate for custom `app.py`

After declarative config and real rendering tests are green, inspect representative apparatus passages with multiple alternatives and omissions.

Only create `app.py` if a concrete RED test shows declarative Text-Fabric presentation is still semantically misleading or unusable.

If a custom apparatus format is necessary:

- add a separate RED semantic-rendering test first;
- implement a `fmt_*` method through `dataDisplay.textFormats`;
- reuse `Apparatus` semantics or a shared lower-level formatter; do not independently reinterpret `reading`, `omission`, `unattested`, or synthetic-witness rules;
- keep it a display adapter, not a new server or alternate research API.

If declarative rendering is sufficient, explicitly record that `app.py` is unnecessary and leave it absent.

## Verification gate

Run all of these on the same implementation head:

1. new app config contract tests;
2. new real-Text-Fabric app/rendering tests;
3. complete existing `pytest` suite;
4. wheel build + fresh install;
5. exact pinned OCP conversion at `c939dcbacad78c5d18d2c4282cad23c47e19ac07`;
6. independent raw-source semantic parity report;
7. real TF reload and current apparatus/generated-translation/public-metadata/classification/license interface checks;
8. exact runtime `otype` inventory vs app-policy drift check;
9. local materialized-corpus app startup without external network dependency.

No Selenium/browser-driver dependency is planned. If server routing itself needs a regression, use Text-Fabric/Flask's test client in-process.

## Independent adversarial review gate

A logically independent reviewer must inspect the exact green head and challenge at least:

- every runtime `otype` has a deliberate display outcome;
- hidden defaults do not make source evidence impossible to inspect;
- labels/templates cannot expose technical anchor text as node content;
- `reading`, `omission`, and `unattested` semantics are not flattened by presentation;
- generated translation provenance and `OCP-Trans` synthetic witnesses remain visually distinguishable from source/historical evidence;
- no researcher-significant feature was excluded merely to make the browser cleaner;
- raw XML/HTML exclusions, if any, are browser-load decisions only and data remains queryable through the TF/API layer;
- documentation definitions cannot silently drift from canonical feature metadata;
- no unstable/decommissioned OCP URL was introduced;
- no remote-data availability is claimed while generated TF remains unshipped;
- no custom server or custom Python app code was added without a failing semantic requirement;
- tests assert corpus semantics rather than incidental HTML formatting.

Any blocker becomes a new RED regression or a research/plan correction, followed by implementation, the complete verification gate, and another exact-head independent review.

## Out of scope

- publishing generated TF data or changing the current corpus redistribution boundary;
- building a standalone Pseudepigrapha web server;
- implementing OCP DTS integration before a stable external URL contract is established;
- changing the graph model, apparatus semantics, generated-translation alignment, or technical-anchor architecture merely for display convenience;
- adding a global writing code to a multilingual corpus.
