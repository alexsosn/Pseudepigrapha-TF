# OCP 2026 source and edition rights review

**Evidence revision:** `853a64b623de296d2b8532a43593607772e7c45a` (immutable OCP source snapshot).  
**Scope:** candidate source XML, metadata, and TEI conversion mirrors, **not** a declaration of verified rights to redistribute the new dataset.

The upstream [OCP README](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/README.md) and [CC BY 4.0 license file](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/LICENSE.CC-BY-4.0) state that source editions and TEI XML are under CC BY 4.0. We preserve this source declaration. A repository-level license statement does not by itself tell us who supplied each new English translation or whether additional material is covered by rights belonging to another publisher.

## Six new parallel English editions awaiting explicit attribution review

Every file below contains an original Greek/Latin version and an additional source-declared English version. The English is present as native editorial XML text. It is **not** the older OCP-Trans machine-generated layer and must not be assigned to the source manuscript `Eng` as a historical witness. Each `intros.json` entry mentions the English translation, but none contains `fields.copyright`, and no `version/@translator` or equivalent attribute is declared in the strict compact source vocabulary.

| Source XML | Original-language edition identified by OCP | Individual English translator | Current review state |
|---|---|---|---|
| [CithDavid.xml](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/CithDavid.xml) | Latin, based on M. R. James, *Apocrypha Anecdota* (1893) | Not stated | Requires attribution/rights confirmation |
| [Demetr.xml](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/Demetr.xml) | Greek fragments, citing Jacoby, Holladay and Denis | Not stated | Requires attribution/rights confirmation |
| [Justus.xml](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/Justus.xml) | Greek testimonia, citing Photius, Diogenes Laertius, Josephus, and modern editions | Not stated | Requires attribution/rights confirmation |
| [OrMois.xml](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/OrMois.xml) | Latin, based on M. R. James (1893) | Not stated | Requires attribution/rights confirmation |
| [ThrenSeila.xml](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/ThrenSeila.xml) | Latin, based on M. R. James (1893) | Not stated | Requires attribution/rights confirmation |
| [VisKenaz.xml](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/VisKenaz.xml) | Latin, based on M. R. James (1893) | Not stated | Requires attribution/rights confirmation |

Editorial bibliographies for the *originals* should be retained as recorded, but not silently treated as English translator credits.

## Separate ApDan morphology and TEI conversions

- [`static/docs/ApDan.xml`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/ApDan.xml) is the primary Grammateus Greek source version.
- [`static/docs/tei/ApDan.xml`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/tei/ApDan.xml) states that it is a **TEI P5 conversion from the Grammateus XML**, with a CC BY 4.0/free source declaration. It is not an additional historical edition by default.
- [`static/docs/ApDan_TEI.xml`](https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/853a64b623de296d2b8532a43593607772e7c45a/static/docs/ApDan_TEI.xml) explicitly declares **CC BY-NC 4.0 / restricted**, sourced from Heiser–Penner, *Old Testament Greek Pseudepigrapha with Morphology* (Lexham Press, 2022, Logos `LLS:8.20.7`). Its 170 verses and 2,150 morphologically annotated words align with the primary source. This file is the **67th root XML**, and it is **not** included as a second textual edition in the 66-file core candidate. Its separate, optional **local** Text-Fabric module requires an explicit noncommercial opt-in. Permission to redistribute the morphology has not been independently attested.

The original `intros.json` metadata uses the phrase *Public domain* for the base ApDan text. That cannot silently relicense the more specific restricted morphological annotations. Likewise, the upstream CC BY claim and the individual edition's restricted statement must both remain visible until their applicable scope is resolved.

## Reproducible evidence and publication boundary

The [candidate acceptance script](../tests/candidate_ocp_acceptance.py) attests the source Git HEAD and clean `static/docs` tree, then calls `rights_review.build_2026_rights_evidence()`. This produces a temporary `rights-evidence.json` containing full SHA-256 and Git blob hashes for every one of the **67** root XMLs and all observed `tei/` conversion-mirror files, plus classification, asserted license sources, explicit exceptions and unresolved claims. It is **not** included in any public release asset or Text-Fabric corpus. The reviewed README/license files and high-risk edition Git blobs are independently pinned in the verifier.

The status stays `rights_attestation=not_attested` and `publication_allowed=false`. These mean the evidence is reproducible but **cannot itself authorize publication**. The existing canonical distribution validator requires a verified 2026 source/license profile before accepting release artifacts, so this PR does not add a new release or alter the verified old v1.1 profile.

Before the new dataset is made public, obtain source-owner confirmation of:

1. Whether the upstream CC BY 4.0 statement is authorized to cover the six **English translation texts**, and what editor/translator attribution they require.
2. Whether the base ApDan and converted TEI rights can be distributed separately from the **CC BY-NC** morphological layer, and whether any Lexham/Logos permissions restrict that distinction.
3. Whether additional third-party critical-edition sources in the 2026 additions have distinct attribution or reuse conditions, especially where `intros.json` lists a modern scholarly edition without a per-work copyright field.

Only after that review should the new versioned manifest, GitHub release archive, external clean-download and autonomous browser E2E be executed. See [issue #228](https://github.com/alexsosn/Pseudepigrapha-TF/issues/228) and [issue #240](https://github.com/alexsosn/Pseudepigrapha-TF/issues/240).
