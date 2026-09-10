# Issue #130 plan amendment — bind the actual express release

## Review finding

The first GREEN workflow checked that GitHub's latest release was the requested `RELEASE_TAG` before the express acquisition and instrumented `Checkout.downloadComplete()` to prove the express path executed successfully. That still leaves a time-of-check/time-of-use window: Text-Fabric resolves `/releases/latest` again inside `downloadComplete()` later.

At Text-Fabric 13.1.0 commit `dd227ce62b5536de53a0e20eac98c0459da8fd3d`, `downloadComplete()` assigns the tag parsed from the final `/releases/latest` URL to `self.releaseOn` before downloading `complete.zip`. This is the authoritative release identity for the actual express acquisition.

A newer app-only release could become latest after the workflow's early check while retaining identical TF data/converter/upstream metadata. The existing post-load metadata assertions would then be insufficient to prove that the requested release's `complete.zip` was tested.

## Amended TDD contract

Before implementation, add a workflow-contract regression requiring the express instrumentation to:

1. record `self.releaseOn` after each `Checkout.downloadComplete()` invocation;
2. assert at least one resolved release was observed;
3. require every successful express resolution to equal `os.environ['RELEASE_TAG']`;
4. retain the earlier latest-release precheck as a fast fail-closed guard;
5. retain the manifest-derived corpus identity assertions and network-blocked local reload.

Then implement only that resolved-release binding, run the full exact-head CI gates, and perform a new logically-independent adversarial review of the repaired head.