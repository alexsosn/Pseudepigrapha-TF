# Agora local materialization

Pseudepigrapha-TF can act as a locally trusted Agora materializer that rebuilds a derived Text-Fabric corpus from authoritative OCP source XML. This local materialization path is an alternative to consuming the published derived corpus; it does not redistribute OCP source XML.

The repository-level [`agora.materializer.json`](../agora.materializer.json) declares:

- materializer id `ocp-text-fabric`;
- automatic source: the official Online Critical Pseudepigrapha Git repository pinned to commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`, using `static/docs` as input;
- fallback source mode: a user-provided local `static/docs` directory;
- required direct `*.xml` input with symlinks disallowed by the host contract;
- execution through the existing `pseudepigrapha_tf.cli convert` command;
- immutable source revision propagation through the converter's existing `--upstream-commit` option;
- network denied while conversion runs;
- Text-Fabric output with `otype.tf`, `oslots.tf`, and `conversion-report.json` required.

The converter still works standalone:

```bash
pseudepigrapha-tf convert /path/to/OCP/static/docs --output tf/1.0
```

Agora invokes the same public CLI implementation as a Python module. For Git acquisition, Agora resolves the fetched commit and substitutes it into `{source_revision}`; for a user-local checkout it passes a locally detected Git `HEAD` when available. If local files have no Git revision, the placeholder is empty and the converter records no upstream commit, matching its non-Git standalone behavior.

This avoids mounting `.git` into the sandbox while preserving the converter's provenance semantics.

## Licensing boundary

This integration does not change source licensing. Pseudepigrapha-TF public releases may redistribute the derived Text-Fabric corpus under the documented OCP content-license boundary; the upstream OCP source XML itself remains in the OCP repository. Agora's materializer acquires the authoritative source revision or accepts user-local sources and produces a local derived artifact.

The Agora-produced artifact remains local unless its source and derived-data licenses independently permit redistribution.

## Responsibility boundary

Pseudepigrapha-TF remains responsible for parsing, semantic preservation, Text-Fabric construction, and the conversion parity audit. Agora is responsible for acquisition orchestration, sandboxed process launch, integration path validation, transactional artifact publication, and local provenance.

A conversion error that also occurs when `pseudepigrapha-tf convert` is run directly remains a Pseudepigrapha-TF issue rather than an Agora integration fix.
