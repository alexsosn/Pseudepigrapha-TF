# Issue 206 — 1.1 release identity and publishable corpus data version

## Goal

Make `main` publishable as `v1.1.0` with a coherent `1.1.0` / `1.1` identity, without ever republishing changed corpus bytes under the already-published `1.0` data version.

## Research findings

`main` (`9036250`) is 21 commits past published `v1.0.0` (`7c4b757`). CI is green on every one of them, and there are no open PRs or issues. The release identity was never advanced:

- `pyproject.toml`, `release_identity.CONVERTER_VERSION`, `pseudepigrapha_tf.__version__` all read `1.0.0`;
- `release_identity.TF_DATA_VERSION` and `app/config.yaml` `provenanceSpec.version` read `1.0`;
- `agora.materializer.json` `plugin.version` reads `1.0.0`.

`build-corpus-release-assets.yml` asserts `release_tag == "v" + pyproject version`, so the only tag the publisher currently accepts is `v1.0.0`, which already exists and resolves to a different commit. Publication is therefore blocked, not merely undesirable.

### The derived corpus changed

Converting the same pinned OCP source (`c939dcbacad78c5d18d2c4282cad23c47e19ac07`) with the `v1.0.0` converter and with current `main` produces identical node and slot counts — 922,922 word slots, 1,193,651 nodes, 6,479,988 `oslots` edges — but eight differing manuscript-metadata features: `bibliography`, `bibliography_xml`, `manuscript_index`, `ms_language`, `ms_name`, `ms_name_xml`, `ms_show`, `undefined_manuscript`.

| Measure | v1.0.0 | main |
| --- | --- | --- |
| `ms_name` rows | 419 | 422 |
| `undefined_manuscript` rows | 30 | 27 |
| `manuscript` nodes | 483 | 483 |

The three records are the TSol manuscripts `HI`, `L`, and `VW`, recovered by #182 and #202. Manuscript node count is unchanged, so this is metadata completeness rather than added structure.

Since the native asset is named `tf-${DATA_VERSION}.zip`, publishing without advancing the data version would reissue different corpus content as `tf-1.0.zip`, defeating the immutable checksum-bound release guarantees established by #113, #115, and #251.

## Release identity decision

Semantic package/release version **1.1.0** and Text-Fabric data version **1.1**:

- package / converter: `1.1.0`;
- GitHub release tag expected by the existing builder: `v1.1.0`;
- Text-Fabric dataset path/version: `1.1`;
- native TF asset: `tf-1.1.zip`.

Minor rather than patch. Beyond the data change, #180, #196, #198, and #204 reject OCP input that earlier converters accepted, which is a behavioral change for anyone converting their own checkout.

## Scope

1. Advance owned current-version surfaces to `1.1.0` / `1.1`.
2. Update the normal full-corpus CI lane to build and test the 1.1 wheel and the `tf/1.1` dataset.
3. Update the existing publisher's expected current-version values and point `--notes-file` at issue-206 release notes.
4. Add 1.1 release notes describing researcher-visible changes since `v1.0.0`, including the data-version change and its cause.
5. Update current/local researcher examples to the 1.1 data identity.
6. Carry the readiness contract forward to `tests/test_release_110_readiness.py` and advance the frozen-identity constants in `tests/test_release_020_contract.py`.
7. Keep published `v1.0.0` and `v0.2.0` measurements and verification explicitly historical.

## TDD contract

The focused 1.1 readiness contract proves:

- package, `__version__`, release identity, app data version, Agora plugin version, CLI default output, and package description are coherent at 1.1;
- normal PR CI builds and materializes the 1.1 identity rather than a stale 1.0 one;
- the publisher validates 1.1 identities and uses issue-206 release notes;
- the new release notes name `v1.1.0`, name `tf-1.1.zip`, state that the data version changed, and summarize the actual 1.1 themes;
- current/local researcher examples use the 1.1 data identity while historical v0.2 verification is retained;
- the primary public-acquisition path is not frozen to `v0.2.0` **or** `v1.0.0`;
- no runtime figure is reattributed to a 1.1 corpus that was never measured.

## Observed RED evidence

Readiness RED on branch head `46242fc`, before any identity change: **6 failed, 2 passed** in the focused contract — exactly the frozen gaps (package identity, normal CI identity, publisher identity/release notes, missing 1.1 release notes, current local examples, release-ready README). The two new anti-fabrication guards passed from the start, confirming they do not depend on the bump.

## Implementation

Release identity and release-facing documentation only, not scholarly semantics:

- package/converter identity: `1.1.0`;
- TF/app data identity and CLI default: `1.1` / `tf/1.1`;
- Agora plugin manifest: `1.1.0`;
- ordinary full-corpus CI: 1.1.0 wheel, `/tmp/pseudepigrapha-tf/1.1`, `v1.1.0-ci`, 1.1 app/data assertions;
- existing publisher: expected 1.1.0/1.1 identities and issue-206 release notes, with no architectural changes;
- `research/issue-206/RELEASE_NOTES.md`: researcher-visible 1.1 changes;
- README comparison recipe targets the `v1.1.0` native `tf-1.1.zip` asset and 1.1 app/data paths; the rebuild recipe writes `tf/1.1`;
- `docs/tf-app.md`, `docs/runtime-footprint.md`, `docs/agora-materialization.md` current examples use 1.1.

The pinned OCP source commit, feature schema, apparatus/translation semantics, provenance model, distribution format, and publisher architecture are unchanged.

### Runtime measurements

1.1 was deliberately **not** re-measured. The existing figures stay attributed to the corpus they were measured on, and `README.md` says so explicitly. A readiness guard fails if a 1.1 measurement claim appears without one being taken.

## Implementation boundaries

Do not change scholarly data, the source pin, the feature schema, apparatus/translation semantics, the provenance model, or release architecture. Do not revisit immutable-release/attestation work. Do not edit Agora's registry to an unpublished commit; the pin moves only after `v1.1.0` is public, through Agora's existing stable-release review path.

## Final gates

1. Focused RED on the 1.1 readiness contract. **Complete.**
2. Implement only the frozen identity/release-note/current-doc changes. **Complete.**
3. Ordinary suite GREEN on the exact final head.
4. Existing pinned full-corpus conversion/audit/reload/comparison gate GREEN on the exact final head.
5. Logically independent adversarial review of the exact final SHA, specifically challenging stale 1.0 current-version surfaces, accidental rewriting of historical v0.2/v1.0 evidence, package/data/tag coherence, release-note accuracy against the 21 merged changes, whether any runtime figure was silently reattributed, and whether unrelated release machinery crept in.
6. Merge with expected-head protection.

Publication is a post-merge action against the exact merge commit, because the publisher requires the release tag to resolve to that commit. This PR makes `main` release-ready and must not pretend the public `v1.1.0` release exists.

After merge:

1. create tag `v1.1.0` at the exact merge commit;
2. dispatch `.github/workflows/publish-corpus-release.yml` from that exact commit with `release_tag=v1.1.0` and `release_commit=<exact merge SHA>`, requiring its live verification to succeed;
3. once the public non-prerelease `v1.1.0` exists, let Agora's stable-release tracker propose the `pseudepigrapha-tf` registry update to version `1.1.0` and the exact immutable release commit, then review and merge that Agora PR.

Issue #206 closes only after publication/live verification and the reviewed Agora registry pin are both current.
