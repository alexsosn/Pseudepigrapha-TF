# Issue #180 — Source XML structural mixed-content boundary

**Frozen research and implementation plan.** Written before RED-first tests and production changes.

## Direct evidence in code

- `source_structure.validate_source_structure` walks the full ElementTree and checks child tags, attributes, identity fields and known anomalies; **no check on `Element.text` / child `Element.tail`** exists.
- `parser._parse_div` iterates only child `div`, `unit`, direct anomalous `reading` and `elipsis`; `_parse_unit` only walks `reading`; `_parse_version` only specific XML subelements; `_parse_legacy_divs` only `chapter/verse/unit`. Non-whitespace text directly under these containers can be silently discarded in both model and graph, even while a raw inventory based on the same recognized elements agrees.
- **Preserved legitimate mixed content must not be rejected:** `reading` and its `w` tails are read by `_tokens` and `_inner_xml`; `name`/`sup`, `bibliography`/`booktitle`, `division` body descriptions, `elipsis`, `info`, `URL` and `w` text are consumed by `_plain_text` or kept as XML.

## Chosen fail-closed boundary

Check `Element.text` and direct-child `Element.tail` only for **structural-only parent elements**:
`book`, `version`, `divisions`, `resources`, `resource`, `manuscripts`, `ms`, `text`, `div`, `unit`, `chapter`, `verse`.

For these elements, only whitespace (`str.isspace`; XML indentation, spaces, tabs and CRLF) is allowed between recognized children. Reject any other character as unsupported source content. Do not trim/move/normalize source text and do not reject inline tails in recognized mixed-content parents. The existing iterative validator already traverses every node exactly once; perform one linear scan of each parent text/tail, preserving asymptotic complexity.

A structural parent with no children but non-whitespace text is equally unsupported. Raise `SourceStructureError` with source pathname, owning parent element/path and specific `direct text` vs `tail after <child>` information. `parse_bytes` rewraps this as `InvalidSourceError`; raw audit should independently reject the same mutated input.

## RED → GREEN → independent review

1. Test-only commit (RED): positive baseline source plus parametrized mutations to `book/version/divisions/resources/resource/manuscripts/ms/text/div/unit`, and legacy `chapter/verse`; test both direct `.text` and child `.tail`, including significant text interspersed with whitespace. Confirm previously accepted inputs now fail tests. No production edits yet.
2. Positive control tests: actual reading with `<w>` plus trailing text, manuscript `<name>` with `<sup>` plus trailing text, bibliography inline `<booktitle>`, division description, legacy reading, and whitespace CRLF structural formatting remain valid and preserve existing model/serialized representations. Test that validation does not mutate `Element.text`/`tail` values.
3. Add minimal constant whitelist and checks in `source_structure.validate_source_structure`, then unit/TF suite GREEN.
4. Full pinned upstream OCP XML conversion + semantic audit, release ZIP offline Text-Fabric reload, actual 1En comparison CI success; if legitimate pinned structural non-whitespace is observed, inspect its concrete source record, and decide whether to model it rather than bypassing validation.
5. Perform a genuinely independent skeptical review against final patch, real fixture/source behavior, tests, exact CI head; post review to GitHub and merge only after gates.

## Non-goals and limits

- Not DTD expansion or full DTD order/cardinality validation.
- Not preserving unsupported structural free text by misattributing it to a neighboring `reading`.
- Not banning legitimate mixed text in content-bearing elements.
- Fail-closed source refreshs may reject previously accepted *lossy* custom XML until a proper mapping is implemented.

## Pre-merge adversarial refinement of the frozen plan

The original plan proposed Python `str.isspace()` to recognize formatting whitespace. Independent inspection of the initial implementation showed that `isspace()` also returns true for U+00A0 NO-BREAK SPACE, U+2007 FIGURE SPACE and U+2028 LINE SEPARATOR, which are **not** the XML 1.0 `S` formatting characters. Those characters can encode meaningful textual evidence and must not be silently discarded even under a structural-only node.

A supplementary **RED-only** test commit `035db127c6e827a3e24e402250cb62584aa5bcf3` (Actions run `38093722761`) verified **6 expected failures, 686 passing tests**, covering all three code points in both direct text and child tails on top of the original 38 failures / 648 passing baseline. The revised implementation compares against exactly `" \\t\\r\\n"` (XML space, tab, CR, LF), preserving standard pretty-printing and rejecting Unicode separators. This refinement does not widen acceptance or change content-bearing mixed-XML handling.
