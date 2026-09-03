from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

from . import __version__
from .conversion import build_tf_data
from .semantic_audit import build_conversion_report, write_conversion_report
from .source import detect_git_commit, load_source_directory
from .writer import write_tf

UPSTREAM_REPOSITORY = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert Online Critical Pseudepigrapha XML to Text-Fabric")
    sub = parser.add_subparsers(dest="command", required=True)
    convert = sub.add_parser("convert", help="convert all direct *.xml files in an OCP docs directory")
    convert.add_argument("source", type=Path, help="path to OCP static/docs")
    convert.add_argument("--output", type=Path, default=Path("tf/0.1"), help="Text-Fabric output directory")
    convert.add_argument(
        "--upstream-commit",
        default=None,
        help="override the OCP Git commit recorded in provenance (auto-detected by default)",
    )
    convert.add_argument(
        "--report",
        type=Path,
        default=None,
        help="conversion report path (default: OUTPUT/conversion-report.json)",
    )
    return parser


def _stage(name: str, started: float) -> float:
    now = perf_counter()
    print(f"timing: {name} {now - started:.3f}s", flush=True)
    return now


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "convert":
        return 2

    total_started = stage_started = perf_counter()
    books, source_warnings = load_source_directory(args.source)
    stage_started = _stage("load_source", stage_started)
    if not books:
        raise SystemExit("no non-empty OCP XML files found")

    upstream_commit = args.upstream_commit if args.upstream_commit is not None else detect_git_commit(args.source)
    data = build_tf_data(
        books,
        upstream_repository=UPSTREAM_REPOSITORY,
        upstream_commit=upstream_commit,
        converter_version=__version__,
    )
    stage_started = _stage("build_graph", stage_started)
    for warning in [*source_warnings, *data.warnings]:
        print(f"warning: {warning}")

    report_path = args.report or (args.output / "conversion-report.json")
    report = build_conversion_report(args.source, books, data)
    stage_started = _stage("semantic_audit", stage_started)
    write_conversion_report(report, report_path)
    stage_started = _stage("write_report", stage_started)
    if report["status"] != "ok":
        raise SystemExit(
            f"semantic parity audit failed ({', '.join(report['failed_checks'])}); report: {report_path}"
        )

    if not write_tf(data, args.output):
        raise SystemExit("Text-Fabric refused the generated dataset")
    _stage("write_text_fabric", stage_started)
    print(f"timing: total {perf_counter() - total_started:.3f}s", flush=True)
    print(
        f"converted {len(books)} OCP files to {args.output} "
        f"({data.max_slot} word slots, {data.max_node} total nodes, "
        f"{data.oslots_edge_count} oslots edges); parity report: {report_path}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())