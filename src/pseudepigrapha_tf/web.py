from __future__ import annotations

from pathlib import Path
from typing import Any

from .comparison import build_passage_comparison, render_passage_comparison


def list_comparison_works(api: Any) -> tuple[str, ...]:
    """Return source/critical OCP work identifiers available for comparison."""

    return ()


def register_comparison_route(flask_app: Any, tf_app: Any) -> Any:
    """Register the verse comparison page on an existing TF Flask app.

    RED-gate scaffold for issue #109. Route behavior is intentionally absent.
    """

    return flask_app


def create_comparison_web_app(tf_app: Any, *, app_name: str | None = None) -> Any:
    """Wrap one loaded TfApp with the stock TF Flask browser plus /compare."""

    raise NotImplementedError("issue #109 RED gate")


def load_local_comparison_web_app(
    data_path: Path,
    app_path: Path,
    *,
    version: str = "0.1",
    silent: str | bool = "deep",
) -> Any:
    """Load local TF data/app and return the stock browser with /compare."""

    raise NotImplementedError("issue #109 RED gate")


def run_local_comparison_browser(
    data_path: Path,
    app_path: Path,
    *,
    version: str = "0.1",
    port: int = 8000,
    debug: bool = False,
) -> int:
    """Run the stock TF web server after adding the comparison route."""

    raise NotImplementedError("issue #109 RED gate")
