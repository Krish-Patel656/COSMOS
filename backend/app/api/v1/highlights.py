"""Curated highlight sections for the explorer landing page."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter

from app.api.deps import CacheDep, SessionDep
from app.core.cache import cache_key
from app.schemas.astronomy import HighlightSection, HighlightsResponse
from app.services import planet_query
from app.services.presentation import to_planet_card

router = APIRouter(prefix="/highlights", tags=["highlights"])


@dataclass(frozen=True)
class SectionSpec:
    key: str
    title: str
    description: str
    filters: dict[str, Any]


# Each section is a saved query over the same filter machinery the explorer uses,
# so a user can always click through to the full, editable filter set.
SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec(
        key="most-earth-like",
        title="Most Earth-like worlds",
        description=(
            "Ranked by the Earth Similarity Index, which compares radius, density, escape "
            "velocity and temperature against Earth's. High similarity does not imply "
            "habitability — it means the bulk physical properties resemble ours."
        ),
        filters={"sort": "esi", "order": "desc", "min_esi": 0.7, "include_solar_system": False},
    ),
    SectionSpec(
        key="potentially-habitable",
        title="Potentially habitable candidates",
        description=(
            "Planets inside the conservative habitable zone that are also small enough to be "
            "rocky. These are the worlds where liquid surface water is physically plausible "
            "given what we can measure."
        ),
        filters={
            "sort": "habitability",
            "order": "desc",
            "in_conservative_hz": True,
            "max_radius": 1.8,
            "include_solar_system": False,
        },
    ),
    SectionSpec(
        key="nearby",
        title="Nearest exoplanets",
        description=(
            "The closest known worlds to Earth. Proximity matters scientifically as well as "
            "romantically: nearby planets are the only ones whose atmospheres current and "
            "near-future telescopes have any hope of characterising."
        ),
        filters={
            "sort": "distance",
            "order": "asc",
            "max_distance_ly": 40,
            "include_solar_system": False,
        },
    ),
    SectionSpec(
        key="temperate",
        title="Temperate worlds",
        description=(
            "Planets whose equilibrium temperature sits in the range where water could be "
            "liquid under a plausible atmosphere, regardless of size."
        ),
        filters={
            "sort": "esi",
            "order": "desc",
            "min_temp": 200,
            "max_temp": 320,
            "include_solar_system": False,
        },
    ),
    SectionSpec(
        key="extremes",
        title="Hottest known worlds",
        description=(
            "Ultra-hot Jupiters whose daysides exceed the surface temperature of many stars. "
            "Hostile, but they are the easiest atmospheres to study, which is why we know so "
            "much about them."
        ),
        filters={
            "sort": "temperature",
            "order": "desc",
            "include_solar_system": False,
        },
    ),
    SectionSpec(
        key="recent",
        title="Recent discoveries",
        description=(
            "The newest confirmed planets in the archive, dominated by TESS and the ongoing "
            "radial-velocity surveys."
        ),
        filters={
            "sort": "discovery_year",
            "order": "desc",
            "include_solar_system": False,
            "has_habitability_score": True,
        },
    ),
    SectionSpec(
        key="solar-system",
        title="Our own Solar System",
        description=(
            "The reference set, scored by exactly the same engine. Earth sits at 100 by "
            "construction; Venus and Mars show how differently two nearly Earth-sized planets "
            "can turn out."
        ),
        filters={"sort": "habitability", "order": "desc", "q": None},
    ),
)


@router.get("", response_model=HighlightsResponse, summary="Curated planet collections")
async def highlights(
    session: SessionDep, cache: CacheDep, per_section: int = 8
) -> HighlightsResponse:
    """Six themed collections plus the Solar System, each a saved explorer query."""
    per_section = max(1, min(per_section, 24))
    key = cache_key("highlights", per_section=per_section)
    cached = await cache.get(key)
    if cached is not None:
        return HighlightsResponse.model_validate(cached)

    sections: list[HighlightSection] = []
    for spec in SECTIONS:
        overrides = dict(spec.filters)
        overrides["limit"] = per_section
        filters = planet_query.highlight_filters(**overrides)

        statement = planet_query.build_select(filters)
        if spec.key == "solar-system":
            # The one section defined by membership rather than by thresholds.
            from app.models import Planet

            statement = statement.where(Planet.is_solar_system.is_(True))

        rows = (await session.execute(statement)).scalars().all()
        sections.append(
            HighlightSection(
                key=spec.key,
                title=spec.title,
                description=spec.description,
                planets=[to_planet_card(p) for p in planet_query.unique_planets(rows)],
            )
        )

    response = HighlightsResponse(sections=sections)
    await cache.set(key, response.model_dump(mode="json"))
    return response
