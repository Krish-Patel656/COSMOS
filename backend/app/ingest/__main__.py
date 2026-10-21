"""Command-line entry point for catalogue ingestion.

    python -m app.ingest                 # seed from the committed snapshot
    python -m app.ingest --refresh       # re-query NASA and update the snapshot
    python -m app.ingest --limit 500     # small slice, useful while developing
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.db.session import SessionLocal, dispose_engine, init_models
from app.ingest.pipeline import run_ingest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.ingest",
        description="Ingest the NASA Exoplanet Archive into the COSMOS database.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="query the live archive instead of the committed snapshot",
    )
    parser.add_argument(
        "--curated",
        action="store_true",
        help="ingest the offline notable-systems catalogue instead of NASA",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="only ingest the first N catalogue rows",
    )
    parser.add_argument(
        "--no-solar-system",
        action="store_true",
        help="skip the Solar System reference records",
    )
    parser.add_argument("--quiet", action="store_true", help="only log warnings and errors")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    await init_models()
    async with SessionLocal() as session:
        report = await run_ingest(
            session,
            refresh=args.refresh,
            curated=args.curated,
            row_limit=args.limit,
            include_solar_system=not args.no_solar_system,
        )
    await dispose_engine()

    print(f"\nsource            {report.source}")
    print(f"rows fetched      {report.rows_fetched}")
    print(f"systems written   {report.stars_written}")
    print(f"planets written   {report.planets_written}")
    print(f"elapsed           {report.duration_seconds:.1f}s")
    return 0 if report.planets_written else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)-8s %(name)s: %(message)s",
    )
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
