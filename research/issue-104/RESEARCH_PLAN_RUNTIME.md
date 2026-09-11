# Issue 104 — clean public v0.2.0 researcher acquisition and runtime measurement

## Research findings

The published `v0.2.0` release already contains the stock Text-Fabric `complete.zip` transport and native `tf-0.2.zip`. Text-Fabric's documented checkout semantics allow a corpus app/data release to be fetched with `checkout="latest"` or a concrete release tag and then reused with `checkout="local"` from `~/text-fabric-data`.

The existing repository CI proves an equivalent locally staged `complete.zip` can be loaded from a fresh cache with networking forbidden, but it does not perform the missing user-facing experiment: fetch the **public GitHub v0.2.0 release** into an empty cache and measure the resulting normal consumption footprint.

Agora already points to Pseudepigrapha-TF `0.2.0` at release commit `317e960e05ca7f36f35a11fcf567285312951095`; no registry edit is planned unless a smoke test finds an actual defect.

## Frozen plan

1. Use an ephemeral GitHub-hosted Ubuntu runner with a new HOME/cache; do not clone OCP and do not run the converter.
2. Install only the released package/runtime dependencies needed by the researcher path. Pin Pseudepigrapha-TF to tag `v0.2.0`, never to the PR branch.
3. Acquire the corpus/app from the **public release** through stock `tf.app.use()` using the concrete release checkout and data version `0.2`.
4. Verify the acquired app loads 922,922 slots and can resolve `1En__Ethiopic / 1 / 2`.
5. Exercise the representative 1 Enoch comparison through the released package against the acquired public corpus.
6. Immediately disable network access in-process and prove `checkout="local"` reload succeeds from the populated cache.
7. Record, on the same runner:
   - published `complete.zip` size;
   - final Text-Fabric cache footprint and retained archive files;
   - cold public acquisition+load wall time and peak RSS;
   - warm local full-app load wall time and peak RSS;
   - representative comparison wall time and peak RSS;
   - a practical selective `Fabric.load()` path wall time and peak RSS using only features required for a normal apparatus/translation query.
8. Keep the measurement workflow temporary. Its run history is research evidence; remove it before merge so ordinary CI does not acquire a historical public release on every PR.
9. Convert the measured results into a concise user-facing runtime note. If a major avoidable hotspot appears, file/fix it under #141 before closing #104.
10. Smoke-test Agora only if its current documented/install route is exposed by available tooling; do not modify the already-current registry merely to touch it.

## Acceptance

The public v0.2.0 corpus must be obtainable without OCP/conversion, survive an offline local reload, support a real comparison workflow, and have measured download/cache/time/RSS characteristics. Any major avoidable consumption-path problem blocks closure and becomes #141 work.
