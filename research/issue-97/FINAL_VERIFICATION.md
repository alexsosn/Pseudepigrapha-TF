# Issue #97 final verification gate

The final distribution-integrity candidate incorporates the adversarial RED cases discovered after the initial implementation:

- serialized Text-Fabric identity is cross-checked against the conversion report through the canonical provenance-field mapping;
- real Text-Fabric `otype.tf` headers remain compatible with repeated non-identity metadata such as `writtenBy`, while duplicate identity-bearing metadata fails closed;
- malformed/missing `@node` metadata headers and missing blank separators are rejected;
- TF data-version path components reject traversal, separators, and embedded NUL bytes;
- materialized TF directories reject root, file, and directory symlinks before staging trusts colocated reports;
- synthetic publication fixtures now serialize the same minimum identity contract expected from real release candidates.

This commit intentionally changes no runtime behavior. Its purpose is to trigger the authoritative normal PR CI on the combined human-authored candidate. Finalization still requires both the unit/Text-Fabric and exact pinned-OCP jobs to pass, followed by a fresh logically independent separate-pass adversarial review of that exact green head.
