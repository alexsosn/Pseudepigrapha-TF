# Agora local materialization

Pseudepigrapha-TF can act as a locally installed Agora materializer without redistributing OCP source XML or a generated Text-Fabric corpus.

The repository-level [`agora.materializer.json`](../agora.materializer.json) is the machine-readable contract. It declares:

- materializer id: `ocp-text-fabric`;
- automatic source: the official Online Critical Pseudepigrapha Git repository pinned to commit `2d1d14d23434a784d377ff7f4409ccdb2d18aafb`, using `static/docs` as input;
- fallback source mode: a user-provided local `static/docs` directory;
- required input: a directory containing direct `*.xml` files and no symlinks;
- execution: the installed Python module `pseudepigrapha_tf.cli` with the existing `convert` command;
- network policy: denied while the converter runs;
- output format: `text-fabric`;
- required output files: `otype.tf`, `oslots.tf`, and `conversion-report.json`.

The converter itself does not download source data in this integration. Agora acquires or asks the user for source files first and passes a local read-only source directory to the materializer. This keeps acquisition policy and host privileges outside the converter while preserving the existing standalone CLI:

```bash
pseudepigrapha-tf convert /path/to/OCP/static/docs --output tf/0.1
```

Agora's prototype host invokes the same implementation as a Python module, with only `{source}` and `{output}` substituted from the trusted installed manifest. No shell command is required by this repository.

## Licensing boundary

This integration does not change the repository's distribution policy. Pseudepigrapha-TF distributes converter code and the materializer recipe, not OCP XML and not generated TF data. Automatic acquisition points at the authoritative public upstream revision; sources that a user obtained under separate terms can instead be supplied locally.

The resulting artifact is intended to remain local unless its source and derived-data licenses independently permit redistribution.

## Responsibility boundary

Pseudepigrapha-TF remains responsible for parsing, semantic preservation, Text-Fabric construction, and the conversion parity audit. Agora is responsible for acquisition orchestration, sandboxed process launch, path validation, and local artifact provenance. A conversion error that also occurs when `pseudepigrapha-tf convert` is run directly remains a Pseudepigrapha-TF issue rather than an Agora integration fix.
