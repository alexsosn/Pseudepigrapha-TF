# Issue #97 — canonical Text-Fabric distribution/loading research

Research base: Pseudepigrapha-TF `59ca5021e3c174e16ece532b9fabc22e9e06985f`.

External contracts inspected on 2026-09-08:

- Text-Fabric 13.1.0 (PyPI release 2026-01-15) and current 13.1 documentation;
- Text-Fabric data-sharing / advanced-repository loading documentation and source;
- ETCBC/BHSA repository/app/release pattern, especially `v1.8` and `v1.8.1`;
- current Pseudepigrapha-TF `v0.1.0` release, app config and Agora materializer registration.

This is a research artifact. No publication or loading behavior is changed yet.

## 1. Text-Fabric 13.1 transport contract

### App + data resolution

The high-level researcher path is:

```python
from tf.app import use
A = use("org/repo")
```

or `tf org/repo` in the browser CLI.

The app checkout and main-data checkout are independent:

- app specifier follows the app name, e.g. `org/repo:clone`;
- main data uses `checkout=...`.

Supported checkout identities include:

- empty/default: use local cache if present, otherwise current release, otherwise current commit;
- `local`: local TF cache only, no network fallback;
- `clone`: local GitHub/GitLab clone only;
- `latest`: current release;
- `hot`: current repository commit;
- an explicit release tag such as `v1.8`;
- an explicit commit SHA.

This gives both online one-command loading and an explicit offline/cache mode without inventing a Pseudepigrapha-specific downloader.

### Repository layout

For main data, Text-Fabric resolves:

```text
{org}/{repo}/{relative}/{version}
```

where the conventional/default relative path is `tf`. `provenanceSpec.version` supplies the data version unless the caller overrides it. The current Text-Fabric source also defaults `relative` to `tf` if it is omitted.

Clone mode expects the corresponding path below the user's GitHub/GitLab clone tree. Automatic downloads are cached below Text-Fabric's cache tree and can subsequently be requested with `checkout="local"`.

### Release assets

Text-Fabric can download individual main-data archives attached to a GitHub release. `tf-zip org/repo/tf` produces release assets named by relative path and data version; for a conventional layout this is:

```text
tf-<data-version>.zip
```

For Pseudepigrapha-TF data version `0.1`, the expected express asset name is therefore `tf-0.1.zip`.

Text-Fabric also supports `complete.zip`, produced by `tf-zipall`, containing the app plus main data, standard modules and selected extra/graphics data. It includes checkout marker files so the cache can report the release/commit provenance from which the data came.

For this project, an individual `tf-0.1.zip` is the narrower canonical data unit. `complete.zip` may be a convenience asset later, but should not become a second release identity.

References:

- https://annotation.github.io/text-fabric/tf/about/datasharing.html
- https://annotation.github.io/text-fabric/tf/advanced/repo.html
- https://annotation.github.io/text-fabric/tf/advanced/zipdata.html
- https://annotation.github.io/text-fabric/tf/about/use.html
- https://pypi.org/project/text-fabric/13.1.0/

## 2. BHSA reference publication pattern

BHSA documents the one-command path directly:

```python
A = use("etcbc/bhsa")
```

The app now lives in the same repository as the data. `app/config.yaml` declares data version `2021`; Text-Fabric's conventional relative path `tf` resolves the core data under `tf/2021`.

BHSA release `v1.8` demonstrates the express-asset contract directly:

- `tf-2017.zip` — 26,936,596 bytes;
- `tf-2021.zip` — 32,646,200 bytes;
- `tf-c.zip` — 25,621,712 bytes;
- `complete.zip` was added/used as a full app+data express archive as well.

BHSA `v1.8.1` retains `complete.zip` (33,963,367 bytes). The repository also keeps versioned TF data in Git; the release zip is an efficient transport/cache surface for the same data identity, not a separately curated corpus.

Relevant evidence:

- https://github.com/ETCBC/bhsa
- https://github.com/ETCBC/bhsa/releases/tag/v1.8
- https://github.com/ETCBC/bhsa/releases/tag/v1.8.1
- https://github.com/ETCBC/bhsa/blob/master/app/config.yaml

## 3. Current Pseudepigrapha-TF surfaces

### GitHub release

Current public release: `v0.1.0`, release commit `315439284e765c1d7ea89ffdefdd10f403aa1293`.

The release records:

- converter/package version `0.1.0`;
- TF data version/path `tf/0.1`;
- supported OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`;
- exact license/provenance boundary.

But the release has **zero assets**. The release text explicitly says the generated TF corpus is not redistributed and instructs users to clone OCP and run the converter. The repository does not contain generated `tf/0.1/*.tf` files either.

Consequence: current `use("alexsosn/Pseudepigrapha-TF")` cannot satisfy the normal remote main-data contract from the release, despite `app/config.yaml` declaring version `0.1`.

### App configuration

Current `app/config.yaml` has:

```yaml
provenanceSpec:
  corpus: Online Critical Pseudepigrapha (Text-Fabric conversion)
  version: "0.1"
```

No explicit `org`, `repo`, or `relative` is present. The app identity supplies org/repo and Text-Fabric defaults the relative data directory to `tf`, so this is structurally compatible with a future `tf-0.1.zip` asset. It currently describes a versioned data location that the release does not publish.

### CI/release automation

The repository currently has test/integration workflows only. There is no tracked release workflow that materializes a corpus and attaches a TF archive. The existing pinned integration does materialize and fully verify the exact corpus, but discards it at job end.

### Agora

Agora `registry/materializers.yaml` currently tracks Pseudepigrapha-TF release `0.1.0` at exact repo commit `315439284e765c1d7ea89ffdefdd10f403aa1293`.

The repository's `agora.materializer.json` specifies:

- source acquisition from exact OCP commit `c939dcb...` / `static/docs`;
- execution of the same package CLI;
- network denied during conversion;
- required Text-Fabric output plus `conversion-report.json`.

Agora therefore already supplies a deterministic reproducibility/materialization path, but it is not currently a canonical prebuilt release transport. That distinction should remain explicit.

## 4. Version identities that already exist

There are four independent values today and they should not be collapsed accidentally:

1. **converter release**: `0.1.0` / Git tag `v0.1.0`;
2. **TF data schema/version directory**: `0.1`;
3. **exact upstream edition snapshot**: OCP `c939dcb...`;
4. **generated artifact identity**: currently absent because no canonical corpus archive/checksum is published.

The generated TF generic metadata already records converter version, exact upstream commit, source-identity status and license provenance. `conversion-report.json` independently records and audits the same source identity plus semantic parity.

A release artifact should add a fifth machine-verifiable binding rather than replace those values: a checksum/manifest tying `tf-0.1.zip` and its report to the Git release/tag and converter/OCP identities.

## 5. Candidate publication models

| Model | One-command TF loading | Reproducible | Git size impact | Canonical identity risk | Assessment |
| --- | --- | --- | --- | --- | --- |
| Commit generated `tf/0.1` to Git | yes | yes | high/permanent history growth | low if release mirrors Git | viable but premature until size measured |
| GitHub Release `tf-0.1.zip` only | yes (`use`) | yes, if built by pinned converter | none in Git history | low if checksum/report bound to release | **leading candidate** |
| Agora materialization only | not normal TF remote `use()` | yes | none | medium: Agora runtime becomes de facto transport | keep as reproducibility path, insufficient alone |
| Release asset canonical + Agora deterministic rebuild | yes | yes | none | low if both bind to same release manifest | **preferred architecture pending size/integrity probe** |
| `complete.zip` as only artifact | yes | yes | none | mixes app/data packaging into one opaque unit | useful convenience, not preferred canonical data unit |

## 6. Preliminary design direction — not yet plan-frozen

Pending exact generated-size/archive measurement, the strongest current design is:

- Git tag/release `vX.Y.Z` remains the **release identity** for converter+app+dataset publication event;
- core TF data keeps explicit data version `0.1` (future incompatible/new corpus versions can advance independently);
- release attaches canonical Text-Fabric express asset `tf-0.1.zip`;
- release also attaches or embeds a compact immutable dataset manifest containing at least:
  - release tag/commit;
  - converter version;
  - TF data version;
  - exact OCP commit;
  - `tf-0.1.zip` SHA-256 and byte size;
  - `conversion-report.json` SHA-256;
  - semantic-report status;
  - content-license/source provenance identifiers;
- `conversion-report.json` is included in or paired with the release artifact in a way that can be verified against the manifest;
- normal users can run `use("alexsosn/Pseudepigrapha-TF", checkout="vX.Y.Z")` or the documented latest-release equivalent;
- users who already have the cache can run with `checkout="local"` without network;
- clone/local materialization remains supported explicitly for developers/reproducers;
- Agora resolves the same Pseudepigrapha-TF release identity and either downloads/verifies the canonical artifact or deterministically rebuilds it and verifies semantic/artifact identity against the release manifest. It must not assign an independent corpus version.

No current OCP reader/DTS deep link should be added to this transport contract unless separately demonstrated stable. TF transport does not need one.

## 7. Outstanding research gate: exact corpus transport size

Before freezing the plan, measure the exact pinned generated corpus at the current head:

- number of `.tf` feature files;
- uncompressed bytes;
- `conversion-report.json` bytes;
- exact `tf-zip`/equivalent release archive bytes;
- compression ratio;
- packaging time only as an observation, never an acceptance threshold.

A temporary research workflow will record these values. The workflow must be removed before implementation PR readiness.
