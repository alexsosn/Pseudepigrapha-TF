from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from flask import Response, request

from .comparison import (
    build_passage_comparison,
    passage_neighbors,
    render_passage_comparison,
)
from .release_identity import TF_DATA_VERSION


def _h(value: object) -> str:
    return escape(str(value), quote=True)


def list_comparison_works(api: Any) -> tuple[str, ...]:
    """Return source/critical OCP work identifiers available for comparison."""

    otype = getattr(api.F, "otype", None)
    books = getattr(otype, "s", None) if otype is not None else None
    ocp_book = getattr(api.F, "ocp_book", None)
    if books is None or ocp_book is None:
        raise ValueError("otype and ocp_book features must be loaded for comparison browsing")

    version_kind = getattr(api.F, "version_kind", None)
    works: set[str] = set()
    for node in books("book"):
        if version_kind is not None and version_kind.v(node) == "generated_translation":
            continue
        work = str(ocp_book.v(node) or "").strip()
        if work:
            works.add(work)
    return tuple(sorted(works))


def _landing_html(api: Any) -> str:
    options = "".join(
        f'<option value="{_h(work)}">{_h(work)}</option>'
        for work in list_comparison_works(api)
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Passage comparison</title>'
        '<link rel="stylesheet" href="/data/static/comparison.css">'
        '</head><body><main class="comparison-page">'
        '<nav class="comparison-nav"><a href="/">Text-Fabric browser</a></nav>'
        '<h1>Passage comparison</h1>'
        '<form class="comparison-landing" action="/compare" method="get">'
        '<label>Work <select name="work" required>'
        '<option value="">Choose a work</option>'
        f'{options}</select></label>'
        '<label>Chapter <input name="chapter" required></label>'
        '<label>Verse <input name="verse" required></label>'
        '<button type="submit">Open passage</button>'
        '</form></main></body></html>'
    )


def _error_html(message: object) -> str:
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Invalid comparison request</title>'
        '<link rel="stylesheet" href="/data/static/comparison.css">'
        '</head><body><main class="comparison-page">'
        '<nav class="comparison-nav"><a href="/compare">Passage comparison</a> · '
        '<a href="/">Text-Fabric browser</a></nav>'
        '<h1>Invalid comparison request</h1>'
        f'<p class="comparison-error">{_h(message)}</p>'
        '</main></body></html>'
    )


def _witness_selection(args: Any) -> dict[str, tuple[str, ...]] | None:
    result: dict[str, tuple[str, ...]] = {}
    for key in args.keys():
        if not key.startswith("witness."):
            continue
        version_id = key[len("witness.") :]
        if not version_id:
            continue
        # A hidden empty input is rendered for every witness selector. Its
        # presence distinguishes an explicit "show no witnesses" submission
        # from an untouched request, where defaults should still apply.
        result[version_id] = tuple(value for value in args.getlist(key) if value)
    return result or None


def _selected_version_ids(model: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        str(choice.get("id", ""))
        for choice in model.get("version_choices", ())
        if isinstance(choice, dict) and choice.get("selected")
    )


def register_comparison_route(flask_app: Any, tf_app: Any) -> Any:
    """Register the verse comparison page on an existing TF Flask app."""

    if "pseudepigrapha_compare" in flask_app.view_functions:
        return flask_app

    @flask_app.get("/compare", endpoint="pseudepigrapha_compare")
    def compare_passage():
        work = (request.args.get("work") or "").strip()
        chapter = (request.args.get("chapter") or "").strip()
        verse = (request.args.get("verse") or "").strip()
        if not (work and chapter and verse):
            return Response(_landing_html(tf_app.api), mimetype="text/html")

        selected_versions = tuple(
            value for value in request.args.getlist("version") if value
        )
        selected_witnesses = _witness_selection(request.args)
        try:
            model = build_passage_comparison(
                tf_app.api,
                work,
                chapter,
                verse,
                selected_versions=selected_versions or None,
                selected_witnesses=selected_witnesses,
            )
            # The normal builder always exposes version choices. Keep route unit
            # tests free to substitute a deliberately tiny fake model.
            if "version_choices" in model:
                model["navigation"] = passage_neighbors(
                    tf_app.api,
                    work,
                    chapter,
                    verse,
                    preferred_versions=_selected_version_ids(model),
                )
        except (KeyError, ValueError) as error:
            return Response(_error_html(error), status=400, mimetype="text/html")
        return Response(render_passage_comparison(model), mimetype="text/html")

    return flask_app


def create_comparison_web_app(tf_app: Any, *, app_name: str | None = None) -> Any:
    """Wrap one browser-mode TfApp with the stock TF Flask browser plus /compare."""

    if tf_app is None or getattr(tf_app, "api", None) is None:
        raise ValueError("a loaded Text-Fabric app with api is required")
    if getattr(tf_app, "_browse", False) is not True:
        raise ValueError(
            "Text-Fabric app must be loaded in browser mode; use "
            "load_local_comparison_web_app() or findApp(..., browse=True, ...)"
        )
    try:
        from tf.browser.kernel import makeTfKernel
        from tf.browser.web import Web, factory
    except (ImportError, AttributeError) as error:  # pragma: no cover - compatibility guard
        raise RuntimeError(
            "Text-Fabric 13.x browser integration is unavailable; "
            "Pseudepigrapha-TF comparison browsing requires tf.browser.web/kernel"
        ) from error

    context = getattr(tf_app, "context", None)
    resolved_name = (
        app_name or getattr(context, "appName", None) or "pseudepigrapha-tf"
    )
    web = Web(makeTfKernel(tf_app, resolved_name))
    return register_comparison_route(factory(web), tf_app)


def load_local_comparison_web_app(
    data_path: Path,
    app_path: Path,
    *,
    version: str = TF_DATA_VERSION,
    silent: str | bool = "deep",
) -> Any:
    """Load local TF data/app in browser mode and return the stock browser plus /compare."""

    data_path = Path(data_path)
    app_path = Path(app_path)
    if not data_path.is_dir():
        raise FileNotFoundError(f"Text-Fabric data directory not found: {data_path}")
    if not app_path.is_dir():
        raise FileNotFoundError(f"Text-Fabric app directory not found: {app_path}")

    from tf.advanced.app import findApp

    # Match tf.browser.web.setup(): browser mode is required because advanced
    # links/header methods return browser HTML only when _browse is true.
    tf_app = findApp(
        f"app:{app_path}",
        "",
        None,
        "github",
        True,
        version=version,
        locations=[str(data_path)],
        modules=[""],
        silent=silent,
    )
    if tf_app is None or getattr(tf_app, "api", None) is None:
        raise RuntimeError(
            f"could not load Text-Fabric app {app_path} against materialized data {data_path}"
        )
    return create_comparison_web_app(tf_app)


def run_local_comparison_browser(
    data_path: Path,
    app_path: Path,
    *,
    version: str = TF_DATA_VERSION,
    port: int = 8000,
    debug: bool = False,
) -> int:
    """Run the stock TF web server after adding the comparison route."""

    if not 1 <= int(port) <= 65535:
        raise ValueError(f"port must be between 1 and 65535, got {port}")
    webapp = load_local_comparison_web_app(
        Path(data_path),
        Path(app_path),
        version=version,
        silent=False,
    )
    from tf.browser.web import runWeb

    return int(runWeb(webapp, debug, int(port)))
