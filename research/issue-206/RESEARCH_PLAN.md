# Issue #206 — prepare v1.1.0 / TF 1.1 release identity

Frozen source-grounded research and implementation plan, committed before RED tests and production edits.

## Research evidence
- Current `main` at `903625047ba7dcadc6aad25e65c8a9f48e7e014f` carries previously published `v1.0.0` converter identity and TF data version `1.0`. `pyproject.toml`, `src/pseudepigrapha_tf/release_identity.py`, `app/config.yaml`, and `agora.materializer.json` disagree with planned `v1.1.0`.
- `.github/workflows/test.yml` tests a concrete 1.0 wheel, TF directory, candidate tag, native archive validation and Text-Fabric reload. Publisher hardcodes expected converter/data versions `1.0.0/1.0` and points release notes at issue #142, even though `build-corpus-release-assets.yml` verifies the tag/version relationship.
- `tests/test_release_100_readiness.py` freezes 1.0 assertions. `tests/test_release_020_contract.py` contains present-tense 1.0 identity constants despite its historical name. The standalone published-release verification workflow derives versions dynamically and must remain untouched.
- In existing `README.md` browser setup and rebuild sections, and `docs/tf-app.md`, current local workflows use `tf/1.0`. `docs/runtime-footprint.md` has historical 1.0 measurement tables that must stay correctly attributed when the *selective load example* shifts to 1.1.
- Issue #206 reports pinned OCP corpus outputs differ from 1.0 in eight manuscript metadata features, with TSol source witnesses HI/L/VW corrected; an immutable new 1.1 data version is required even though node/slot counts match.

## Frozen plan and gates
1. Add RED-only 1.1 contract tests first: coherent package/app/Agora identities; concrete expected CI wheel/data paths; publisher expected version and 1.1 notes path; unchanged upstream OCP pin; local examples 1.1. Check that existing historical benchmark language is preserved.
2. Commit RED tests separately, capture GitHub Actions failure evidence on exact test-only SHA. Do not treat unrelated failures as RED confirmation.
3. Advance owned versions `1.0.0 → 1.1.0` and TF identity `1.0 → 1.1` in release identity, pyproject, app, Agora, the current CI, publisher, README and current/local docs. Update old current-version tests and replace `test_release_100_readiness.py` with `test_release_110_readiness.py`, preserving historical 0.2 and 1.0 observations. Do not relabel numerical runtime benchmarks as 1.1 measurements.
4. Write `research/issue-206/RELEASE_NOTES.md` recording source/witness corrections, fail-closed validator/transaction hardening, stream-memory improvements and researcher acquisition; pinned upstream OCP commit and dataset semantics remain.
5. Run full unit suite and exact-head pinned upstream conversion, semantic audits, native/express distributions, offline Text-Fabric load, web/API acceptance. Independently examine finalized changed-files diff, failure paths and absence of unintended 1.0 replacements; post skeptical PR review. Merge only after exact-head CI green.
6. Release tag creation and publish workflow dispatch are **post-merge separate actions** that must bind immutable tag to merged SHA and pass published-live verifier; no false claim that a draft PR publishes data.

## Deliberate limits
- The historical v1.0.0 release assets remain immutable. Historical 1.0 RSS/disk benchmarks and 0.2 comparisons remain labeled as measured, while examples use 1.1.
- No new corpus schema features, source pin changes, license reinterpretation, TF interface changes, or performance estimates.
