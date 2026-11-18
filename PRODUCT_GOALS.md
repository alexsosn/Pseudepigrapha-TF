# Product goals — Pseudepigrapha-TF

## Users and purpose

Researchers of Jewish and Christian pseudepigrapha should be able to read, compare, search and cite Online Critical Pseudepigrapha source versions, textual apparatus, witnesses and generated translations through the released Text-Fabric corpus and small documented Python helpers.

## Representative research journeys

1. Open a passage in a specific textual version using a stable upstream reference; distinguish work identity from version identity.
2. Compare source versions of one work at a cited location without treating differing structures as automatically aligned.
3. Inspect apparatus readings and manuscript witnesses, distinguishing attested reading, explicit omission and unattested evidence.
4. Trace a generated translation to its explicitly linked source-version units while keeping it separate from historical witness evidence.
5. Search, navigate and cite a passage using the public browser/comparison workflow with source provenance and known gaps visible.

## Minimum usable release

The normal researcher can load an actual published corpus directly (without cloning or rebuilding OCP), perform the journeys above using documented commands/browser routes, and retrieve supporting source identities. A real clean-install/remote-download and offline-reload check must succeed. Converters, source snapshots, helper code and published data versions are distinguished honestly.

## Boundaries and priorities

Preserve OCP editorial uncertainty, version distinctions and upstream rights. No invented witness attribution, silent source normalization or extra semantic sidecars. Prefer real comparison/navigation improvements, source-version migration when justified and corrected published docs over new infrastructure. Follow current v1.1 release behavior rather than treating main-only changes as already published.

## Autonomous-development decision rules

- Select work by the researcher journeys above, not issue count or the ease of adding tests. Prefer finishing active PRs and releases over opening new tickets.
- Before introducing a new adapter, workflow, registry, protocol, or validation layer, demonstrate that an existing mechanism cannot meet a concrete acceptance need.
- Preserve source fidelity, access controls, security, and applicable upstream rights. Do not invent inferred text or silently weaken correctness gates.
- Batch repetitive data changes and reuse parameterized tests. Keep independent adversarial review proportional to risk, and validate the actual researcher path.
- If two successive cycles do not advance a journey or remove an observed blocker, reconsider the approach. Stop when the scoped deliverable works instead of generating optional infrastructure work.
