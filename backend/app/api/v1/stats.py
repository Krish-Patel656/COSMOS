"""Catalogue statistics.

Powers the landing-page counters and, more usefully, gives the explorer the real
min/max of every numeric column so sliders span the actual data instead of
hard-coded guesses that would hide planets at the extremes.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import desc, func, select

from app.api.deps import CacheDep, SessionDep
from app.core.cache import cache_key
from app.models import IngestRun, Planet, Star
from app.schemas.astronomy import CatalogueStats

router = APIRouter(tags=["catalogue"])

EARTH_LIKE_ESI_THRESHOLD = 0.8

_RANGE_COLUMNS = {
    "radius_earth": Planet.radius_earth,
    "mass_earth": Planet.mass_earth,
    "equilibrium_temp_k": Planet.equilibrium_temp_k,
    "orbital_period_days": Planet.orbital_period_days,
    "semi_major_axis_au": Planet.semi_major_axis_au,
    "insolation_earth": Planet.insolation_earth,
    "density_g_cm3": Planet.density_g_cm3,
    "esi": Planet.esi,
    "habitability_score": Planet.habitability_score,
    "discovery_year": Planet.discovery_year,
}


async def _group_counts(session, column, limit: int | None = None) -> dict[str, int]:
    statement = (
        select(column, func.count()).where(column.is_not(None)).group_by(column).order_by(desc(func.count()))
    )
    if limit:
        statement = statement.limit(limit)
    rows = (await session.execute(statement)).all()
    return {str(key): int(count) for key, count in rows}


@router.get("/stats", response_model=CatalogueStats, summary="Catalogue summary and filter ranges")
async def stats(session: SessionDep, cache: CacheDep) -> CatalogueStats:
    key = cache_key("catalogue-stats", version=2)
    cached = await cache.get(key)
    if cached is not None:
        return CatalogueStats.model_validate(cached)

    planet_count = await session.scalar(select(func.count(Planet.id))) or 0
    star_count = await session.scalar(select(func.count(Star.id))) or 0
    scored = (
        await session.scalar(
            select(func.count(Planet.id)).where(Planet.habitability_score.is_not(None))
        )
        or 0
    )
    conservative = (
        await session.scalar(
            select(func.count(Planet.id)).where(Planet.in_conservative_hz.is_(True))
        )
        or 0
    )
    optimistic = (
        await session.scalar(
            select(func.count(Planet.id)).where(Planet.in_optimistic_hz.is_(True))
        )
        or 0
    )
    earth_like = (
        await session.scalar(
            select(func.count(Planet.id)).where(Planet.esi >= EARTH_LIKE_ESI_THRESHOLD)
        )
        or 0
    )

    nearest = await session.scalar(
        select(func.min(Star.distance_ly)).where(Star.distance_ly > 0)
    )
    farthest = await session.scalar(select(func.max(Star.distance_ly)))

    ranges: dict[str, dict[str, float | None]] = {}
    for name, column in _RANGE_COLUMNS.items():
        low, high = (
            await session.execute(select(func.min(column), func.max(column)))
        ).one()
        ranges[name] = {
            "min": float(low) if low is not None else None,
            "max": float(high) if high is not None else None,
        }

    last_run = (
        await session.execute(select(IngestRun).order_by(IngestRun.id.desc()).limit(1))
    ).scalars().first()

    response = CatalogueStats(
        planet_count=planet_count,
        star_count=star_count,
        scored_planet_count=scored,
        conservative_hz_count=conservative,
        optimistic_hz_count=optimistic,
        earth_like_count=earth_like,
        nearest_system_ly=float(nearest) if nearest is not None else None,
        farthest_system_ly=float(farthest) if farthest is not None else None,
        discovery_year_range=[
            int(ranges["discovery_year"]["min"]) if ranges["discovery_year"]["min"] else None,
            int(ranges["discovery_year"]["max"]) if ranges["discovery_year"]["max"] else None,
        ],
        by_discovery_method=await _group_counts(session, Planet.discovery_method),
        by_size_class=await _group_counts(session, Planet.size_class),
        by_spectral_class=await _group_counts(session, Star.spectral_class),
        by_discovery_year=await _group_counts(session, Planet.discovery_year, limit=60),
        ranges=ranges,
        data_source="NASA Exoplanet Archive — Planetary Systems Composite Parameters",
        last_ingest=(
            {
                "source": last_run.source,
                "status": last_run.status,
                "planets": last_run.planets_written,
                "systems": last_run.stars_written,
                "at": last_run.created_at.isoformat() if last_run.created_at else None,
            }
            if last_run
            else None
        ),
    )

    await cache.set(key, response.model_dump(mode="json"), ttl=600)
    return response
