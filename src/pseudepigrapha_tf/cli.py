from __future__ import annotations

import argparse
from pathlib import Path

from .graph import build_tf_data
from .source import load_source_directory
from .writer import write_tf


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert Online Critical Pseudepigrapha XML to Text-Fabric")
    sub = parser.add_subparsers(dest="command", required=True)
    convert = sub.add_parser("convert", help="convert all direct *.xml files in an OCP docs directory")
    convert.add_argument("source", type=Path, help="path to OCP static/docs")
    convert.add_argument("--output", type=Path, default=Path("tf/0.1"), help="Text-Fabric output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "convert":
        books, source_warnings = load_source_directory(args.source)
        if not books:
            raise SystemExit("no non-empty OCP XML files found")
        data = build_tf_data(books)
        for warning in [*source_warnings, *data.warnings]:
            print(f"warning: {warning}")
        if not write_tf(data, args.output):
            raise SystemExit("Text-Fabric refused the generated dataset")
        print(
            f"converted {len(books)} OCP files to {args.output} "
            f"({data.max_slot} word slots, {data.max_node} total nodes)"
        )
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
