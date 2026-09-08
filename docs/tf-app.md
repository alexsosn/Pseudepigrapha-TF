# Text-Fabric application and browser

Pseudepigrapha-TF uses Text-Fabric's generic advanced application and Flask browser. It does not maintain a second corpus web server. The `pseudepigrapha-tf browse` launcher loads the tracked `TfApp` in Text-Fabric browser mode, creates the stock Text-Fabric Flask application/kernel, and registers one corpus-specific `/compare` route on that same application. The ordinary Text-Fabric browser remains available at `/` for search, graph inspection, node display, and other generic TF work.

## Loading a local materialization

The current TF data release identity is `0.2`. For a checkout containing the tracked `app/` directory and a local materialization, run:

```bash
pseudepigrapha-tf browse tf/0.2 --app app
```

The `--version` default follows the package's authoritative `TF_DATA_VERSION`; it is not maintained as a separate browser constant. `--port` defaults to `8000`, and `--debug` enables the underlying Text-Fabric/Flask debug mode.

The launcher deliberately uses the same browser-mode loading contract as Text-Fabric's own web setup. A programmatic caller may use `load_local_comparison_web_app(data_path, app_path, version=...)` when it needs a Flask application/test client rather than a listening server.

## Verse comparison workflow

Open `/compare` to choose an OCP work, chapter, and verse. The result page is centered on one passage and keeps source-critical evidence separate from generated text:

- source-version selectors contain textual OCP source/critical versions only; generated translations are never peer source choices;
- two available source versions are selected by default when possible, while an explicitly selected version that lacks the requested passage remains visible as `not present`;
- metadata-only versions are listed separately and are not fabricated into textual passages;
- each source-version card shows its primary source text and historical manuscript comparison;
- manuscript segments preserve the distinct `reading`, `[omission]`, and `[unattested]` states supplied by `Apparatus`;
- the witness selector is submitted with the same comparison form, so a researcher can reduce or change the witnesses shown for each selected source version;
- English/French generated translations are nested under the exact source version identified by `translation_of`/`source_id`; they are expandable and include the preserved generation provenance;
- generated passage content comes from `Translations.passage()`, including occurrence-aware source/translation unit alignment;
- Previous/Next links are derived from the actual TF `verse` topology of a source version that contains the current passage. If a preferred selected version lacks that passage, navigation falls back to another source version of the same work rather than assuming identical cross-version coverage;
- Previous/Next links retain the selected source versions and witnesses.

A source ambiguity remains an error rather than a UI guess. For example, if one manuscript is assigned to multiple competing readings at the same unit, the comparison route returns a readable HTTP 400 diagnostic from the underlying apparatus contract.

The comparison page is a researcher-facing projection of the existing graph APIs. It does not reconstruct witness readings from `oslots`, scrape rendered TF text, or maintain a second scholarly interpretation layer.

## Default text view

The generic app uses `text-orig-full` as its default text format and keeps the ordinary `book` / `chapter` / `verse` / `word` stream as the primary browser view. Book nodes expose version title, version kind, and language so source versions and generated translations remain distinguishable.

The corpus is multilingual, so the app deliberately does not declare one global Text-Fabric `writing` value.

## Apparatus and technical anchors

Several non-slot node types preserve source structure or scholarly apparatus while using an `oslots` position only because Text-Fabric requires non-slot nodes to occupy slots. For these nodes, an `oslots` edge can be a technical anchor rather than the node's textual content.

The YAML app configuration is the single source of generic display policy. It distinguishes two groups:

- `div` and `unit` are hidden by default but remain structural. Revealing them can show the primary textual locus they organize.
- `reading`, `variant_word`, `manuscript`, `resource`, `version_metadata`, `ellipsis`, `orphan_reading`, and `document_metadata` are hidden by default and configured as Text-Fabric base types. Their browser templates mirror the same own-content features used by their dedicated TF text formats.

Not every valid materialization contains every technical type. For example, the pinned full OCP snapshot contains no `resource` nodes, while resource nodes remain supported by the converter. Text-Fabric normally reports any configured-but-absent `typeDisplay` entry as an app configuration error. `TfApp` therefore postpones validation of the technical-type entries and reapplies only those whose node types are actually present. This keeps full and subset materializations clean without maintaining a second policy table in Python.

Text-Fabric 13.1 needs one additional rendering hook. During `pretty()` rendering of a base non-slot, Text-Fabric internally asks for a plain rendering of the same unravel tree. Even after an explicit parent template is rendered, that plain pass normally continues into the node's `oslots` children. For the technical-anchor node types above this can append unrelated primary-locus text after the node's own content.

`app/app.py` therefore registers one shared `plainCustom` hook for the present own-content technical node types. The hook delegates the node's actual content back to Text-Fabric's configured template renderer and stops the plain pass before it descends into the technical anchor. It does not reconstruct apparatus or witness semantics. The only semantic presentation special case is an explicit empty `reading`, which is shown as `[omission]` instead of as visually empty content.

Hidden types are not removed from the graph. Researchers can reveal them with Text-Fabric display options such as `hideTypes=False`, query them normally through the TF API, and traverse their explicit edges.

In particular:

- alternative `reading` nodes render their own `reading_text`, not the primary reading occupying the locus;
- explicit empty readings remain visibly marked as omissions;
- `variant_word` nodes render their own variant-token surface;
- `manuscript` nodes render `ms_abbrev`;
- `resource` nodes, when present, render `resource_name` without making resource-free corpora emit configuration errors;
- metadata and preserved anomaly nodes use their own identity/content features rather than the anchor word.

For programmatic witness reconstruction and omission/unattested semantics, use the public `Apparatus` API. For generated parallel text and occurrence-aware alignment, use `Translations`. Browser presentation does not replace the graph's `reading_of`, `witness`, `variant_word_of`, `translation_of`, or `translation_unit_of` relations.

## Feature help

Per-feature browser-addressable reference pages are generated/validated from the canonical TF feature metadata under `docs/features/` and are linked by the app configuration.

## External edition links

The app does not currently define `webBase`, `webUrl`, or lexeme-web links. OCP deep links will only be added when a stable current reader/DTS identifier contract is demonstrated; legacy/decommissioned routes are not treated as stable identifiers.
