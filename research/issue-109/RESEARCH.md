# Issue #109 research — verse-level manuscript, translation, and version comparison

Baseline repository head: `ec0139670ffeeb80dabb3668bbed7af69049e8e8`.

Reference Text-Fabric source inspected: `annotation/text-fabric@1079c68e051947efd955b61ad499e3a9beb03b09`, which reports Text-Fabric `13.1.0`. The project dependency contract is `text-fabric>=13.1,<14`.

Pinned OCP source used by CI: `OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha@c939dcbacad78c5d18d2c4282cad23c47e19ac07`.

## User-validation finding

The browser work completed under #95 fixed false *node content* caused by technical `oslots` anchors, but it did not make the primary textual-criticism workflow usable. Generic TF browsing still exposes manuscripts, source versions, and generated translations along graph/section axes that do not match the research question.

The desired primary interaction is `work -> chapter -> verse`, with source/critical versions compared at the same passage, historical witness readings compared inside each source version, and generated translations shown under the exact source version and passage that they translate.

The data model must remain unchanged for this issue. Technical manuscript anchors are positional implementation details and must never be consulted to reconstruct a witness reading.

## Existing semantic APIs are sufficient

`pseudepigrapha_tf.apparatus.Apparatus` already provides the required historical semantics.

- `work_passage(work, chapter, verse)` groups textual versions by `ocp_book` and explicitly excludes `version_kind == generated_translation`.
- Each textual version has `available` or `not_present` passage status.
- Metadata-only versions are returned separately in `metadata_only_versions`.
- For an available passage, the returned unit records expose primary/alternative readings and witness sigla.
- Per-witness passage records preserve segment-level `reading`, `omission`, and `unattested` states. A partially unattested witness is not silently promoted to complete text.

`pseudepigrapha_tf.translations.Translations` already provides the generated layer semantics.

- `versions(work=...)` returns generated translation books with explicit `source_id` / `source_node` from `translation_of` and generation provenance.
- `passage(generated_book, chapter, verse)` resolves the requested generated section and returns `translation_unit_of`-aligned source/translation units in document order.

A comparison UI should therefore assemble a presentation view-model from these two public APIs. It must not reproduce `reading_of`, `witness`, `translation_of`, or `translation_unit_of` traversal rules.

## Exact TF 13.1 browser extension boundary

The generic browser is a Flask app built in `tf.browser.web.factory(web)`.

At the inspected TF 13.1 source:

- `factory()` creates the Flask application and registers a fixed route set for static assets, sections, tuples, query, passage, export/download, and the catch-all index route;
- `servePassage()` reads `sec0`, `sec1`, and `sec2` from browser form state and calls `kernelApi.passage(...)`;
- `TfKernel.passage()` resolves one `sec0Node = T.nodeFromSection((sec0,))` and composes passage content from descendants of that one section/book;
- corpus `app.py` is loaded through `findAppClass()` as a `TfApp` subclass and is an application/display customization surface; no corpus hook is invoked by `factory()` to register a Flask route or blueprint;
- app-specific static files are already served by the generic browser under `/data/static/...`.

Consequently the stock `/passage` endpoint cannot express a view that aggregates sibling TF `book` nodes representing multiple OCP versions of one work. Declarative `config.yaml`, custom text formats, and `TfApp` rendering hooks can improve a node display but cannot change this cross-book passage aggregation rule.

The smallest viable integration is to keep the TF browser's Flask app/kernel and register one more, more-specific route on that same Flask application after `factory()` constructs it. The launcher may reuse TF's `Web`, `makeTfKernel`, `factory`, and `runWeb`; it must not introduce a second corpus server or parallel TF loader.

This integration necessarily touches TF browser internals because TF 13.1 does not expose a supported corpus route-registration hook. Compatibility tests must therefore fail clearly if the imported TF 13.x browser surface changes.

## Real pinned-corpus acceptance case

`static/docs/1En.xml` in the pinned OCP source is a suitable full-corpus case.

It contains source versions including:

- Ethiopic;
- Qumran Aramaic;
- Latin Fragments;
- Greek.

It also contains OCP-generated English and French versions corresponding to source versions; conversion maps these into the generated translation layer rather than historical source versions.

The Ethiopic version declares at least witnesses `p` and `Bertalotto`. At 1 Enoch 1:2 the source contains multiple apparatus units, including unit `3`, where `p` reads `ራዕየ፡` and `Bertalotto` reads `ራእየ፡`. This gives a deterministic real-corpus assertion that two manuscripts at one verse must not collapse to the same technical anchor text.

The existing pinned-upstream CI already builds the complete corpus and verifies 231 generated translation versions, 54,143 aligned generated units, full `translation_of` / `translation_unit_of` coverage, and English/French generated-language counts. #109 can extend that existing job instead of creating a separate upstream download/build path.

For omission/unattested edge cases, focused synthetic tests are preferable because they can force all required states in a small deterministic graph without depending on the current scholarly contents of one upstream passage.

## Interaction and view-model decisions

### Primary identity

The comparison page is addressed by OCP work identity plus chapter and verse: `work`, `chapter`, `verse`. Source version ids remain TF section/book ids and are displayed/selectable inside that work.

Generated translation ids never enter the source-version selector. They are grouped by the explicit `source_id` from `Translations.versions()`.

### Source version cards

The page exposes all textual source/critical versions as available choices but renders a bounded default selection to avoid an unreadable wall. The default is up to two textual versions, preferring versions where the requested passage is available. Users may explicitly select more.

A selected version with no matching passage remains visible with `not present`. Metadata-only versions appear in secondary metadata, never as textual comparison cards.

The version's primary passage text is reconstructed only from `primary=True` readings already returned in `Apparatus.work_passage()`. No technical manuscript or metadata anchor participates.

### Witness rows

Witness rows are built from the passage's returned witness records and keep segment states. Their display must preserve distinctions among:

- reading text;
- explicit omission;
- unattested coverage.

The default witness selection is bounded and prefers declared/showable witnesses; users can request additional sigla. Siglum, name, and language come from the witness metadata already returned by `Apparatus`.

### Generated translations

For each source version card, translation candidates are the generated records whose explicit `source_id` equals that source version id. Requested-passage translation text comes from `Translations.passage()` aligned units.

Multiple translations are presented as compact toggles/details beneath the source text. Language/method/model/marker are secondary metadata. A generated translation whose requested section is absent receives its own `not present` state rather than borrowing source text.

### Navigation

Previous/next passage navigation uses section topology only. It may inspect `verse` descendants of an available selected/source book to obtain neighboring `(chapter, verse)` section addresses, but it must not infer witness/version alignment from `oslots`.

Navigation preserves source-version and witness selection query parameters.

### Responsive layout

Desktop renders selected source versions as cards in a comparison grid. Narrow screens stack the same cards vertically. Witness state labels remain explicit, so understanding the comparison does not depend on horizontal alignment alone.

## Testing boundary

Three layers are required.

1. Pure view-model tests verify grouping, source-version selection, primary text, witness state preservation, generated translation attachment, metadata-only handling, and `not present` behavior.
2. Deterministic HTML tests verify semantic labels/order, escaping, inline translation placement, and responsive-class contract without full-page snapshots.
3. Real TF/Flask integration tests verify the comparison route can be registered on the stock TF Flask app, the ordinary TF root route remains operational, and technical anchor text never becomes manuscript reading text.

The pinned-upstream job adds a full-corpus smoke/semantic assertion using 1 Enoch 1:2 and its real generated translations.

## Explicit non-goals

- no TF serialization or anchoring changes;
- no new scholarly edge semantics;
- no replacement for generic TF query/search/node inspection;
- no Selenium/browser-driver dependency;
- no second long-running web server implementation;
- no inference of translation or witness relationships from ordering, names, or technical `oslots`.
