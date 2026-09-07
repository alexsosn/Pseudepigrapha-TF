from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_exact(path: Path, old: str, new: str, expected: int, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} matches, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


model = ROOT / "src" / "pseudepigrapha_tf" / "model.py"
replace_exact(
    model,
    '''    generation_method: str = "llm"\n    generation_model: str = "openrouter/google/gemini-3.7-flash"\n''',
    '''    # Method/model come from repository history, not from the XML marker.\n    # They remain unknown until conversion is tied to an evidenced snapshot.\n    generation_method: str = ""\n    generation_model: str = ""\n''',
    1,
    "model provenance defaults",
)

conversion = ROOT / "src" / "pseudepigrapha_tf" / "conversion.py"
replace_exact(
    conversion,
    '''from .model import (\n''',
    '''PINNED_GENERATION_PROVENANCE = {\n    "c939dcbacad78c5d18d2c4282cad23c47e19ac07": (\n        "llm",\n        "openrouter/google/gemini-3.7-flash",\n    ),\n}\n\n\nfrom .model import (\n''',
    1,
    "conversion provenance map",
)
replace_exact(
    conversion,
    '''    if generation is not None:\n        values.update(\n            generation_marker=generation.marker,\n            generation_method=generation.generation_method,\n            generation_model=generation.generation_model,\n            generated_language=generation.target_language,\n        )\n''',
    '''    if generation is not None:\n        values.update(\n            generation_marker=generation.marker,\n            generated_language=generation.target_language,\n        )\n        if generation.generation_method:\n            values["generation_method"] = generation.generation_method\n        if generation.generation_model:\n            values["generation_model"] = generation.generation_model\n''',
    1,
    "conditional generator metadata",
)
replace_exact(
    conversion,
    '''        generated_id_counts: dict[str, int] = {}\n        for generated_index, translation in enumerate(book.generated_translations, 1):\n''',
    '''        generated_id_counts: dict[str, int] = {}\n        generation_method, generation_model = PINNED_GENERATION_PROVENANCE.get(\n            upstream_commit, ("", "")\n        )\n        for generated_index, translation in enumerate(book.generated_translations, 1):\n            if generation_method or generation_model:\n                translation = replace(\n                    translation,\n                    generation_method=generation_method,\n                    generation_model=generation_model,\n                )\n''',
    1,
    "snapshot-scoped generated provenance",
)

semantic = ROOT / "src" / "pseudepigrapha_tf" / "semantic_audit.py"
replace_exact(
    semantic,
    '''def _generated_provenance_features_ok(\n    data: TFData,\n    node_index: dict[str, list[int]],\n) -> bool:\n''',
    '''def _generated_provenance_features_ok(\n    data: TFData,\n    node_index: dict[str, list[int]],\n    upstream_commit: str,\n) -> bool:\n''',
    1,
    "semantic audit provenance signature",
)
replace_exact(
    semantic,
    '''    return all(\n        base._feature(data, "generation_marker", node) == "OCP-Trans"\n        and base._feature(data, "generation_method", node) == "llm"\n        and base._feature(data, "generation_model", node)\n        == "openrouter/google/gemini-3.7-flash"\n        for node in generated_books\n    )\n''',
    '''    marker_ok = all(\n        base._feature(data, "generation_marker", node) == "OCP-Trans"\n        for node in generated_books\n    )\n    if not marker_ok:\n        return False\n\n    if upstream_commit == "c939dcbacad78c5d18d2c4282cad23c47e19ac07":\n        return all(\n            base._feature(data, "generation_method", node) == "llm"\n            and base._feature(data, "generation_model", node)\n            == "openrouter/google/gemini-3.7-flash"\n            for node in generated_books\n        )\n\n    # The XML marker proves generated status, but not which historical generator\n    # implementation/model produced an unresearched snapshot. Unsupported\n    # history-derived claims must therefore be absent rather than guessed.\n    return all(\n        not base._feature(data, "generation_method", node)\n        and not base._feature(data, "generation_model", node)\n        for node in generated_books\n    )\n''',
    1,
    "semantic audit provenance policy",
)
replace_exact(
    semantic,
    '''        generated_alignment_ok\n        and _generated_provenance_features_ok(data, node_index)\n    )\n''',
    '''        generated_alignment_ok\n        and _generated_provenance_features_ok(\n            data,\n            node_index,\n            str(data.metadata.get("", {}).get("upstreamCommit", "")),\n        )\n    )\n''',
    1,
    "semantic audit provenance call",
)

tests = ROOT / "tests" / "test_generated_translations.py"
replace_exact(
    tests,
    '''    assert generated.generation_method == "llm"\n    assert generated.generation_model == "openrouter/google/gemini-3.7-flash"\n''',
    '''    # The parser sees XML structure only; history-derived generator claims\n    # are attached later only when conversion identifies an evidenced snapshot.\n    assert generated.generation_method == ""\n    assert generated.generation_model == ""\n''',
    1,
    "parser provenance expectations",
)
replace_exact(
    tests,
    '''    assert data.node_features["generation_method"][generated] == "llm"\n    assert data.node_features["generation_model"][generated] == "openrouter/google/gemini-3.7-flash"\n''',
    '''    assert generated not in data.node_features.get("generation_method", {})\n    assert generated not in data.node_features.get("generation_model", {})\n''',
    1,
    "unpinned graph provenance expectations",
)

plan = ROOT / "docs" / "generated-translations-plan.md"
replace_exact(
    plan,
    '''- exact generation method/model facts evidenced by the selected OCP snapshot (`llm`, `openrouter/google/gemini-3.7-flash`);\n''',
    '''- exact generation method/model facts evidenced by the selected OCP snapshot (`llm`, `openrouter/google/gemini-3.7-flash`); these history-derived values are attached only when the conversion identifies that evidenced upstream commit, never inferred from the XML marker on an arbitrary snapshot;\n''',
    1,
    "plan provenance scope",
)
