# Issue #182 — XML singleton-child cardinality and source preservation

**Frozen research/plan before RED tests and implementation.**

## Actual parser branches examined

- `parser._parse_version`: `find("divisions")`, `find("manuscripts")`, `find("text")` consume only one child each. Extra recognized siblings are never traversed by conversion.
- `parser._parse_legacy_version`: `find("manuscripts")`, `find("text")` similarly lose duplicates at a legacy book root.
- `parser._parse_manuscript`: `find("name")` consumes one; `findall("bibliography")` consumes *all* bibliographies.
- `parser._parse_resource`: `find("URL")` consumes one; `findall("info")` consumes all.
- `parser._parse_version` iterates `findall("resources")`, `findall("resource")`; source versions, divs, units, readings and annotated words are iterated and preserve multiplicity. No blanket de-duplication.
- `source_structure.validate_source_structure` validates tag/attributes and existing witness abbrev identities but has no per-parent cardinality gate. The raw audit's recognized-subtree traversal need not notice an additional `find()`-discarded child, so the parser should fail closed at its common boundary.

## Chosen validation policy

Enforce **at most one** (not mandatory new presence) of each **direct** singleton child:

| Parent | Direct children at most once |
| --- | --- |
| `book` (legacy root) | `manuscripts`, `text` |
| `version` (modern or wrapped legacy) | `divisions`, `manuscripts`, `text` |
| `ms` | `name` |
| `resource` | `URL` |

Use one per-parent `seen` set in the existing iterative traversal; duplicate error must name the source file, parent tag, child tag and XML path. The tag whitelist rejects unsupported parent/child arrangements as it already does. No changes to Text-Fabric nodes/slots/metadata and no arbitrary deduplication of source input.

## Research → RED → GREEN → real-data → skeptical review

1. RED-only tests mutate **otherwise valid** modern sample, legacy sample, and converted/wrapped legacy samples with a second meaningful `divisions`, `manuscripts`, `text`, `name`, or `URL`; test `parse_bytes` and independent raw inventory fail closed with good diagnostics. These tests must fail against current production behavior.
2. Positive tests retain repeated `resources`, repeated `info`, repeated `bibliography`, multiple `version` siblings and repeated divs/units/readings, and preserve actual XML text (not just counts).
3. Implement minimal cardinality checking and run full unit/TF suite.
4. Run unchanged pinned OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`: complete conversion, semantic audit, stock `complete.zip` offline load, app and 1 Enoch comparison tests must pass. If the upstream corpus itself contains singleton duplicates, inspect exact bytes and add explicit representation rather than silently accepting lossy conversion.
5. Freeze final tested head; logically independent adversarial review against actual patch, errors, real corpus, and documented constraints; post directly to PR and only merge with both CI gates green.

## Boundaries

A singleton field duplicated with identical literal values is still unsupported because the converter promises one source-to-model mapping, not implicit normalization. XML child **order** and missing mandatory DTD fields are deliberately outside this issue unless required by an existing independent validation gate. Concurrency/performance impact is negligible: one set membership check per recognized child.
