"""Side-by-side planet comparison."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import SessionDep
from app.models import Planet
from app.schemas.astronomy import ComparisonResponse
from app.services.presentation import comparison_notes, comparison_rows, to_planet_detail

router = APIRouter(prefix="/compare", tags=["compare"])

MAX_COMPARISON_SIZE = 4


@router.get("", response_model=ComparisonResponse, summary="Compare 2-4 planets")
async def compare(
    session: SessionDep,
    slugs: Annotated[
        list[str],
        Query(
            min_length=2,
            max_length=MAX_COMPARISON_SIZE,
            description="Planet slugs, e.g. slugs=earth&slugs=trappist-1-e",
        ),
    ],
) -> ComparisonResponse:
    """Build a property-by-property comparison table.

    Rows where no selected planet has a value are omitted rather than rendered as
    a line of dashes, and each row declares which direction is "better" so the UI
    can highlight a winner without duplicating that judgement in the client.
    """
    wanted = [slug.strip().lower() for slug in slugs if slug.strip()]
    if len(set(wanted)) < 2:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "provide at least two distinct planet slugs"
        )

    statement = (
        select(Planet).options(joinedload(Planet.star)).where(Planet.slug.in_(set(wanted)))
    )
    found = (await session.execute(statement)).scalars().unique().all()
    by_slug = {planet.slug: planet for planet in found}

    missing = [slug for slug in wanted if slug not in by_slug]
    if missing:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"unknown planet slug(s): {', '.join(missing)}"
        )

    # Preserve the caller's ordering so the table columns match the UI's chips.
    ordered = [by_slug[slug] for slug in dict.fromkeys(wanted)]

    return ComparisonResponse(
        planets=[to_planet_detail(planet) for planet in ordered],
        rows=comparison_rows(ordered),
        notes=comparison_notes(ordered),
    )
