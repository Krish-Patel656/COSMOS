"""Planet endpoints: the Exoplanet Explorer list, detail and neighbours."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import SessionDep
from app.models import Planet, Star
from app.schemas.astronomy import PlanetDetail, PlanetPage, PlanetWithStar
from app.services import planet_query
from app.services.planet_query import PlanetFilters
from app.services.presentation import to_planet_card, to_planet_detail

router = APIRouter(prefix="/planets", tags=["planets"])

FiltersDep = Annotated[PlanetFilters, Query()]


@router.get("", response_model=PlanetPage, summary="Browse and filter exoplanets")
async def list_planets(session: SessionDep, filters: FiltersDep) -> PlanetPage:
    """Filterable, sortable, paginated catalogue of every known planet.

    Unknown values always sort last, so "coldest first" surfaces the coldest
    *measured* planets rather than the ones with no measurement.
    """
    total = await session.scalar(planet_query.build_count(filters)) or 0
    rows = (await session.execute(planet_query.build_select(filters))).scalars().all()
    planets = planet_query.unique_planets(rows)

    return PlanetPage(
        items=[to_planet_card(planet) for planet in planets],
        total=total,
        limit=filters.limit,
        offset=filters.offset,
        has_more=filters.offset + len(planets) < total,
    )


@router.get(
    "/random",
    response_model=PlanetWithStar,
    summary="A random well-characterised planet",
)
async def random_planet(session: SessionDep) -> PlanetWithStar:
    """Used by the "surprise me" control.

    Restricted to planets with a habitability score, because landing a first-time
    visitor on a microlensing detection with five unknown properties is a poor
    introduction to the catalogue.
    """
    statement = (
        select(Planet)
        .options(joinedload(Planet.star))
        .where(Planet.habitability_score.is_not(None), Planet.radius_earth.is_not(None))
        .order_by(func.random())
        .limit(1)
    )
    planet = (await session.execute(statement)).scalars().first()
    if planet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "catalogue is empty")
    return to_planet_card(planet)


@router.get("/{slug}", response_model=PlanetDetail, summary="Full planet record")
async def get_planet(session: SessionDep, slug: str) -> PlanetDetail:
    """Everything known about one planet, including both score breakdowns."""
    statement = (
        select(Planet).options(joinedload(Planet.star)).where(Planet.slug == slug.lower())
    )
    planet = (await session.execute(statement)).scalars().first()
    if planet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no planet with slug {slug!r}")
    return to_planet_detail(planet)


@router.get(
    "/{slug}/similar",
    response_model=list[PlanetWithStar],
    summary="Planets most similar to this one",
)
async def similar_planets(
    session: SessionDep,
    slug: str,
    limit: Annotated[int, Query(ge=1, le=24)] = 6,
) -> list[PlanetWithStar]:
    """Nearest neighbours in radius, temperature and Earth-similarity space."""
    planet = (
        await session.execute(
            select(Planet).options(joinedload(Planet.star)).where(Planet.slug == slug.lower())
        )
    ).scalars().first()
    if planet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no planet with slug {slug!r}")

    rows = (
        await session.execute(planet_query.similar_planets_select(planet, limit))
    ).scalars().all()
    return [to_planet_card(p) for p in planet_query.unique_planets(rows)]


@router.get(
    "/{slug}/system",
    response_model=list[PlanetWithStar],
    summary="Sibling planets in the same system",
)
async def planet_siblings(session: SessionDep, slug: str) -> list[PlanetWithStar]:
    planet = (
        await session.execute(select(Planet).where(Planet.slug == slug.lower()))
    ).scalars().first()
    if planet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no planet with slug {slug!r}")

    statement = (
        select(Planet)
        .options(joinedload(Planet.star))
        .join(Star, Planet.star_id == Star.id)
        .where(Planet.star_id == planet.star_id)
        .order_by(Planet.semi_major_axis_au.asc().nulls_last())
    )
    rows = (await session.execute(statement)).scalars().all()
    return [to_planet_card(p) for p in planet_query.unique_planets(rows)]
