# Issue #218: release-launcher Bash heredoc parse failure

## Evidence and independent source read

- Main `5c6f866540e8cbcee8292bb5b31d835ee2713db2` passed full unit and pinned OCP CI #38180920440.
- `workflow_run` launcher #38181125401 job 114593713731 on that main SHA checked out correctly, passed main liveness and v1.1 identity; failed in the `Probe immutable tag and release without masking GitHub API errors` step **before any tag/release mutation**.
- Runner log: `here-document at line 35 delimited by end-of-file (wanted PY)`; `syntax error: unexpected end of file`.
- In actual `.github/workflows/launch-v1-1-release.yml`, the `200:200)` case arm contains a `python - <<'PY'` body and closing delimiter indented at the case-arm depth. YAML strips the block scalar's common indentation, leaving the `PY` delimiter indented by four shell spaces. Bash heredocs require the delimiter to begin at column zero (unless using tab-stripping `<<-` with literal tabs). The other top-level heredoc does not share this defect.
- Previous `tests/test_release_110_launcher_contract.py` asserted YAML substrings, so it passed despite a syntactically invalid runner script.

## Frozen plan (before tests and code)

1. Add `tests/test_release_110_launcher_shell_syntax.py`: parse the **real YAML** with `yaml.safe_load` and validate that each `jobs.launch.steps[].run` is a string that passes `bash -n`, preserving runner command text. Cover both a deliberately broken nested heredoc and valid case-arm delimiter, so the test would fail for the exact observed defect, not a string search.
2. Commit only the test first and confirm RED against the current branch in GitHub Actions or local pytest. Existing tests remain passing.
3. Correct only the broken Python heredoc body and delimiter indentation inside the `200:200)` arm. Keep its shell `python - <<'PY'` invocation and all validation semantics intact. Make Python code flush-left **after YAML common block indentation**, and ensure shell `PY` appears at column zero; do not change tag-selection behavior.
4. Verify exact-head unit and pinned OCP end-to-end CI; independently review actual YAML, parsed `run:` script, GitHub original runner logs, and immutable-release branch decisions. Do not merge on a failing/queued head.
5. Merge with exact reviewed SHA; require green post-merge main CI then inspect new launcher, tagged SHA, publisher workflow, public assets and Agora pin. Keep release Issue #206 open until publication genuinely complete.

## Risk boundaries

- No converter, data schema or publisher workflow changes; runtime corpus source remains `c939dcbacad78c5d18d2c4282cad23c47e19ac07`.
- No force push/move of release tags, no unverified release publication, no separate agent claimed.
- `yaml.safe_load` is available from existing TF/PyYAML dependencies in CI; the unit test does not fetch upstream data or require GitHub credentials.
