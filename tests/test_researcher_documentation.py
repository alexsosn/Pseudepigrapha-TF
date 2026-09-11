from pathlib import Path


README = Path("README.md")


def _heading_position(text: str, heading: str) -> int:
    position = text.find(f"\n## {heading}\n")
    assert position >= 0, f"README is missing researcher-facing section: {heading!r}"
    return position


def test_readme_leads_with_published_corpus_use_before_rebuilding():
    text = README.read_text(encoding="utf-8")

    required_order = (
        "What the corpus contains",
        "Get and load the published corpus",
        "Query a passage",
        "Apparatus and witnesses",
        "Generated translations",
        "Browse and compare",
        "Resource expectations",
        "Metadata and feature reference",
        "Known limitations",
        "Rebuild from OCP",
    )
    positions = tuple(_heading_position(text, heading) for heading in required_order)
    assert positions == tuple(sorted(positions)), "README researcher workflow is out of order"

    public_use = text[positions[1] : positions[-1]]
    assert "from tf.app import use" in public_use
    assert "alexsosn/Pseudepigrapha-TF" in public_use
    assert "complete.zip" in public_use

    assert "docs/runtime-footprint.md" in public_use
    assert "docs/features/0_home.md" in public_use

    rebuild = text[positions[-1] :]
    assert "pseudepigrapha-tf convert" in rebuild


def test_readme_does_not_claim_the_published_corpus_is_unavailable():
    text = README.read_text(encoding="utf-8").lower()
    obsolete_claims = (
        "does **not** include ocp xml or generated corpus data",
        "does **not** redistribute the ocp xml or a generated tf corpus",
    )
    for claim in obsolete_claims:
        assert claim not in text

    assert "v0.2.0" in text
    assert "published corpus" in text


def test_readme_metadata_example_treats_optional_citation_as_optional():
    text = README.read_text(encoding="utf-8")
    metadata_section = text.split("## Metadata and feature reference", 1)[1].split(
        "## Known limitations", 1
    )[0]

    assert 'tjob.get("citation")' in metadata_section
    assert 'tjob["citation"]' not in metadata_section
