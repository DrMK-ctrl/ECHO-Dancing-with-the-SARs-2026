"""Command-line entry point for ECHO's SAR catalog discovery."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from echo.catalog import CatalogQuery, CatalogQueryError, build_catalog_record, search_gcov


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="echo")
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog", help="search ASF for NISAR GCOV metadata")
    catalog.add_argument("--longitude", type=float, required=True)
    catalog.add_argument("--latitude", type=float, required=True)
    catalog.add_argument("--start", dest="start_date", required=True)
    catalog.add_argument("--end", dest="end_date", required=True)
    catalog.add_argument("--maturity", choices=("BETA", "PROVISIONAL"), default="PROVISIONAL")
    catalog.add_argument("--max-results", type=int, default=250)
    catalog.add_argument("--output", type=Path, help="write metadata JSON to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    query = CatalogQuery(
        longitude=args.longitude,
        latitude=args.latitude,
        start_date=args.start_date,
        end_date=args.end_date,
        maturity=args.maturity,
        max_results=args.max_results,
    )
    try:
        features = search_gcov(query)
        record = build_catalog_record(query, features)
    except CatalogQueryError as exc:
        print(f"echo: {exc}", file=sys.stderr)
        return 2

    content = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"Wrote {record['feature_count']} catalog features to {args.output}")
    else:
        print(content, end="")
    return 0
