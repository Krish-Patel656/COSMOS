"""Unified search across stars and planets."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import SessionDep
from app.models import Planet, Star
from app.schemas.astronomy import SearchHit, SearchResponse
from app.services.presentation import to_search_hit_planet, to_search_hit_star

router = APIRouter(prefix="/search", tags=["search"])


def _relevance(name: str, query: str, popularity: float | None) -> float:
    """Rank a match.

    Astronomical catalogues are adversarial for substring search: typing
    "TRAPPIST-1" matches eight planets and one star, while "Kepler-4" matches
    "Kepler-4 b", "Kepler-40 b", "Kepler-400 b" and so on. Exact and prefix
    matches are therefore weighted far above substring matches, shorter names win
    ties (so "Kepler-4 b" beats "Kepler-442 b" for the query "Kepler-4"), and a
    planet's habitability acts as a final, small tiebreaker so the interesting
    worlds surface first among otherwise equal matches.
    """
    lowered = name.lower()
    needle = query.lower()

    if lowered == needle:
        base = 1000.0
    elif lowered.startswith(needle):
        base = 700.0 - min(len(lowered) - len(needle), 60) * 2.0
    elif needle in lowered:
        base = 400.0 - min(lowered.index(needle), 40) * 2.0
    else:
        base = 100.0

    return base + (popularity or 0.0) / 1000.0


@router.get("", response_model=SearchResponse, summary="Search stars and planets")
async def search(
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, max_length=120, description="Name fragment")],
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
    kind: Annotated[str | None, Query(pattern="^(planet|star)$")] = None,
) -> SearchResponse:
    query = q.strip()
    pattern = f"%{query.lower()}%"
    # Over-fetch so that relevance ranking has a real candidate pool to sort,
    # rather than ranking whatever arbitrary rows the database returned first.
    pool = min(limit * 8, 300)

    hits: list[SearchHit] = []

    if kind != "star":
        statement = (
            select(Planet)
            .options(joinedload(Planet.star))
            .where(func.lower(Planet.name).like(pattern))
            .order_by(
                func.length(Planet.name).asc(),
                Planet.habitability_score.desc().nulls_last(),
            )
            .limit(pool)
        )
        for planet in (await session.execute(statement)).scalars().unique().all():
            hits.append(
                to_search_hit_planet(
                    planet, _relevance(planet.name, query, planet.habitability_score)
                )
            )

    if kind != "planet":
        statement = (
            select(Star)
            .where(
                or_(
                    func.lower(Star.name).like(pattern),
                    func.lower(Star.slug).like(pattern),
                )
            )
            .order_by(
                func.length(Star.name).asc(),
                Star.best_habitability_score.desc().nulls_last(),
            )
            .limit(pool)
        )
        for star in (await session.execute(statement)).scalars().all():
            # Nudge systems above their own planets for the same query so that
            # searching "TRAPPIST-1" offers the system first, which is the view a
            # user almost always wants.
            relevance = _relevance(star.name, query, star.best_habitability_score) + 25.0
            hits.append(to_search_hit_star(star, relevance))

    hits.sort(key=lambda hit: -hit.score)
    return SearchResponse(query=query, hits=hits[:limit])
