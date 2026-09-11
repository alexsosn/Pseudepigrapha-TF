# Issue 142 — 1.0 researcher-facing readiness and release identity

## Goal

Close the already-defined 1.0 gate without creating another certification phase. All six researcher-facing blockers (#104, #137, #138, #139, #140, #141) are complete; this ticket now owns only the minimum coherent release identity needed to publish the proven corpus as 1.0.

## Research findings

Current `main` is functionally 1.0-ready but still identifies the current product as the previous release generation:

- `pyproject.toml` package version is `0.2.0`;
- `src/pseudepigrapha_tf/release_identity.py` owns converter `0.2.0` and TF data `0.2`;
- `app/config.yaml` advertises TF data version `0.2`;
- `agora.materializer.json` advertises plugin version `0.2.0`;
- `.github/workflows/test.yml` hard-codes the `0.2.0` wheel, `/tmp/.../0.2` materialization path, converter `0.2.0`, and data version `0.2`;
- `.github/workflows/publish-corpus-release.yml` still validates draft/public release bytes against converter `0.2.0` and data `0.2` and still uses `research/issue-104/RELEASE_NOTES.md`;
- `tests/test_release_020_contract.py` is actually the current release-identity contract despite its historical-looking name.

The reusable asset builder already derives package/data identity from `pyproject.toml` and `app/config.yaml`; no new release machinery is needed. The read-only published-release verifier also derives identity from the manifest and should remain generic.

Public `v0.2.0` verification remains historical evidence and must not be rewritten as if that release never existed. Documentation that explicitly compares the published v0.2.0 baseline with the post-#141 candidate may keep those historical values until v1.0.0 is actually published.

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
6. Keep historical public-v0.2 verification and measurements explicitly historical.

## TDD contract

Add a focused 1.0 readiness test that fails current main and proves:

- package, `__version__`, release identity, app data version, Agora plugin version, CLI default output, and package description are coherent at 1.0;
- normal PR CI no longer hard-codes the current build/materialization as 0.2;
- the publisher validates 1.0 identities and uses issue-142 release notes;
- the new release notes name v1.0.0 and summarize the six completed researcher-facing gates;
- historical v0.2 verification remains available rather than being deleted.

Do not add another network/release-certification lane. Existing unit + pinned full-corpus CI is the GREEN gate.

## Implementation boundaries

Do not change scholarly data, source pin, feature schema, apparatus/translation semantics, provenance model, or release architecture. Do not revisit immutable-release/attestation work. Versioned paths and release identity are the intended production change.

## Final gates

1. Focused RED on the 1.0 readiness contract.
2. Implement only the frozen identity/release-note changes.
3. Ordinary suite GREEN.
4. Existing pinned full-corpus conversion/audit/reload/comparison gate GREEN on the exact final head.
5. Logically independent adversarial review of exact final SHA, specifically challenging stale 0.2 current-version surfaces, accidental rewriting of historical v0.2 evidence, package/data/tag coherence, release-note accuracy, and whether any unrelated release machinery crept in.
6. Merge with expected-head protection.

Actual GitHub tag/release publication is a post-merge action against the exact merge commit because the existing publisher requires the release tag to resolve to that commit. If the available GitHub connection cannot create a tag or dispatch the publisher, record that external action explicitly rather than adding substitute automation.