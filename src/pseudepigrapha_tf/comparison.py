from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .apparatus import Apparatus
from .translations import Translations


def build_passage_comparison(
    api: Any,
    work: str,
    chapter: str | int,
    verse: str | int,
    *,
    selected_versions: Iterable[str] | None = None,
    selected_witnesses: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, object]:
    """Build the researcher-facing comparison model for one work passage.

    This interface is introduced by the RED gate for issue #109. Production
    semantics are intentionally not implemented in this scaffold commit.
    """

    return {}


def render_passage_comparison(model: Mapping[str, object]) -> str:
    """Render a passage-comparison model as deterministic HTML."""

    return ""
