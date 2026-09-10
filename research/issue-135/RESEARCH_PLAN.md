# Issue #135 — research and implementation plan

Base: `cf7125edd6cb4b680754de7b485daef17d2ab511`.

## Research findings

GitHub now has a first-class immutable-releases policy. When enabled before publication, a published release locks its associated tag and assets; GitHub also generates a release attestation. GitHub's documented publication pattern matches this repository's existing design: create a draft, attach/validate all assets, then publish. Immutability applies only to future releases.

The live historical `v0.2.0` release currently reports `immutable: false`. It must not be recreated, retagged, or asset-replaced merely to obtain the newer GitHub protection. The project-owned manifest/hash verification remains the authority for the v0.2.0 corpus generation.

GitHub exposes a repository endpoint `GET /repos/{owner}/{repo}/immutable-releases`: HTTP 200 with `enabled: true` when enabled, 404 when not enabled. Enabling uses the corresponding repository administration endpoint and requires Administration(write). The GitHub connector available to this development loop intentionally does not expose repository-administration mutation, so enabling the setting is an external administrative gate; ordinary release workflows should not receive Administration(write) just to compensate.

GitHub also documents `gh release verify TAG` and `gh release verify-asset TAG FILE` for immutable releases/attestations. These are complementary to, not substitutes for, `dataset-manifest.json`: GitHub attestation protects the GitHub publication event, while the project manifest binds converter/data/upstream/provenance/feature identities.

Current publisher behavior is already structurally compatible with immutability: it creates a draft, validates/downloads/revalidates draft assets, promotes once, then downloads and validates the public generation. There is no `--clobber` or intended post-publication asset replacement path.

## Design decision

Do not alter v0.2.0. For the next release generation, require two independent integrity layers:

1. project-owned canonical distribution validation and manifest binding;
2. GitHub immutable-release enforcement and post-publication release/asset verification.

The workflow may *check* repository immutable-release state with read-only GitHub API access; it must not enable/disable the administrative policy itself.

## TDD plan

### RED 1 — pre-publication policy evidence

Add static/workflow-contract coverage requiring the publisher's preflight to query the repository immutable-release setting fail-closed before building/publishing a future release. The check must distinguish enabled from 404/other API failure and must not request repository administration permissions.

Expected RED on this base: current publisher has no immutable-release setting preflight.

### GREEN 1

Add the narrow read-only preflight. Use the current GitHub API contract explicitly rather than inferring immutability from a release that does not yet exist. Preserve exact release SHA/tag binding and existing draft-first flow.

### RED 2 — published release immutability/attestation

Add workflow-contract coverage requiring post-publication verification that the release reports `immutable: true`, plus attestation/release verification where runner `gh` capability supports it. Asset verification must be performed on the same downloaded canonical assets already validated by `validate_distribution()`.

### GREEN 2

Extend only the post-publication verification lane. Do not replace manifest validation, loosen asset-set checks, or make ordinary unit tests network-dependent.

## Test gates

For the implementation PR:

1. focused workflow-contract tests;
2. full pytest / real Text-Fabric suite;
3. exact pinned OCP integration;
4. release workflow remains draft-first and permission-minimal;
5. no mutation path for historical `v0.2.0`;
6. exact-head logically independent adversarial review.

The *live* acceptance gate cannot be completed until repository release immutability has been enabled administratively and a future release is published. Tests must not pretend that static workflow support proves the external setting is enabled.

## Independent adversarial review checklist

Challenge:

- accidental Administration(write) permission creep;
- a check that treats 404/API errors as disabled-but-acceptable;
- checking `immutable` only after publication while failing to establish pre-publication policy state;
- relying on mutable `latest` rather than the exact release tag under verification;
- replacing project manifest validation with GitHub attestation;
- post-publication mutation/retry assumptions incompatible with immutable assets;
- any attempt to retrofit v0.2.0;
- `gh release verify` availability/version assumptions on hosted runners;
- workflow checks that are syntactic but never execute in the live release path.

## External blocker / ownership boundary

Repository release immutability must be enabled by an administrator through GitHub Settings or the Administration(write) API. This agent cannot perform that setting mutation with the available connector. Implementation can prepare fail-closed verification, but issue #135 must remain open until the external policy is enabled and a future release demonstrates the live immutable-release contract.