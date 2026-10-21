"""Ingestion pipeline.

Resolution order for catalogue data, chosen so that a clean checkout works
offline and at zero cost:

1. the committed gzipped snapshot, if present and ``refresh`` was not requested;
2. a live TAP query against the NASA Exoplanet Archive, which then updates the
   snapshot;
3. the Solar System alone, which is always loaded regardless.

Writes are destructive-and-atomic for the catalogue tables: a refresh replaces
every star and planet inside one transaction. User data is untouched, because
favourites and collections reference planets by slug rather than by surrogate
id, and slugs are derived from names that the archive keeps stable.
"""

from __future__ import annotations

import gzip
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ingest import nasa, notable, normalize
from app.models import IngestRun, Planet, Star

logger = logging.getLogger(__name__)

STAR_ONLY_KEYS = {"planets"}


@dataclass
class IngestReport:
    source: str
    rows_fetched: int
    stars_written: int
    planets_written: int
    duration_seconds: float
    message: str = ""

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "rows_fetched": self.rows_fetched,
            "stars_written": self.stars_written,
            "planets_written": self.planets_written,
            "duration_seconds": round(self.duration_seconds, 2),
            "message": self.message,
        }


# --- Snapshot --------------------------------------------------------------


def snapshot_exists(path: Path | None = None) -> bool:
    return (path or settings.snapshot_path).exists()


def read_snapshot(path: Path | None = None) -> list[dict[str, str | None]]:
    target = path or settings.snapshot_path
    with gzip.open(target, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload["rows"] if isinstance(payload, dict) else payload
    logger.info("Loaded %d rows from snapshot %s", len(rows), target.name)
    return rows


def write_snapshot(
    rows: list[dict[str, str | None]], path: Path | None = None
) -> Path:
    target = path or settings.snapshot_path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "NASA Exoplanet Archive — pscomppars",
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "row_count": len(rows),
        "columns": list(nasa.COLUMNS),
        "rows": rows,
    }
    # mtime=0 and an empty stored filename keep the gzip byte-identical across
    # runs with identical content, so re-running ingestion does not create a
    # spurious git diff. (GzipFile would otherwise embed both in the header.)
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    with target.open("wb") as handle, gzip.GzipFile(
        filename="", mode="wb", fileobj=handle, mtime=0
    ) as raw:
        raw.write(body)
    logger.info("Wrote snapshot %s (%.1f MB)", target.name, target.stat().st_size / 1e6)
    return target


async def load_rows(
    refresh: bool = False,
    row_limit: int | None = None,
    curated: bool = False,
) -> tuple[list[dict[str, str | None]], str]:
    """Return catalogue rows plus a label describing where they came from.

    Resolution order: ``--curated`` notable set, existing gzip snapshot, live NASA
    TAP query, then notables again if the archive is unreachable.
    """
    if curated:
        rows = notable.catalogue_rows()
        if row_limit:
            rows = rows[:row_limit]
        return rows, "notable-catalogue"

    if not refresh and snapshot_exists():
        return read_snapshot(), "snapshot"

    try:
        rows = await nasa.fetch_rows(row_limit=row_limit or settings.ingest_row_limit)
        write_snapshot(rows)
        return rows, "nasa-archive"
    except nasa.NasaArchiveError as exc:
        if snapshot_exists():
            logger.warning("Live fetch failed (%s); falling back to snapshot", exc)
            return read_snapshot(), "snapshot-fallback"
        logger.warning("Live fetch failed (%s); falling back to notable catalogue", exc)
        return notable.catalogue_rows(), "notable-catalogue"


# --- Database writes -------------------------------------------------------


async def _replace_catalogue(
    session: AsyncSession, stars: list[dict[str, Any]]
) -> tuple[int, int]:
    """Replace every star and planet with the supplied records."""
    # ON DELETE CASCADE removes the planets, but SQLite only honours that when
    # foreign keys are enforced, so delete children explicitly first.
    await session.execute(delete(Planet))
    await session.execute(delete(Star))

    star_rows = [{k: v for k, v in star.items() if k not in STAR_ONLY_KEYS} for star in stars]
    if not star_rows:
        return (0, 0)

    # Chunked inserts keep SQLite's statement-variable limit out of reach.
    chunk = 400
    for start in range(0, len(star_rows), chunk):
        await session.execute(insert(Star), star_rows[start : start + chunk])
    await session.flush()

    id_by_slug = {
        slug: star_id
        for star_id, slug in (await session.execute(select(Star.id, Star.slug))).all()
    }

    planet_rows: list[dict[str, Any]] = []
    for star in stars:
        star_id = id_by_slug.get(star["slug"])
        if star_id is None:
            continue
        for planet in star["planets"]:
            row = {k: v for k, v in planet.items() if k != "surface_temp_k"}
            row["star_id"] = star_id
            planet_rows.append(row)

    for start in range(0, len(planet_rows), chunk):
        await session.execute(insert(Planet), planet_rows[start : start + chunk])

    return (len(star_rows), len(planet_rows))


async def run_ingest(
    session: AsyncSession,
    refresh: bool = False,
    row_limit: int | None = None,
    include_solar_system: bool = True,
    curated: bool = False,
) -> IngestReport:
    """Fetch, normalise, score and persist the full catalogue."""
    started = time.monotonic()
    rows, source = await load_rows(refresh=refresh, row_limit=row_limit, curated=curated)

    stars = normalize.normalize_rows(rows) if rows else []
    if include_solar_system:
        # Prepended so the Sun is the lowest star id, a small convenience when
        # eyeballing the database.
        stars.insert(0, normalize.build_solar_system())

    stars_written, planets_written = await _replace_catalogue(session, stars)

    duration = time.monotonic() - started
    message = (
        f"Loaded {planets_written} planets across {stars_written} systems from {source}."
        if planets_written
        else "No catalogue data available."
    )
    report = IngestReport(
        source=source,
        rows_fetched=len(rows),
        stars_written=stars_written,
        planets_written=planets_written,
        duration_seconds=duration,
        message=message,
    )

    session.add(
        IngestRun(
            source=source,
            status="success" if planets_written else "empty",
            rows_fetched=len(rows),
            stars_written=stars_written,
            planets_written=planets_written,
            duration_seconds=duration,
            message=message,
        )
    )
    await session.commit()

    logger.info("%s (%.1fs)", message, duration)
    return report
