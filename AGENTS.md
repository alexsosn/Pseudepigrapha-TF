# Agent instructions

> **Autonomous-development policy:** Before selecting or inventing work, read [PRODUCT_GOALS.md](PRODUCT_GOALS.md) and [docs/agentic-development-policy.md](docs/agentic-development-policy.md). State the targeted researcher journey, observed blocker, minimal reuse-first solution and real-data/public-interface acceptance criterion. Follow proportional research → plan → TDD → test → logically independent adversarial review. Preserve all more specific source, editorial, safety and release requirements below.

> **Product-goal gate:** Before selecting a task or expanding the backlog, read [PRODUCT_GOALS.md](PRODUCT_GOALS.md). Prioritize its researcher journeys and minimum usable release; require concrete evidence for infrastructure work. Keep all mandatory source, security, licensing, TDD and independent-review checks below.

Before changing Text-Fabric serialization, node anchoring, apparatus loci, or empty-source handling, read `docs/architecture/ADR-0001-empty-slots-not-sidecars.md` and the current data-model sections in `README.md`.

## Zero-span TF invariant

An independently positioned source entity that belongs to the textual sequence but has no ordinary semantic slot remains inside Text-Fabric through an explicit empty/synthetic slot. Do not invent a sidecar solely to satisfy the TF `oslots` invariant.

Pseudepigrapha-TF already distinguishes textual gap anchors from non-textual technical anchors. Preserve that distinction:

- empty textual readings/loci use explicit surface-less gap/empty slots;
- metadata, manuscript, resource, provenance, and apparatus abstractions may use documented O(1) technical anchors when required, but those anchors are not their textual content;
- ancestors reuse descendant anchors rather than multiplying synthetic slots;
- never borrow a neighbouring real slot for an independently positioned textual entity;
- never fabricate visible source text for a technical/empty anchor;
- tests and reports must distinguish semantic/source slots, synthetic empty slots, and total TF slots where relevant;
- a sidecar for textual zero-span nodes is an architectural deviation requiring a corpus-specific ADR and independent review.

For behavioral changes, use the repository's issue-driven research → plan → RED-first TDD → verification → independent skeptical review loop.
