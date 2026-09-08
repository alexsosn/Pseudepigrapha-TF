# Text-Fabric application and browser

Pseudepigrapha-TF uses Text-Fabric's generic advanced application and browser. The repository does not implement a separate corpus-specific web server.

## Loading a local materialization

The current release contract is converter-first: generated `tf/0.1` data is materialized locally rather than committed to this repository. Until the canonical remote distribution contract is defined, do not assume that `use("alexsosn/Pseudepigrapha-TF")` can fetch the corpus data from GitHub.

A local materialized corpus can be paired with the tracked app directory through Text-Fabric's local-app support. In programmatic integration, use the repository `app/` directory together with the local TF data location. The test suite exercises this path with the real Text-Fabric advanced API, including the exact pinned full OCP materialization, without relying on a remote TF-data contract.

Canonical remote publication, release identity, and Agora/Text-Fabric loading semantics are tracked separately in issue #97.

## Default text view

The app uses `text-orig-full` as its default text format and keeps the ordinary `book` / `chapter` / `verse` / `word` stream as the primary browser view. Book nodes expose version title, version kind, and language so source versions and generated translations remain distinguishable.

The corpus is multilingual, so the app deliberately does not declare one global Text-Fabric `writing` value.

## Apparatus and technical anchors

Several non-slot node types preserve source structure or scholarly apparatus while using an `oslots` position only because Text-Fabric requires non-slot nodes to occupy slots. For these nodes, an `oslots` edge can be a technical anchor rather than the node's textual content.

The YAML app configuration is the single source of display policy. It distinguishes two groups:

- `div` and `unit` are hidden by default but remain structural. Revealing them can show the primary textual locus they organize.
- `reading`, `variant_word`, `manuscript`, `resource`, `version_metadata`, `ellipsis`, `orphan_reading`, and `document_metadata` are hidden by default and configured as Text-Fabric base types. Their browser templates mirror the same own-content features used by their dedicated TF text formats.

Not every valid materialization contains every technical type. For example, the current pinned full OCP snapshot contains no `resource` nodes, while resource nodes remain supported by the converter. Text-Fabric normally reports any configured-but-absent `typeDisplay` entry as an app configuration error. `TfApp` therefore postpones validation of the technical-type entries and reapplies only those whose node types are actually present. This keeps full and subset materializations clean without maintaining a second policy table in Python.

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

For witness reconstruction and omission/unattested semantics, use the public `Apparatus` API. Browser display is a presentation layer and does not replace the graph's `reading_of`, `witness`, `variant_word_of`, or other scholarly relations.

## Feature help

Per-feature browser-addressable reference pages are intentionally handled in issue #96 so that they can be generated or validated from the canonical TF feature metadata instead of duplicated by hand here.

## External edition links

The app does not currently define `webBase`, `webUrl`, or lexeme-web links. OCP's public reader/API surface is being treated as a separate stability contract; links will only be added after a current stable identifier/URL scheme is demonstrated.
