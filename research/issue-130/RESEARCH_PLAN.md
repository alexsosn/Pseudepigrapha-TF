# Issue #130 — verify published `complete.zip` through Text-Fabric express download

## Research

This ticket is grounded in the Text-Fabric version constrained by Pseudepigrapha-TF: Text-Fabric **13.1.0**, commit `dd227ce62b5536de53a0e20eac98c0459da8fd3d`.

At that exact revision, `tf.advanced.repo.Checkout.isExpress()` returns true only when:

- express transport is allowed;
- the checkout is not local/clone;
- there is no version override;
- there is no explicit commit checkout;
- there is no explicit release checkout.

`Checkout.makeSureLocal()` calls `downloadComplete()` only when `isExpress()` is true. `downloadComplete()` resolves the backend's **latest public release**, constructs the release asset URL ending in `/complete.zip`, downloads it, changes directory to the Text-Fabric cache base, and calls `extractPrecise()` there. The archive therefore must carry cache-relative `org/repo/...` roots, which #124 implemented and tested locally.

The verifier added by #128 currently performs its online acquisition as:

```python
use(
    f'alexsosn/Pseudepigrapha-TF:{release_tag}',
    checkout=release_tag,
    silent='deep',
)
```

That supplies explicit release checkouts for app/data. It exercises GitHub-backed tagged acquisition, but by construction it does **not** exercise `downloadComplete()` and therefore cannot prove that the published `complete.zip` HTTP transport is usable by stock Text-Fabric.

## Published release evidence before implementation

As of 2026-09-10:

- latest public release is `v0.2.0`;
- annotated tag object: `8d855e0b0f7d83be1e510865f380f3589f37eb8a`;
- tag dereferences to immutable release commit `317e960e05ca7f36f35a11fcf567285312951095`;
- public release id: `386222479`;
- release is public and non-prerelease;
- public assets are exactly:
  - `complete.zip` — 9,816,530 bytes, SHA-256 `6117c345eb3af44b23e4bf86f53ab49a151c487dc99e398c2ba91223a01b8a4a`;
  - `tf-0.2.zip` — 9,805,832 bytes, SHA-256 `e529668bde1c01facdba635e2e251e6a7810425984c0e115fe0b903f12d03056`;
  - `conversion-report.json` — 24,375 bytes, SHA-256 `59f6ee3a6f66b3caa90d645012b6eef16390143a78f5c920c991bd1be2f4eb61`;
  - `dataset-manifest.json` — 12,645 bytes, SHA-256 `b2c05eb81f05a7615f343e93a938aca79bf7c813860325627f60fb63abb15145`.

The tag/assets are immutable inputs to this ticket. This ticket must not move the tag, recreate the release, replace an asset, or invoke the destructive publisher.

## Design / plan

Keep both acquisition modes in the read-only verifier because they prove different contracts:

1. **Explicit-tag gate** — retain the existing fresh tagged `use(...:{release_tag}, checkout=release_tag)` path to prove the immutable release can be acquired by exact release identity.
2. **Express gate** — add a second, separate empty HOME/cache and call `use('alexsosn/Pseudepigrapha-TF', silent='deep')` with no app or data checkout spec. With `v0.2.0` currently latest, Text-Fabric 13.1 must enter `downloadComplete()` and fetch the public `complete.zip` asset.
3. Load `dataset-manifest.json` first and compare express-loaded generic metadata against manifest-derived data version, converter version, upstream commit, source identity status, license status and content license; require positive slot count.
4. After the online express acquisition succeeds, monkeypatch socket connection entry points and load `use('alexsosn/Pseudepigrapha-TF:local', checkout='local')` from the **same** express-populated cache. Require the same metadata and slot count.
5. Keep `text-fabric[github]>=13.1,<14` provisioning before both online gates.
6. Keep the workflow `contents: read` only. No release/tag mutation commands may be introduced.

The express test intentionally targets the current latest release rather than passing a tag, because that is the condition under which Text-Fabric 13.1 uses `downloadComplete()`. The verifier already proves immediately beforehand that the requested release is public and that its four assets validate; live dispatch for #104/#127 must additionally ensure `v0.2.0` is still the latest public release when this gate runs.

## TDD RED gate

Before workflow implementation, add a workflow-contract regression requiring:

- a distinct fresh express HOME/cache;
- a no-explicit-checkout `use('alexsosn/Pseudepigrapha-TF', ...)` call;
- existing explicit tagged acquisition remains present;
- the express call occurs after GitHub backend provisioning;
- manifest-derived identity assertions apply to the express result;
- network is blocked only after the first online express acquisition and a local reload follows.

The current `main` verifier must fail that regression because it contains only explicit-tag online acquisition.

## GREEN / full gates

After the minimal workflow change:

1. focused workflow-contract tests;
2. full unit/Text-Fabric suite;
3. pinned OCP full conversion/audit, semantic parity, canonical release staging, local `complete.zip` load, metadata reload, advanced app and 1 Enoch comparison;
4. exact-head logically independent adversarial review against Text-Fabric 13.1 source and current public-release invariants.

No live workflow dispatch is required to merge #130 because the connector cannot dispatch workflows; #127/#104 remain open until the merged read-only verifier is manually dispatched and succeeds.