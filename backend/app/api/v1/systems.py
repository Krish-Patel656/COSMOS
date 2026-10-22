"""Star and planetary-system endpoints, including the 3D stellar map feed."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, select

from app.api.deps import CacheDep, SessionDep
from app.core.cache import cache_key
from app.models import Star
from app.schemas.astronomy import (
    StarDetail,
    StarMapPoint,
    StarPage,
    StarSummary,
    SystemDetail,
)
from app.services.presentation import to_planet_summary

router = APIRouter(tags=["systems"])


@router.get("/stars/map", response_model=list[StarMapPoint], summary="Stellar map point cloud")
async def stellar_map(
    session: SessionDep,
    cache: CacheDep,
    max_distance_ly: Annotated[float, Query(ge=1, le=20000)] = 350.0,
    limit: Annotated[int, Query(ge=10, le=6000)] = 1200,
    require_planets: bool = True,
    sort_by: Annotated[Literal["distance", "habitability"], Query()] = "distance",
) -> list[StarMapPoint]:
    """Minimal records for plotting stars in 3D.

    Cartesian coordinates are precomputed at ingest, so this is a plain indexed
    read. The payload is deliberately trimmed to the fields the renderer needs:
    sending full star records would multiply the response size roughly twentyfold
    for a view that only draws a point and a label.

    ``max_distance_ly`` defaults to 350 ly, which covers the overwhelming
    majority of systems with well-characterised planets while keeping the cloud
    legible.
    """
    key = cache_key(
        "stellar-map",
        max_distance_ly=max_distance_ly,
        limit=limit,
        require_planets=require_planets,
        sort_by=sort_by,
    )
    cached = await cache.get(key)
    if cached is not None:
        return [StarMapPoint.model_validate(item) for item in cached]

    conditions = [
        Star.x_pc.is_not(None),
        Star.distance_ly.is_not(None),
        Star.distance_ly <= max_distance_ly,
    ]
    if require_planets:
        conditions.append(Star.planet_count > 0)

    order = (
        Star.best_habitability_score.desc().nulls_last()
        if sort_by == "habitability"
        else Star.distance_ly.asc()
    )

    statement = select(Star).where(and_(*conditions)).order_by(order).limit(limit)
    stars = (await session.execute(statement)).scalars().all()

    # The Sun sits at the origin and anchors the map, so include it even when a
    # distance filter or ordering would otherwise have excluded it.
    if not any(star.is_solar_system for star in stars):
        sun = (
            await session.execute(select(Star).where(Star.is_solar_system.is_(True)))
        ).scalars().first()
        if sun is not None:
            stars = [sun, *stars]

    points = [StarMapPoint.model_validate(star) for star in stars]
    await cache.set(key, [point.model_dump() for point in points])
    return points


@router.get("/systems", response_model=StarPage, summary="Browse planetary systems")
async def list_systems(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=120)] = None,
    min_planets: Annotated[int, Query(ge=0, le=20)] = 0,
    max_distance_ly: Annotated[float | None, Query(ge=0)] = None,
    spectral_class: Annotated[list[str] | None, Query()] = None,
    sort: Annotated[
        Literal["distance", "planet_count", "habitability", "name"], Query()
    ] = "distance",
    order: Annotated[Literal["asc", "desc"], Query()] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> StarPage:
    conditions = []
    if q:
        conditions.append(func.lower(Star.name).like(f"%{q.strip().lower()}%"))
    if min_planets:
        conditions.append(Star.planet_count >= min_planets)
    if max_distance_ly is not None:
        conditions.append(Star.distance_ly <= max_distance_ly)
    if spectral_class:
        conditions.append(Star.spectral_class.in_([c.upper()[:1] for c in spectral_class]))

    columns = {
        "distance": Star.distance_ly,
        "planet_count": Star.planet_count,
        "habitability": Star.best_habitability_score,
        "name": Star.name,
    }
    column = columns[sort]
    direction = column.desc() if order == "desc" else column.asc()

    where = and_(*conditions) if conditions else None
    count_statement = select(func.count(Star.id))
    statement = select(Star)
    if where is not None:
        count_statement = count_statement.where(where)
        statement = statement.where(where)

    total = await session.scalar(count_statement) or 0
    statement = statement.order_by(direction.nulls_last(), Star.slug.asc()).limit(limit).offset(
        offset
    )
    stars = (await session.execute(statement)).scalars().all()

    return StarPage(
        items=[StarSummary.model_validate(star) for star in stars],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(stars) < total,
    )


@router.get(
    "/systems/{slug}",
    response_model=SystemDetail,
    summary="One system with all its planets",
)
async def get_system(session: SessionDep, slug: str) -> SystemDetail:
    """The payload the 3D system scene consumes: the star plus every planet,
    ordered outward from the star."""
    star = (
        await session.execute(select(Star).where(Star.slug == slug.lower()))
    ).scalars().first()
    if star is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no system with slug {slug!r}")

    detail = SystemDetail.model_validate(
        {
            **{
                field: getattr(star, field)
                for field in StarDetail.model_fields
                if hasattr(star, field)
            },
            "planets": [to_planet_summary(planet) for planet in star.planets],
        }
    )
    return detail


@router.get("/stars/{slug}", response_model=StarDetail, summary="One star")
async def get_star(session: SessionDep, slug: str) -> StarDetail:
    star = (
        await session.execute(select(Star).where(Star.slug == slug.lower()))
    ).scalars().first()
    if star is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no star with slug {slug!r}")
    return StarDetail.model_validate(star)
