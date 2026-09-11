# Issue 139 — researcher-first documentation

## Goal

Make the normal consumption path obvious before any converter, release, or maintainer machinery: obtain the published corpus, load/query it, inspect apparatus and translations, browse/compare it, understand resource expectations and limitations, and only then learn how to rebuild from OCP.

## Research findings

The current README is materially misleading for a new researcher:

- it opens by describing Pseudepigrapha-TF as a converter rather than a usable published corpus;
- the first normal-install text assumes a repository checkout;
- `## Convert OCP` appears before ordinary corpus querying and therefore makes source conversion look like the acquisition path;
- it later states that the repository does not redistribute a generated TF corpus, which is no longer true now that public `v0.2.0` provides stock Text-Fabric `complete.zip` and native `tf-0.2.zip` assets;
- useful researcher APIs are documented, but they are buried among converter/audit implementation details;
- resource measurements exist in `docs/runtime-footprint.md`, and the generated feature reference already exists in `docs/features/0_home.md`; these should be linked rather than duplicated.

The clean public path has already been proven by #104: Text-Fabric 13.1 with its GitHub backend can acquire the public release from `alexsosn/Pseudepigrapha-TF`, and `checkout="local"` reload works with network access blocked. Public `v0.2.0` ships `complete.zip` at 9,816,530 bytes. Current main also fixes the old v0.2.0 package metadata defect by depending directly on `text-fabric[github]>=13.1,<14`.

#141 established current reference consumption measurements: about 9.20 MiB stock transport, 145.4 MiB populated stock cache with no retained ZIP, about 1.34 GiB peak RSS for a warm full-app load, and about 1023 MiB for the measured translation-oriented selective load. These are CI reference measurements, not hardware requirements.

#140 established the supported local comparison behavior on the pinned full corpus, including TJob metadata-only evidence, 1 Enoch witness-state/translation comparison, readable PssSol ambiguity, Aristob anomaly tolerance, and duplicate 4Ezra section handling.

## Documentation information architecture

README should lead in this order:

1. what the corpus is and what it preserves;
2. quickest supported public acquisition/load path;
3. minimal passage query;
4. apparatus/witness semantics (`reading`, `omission`, `unattested`);
5. generated-translation discovery/alignment;
6. local browser/comparison UI;
7. resource expectations and selective loading;
8. metadata and feature-reference links;
9. known source/interface limitations and anomalies;
10. rebuilding from OCP and contributor/developer details.

Deep converter validation, preservation-audit internals, release machinery, and implementation rationale remain available but must not interrupt the onboarding path.

## Scope

Primary change: rewrite/restructure `README.md` around researcher use. Reuse and link existing specialist documentation:

- `docs/apparatus.md`
- `docs/runtime-footprint.md`
- `docs/features/0_home.md`
- `docs/source-identity-and-anomalies.md`
- `docs/historical-classifications.md`
- `DATA_LICENSE.md`

Do not add tutorial notebooks, duplicate the generated feature catalogue, or expand release-certification documentation.

## TDD documentation contract

Add a focused test that fails current main and enforces only durable researcher-facing properties:

- README must identify a published corpus and must not claim that generated corpus data is unavailable;
- a public Text-Fabric acquisition/load section must precede any OCP conversion/rebuild section;
- the onboarding sequence must expose passage, apparatus, translations, web comparison, resource guidance, feature reference, limitations, and rebuild/development in researcher-first order;
- README must contain the proven stock Text-Fabric repository identity and a `tf.app.use` acquisition example;
- README must link the existing runtime-footprint and feature-reference documents;
- converter/source-rebuild instructions remain present but secondary.

The contract should avoid brittle prose snapshots and should not require exact paragraph wording.

## Copy-paste evidence

Do not invent a second expensive network lane. The acquisition path is already independently exercised by the permanent published-release verifier from #104. The APIs used in the README are already exercised by the ordinary and pinned full-corpus suites. For this ticket, CI should combine the durable documentation contract with the existing full suite rather than re-download the public release just to re-prove the same transport.

## Acceptance

- README no longer implies that cloning OCP or running the converter is normal corpus acquisition.
- The public-load example is visibly earlier than rebuild instructions.
- A researcher can find concise examples for passage text, apparatus witness states, generated translations, and the comparison UI without reading converter internals.
- Resource expectations use the measured numbers from #141 with an explicit hardware/CI caveat.
- Known limitations explain normalized TF section addresses, duplicate `~N` disambiguators, metadata-only versions, source anomalies, and generated translations without overwhelming onboarding.
- Feature details are linked to the generated reference instead of copied into README.
- Developer conversion/audit/release material remains discoverable after researcher documentation.

## Independent review checklist

The final review should challenge:

- whether the documented public acquisition command is actually the path proven by #104;
- whether package installation and corpus acquisition are accidentally conflated;
- whether examples use real IDs/API contracts from pinned acceptance (`1En__Ethiopic`, `1En 1:2`, generated translations);
- whether omission/unattested/not-present/metadata-only distinctions remain accurate;
- whether memory/cache figures are clearly reference measurements rather than requirements;
- whether known anomalies are explained without suggesting the converter repaired OCP source numbering/content;
- whether developer machinery has genuinely moved behind researcher use rather than merely receiving a new introductory paragraph.
