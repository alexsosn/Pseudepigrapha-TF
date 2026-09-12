# Issue 142 — 1.0 researcher-facing readiness and release identity

## Goal

Close the already-defined 1.0 gate without creating another certification phase. All six researcher-facing blockers (#104, #137, #138, #139, #140, #141) are complete; this ticket now owns the minimum coherent release identity and publication/distribution handoff needed to publish the proven corpus as 1.0.

## Research findings

The pre-1.0 `main` was functionally ready but still identified the current product as the previous release generation:

- `pyproject.toml` package version was `0.2.0`;
- `src/pseudepigrapha_tf/release_identity.py` owned converter `0.2.0` and TF data `0.2`;
- `app/config.yaml` advertised TF data version `0.2`;
- `agora.materializer.json` advertised plugin version `0.2.0`;
- `.github/workflows/test.yml` hard-coded the `0.2.0` wheel, `/tmp/.../0.2` materialization path, converter `0.2.0`, and data version `0.2`;
- `.github/workflows/publish-corpus-release.yml` still validated draft/public release bytes against converter `0.2.0` and data `0.2` and still used `research/issue-104/RELEASE_NOTES.md`;
- `tests/test_release_020_contract.py` was actually the current release-identity contract despite its historical-looking name.

The reusable asset builder already derives package/data identity from `pyproject.toml` and `app/config.yaml`; no new release machinery is needed. The read-only published-release verifier also derives identity from the manifest and remains generic.

Public `v0.2.0` verification is historical evidence and must not be rewritten as if that release never existed. Documentation that explicitly compares the published v0.2.0 baseline with the 1.0 corpus may keep those historical values.

A systematic tracked-file version audit found two additional classes of current-documentation drift:

- `docs/tf-app.md`, the README rebuild example, and the post-#141 selective-load example still used the old `0.2` local data path;
- `docs/agora-materialization.md` still said Pseudepigrapha-TF did not redistribute a generated TF corpus, contradicting the already-public v0.2.0 derived corpus.

A final release-readiness pass found a distinct publication-time problem in the README: its primary public-acquisition example was hard-pinned to `v0.2.0`, its local comparison recipe still materialized `tf/0.2`, and its resource section described v0.2.0 as "currently published". Those statements were true before 1.0 publication but would become false or misleading at the instant the v1.0.0 tag/release was published. The stable researcher-facing acquisition contract is therefore the stock Text-Fabric latest-public-release path; explicit v0.2.0 references are retained only where they are historical baselines/evidence.

The same release-time review found mutable publication-state wording in `docs/runtime-footprint.md`: the 1.0 measurements were described as a corpus "not yet" published and "intended for the next publication". Those facts were true when the benchmark ran but would become false inside the v1.0.0 tag. The note now records the same numbers as **1.0 measurements taken pre-publication**, which permanently explains why that benchmark has no network-inclusive v1.0 timing without making a claim about the release's current state.

The same audit confirmed that the remaining `0.2` references are historical v0.2 release/research evidence, synthetic distribution-test identities, or published-v0.2 baseline measurements and should remain unchanged.

The logically independent release-distribution review also checked Agora's external registry. `alexsosn/Agora` currently pins `pseudepigrapha-tf` to version `0.2.0` at immutable commit `317e960e05ca7f36f35a11fcf567285312951095`. This is intentional before publication: Agora's `release_tracking: github-releases` policy passively discovers only published, non-draft, non-prerelease SemVer releases and never changes runtime pins automatically. After v1.0.0 is public, the existing tracker may propose a PR that changes only the registered `version` and immutable `ref`; that PR still requires review and merge. Because #142 explicitly includes the current Agora entry in the 1.0 consumption path, the umbrella closes only after that reviewed registry promotion is complete.

## Release identity decision

Use semantic package/release version **1.0.0** and Text-Fabric data version **1.0**:

- package / converter: `1.0.0`;
- GitHub release tag expected by the existing builder: `v1.0.0`;
- Text-Fabric dataset path/version: `1.0`;
- native TF asset: `tf-1.0.zip`.

This follows the repository's existing package-tag and TF-data conventions rather than introducing a new scheme.

## Scope

1. Update owned current-version surfaces to `1.0.0` / `1.0`.
2. Update the normal full-corpus CI lane so it builds/tests the 1.0 wheel and `tf/1.0` dataset rather than a stale 0.2 identity.
3. Update the existing publisher's explicit expected current version values and point it to issue-142 1.0 release notes.
4. Add concise 1.0 release notes describing researcher-visible changes since v0.2.0.
5. Update Agora's local materializer plugin version to match the package.
6. Update only current/local user examples that are now 1.0-owned; keep historical public-v0.2 verification and measurements explicitly historical.
7. Make the primary public-acquisition instructions release-stable: load the latest public release through stock Text-Fabric rather than pinning the README's normal path to the previous release.
8. Preserve Agora's existing immutable reviewed pin until the public v1.0.0 release exists; then use Agora's existing stable-release tracking/review path to promote the registry entry rather than pre-pointing it at an unpublished commit.

## TDD contract

The focused 1.0 readiness contract proves:

- package, `__version__`, release identity, app data version, Agora plugin version, CLI default output, and package description are coherent at 1.0;
- normal PR CI no longer hard-codes the current build/materialization as 0.2;
- the publisher validates 1.0 identities and uses issue-142 release notes;
- the new release notes name v1.0.0 and summarize the six completed researcher-facing gates;
- historical v0.2 verification remains available rather than being deleted;
- current/local researcher examples use the 1.0 data identity;
- Agora documentation no longer falsely denies publication of the derived corpus;
- the README's primary public-acquisition path follows the latest public release rather than freezing v0.2.0;
- the release-specific local comparison recipe and current resource guidance use 1.0 while v0.2.0 remains explicitly historical;
- runtime-footprint measurements remain accurate after publication rather than encoding a mutable "not yet published" state.

Do not add another network/release-certification lane. Existing unit + pinned full-corpus CI is the GREEN gate.

## Observed RED evidence

Initial readiness RED: Actions run `34658342708`, unit job `103455463319` — **4 failed, 586 passed**. The four failures were exactly the frozen readiness gaps: package identity, normal CI identity, publisher identity/release notes, and missing v1.0.0 release notes.

After implementing 1.0 identity, the first ordinary GREEN attempt exposed one stale app-config assertion that still expected `0.2` while protecting the important quoted-string YAML contract. It was updated to `1.0` without weakening the type-safety assertion.

Documentation audit RED: Actions run `34659185382`, unit job `103457989562` — **2 failed, 590 passed**. The failures were exactly the obsolete Agora no-redistribution claim and current/local examples still pointing at 0.2. No product/API test failed.

Release-time README RED: Actions run `34701136399`, unit job `103572993148` — **2 failed, 592 passed**. The failures were exactly the primary acquisition path frozen to v0.2.0 and the current local comparison/resource guidance still using the previous release identity. The same run's pinned full-corpus lane continued successfully through the real 1.0 package/corpus path, confirming these were documentation-release failures rather than scholarly/runtime regressions.

Publication-timeless runtime-note RED: Actions run `34701677635`, unit job `103574463047` — **1 failed, 594 passed**. The sole failure was the new contract detecting release-state prose in `docs/runtime-footprint.md`; no implementation/API contract failed. The fix preserves every benchmark value and rewrites only the temporal interpretation around when the 1.0 measurements were taken.

## Implementation

The implementation intentionally changes release identity and release-facing documentation, not scholarly semantics:

- package/converter identity: `1.0.0`;
- TF/app data identity and CLI default: `1.0` / `tf/1.0`;
- Agora plugin manifest: `1.0.0`;
- ordinary full-corpus CI: 1.0.0 wheel, `/tmp/pseudepigrapha-tf/1.0`, `v1.0.0-ci`, 1.0 app/data assertions;
- existing publisher: expected 1.0.0/1.0 identities and issue-142 release notes, with no architectural changes;
- `research/issue-142/RELEASE_NOTES.md`: researcher-visible 1.0 changes;
- current TF-app/rebuild/selective-load/Agora materialization docs aligned to 1.0 and the actual derived-corpus distribution policy;
- README primary corpus loading now uses stock Text-Fabric's latest-public-release path instead of hard-pinning v0.2.0;
- README local comparison instructions target the v1.0.0 native `tf-1.0.zip` release asset and 1.0 app/data paths;
- README resource figures retain v0.2.0 only as an explicitly historical baseline and describe the 1.0 corpus as the current release-owned output;
- runtime-footprint tables and prose label the optimized figures as 1.0 measurements taken pre-publication instead of embedding mutable release-state claims.

The pinned OCP source commit, feature schema, data contents, apparatus/translation semantics, provenance model, distribution format, and publisher architecture are unchanged.

Temporary patch/version-audit workflows were used only to perform guarded edits or inventory tracked version strings and are deleted before the final candidate gate.

## Implementation boundaries

Do not change scholarly data, source pin, feature schema, apparatus/translation semantics, provenance model, or release architecture. Do not revisit immutable-release/attestation work. Versioned paths and release identity are the intended production change. Do not bypass Agora's existing immutable-pin review model by editing its registry to an unpublished branch or pre-release commit.

## Final gates

1. Focused RED on the 1.0 readiness contract. **Complete.**
2. Implement only the frozen identity/release-note/current-doc changes. **Complete.**
3. Ordinary suite GREEN on the exact final head.
4. Existing pinned full-corpus conversion/audit/reload/comparison gate GREEN on the exact final head.
5. Logically independent adversarial review of exact final SHA, specifically challenging stale 0.2 current-version surfaces, accidental rewriting of historical v0.2 evidence, package/data/tag coherence, release-note accuracy, temporary-workflow cleanup, README/runtime-doc publication-time correctness, Agora registry handoff, and whether any unrelated release machinery crept in.
6. Merge with expected-head protection.

Actual GitHub tag/release publication is a post-merge action against the exact merge commit because the existing publisher requires the release tag to resolve to that commit. The available GitHub connector exposes no tag-creation or workflow-dispatch mutation. Therefore the PR must make `main` release-ready but must **not** pretend the public v1.0.0 release exists.

After merge, the remaining release/distribution sequence is:

1. create tag `v1.0.0` at the exact merge commit;
2. dispatch `.github/workflows/publish-corpus-release.yml` from that exact commit with `release_tag=v1.0.0` and `release_commit=<exact merge SHA>` and require its existing live verification to succeed;
3. once the public non-prerelease v1.0.0 release exists, let Agora's existing stable-release tracker propose the `pseudepigrapha-tf` registry update to version `1.0.0` and the exact immutable release commit, then review and merge that Agora PR.

The existing Pseudepigrapha-TF publisher owns candidate construction, draft-byte validation, public promotion, live tagged Text-Fabric acquisition, and network-blocked local reload. Agora's existing release tracker owns passive candidate discovery but never auto-merges trust changes. Issue #142 closes only after publication/live verification and the reviewed Agora registry pin are both current.
