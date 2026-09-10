# Issue #104 — reviewed one-time release execution bridge

This file exists only on the operational review branch and is **not part of `main` or the v0.2.0 release candidate**.

## Reason

The connected GitHub mutation surface available to the agent can edit repository contents/branches but does not expose Git-tag creation or `workflow_dispatch`. The permanent release workflow already exists on `main` and must remain the publisher of record.

GitHub documents that `workflow_dispatch` invoked with a repository `GITHUB_TOKEN` does create a workflow run even though most events emitted with `GITHUB_TOKEN` are recursion-suppressed. Therefore a narrowly scoped one-time workflow on an operational branch can bridge only the two missing control-plane mutations: create the reviewed immutable tag, then dispatch the already-reviewed permanent publisher.

References checked 2026-09-10:

- https://docs.github.com/en/actions/concepts/security/github_token
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

## Frozen execution identity

- repository: `alexsosn/Pseudepigrapha-TF`
- release candidate: `317e960e05ca7f36f35a11fcf567285312951095`
- permanent green main CI: `34459831089`
- tag: `v0.2.0`
- permanent publisher: `.github/workflows/publish-corpus-release.yml`
- publisher inputs: `release_tag=v0.2.0`, `release_commit=317e960e05ca7f36f35a11fcf567285312951095`

## Safety design

The helper workflow listens only to branch `ops/104-v0.2.0-release-execute`. It is authored and reviewed on the different branch `ops/104-v0.2.0-release-review`, so creating or editing it cannot trigger publication.

Activation must create the execution branch from the exact reviewed helper commit and then add only `.release-trigger`. The trigger file records the reviewed helper-parent SHA. At runtime the helper requires:

1. exact repository and execution branch;
2. the trigger commit's only changed path is `.release-trigger`;
3. trigger-declared helper SHA equals the trigger commit's parent;
4. target candidate is an ancestor of the helper and current remote `main` still equals that target;
5. exact main CI run `34459831089` is completed/success and bound to the same target SHA/main branch;
6. owned converter/TF/materializer/OCP identities still match the frozen release;
7. no GitHub release `v0.2.0` exists;
8. an existing remote `v0.2.0` tag is acceptable only if it already resolves to the exact target SHA (partial-run recovery); a wrong tag fails closed;
9. no prior publisher workflow-dispatch run already targets the candidate, preventing duplicate dispatch;
10. if no tag exists, create one annotated tag at the target and push it without force;
11. verify the remote tag resolves to the exact target;
12. dispatch the permanent publisher at ref `v0.2.0` with exact tag/SHA inputs.

The helper never creates a GitHub release, uploads assets, edits `main`, moves a tag, or performs publication itself. Those responsibilities remain exclusively in the permanent publisher.

After execution is accepted, the operational branches should be neutralized by deleting the helper workflow file if branch deletion is unavailable through the connector.
