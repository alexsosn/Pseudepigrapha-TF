# Issue #160: anonymous manuscript display in the Text-Fabric app

## Observed contract

Pseudepigrapha-TF intentionally preserves unaddressable manuscript metadata records when direct-model/legacy-like input contains blank or whitespace-only `Manuscript.abbrev`. The modern XML boundary remains stricter and rejects blank required `ms/@abbrev`; issue #158 and PR #159 did not relax that validation. After Text-Fabric serialization, an intentionally blank `ms_abbrev` is exposed as `None`, while the manuscript node and fields such as `ms_name` remain preserved.

The tracked advanced app is also the documented generic interface for raw-node inspection. `app/config.yaml` currently gives the `manuscript` technical type both `template: '{ms_abbrev}'` and `label: '{ms_abbrev}'`, and `TfApp._plain_own_content()` delegates manuscript rendering to that template. Consequently, a preserved anonymous manuscript can have useful `ms_name` metadata yet no visible own-content in `pretty()`.

This differs from apparatus semantics. The `Apparatus.witnesses` mapping must remain keyed only by usable nonblank sigla; issue #158 correctly excludes anonymous metadata from that mapping. The advanced app, however, should make the preserved raw node inspectable rather than visually empty.

## Intended behavior

For `manuscript` nodes only, keep the existing `ms_abbrev` rendering when the abbreviation is nonblank. When it is absent/blank/whitespace after TF reload, use the preserved plain-text `ms_name` as a presentation fallback if nonblank. The fallback is display text, not a scholarly identifier: do not populate `ms_abbrev`, invent a siglum, change graph edges, or alter apparatus behavior.

The fallback must be HTML-escaped because source text can contain characters meaningful in markup. It must continue to stop Text-Fabric's plain-rendering recursion before the technical `oslots` anchor is rendered as manuscript content.

If both abbreviation and name are absent, leave the content empty rather than fabricating identity.

## Verification target

Construct the already-sanctioned direct-model case from `sample.xml`, append a manuscript with whitespace-only abbreviation and a distinctive preserved name, serialize with `write_tf`, and load through the tracked advanced app. Verify the anonymous node survives, `ms_abbrev` reloads blank/`None`, `ms_name` survives, and `pretty()` displays the escaped name without primary anchor text. Also retain coverage that ordinary manuscripts render by siglum.