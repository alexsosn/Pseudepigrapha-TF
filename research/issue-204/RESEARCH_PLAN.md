# Issue #204 — Git index trust flags and exact OCP source attestation

Frozen research/plan: commit this before regression tests or production modifications.

## Source-grounded research
- `src/pseudepigrapha_tf/source.py:git_source_is_clean` shells out to `git status --porcelain=v1 --untracked-files=all --ignored=matching -- .` from the source folder; it accepts an empty output as proof that the working directory matches HEAD.
- `src/pseudepigrapha_tf/cli.py` obtains the same checkout's commit via `detect_git_commit` and calls `attest_corpus_license_source_identity` on that status. In `src/pseudepigrapha_tf/provenance.py`, a `source_tree_clean=True` value plus the pinned OCP hash yields verified source identity and potentially a verified CC-BY content license claim.
- Real isolated `git init` experiment: after editing a tracked `static/docs/A.xml`, ordinary `git status --porcelain` shows modified. Applying either `git update-index --assume-unchanged` or `git update-index --skip-worktree` hides it; status prints nothing despite differing XML bytes. `git ls-files -v -- .` returns `h` for assume-unchanged and `S` for skip-worktree; ordinary tracked file returns `H`.
- `tests/test_dirty_source_license_identity.py` checks ordinary dirty and untracked cases but not index hint flags. The full pinned-source CI checks verified provenance with ordinary Git index entries.

## Frozen implementation plan and verification
1. New live-Git fixture initializing `static/docs` with committed `sample.xml`, checking clean baseline. For both flags, hide a real tracked XML mutation and assert porcelain itself is empty **while** `git_source_is_clean` must be false. Repeat for flagged-but-unmodified XML to document deliberately conservative downgrade. Add a CLI test using the established fake serializer and a disposable repository commit patched as test `OCP_PIN`; ensure license/source identity downgrade while conversion succeeds.
2. Commit tests **alone** and capture expected failing Actions `unit-and-tf` results (RED), with existing tests passing.
3. Implement only a bounded `git ls-files -v -- .` index query after clean porcelain. Treat lowercase tags as assume-unchanged and `S` as skip-worktree; reject errors and unrecognized ambiguous tags conservatively. Skip unnecessary expensive operations for already dirty checkout. Keep Python + Git behavior and direct source parser unchanged.
4. Full test suite and pinned OCP `c939dcbacad78c5d18d2c4282cad23c47e19ac07` integration/release archive + semantic provenance checks at exact head, ensuring ordinary index stays verified. No release metadata changes.
5. Separate adversarial review of exact diff with focus on Git index tag handling, source path scope, error propagation, additional Git subprocess and CLI read-only attestation semantics. Post to PR; merge only after exact-head CI succeeds and no blockers remain.

## Scope limits
This is fail-closed provenance attestation, not a guarantee against malicious replacement of files **after** the converter read and before Git status; race-free immutable snapshotting requires a separate design. Explicit checked-out sparse worktrees can downgrade instead of making unwarranted byte-identity claims.
