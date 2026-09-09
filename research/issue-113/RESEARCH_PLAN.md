# Issue #113 — release provenance profile authenticity

## Baseline

Merged `main`: `16a6a11920ff232e8101b9cb6a8382d52868a206`.

This ticket is a release-safety follow-up discovered by the exact-head independent review of #111. #111 now proves canonical provenance equality between the conversion report and serialized `otype.tf`. That equality does not prove that a mutually agreeing verified profile is truthful.

## Research findings

### Canonical provenance contract already exists

`pseudepigrapha_tf.provenance` owns the researched source/license semantics:

- `corpus_license_metadata(repository, commit, source_identity_verified=...)` derives the expected profile;
- `corpus_license_provenance_is_consistent(generic)` rejects missing/wrong profile values, verified-only fields on unverified profiles, diagnostics on verified states, and source/license overclaims;
- `REPORT_PROVENANCE_FIELDS` is the one generic-metadata ↔ report-provenance mapping.

For the supported OCP tuple (`OCP_REPOSITORY`, `OCP_PIN`) with verified source identity, the canonical profile includes the verified content license plus its URL/source/scope, converter and upstream software licenses, the upstream license evidence commit, attribution and citation, and no source/license diagnostics.

### The normal conversion path already produces and audits the full profile

`cli.py` calls `attest_corpus_license_source_identity()` before building the report. `semantic_audit.build_conversion_report()` includes a `corpus_license_provenance` semantic check backed by `corpus_license_provenance_is_consistent(generic)` and serializes report provenance with `report_provenance(generic)`.

The full pinned-OCP CI therefore already proves the converter-generated path satisfies the canonical profile.

### The distribution trust boundary is weaker

`distribution._validate_report_audit()` accepts report semantic-check booleans as evidence, and `_report_identity()` currently checks only:

- source identity status == `verified`;
- content license status == `verified`;
- no matching failure diagnostics;
- non-empty required provenance strings;
- converter/upstream identity syntax;
- report ↔ serialized canonical provenance equality later in `_validate_serialized_identity()`.

A handcrafted report can therefore set `semantic_checks.corpus_license_provenance=true`, change the profile in both report and `otype.tf`, recompute feature hashes, and pass agreement checks even though the canonical provenance module would reject the profile.

Examples include mutually agreeing:

- `content_license=OTHER`;
- wrong `content_license_url`;
- wrong `upstream_software_license` or `upstream_license_commit`;
- omission of a required verified-profile field from both report and serialized TF;
- an unknown repository/commit tuple that nevertheless claims `content_license_status=verified`.

This is an authenticity/profile-truth problem, distinct from #110's representation-equality problem.

## Chosen design

At the report publication boundary:

1. use `REPORT_PROVENANCE_FIELDS` in reverse to reconstruct the canonical generic provenance projection from the report;
2. call `corpus_license_provenance_is_consistent()` on that projection;
3. reject inconsistent/unknown verified profiles before manifest construction;
4. keep #110 report ↔ serialized equality as a separate invariant;
5. do not copy OCP license constants or profile logic into `distribution.py`;
6. do not inspect arbitrary non-canonical Text-Fabric metadata.

This preserves one source of truth: `provenance.py` owns profile semantics; `distribution.py` merely revalidates them at a hostile release boundary.

### Validation-order amendment from GREEN CI

The first GREEN implementation put canonical profile authenticity inside `_report_identity()`. Full CI showed that this was too early: malformed archive and report↔serialized mismatch tests were rejected by the generic profile error before the distribution layer could diagnose the actual representation defect. The pinned real-OCP job was green, but 28 unit tests exposed this diagnostic/validation-order regression.

The corrected order is therefore:

1. validate report status, syntax, and basic publication requirements;
2. validate archive feature identity and report feature binding;
3. validate report ↔ serialized Text-Fabric provenance/data identity;
4. only after those representations agree, validate the agreed canonical provenance profile independently;
5. construct/publish the manifest only after all four layers pass.

This does not weaken authenticity: forged-but-mutually-agreeing profiles still reach and fail the final canonical check. It preserves more specific fail-closed diagnostics for malformed or asymmetric representations and ensures `stage_distribution_assets()` cannot publish before authenticity succeeds.

Synthetic fixtures that claim to represent a valid verified release unit now derive the complete profile from `corpus_license_metadata()` / `report_provenance()` instead of maintaining partial hand-written copies.

## TDD sequence

### RED

Add focused tests before production changes proving current `main` accepts mutually agreeing invalid profiles:

1. wrong OCP `content_license` in report + `otype.tf`;
2. wrong OCP `content_license_url` in both;
3. wrong OCP `upstream_software_license` in both;
4. wrong OCP `upstream_license_commit` in both;
5. one required verified-profile field omitted from both representations;
6. unknown repository/commit claiming a verified content-license profile;
7. positive control: exact canonical OCP profile passes;
8. positive control: unrelated non-canonical TF metadata remains accepted.

The RED should fail only because the invalid candidates do not raise.

### GREEN

Minimal implementation in `distribution.py`:

- import `corpus_license_provenance_is_consistent` alongside the shared mapping;
- reconstruct generic provenance from report provenance using the existing mapping;
- after representation integrity has been established, fail closed with a specific profile-consistency diagnostic if the canonical validator rejects it;
- make no serializer/header/parser changes.

## Full gates

1. focused #113 tests;
2. full pytest / real Text-Fabric suite;
3. wheel + fresh install;
4. exact pinned OCP conversion and semantic parity;
5. canonical stage/manifest/extract/reload;
6. public metadata reload;
7. advanced app startup;
8. no tag/release/publication mutation in this ticket.

## Independent adversarial review gate

Review the exact final green head without relying on this plan. Challenge:

- all mutually agreeing wrong canonical profile fields;
- omission of required known-profile evidence;
- unknown repository/commit claiming verified licensing;
- attempts to bypass by setting the report semantic-check boolean true;
- future profile/mapping additions;
- whether distribution duplicates profile policy instead of consuming it;
- validation ordering and whether a more specific representation defect is masked;
- whether normal non-canonical TF metadata is affected;
- whether legitimate converter-generated pinned OCP still stages/reloads exactly.

Any blocking finding restarts RED → GREEN → full gates.

## Release dependency

#104 / PR #108 must not create `v0.2.0` or publish corpus assets until #113 is merged and the release branch incorporates the resulting `main`, then passes its own full gates and exact-head independent adversarial review.
