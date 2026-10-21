"""NASA Exoplanet Archive client.

Data comes from the ``pscomppars`` table ("Planetary Systems Composite
Parameters"), which the archive maintains as one row per confirmed planet with
the most complete parameter set assembled across publications. That is the right
table for an explorer: the alternative, ``ps``, carries one row per publication
per planet and would need its own reconciliation logic.

The archive's TAP endpoint is free, requires no key, and asks only that callers
be reasonable about query volume — so ingestion is a deliberate batch job, not
something an API request triggers.

Reference: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
"""

from __future__ import annotations

import csv
import io
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Only the columns we actually store. Selecting explicitly (rather than `*`)
# keeps the response under a few megabytes and makes a schema change at the
# archive a loud failure instead of a silent one.
COLUMNS: tuple[str, ...] = (
    # Identity
    "pl_name",
    "hostname",
    "sy_snum",
    "sy_pnum",
    # Discovery
    "discoverymethod",
    "disc_year",
    "disc_facility",
    "pl_controv_flag",
    # Orbit
    "pl_orbper",
    "pl_orbsmax",
    "pl_orbeccen",
    "pl_orbincl",
    # Planet bulk
    "pl_rade",
    "pl_radj",
    "pl_bmasse",
    "pl_bmassj",
    "pl_bmassprov",
    # Planet thermal
    "pl_eqt",
    "pl_insol",
    # Star
    "st_spectype",
    "st_teff",
    "st_rad",
    "st_mass",
    "st_met",
    "st_logg",
    "st_age",
    "st_lum",
    "st_rotp",
    # Position / photometry
    "ra",
    "dec",
    "sy_dist",
    "sy_vmag",
    "sy_gaiamag",
    # Provenance. Note `pscomppars` has no `rowupdate` column (that lives on the
    # per-publication `ps` table); `pl_pubdate` is the publication date of the
    # reference the composite parameters were drawn from.
    "pl_pubdate",
)


class NasaArchiveError(RuntimeError):
    """Raised when the archive is unreachable or returns something unusable."""


def build_query(row_limit: int | None = None) -> str:
    columns = ", ".join(COLUMNS)
    top = f"top {int(row_limit)} " if row_limit else ""
    # Ordering by host name keeps planets of the same system adjacent, which
    # makes the grouping step in the normaliser cheap and the output diffable.
    return f"select {top}{columns} from pscomppars order by hostname, pl_name"


async def fetch_rows(
    row_limit: int | None = None, timeout: float | None = None
) -> list[dict[str, str | None]]:
    """Fetch raw catalogue rows as dictionaries of strings.

    Values arrive as strings (possibly empty). Type coercion is the
    normaliser's job so that the snapshot on disk stays a faithful copy of what
    the archive served.
    """
    params = {
        "query": build_query(row_limit),
        "format": "csv",
    }
    timeout_value = timeout or settings.ingest_timeout_seconds

    logger.info("Requesting NASA Exoplanet Archive: %s", settings.nasa_tap_url)
    try:
        async with httpx.AsyncClient(timeout=timeout_value, follow_redirects=True) as client:
            response = await client.get(settings.nasa_tap_url, params=params)
            response.raise_for_status()
            body = response.text
    except httpx.HTTPError as exc:
        raise NasaArchiveError(f"could not reach the NASA Exoplanet Archive: {exc}") from exc

    # TAP reports query errors with HTTP 200 and an XML or plain-text body.
    stripped = body.lstrip()
    if stripped.startswith("<") or "ERROR" in stripped[:400].upper():
        raise NasaArchiveError(f"archive rejected the query: {stripped[:400]}")

    reader = csv.DictReader(io.StringIO(body))
    rows = [{key: (value or None) for key, value in row.items()} for row in reader]
    if not rows:
        raise NasaArchiveError("archive returned no rows")

    missing = set(COLUMNS) - set(rows[0].keys())
    if missing:
        raise NasaArchiveError(f"archive response is missing expected columns: {sorted(missing)}")

    logger.info("Fetched %d planet rows", len(rows))
    return rows
