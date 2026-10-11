# #182 source-data correction: TSol repeated manuscript groups

This amends, but does not rewrite, the frozen initial plan in `RESEARCH_PLAN.md`. The initial plan to classify `manuscripts` as singleton was **invalidated by the actual pinned source**. The true invariant is: *no parser-consumed child may be discarded*. Some fields require cardinality rejection; manuscript groups require full preservation.

## Verified real OCP evidence

Source: `OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha`, commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`, `static/docs/TSol.xml`, original Greek `<version title="Greek" author="" language="Greek">` (not generated OCP-Trans).

There are **four separate `<manuscripts>` containers** in that one version, each containing a unique manuscript:

| Manuscript | language | show | Citations in Greek reading mss values |
| --- | --- | --- | ---: |
| McCown | Greek | yes | 279 |
| HI | Greek | no | 2 |
| L | Greek | no | 2 |
| VW | Greek | no | 2 |

All four entries have upstream `name` and `bibliography` data. Current `parser._parse_version` only selects `element.find("manuscripts")`; the three later blocks are silently absent from the parsed `Version.manuscripts`. Current `audit._raw_inventory` mirrors the bug by selecting `container.find("manuscripts")`, so its independent source count also discards the records. Graph construction may synthesize citation-only undefined manuscript nodes for HI/L/VW despite their **declared** upstream identities. The prior semantic parity result did not detect this.

The test-only PR branch with broad singleton rejection (head `b10c369624fa2ed977be07c2eb4b3663dc49f44f`) had **704 unit tests green but pinned integration failed** at `TSol.xml: duplicate <manuscripts> child of <version>`, run `38094603255`. This was a legitimate research result: **do not whitelist/ignore the source**.

## Revised architecture and gates

1. Keep singleton rejection only for genuinely first-only fields: `version/divisions`, `version/text`, `book/text`, `ms/name`, `resource/URL`.
2. Treat `manuscripts` grouping as **repeatable** on both modern `version` and legacy `book`; flatten in XML document order, in both converter parser and source-independent raw audit, preserving every `ms` record with full name/bibliography/show/language and original abbreviation.
3. Reconcile manuscript abbreviation uniqueness across *all groups in one version/book*. Existing per-`manuscripts` duplicate check is insufficient once the groups are merged; a repeated abbrev across groups is ambiguous and must fail closed rather than losing one.
4. RED-first revised tests: remove incorrect tests expecting rejection of duplicate `manuscripts`; add tests that assert distinct second-group manuscript content is preserved in model and raw inventory for modern, legacy, wrapped-legacy; add test for same abbrev across groups being rejected.
5. Verify pinned `TSol` **actual TF nodes** for Greek McCown/HI/L/VW are source-declared (not `undefined_manuscript=1` synthetic citations), with correct `show`, `name` and bibliography.
6. Preserve untouched ownership, scope and Text-Fabric serialization behavior; independently compare raw and graph inventories, complete pinned OCP conversion/release/offline reload and real 1 Enoch app.
7. Perform logically independent skeptical review against source XML, code, synthetic and pinned tests, exact final CI head and mutation hazards. Do not merge otherwise.

## Boundaries

This corrects historic manuscript identity/metadata loss, not merely acceptance of irregular XML. Blank manuscript abbreviations are handled by existing rules; duplicates across source groups must be detected before graph writes. Other repeatable fields (`resources`, `info`, `bibliography`, `versions`, `readings`) remain repeatable.
