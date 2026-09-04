# Agora local materialization

Pseudepigrapha-TF can act as a locally trusted Agora materializer without redistributing OCP source XML or a generated Text-Fabric corpus.

The repository-level [`agora.materializer.json`](../agora.materializer.json) declares:

- materializer id `ocp-text-fabric`;
- automatic source: the official Online Critical Pseudepigrapha Git repository pinned to commit `2d1d14d23434a784d377ff7f4409ccdb2d18aafb`, using `static/docs` as input;
- fallback source mode: a user-provided local `static/docs` directory;
- required direct `*.xml` input with symlinks disallowed by the host contract;
- execution through the existing `pseudepigrapha_tf.cli convert` command;
- immutable source revision propagation through the converter's existing `--upstream-commit` option;
- network denied while conversion runs;
- Text-Fabric output with `otype.tf`, `oslots.tf`, and `conversion-report.json` required.

The converter still works standalone:

```bash
pseudepigrapha-tf convert /path/to/OCP/static/docs --output tf/0.1
```

Agora invokes the same public CLI implementation as a Python module. For Git acquisition, Agora resolves the fetched commit and substitutes it into `{source_revision}`; for a user-local checkout it passes a locally detected Git `HEAD` when available. If local files have no Git revision, the placeholder is empty and the converter records no upstream commit, matching its non-Git standalone behavior.

This avoids mounting `.git` into the sandbox while preserving the converter's provenance semantics.

## Licensing boundary

This integration does not change the repository's distribution policy. Pseudepigrapha-TF distributes converter code and the materializer recipe, not OCP XML and not generated TF data. Automatic acquisition points at the authoritative public upstream revision; sources that a user obtained under separate terms can instead be supplied locally.

The resulting artifact remains local unless its source and derived-data licenses independently permit redistribution.

## Responsibility boundary

Pseudepigrapha-TF remains responsible for parsing, semantic preservation, Text-Fabric construction, and the conversion parity audit. Agora is responsible for acquisition orchestration, sandboxed process launch, integration path validation, transactional artifact publication, and local provenance.

A conversion error that also occurs when `pseudepigrapha-tf convert` is run directly remains a Pseudepigrapha-TF issue rather than an Agora integration fix.
