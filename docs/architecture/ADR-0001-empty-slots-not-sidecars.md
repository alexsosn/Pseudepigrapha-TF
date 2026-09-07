# ADR-0001: Represent zero-span textual entities with explicit empty slots

Status: Accepted  
Scope: project-family Text-Fabric architecture

## Decision

A source entity that **belongs to the textual sequence** and has an independent source position/order but no ordinary semantic slot MUST remain inside the Text-Fabric warp through an explicit empty/synthetic slot.

Do not move textual zero-span entities into a sidecar merely because Text-Fabric requires every non-slot node to span at least one slot. An empty slot is a technical positional anchor, not fabricated source text.

## Scope boundary

- Textual zero-span entities with their own source position/order get an explicit empty/synthetic slot.
- Ancestor/container nodes reuse descendant slots, including descendant empty slots.
- Genuinely non-textual nodes with no independent textual position (manuscript/resource/metadata/apparatus/provenance abstractions) may anchor through their textual locus or a documented O(1) technical anchor when TF requires one. That anchor is not textual content.
- Sidecars are for data genuinely outside the TF graph/API contract. **Zero span alone is not sufficient reason for a sidecar.**

## Required modelling contract

1. Keep the corpus's normal slot type and mark empty textual anchors explicitly (`type=empty`, `is_gap=1`, and/or `synthetic=1`).
2. Reports/tests distinguish semantic/source slots, synthetic empty slots, and total TF slots.
3. Empty textual units receive an anchor at their source position.
4. Empty containers get a new anchor only if descendants provide none and the container itself has a textual position that must be represented.
5. Never borrow a neighbouring real slot for an independently positioned textual entity.
6. Never fabricate visible Unicode/token/lexical content for an empty anchor.
7. Non-textual technical anchors must be documented and must not leak into APIs as fabricated content.

## Precedent

ETCBC/DSS creates empty slots for otherwise signless words/vacat clusters. Nino-cunei `tfFromAtf`, used by Old Babylonian / Old Assyrian, creates `cv.slot()` anchors for otherwise-empty textual lines/documents. The reusable principle is: **empty slots preserve textual position; they do not fabricate philological content.**

## Existing Pseudepigrapha-TF model

The current corpus already embodies the key distinction:

- an empty primary reading uses an `is_gap=1` surface-less anchor slot so the textual locus remains in TF;
- metadata-only versions are not turned into fabricated book/chapter/verse text;
- manuscripts/resources/apparatus abstractions use documented technical anchors and node-type rendering rather than pretending those anchors are their text.

Future changes must preserve this distinction. In particular, a textual empty locus must not be moved to a sidecar just because its semantic span is empty.

## Agent rule

Autonomous implementation/review agents MUST treat this ADR as the default architecture. Before proposing a zero-span sidecar, classify the object as textual, non-textual-but-in-graph, or genuinely outside TF. A sidecar proposal whose only justification is empty `oslots` is an architectural error. Deviating requires a corpus-specific ADR and independent review.

## Tests

Pin deterministic/source-ordered empty anchors, semantic-vs-total slot counts, normal TF reachability, no borrowed real slots, no fabricated visible content, and non-textual technical-anchor rendering behavior.
