# ADR-0002: Keep the OCP semantic converter; treat Text-Fabric-Factory as reference material

Status: Proposed (issue #165; research-only, no migration authorized)
Date: 2026-10-10
Scope: Pseudepigrapha-TF source ingestion and Text-Fabric conversion

## Decision

**Use `annotation/text-fabric-factory` as implementation/reference material only.** Do not adopt `tff.convert.tei` or the default `tff.convert.xml` as the primary OCP converter; do not add a runtime dependency on Text-Fabric-Factory. Continue converting the pinned Grammateus/OCP XML using `parser.py` → semantic models (`model.py`) → `graph.py` → `writer.py`, with the existing independent raw-source and post-TF semantic audits.

This is a **source-format and semantic-contract decision**, not a claim that Text-Fabric-Factory is poor quality for its intended corpora. Revisit it if OCP actually releases a semantically specified TEI source, and only after an independently reviewed equivalence test.

## 1. Authoritative source-format finding

- The released corpus and full CI gate consume root-level `static/docs/*.xml` from [OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/tree/c939dcbacad78c5d18d2c4282cad23c47e19ac07/static/docs). `source.validate_source_boundary` excludes unreviewed directories/files and accepts `intros.json` separately. See `.github/workflows/test.yml` (clone, pinned checkout, full conversion/parity).
- At that commit, the directory has **39 root XML filenames**, but **`3Macc.xml` is zero bytes**, so the successfully converted source inventory contains **38 files**. The file count is independently visible in the pinned conversion report (`source.files = 38`, CI workflow run `38070460306`, `pinned-upstream-integration`). Do not describe the corpus as 39 nonempty critical editions.
- Representative pinned source files [`Aristob.xml`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/static/docs/Aristob.xml), [`ApocrEzek.xml`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/static/docs/ApocrEzek.xml), and [`4Q548.xml`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/static/docs/4Q548.xml) have a **`<book>` root** with `version/divisions/manuscripts/text/div/unit/reading` structures, not a TEI namespace, `TEI` root, `teiHeader`, or TEI `app/lem/rdg` structure. `4Q548.xml` contains a literal internal DTD describing this Grammateus vocabulary. The checked-in [`grammateus.dtd`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/static/docs/grammateus.dtd) explicitly declares `book`, `version`, `divisions`, and `reading`.
- The [upstream README](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/master/README.md) calls `static/docs` 'TEI XML' and says there are 39 editions. These are **repository-level descriptions**, not evidence of TEI-conformant source markup. The converter itself deliberately rejects roots other than `book` (`parser.parse_bytes`).
- Public OCP text citations, public metadata (`intros.json`), generated translations, and historical classification snapshots have distinct provenance. No evidence was established for a separate, richer, authoritative TEI feed in the pinned release. We **cannot claim** the custom XML is semantically equivalent to or transformed from a hypothetical TEI source; the required cross-format source-pair evidence is absent.

## 2. Pinned real-data semantic baseline

The fully exercised pinned conversion/parity gate (run `38070460306`, job `pinned-upstream-integration`, commit `575a3d531f13f49825e5fdad604d22ff8a2c37e6`) reports:

| Contract | Source inventory | TF graph / acceptance |
|---|---:|---|
| Files processed | 38 | 39 root XML names; `3Macc.xml` empty and skipped |
| Source versions | 349 | 349 versions |
| Apparatus readings | 87,811 | 87,811 readings; 124,278 witness edges |
| Units | 81,275 | 81,275 units |
| Division structures | 46,684 | 46,684 div nodes |
| Manuscripts | 454 | 454 manuscript nodes |
| Generated translations | 231 versions; 54,143 units | 231 `translation_of` and 54,143 `translation_unit_of` edges; exact alignment checked |
| Metadata only | present | 1 metadata-only TF version |
| Missing literal unit IDs | 1 | 1 source-anomaly marker, without manufactured ID |
| Orphan readings | 9 | 9 `orphan_reading` nodes |
| Structural ellipses | 1 | 1 `ellipsis` node |
| Public metadata | 32 documents | 32 document nodes; 244 scalar values |

The gate also checks conversion report semantic booleans, TF 13.1 reload, fresh offline stock `complete.zip` load, generated-to-source alignment and full comparison acceptance. Its tests exercise actual 1 Enoch multilingual witnesses/translations, a `TJob` metadata-only sibling and omissions, `PssSol` ambiguous manuscript assignment (must raise a readable error), `Aristob` `<elipsis>` and deeply nested citations, and `4Ezra` repeated source addresses (`~2`). See `tests/pinned_comparison_acceptance.py`, `tests/pinned_translation_acceptance.py`, and `docs/source-identity-and-anomalies.md`.

These are **current baseline facts**, not measurements of a Text-Fabric-Factory-produced corpus. No factory-generated 1:1 corpus or runtime benchmark was executed in this research; therefore no numeric factory-vs-native performance claim follows.

## 3. Factory implementation findings

- [`tff.convert.tei`](https://github.com/annotation/text-fabric-factory/blob/master/tff/convert/tei.py) is a production-oriented **TEI** importer. It understands TEI schema classifications (including mixed content), customizable schema/templates, validation pathways, and `beforeTag`/related hooks. The pinned OCP root vocabulary is not TEI; feeding it into the TEI path would be a mismatch unless someone first supplied a genuine TEI transformation with a verified semantic mapping.
- [`tff.convert.xml`](https://github.com/annotation/text-fabric-factory/blob/master/tff/convert/xml.py) explicitly describes its general XML path as **an example of how to perform a conversion, rather than a production engine**. It does not read a source schema by default.
- Its [default director in `tff/convert/xmlCustom.py`](https://github.com/annotation/text-fabric-factory/blob/master/tff/convert/xmlCustom.py) creates `cv.node(tag)` for each XML element, forwards attributes as features, and issues **`cv.slot()` per character** (with generic zero-width-space slots for empty XML elements). In particular it has no OCP-specific apparatus/witness edges, version classification, source occurrence identity, manuscript abbreviation resolution, generated translation provenance or exact source-unit alignment. A generic serialization success would **not** establish equivalence.
- One could replace the director/hooks with an OCP-aware implementation; that would effectively reimplement the current parser, semantic model, writer and fail-closed edge logic inside a new framework. No demonstrated payoff compensates for regression, dependency and migration risks.
- The factory is MIT licensed, and its checked-in `setup.cfg` identifies package version **1.0.8**, `python_requires >=3.9`, an unbounded `text-fabric` dependency, and '4 - Beta' classifiers (observed upstream repository version, not a claim about latest PyPI release). Pseudepigrapha-TF pins `text-fabric[github]>=13.1,<14` in its package metadata; compatibility should be verified before *any* future optional tooling use. Factory schema tooling may require Java/JING for TEI/RNG processing; do not add Java to the normal researcher installation.

## 4. Compatibility matrix (default factory behavior vs required OCP semantics)

| Required research semantic | Native converter & pinned acceptance | Default generic XML / TEI importer | Verdict |
|---|---|---|---|
| Word-level slots, section identity, `source_ref` | Yes; BHSA-compatible `book/chapter/verse` plus exact source citations | Generic XML defaults to character slots and tag nodes; TEI path expects TEI | Not equivalent |
| Historical variants and witness attribution | `unit/reading` + `reading_of`, `witness`, `manuscript_of`, omission/unattested distinction | No OCP-specific witness/reading interpretation or edges | Not equivalent |
| Empty primary readings and gap anchors | Explicit source-ordered gap semantics; see ADR-0001 | Generic blank XML-element slot is structural, not a source-ordered textual-locus contract | Not equivalent |
| Multiple languages and metadata-only version | Version ownership and metadata nodes, without fake text | Naive XML element traversal cannot infer edition ownership | Not equivalent |
| Generated translations | Separate `version_kind`, source-version and source-unit edges; 231/54,143 pinned checks | No source-edge semantics from generic tags | Not equivalent |
| Duplicated sections and unusual source structure | `~2` identity, 9 orphan readings, `<elipsis>`, pinned empty unit ID; fail-closed behavior | Generic tree serialization has no equivalent locus policy | Not equivalent |
| Source-structure validation/inventory | Custom grammar plus independent raw parity; source/TF model audit | Generic XML inventory `check` and external schema helpers can be useful diagnostic references | Partial overlap |
| Browser/app generation | Existing tracked app, comparison UI and selective TF loads | Auto-generated generic app is structurally different | No direct benefit |

Do not confuse preservation of the XML tree with preservation of the **scholarly relationships** represented in that tree.

## 5. Architectural choices

1. **Keep bespoke semantic parser → IR → graph → native TF writer (chosen).** Supports pinned identity, raw and graph parity, stable researcher queries, and no extra runtime dependency.
2. **Use factory as reference for XML inventory/schema diagnostics (allowed without dependency).** Review algorithms and ideas; independently implement any clearly justified narrow validation enhancement behind source-parity tests. Avoid importing the framework merely for an inventory that existing code already computes.
3. **Use factory hook/walker as primary conversion (rejected).** Requires rewriting node/slot/edge construction and developing a one-to-one feature/ownership mapping; no evidenced cost or fidelity win.
4. **Migrate to TEI + keep semantic IR/writer (deferred).** First require a demonstrably authoritative TEI document set, pin its source hash/version, compare original OCP readings/omissions/metadata and generated identity mappings, then design a new adapter into the same IR. None was established here.
5. **Adopt TEI factory directly (rejected).** Wrong input syntax and non-equivalent default semantic output.

## 6. Provenance, dependencies, resource impact

The current dataset is intentionally tied to immutable upstream commit, source files, exact raw inventory, public metadata, license attribution and a deterministic TF feature contract. Introducing a generic converter does not produce a provenance improvement unless it retains every current source and graph audit invariant. `xmlCustom.py`'s character-per-slot behavior would create a different slot cardinality and likely a different memory/runtime profile; **magnitude not measured**. Reproducible output and Text-Fabric version compatibility would have to be pinned and tested independently before adoption. A dependency that adds Java/schema setup is especially inappropriate for the normal published-corpus loading path.

## 7. Revisit / migration gate (only if new evidence appears)

1. Obtain a real, versioned OCP TEI corpus and written authority for it, including a mapping to the 39 named files and `intros.json` provenance. Do not infer TEI from README prose.
2. Research and freeze a mapping for source `unit`, `reading`, `mss`, zero-span/omission, repeated section IDs, orphan structures, metadata-only versions, and translation source-occurrence edges.
3. **RED-first** semantic parity fixtures on real representative OCP files and the full pinned source inventory; require exact source identities and no added/removed witness/translation relationships.
4. Convert both paths into the same semantic IR, run an automated complete-corpus graph diff (features/edges + public API), measure peak RSS and runtime in the same environment, and independently adversarially review the diff and fail-closed cases.
5. Only then choose whether a TEI adapter or validation helper is worth the maintenance burden. A passing generic XML→TF serialization check is insufficient.

## 8. Evidence, reproducibility and limitations

- Current source: OCP [`static/docs`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/tree/c939dcbacad78c5d18d2c4282cad23c47e19ac07/static/docs); root-level 39 XML files including empty `3Macc.xml` (GitHub contents inventory). Pin `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.
- Existing production/parity checks: `.github/workflows/test.yml`, `src/pseudepigrapha_tf/source.py`, `parser.py`, `graph.py`, `writer.py`, `audit.py`, `semantic_audit.py` and the pinned acceptance scripts.
- Source-format and generic modeling inspection: OCP pinned `Aristob.xml`, `4Q548.xml`, `ApocrEzek.xml`, `grammateus.dtd`; factory `tff/convert/tei.py`, `xml.py`, `xmlCustom.py`, `setup.cfg`, upstream factory docs.
- The existing pinned integration test covers all **38 nonempty** XML files and proves this converter's semantic parity; it does not run a Text-Fabric-Factory-produced corpus through those same tests. That missing counterfactual is explicitly recorded rather than disguised as an experimental diff.
- This research issue itself does not change runtime/serialization behavior; **TDD implementation gates are not applicable** until a concrete source-adapter or validation improvement is authorized. Any follow-up ticket must use RED → implementation → pinned corpus tests → independent review.

## Conclusion

**Use as implementation/reference material only.** No new Text-Fabric-Factory dependency or converter migration. Maintain the scholarly OCP model and source-parity invariants as the test oracle.